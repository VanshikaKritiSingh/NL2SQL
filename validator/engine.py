"""validator/engine.py — 6-Layer Static SQL AST Validation Engine

Pipeline Architecture:
    PARSE → POLICY → SCHEMA → SEMANTIC → QUERY_AP → SCHEMA_AP

- Deterministic AST analysis via sqlglot.
- Pure in-memory execution; zero network or live DB calls.
- Short-circuits on the first layer encountering an ERROR.
- Accumulates actionable diagnostic issues with fix hints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
import sqlglot
import sqlglot.expressions as exp

from .contracts import (
    Issue,
    IssueCode,
    Layer,
    Severity,
    StatementType,
    Status,
    ValidationResult,
)
from .interfaces import AuditLogger, SchemaProvider
from .rules import DEFAULT_RULES, RuleRegistry


def issue(code: str, layer: Layer, severity: Severity, message: str, fix_hint: str = "", applies_to: Tuple[str, ...] = ()) -> Issue:
    return Issue(code=code, layer=layer, severity=severity, message=message, fix_hint=fix_hint, applies_to=applies_to)


# ------------------------------------------------------------------
# Layer 1 — PARSE
# ------------------------------------------------------------------

def validate_parse(sql: str, dialect: str = "postgres") -> Tuple[List[Issue], Optional[exp.Expression]]:
    """Parse the SQL; reject unparseable or multi-statement input."""
    issues: List[Issue] = []
    stripped = sql.strip()

    if not stripped or stripped == ";":
        issues.append(issue(
            IssueCode.PARSE_02, Layer.PARSE, Severity.ERROR,
            "Empty or whitespace-only SQL statement",
            "Provide a valid SQL query string"
        ))
        return issues, None

    # Multi-statement check
    statements = [s.strip() for s in stripped.split(";") if s.strip()]
    if len(statements) > 1:
        issues.append(issue(
            IssueCode.PARSE_01, Layer.PARSE, Severity.ERROR,
            "Multiple statements detected; only single-statement SQL is permitted",
            "Execute one SQL statement at a time"
        ))
        return issues, None

    try:
        parsed = sqlglot.parse_one(stripped, read=dialect)
    except Exception as exc:
        issues.append(issue(
            IssueCode.PARSE_02, Layer.PARSE, Severity.ERROR,
            f"SQL syntax error for dialect '{dialect}': {str(exc)}",
            "Check query grammar against SQL dialect standard"
        ))
        return issues, None

    return issues, parsed


# ------------------------------------------------------------------
# Layer 2 — POLICY
# ------------------------------------------------------------------

def validate_policy(sql: str, parsed: exp.Expression) -> Tuple[List[Issue], StatementType]:
    """Statement-type classification, explicit allowlist, and policy guardrails."""
    issues: List[Issue] = []
    node = parsed

    if isinstance(node, exp.Command):
        stmt_keyword = node.name.upper()
    elif isinstance(node, exp.Expression):
        stmt_keyword = node.__class__.__name__.upper()
    else:
        stmt_keyword = "UNKNOWN"

    ALLOWED: Dict[str, StatementType] = {
        "SELECT": StatementType.READ,
        "INSERT": StatementType.WRITE,
        "UPDATE": StatementType.WRITE,
        "DELETE": StatementType.WRITE,
        "CREATE": StatementType.DDL,
        "ALTER": StatementType.DDL,
        "DROP": StatementType.DDL,
        "TRUNCATE": StatementType.DDL,
        "GRANT": StatementType.DDL,
        "REVOKE": StatementType.DDL,
    }

    if stmt_keyword not in ALLOWED:
        issues.append(issue(
            IssueCode.POLICY_01, Layer.POLICY, Severity.ERROR,
            f"Statement type '{stmt_keyword}' is unrecognized or not in the allowlist",
            "Permitted statement types are SELECT, INSERT, UPDATE, DELETE, and standard DDL",
            ("UNKNOWN",)
        ))
        return issues, StatementType.UNKNOWN

    stmt_type = ALLOWED[stmt_keyword]
    upper_sql = sql.upper()

    # Denylist checks
    if "DROP DATABASE" in upper_sql or "DROP SCHEMA" in upper_sql:
        issues.append(issue(
            IssueCode.POLICY_02, Layer.POLICY, Severity.ERROR,
            "DROP DATABASE / DROP SCHEMA is prohibited by safety policy",
            "Target specific tables or use sandbox test environment",
            (stmt_type.value,)
        ))

    if "TRUNCATE" in upper_sql:
        issues.append(issue(
            IssueCode.POLICY_02, Layer.POLICY, Severity.ERROR,
            "TRUNCATE is prohibited; use bounded DELETE with WHERE clause",
            "Rewrite using DELETE FROM <table> WHERE <conditions>",
            (stmt_type.value,)
        ))

    if "GRANT" in upper_sql or "REVOKE" in upper_sql:
        issues.append(issue(
            IssueCode.POLICY_03, Layer.POLICY, Severity.ERROR,
            "GRANT / REVOKE security operations are prohibited",
            "Manage permissions through IAM / database administrator interface",
            (stmt_type.value,)
        ))

    if "COPY" in upper_sql and "PROGRAM" in upper_sql:
        issues.append(issue(
            IssueCode.POLICY_04, Layer.POLICY, Severity.ERROR,
            "COPY ... PROGRAM can execute arbitrary shell commands and is blocked",
            "Use standard client-side data streaming or file import",
            (stmt_type.value,)
        ))

    # Dangerous system functions
    for func_node in parsed.find_all(exp.Func):
        fname = func_node.name.lower() if hasattr(func_node, "name") else ""
        if fname in ("pg_sleep", "pg_read_file", "pg_write_file", "load_file", "sys_eval", "xp_cmdshell"):
            issues.append(issue(
                IssueCode.POLICY_06, Layer.POLICY, Severity.ERROR,
                f"Call to hazardous system function '{fname}' is blocked",
                "Remove administrative or execution function calls",
                (stmt_type.value,)
            ))

    # UPDATE / DELETE without WHERE
    if stmt_keyword in ("UPDATE", "DELETE"):
        if parsed.args.get("where") is None:
            issues.append(issue(
                IssueCode.POLICY_05, Layer.POLICY, Severity.ERROR,
                f"{stmt_keyword} without WHERE clause affects all rows in table",
                "Add an explicit WHERE clause to restrict affected scope",
                (stmt_type.value,)
            ))

    return issues, stmt_type


# ------------------------------------------------------------------
# Layer 3 — SCHEMA
# ------------------------------------------------------------------

def validate_schema(parsed: exp.Expression, schema: Optional[SchemaProvider]) -> List[Issue]:
    """Validates tables, columns, and aliases against SchemaProvider."""
    issues: List[Issue] = []
    if schema is None:
        return issues

    known_tables = set(t.lower() for t in schema.get_tables())
    tables_in_query: Dict[str, str] = {}  # alias_or_name -> table_name

    # Check table existence
    for table_node in parsed.find_all(exp.Table):
        t_name = table_node.name.lower()
        if t_name and t_name not in known_tables:
            issues.append(issue(
                IssueCode.SCHEMA_01, Layer.SCHEMA, Severity.ERROR,
                f"Table '{t_name}' does not exist in schema catalog",
                f"Available tables: {', '.join(sorted(known_tables)[:8])}",
                ("READ", "WRITE")
            ))
        else:
            alias = table_node.alias_or_name.lower()
            tables_in_query[alias] = t_name

    # Check column existence
    all_known_cols: Dict[str, Set[str]] = {}
    for alias, t_name in tables_in_query.items():
        if t_name in known_tables:
            cols = {col_name.lower() for col_name, _ in schema.get_columns(t_name)}
            all_known_cols[alias] = cols
            all_known_cols[t_name] = cols

    for col_node in parsed.find_all(exp.Column):
        c_name = col_node.name.lower()
        if c_name == "*":
            continue
        c_table = col_node.table.lower() if col_node.table else None

        if c_table:
            if c_table in all_known_cols:
                if c_name not in all_known_cols[c_table]:
                    issues.append(issue(
                        IssueCode.SCHEMA_02, Layer.SCHEMA, Severity.ERROR,
                        f"Column '{c_name}' does not exist on table/alias '{c_table}'",
                        f"Available columns: {', '.join(sorted(all_known_cols[c_table])[:6])}",
                        ("READ", "WRITE")
                    ))
            else:
                issues.append(issue(
                    IssueCode.SCHEMA_04, Layer.SCHEMA, Severity.ERROR,
                    f"Unresolvable table alias '{c_table}' for column '{c_name}'",
                    "Ensure table alias is defined in FROM or JOIN clause",
                    ("READ", "WRITE")
                ))
        else:
            # Unqualified column
            if len(tables_in_query) == 1:
                single_t = list(tables_in_query.values())[0]
                if single_t in all_known_cols and c_name not in all_known_cols[single_t]:
                    issues.append(issue(
                        IssueCode.SCHEMA_02, Layer.SCHEMA, Severity.ERROR,
                        f"Column '{c_name}' does not exist on table '{single_t}'",
                        f"Available columns: {', '.join(sorted(all_known_cols[single_t])[:6])}",
                        ("READ", "WRITE")
                    ))
            elif len(tables_in_query) > 1:
                matching_tables = [t for t, cols in all_known_cols.items() if c_name in cols]
                if len(matching_tables) == 0:
                    issues.append(issue(
                        IssueCode.SCHEMA_02, Layer.SCHEMA, Severity.ERROR,
                        f"Column '{c_name}' does not exist in any joined tables ({', '.join(tables_in_query.values())})",
                        "Verify column name against joined table schemas",
                        ("READ", "WRITE")
                    ))
                elif len(matching_tables) > 1:
                    issues.append(issue(
                        IssueCode.SCHEMA_03, Layer.SCHEMA, Severity.ERROR,
                        f"Ambiguous column '{c_name}' present in multiple joined tables",
                        f"Prefix column with table name or alias: {matching_tables[0]}.{c_name}",
                        ("READ", "WRITE")
                    ))

    return issues


# ------------------------------------------------------------------
# Layer 4 — SEMANTIC
# ------------------------------------------------------------------

def validate_semantic(parsed: exp.Expression) -> List[Issue]:
    """Validates SQL semantic integrity (GROUP BY, aggregates in WHERE, INSERT counts)."""
    issues: List[Issue] = []

    if isinstance(parsed, exp.Select):
        # 1. Check for aggregate functions in WHERE clause
        where_clause = parsed.args.get("where")
        if where_clause:
            for agg_node in where_clause.find_all(exp.AggFunc):
                issues.append(issue(
                    IssueCode.SEM_02, Layer.SEMANTIC, Severity.ERROR,
                    f"Aggregate function '{agg_node.sql()}' cannot be used in WHERE clause",
                    "Move aggregate filter condition to HAVING clause",
                    ("READ",)
                ))

        # 2. Check GROUP BY consistency
        group_clause = parsed.args.get("group")
        if group_clause:
            grouped_cols = {g.name.lower() for g in group_clause.find_all(exp.Column)}
            for s_exp in parsed.selects:
                inner = s_exp.this if isinstance(s_exp, exp.Alias) else s_exp
                if isinstance(inner, exp.Column):
                    if inner.name.lower() not in grouped_cols:
                        issues.append(issue(
                            IssueCode.SEM_01, Layer.SEMANTIC, Severity.ERROR,
                            f"Column '{inner.name}' must appear in the GROUP BY clause or be used in an aggregate function",
                            f"Add '{inner.name}' to GROUP BY",
                            ("READ",)
                        ))

    elif isinstance(parsed, exp.Insert):
        # 3. Check INSERT column and value counts
        cols = parsed.this.expressions if hasattr(parsed.this, "expressions") else []
        values_node = parsed.expression
        if isinstance(values_node, exp.Values):
            for row in values_node.expressions:
                if isinstance(row, exp.Tuple) and cols:
                    if len(row.expressions) != len(cols):
                        issues.append(issue(
                            IssueCode.SEM_03, Layer.SEMANTIC, Severity.ERROR,
                            f"INSERT has {len(cols)} columns specified but {len(row.expressions)} values provided",
                            "Match the number of target columns to provided values",
                            ("WRITE",)
                        ))

    return issues


# ------------------------------------------------------------------
# Layer 5 — QUERY ANTI-PATTERNS (Warnings & Critical Performance Guards)
# ------------------------------------------------------------------

def validate_query_anti_patterns(parsed: exp.Expression) -> List[Issue]:
    """Detects query performance anti-patterns and Cartesian products."""
    issues: List[Issue] = []

    if isinstance(parsed, exp.Select):
        # 1. SELECT * in production
        for s_exp in parsed.selects:
            if isinstance(s_exp, exp.Star):
                issues.append(issue(
                    IssueCode.QUERY_AP_01, Layer.QUERY_AP, Severity.WARNING,
                    "SELECT * retrieves all columns; explicitly name required columns for performance",
                    "Replace '*' with explicit column list",
                    ("READ",)
                ))

        # 2. Cartesian product / JOIN without ON
        joins = parsed.args.get("joins", [])
        for join in joins:
            if join.kind == "CROSS":
                issues.append(issue(
                    IssueCode.QUERY_AP_02, Layer.QUERY_AP, Severity.ERROR,
                    "Explicit CROSS JOIN detected; risks generating huge Cartesian products",
                    "Add an ON condition or verify intentional Cartesian product",
                    ("READ",)
                ))
            elif not join.args.get("on") and not join.args.get("using") and join.kind != "NATURAL":
                issues.append(issue(
                    IssueCode.QUERY_AP_02, Layer.QUERY_AP, Severity.ERROR,
                    f"JOIN on table '{join.this.name}' is missing an ON join condition (Cartesian product)",
                    f"Add 'ON {join.this.name}.<foreign_key> = <primary_key>'",
                    ("READ",)
                ))

        # 3. Leading-wildcard LIKE pattern
        for like_node in parsed.find_all(exp.Like):
            pat = like_node.right.sql().strip("'\"")
            if pat.startswith("%") or pat.startswith("_"):
                issues.append(issue(
                    IssueCode.QUERY_AP_03, Layer.QUERY_AP, Severity.WARNING,
                    f"Leading-wildcard LIKE '{pat}' disables B-tree index scans",
                    "Use prefix search 'text%' or full-text search index if available",
                    ("READ",)
                ))

        # 4. ORDER BY without LIMIT
        if parsed.args.get("order") and not parsed.args.get("limit"):
            issues.append(issue(
                IssueCode.QUERY_AP_06, Layer.QUERY_AP, Severity.WARNING,
                "ORDER BY without LIMIT requires a full table sort in memory/disk",
                "Add a LIMIT clause to bound sorting overhead",
                ("READ",)
            ))

        # 5. Deep OFFSET
        offset_node = parsed.args.get("offset")
        if offset_node:
            try:
                offset_val = int(offset_node.expression.sql())
                if offset_val >= 10000:
                    issues.append(issue(
                        IssueCode.QUERY_AP_07, Layer.QUERY_AP, Severity.WARNING,
                        f"Deep OFFSET ({offset_val}) scans and discards many rows",
                        "Use keyset pagination (cursor-based WHERE id > last_seen)",
                        ("READ",)
                    ))
            except ValueError:
                pass

    return issues


# ------------------------------------------------------------------
# Layer 6 — SCHEMA ANTI-PATTERNS (DDL Checks)
# ------------------------------------------------------------------

def validate_schema_anti_patterns(parsed: exp.Expression) -> List[Issue]:
    """Validates DDL statements for schema design best practices."""
    issues: List[Issue] = []

    if isinstance(parsed, exp.Create):
        schema_def = parsed.this
        if isinstance(schema_def, exp.Schema):
            col_defs = schema_def.expressions
            has_pk = any(
                any(isinstance(c, exp.PrimaryKeyColumnConstraint) for c in col.find_all(exp.PrimaryKeyColumnConstraint))
                for col in col_defs if isinstance(col, exp.ColumnDef)
            )
            # Check table constraints
            for constraint in schema_def.find_all(exp.PrimaryKey):
                has_pk = True

            if not has_pk:
                issues.append(issue(
                    IssueCode.SCHEMA_AP_01, Layer.SCHEMA_AP, Severity.WARNING,
                    f"Table '{schema_def.name}' created without a PRIMARY KEY constraint",
                    "Add PRIMARY KEY constraint to ensure entity integrity",
                    ("DDL",)
                ))

    return issues


# ------------------------------------------------------------------
# Unified Engine Pipeline Entrypoint
# ------------------------------------------------------------------

def run_validation(
    sql: str,
    dialect: str = "postgres",
    schema: Optional[SchemaProvider] = None,
    rules: Optional[RuleRegistry] = None,
    audit_logger: Optional[AuditLogger] = None,
) -> ValidationResult:
    """
    Executes the full 6-layer validation pipeline:
    PARSE → POLICY → SCHEMA → SEMANTIC → QUERY_AP → SCHEMA_AP
    """
    registry = rules or RuleRegistry()
    all_issues: List[Issue] = []

    # 1. PARSE
    parse_issues, parsed = validate_parse(sql, dialect=dialect)
    all_issues.extend(parse_issues)
    if any(i.severity == Severity.ERROR for i in parse_issues) or parsed is None:
        result = ValidationResult(
            status=Status.INVALID,
            statement_type=StatementType.UNKNOWN,
            normalized_sql=None,
            issues=tuple(all_issues)
        )
        if audit_logger:
            audit_logger.log_validation(sql, result)
        return result

    # 2. POLICY
    policy_issues, stmt_type = validate_policy(sql, parsed)
    all_issues.extend(policy_issues)
    if any(i.severity == Severity.ERROR for i in policy_issues):
        result = ValidationResult(
            status=Status.INVALID,
            statement_type=stmt_type,
            normalized_sql=parsed.sql(dialect=dialect),
            issues=tuple(all_issues)
        )
        if audit_logger:
            audit_logger.log_validation(sql, result)
        return result

    # 3. SCHEMA
    schema_issues = validate_schema(parsed, schema)
    all_issues.extend(schema_issues)
    if any(i.severity == Severity.ERROR for i in schema_issues):
        result = ValidationResult(
            status=Status.INVALID,
            statement_type=stmt_type,
            normalized_sql=parsed.sql(dialect=dialect),
            issues=tuple(all_issues)
        )
        if audit_logger:
            audit_logger.log_validation(sql, result)
        return result

    # 4. SEMANTIC
    semantic_issues = validate_semantic(parsed)
    all_issues.extend(semantic_issues)
    if any(i.severity == Severity.ERROR for i in semantic_issues):
        result = ValidationResult(
            status=Status.INVALID,
            statement_type=stmt_type,
            normalized_sql=parsed.sql(dialect=dialect),
            issues=tuple(all_issues)
        )
        if audit_logger:
            audit_logger.log_validation(sql, result)
        return result

    # 5. QUERY_AP
    query_ap_issues = validate_query_anti_patterns(parsed)
    all_issues.extend(query_ap_issues)
    if any(i.severity == Severity.ERROR for i in query_ap_issues):
        result = ValidationResult(
            status=Status.INVALID,
            statement_type=stmt_type,
            normalized_sql=parsed.sql(dialect=dialect),
            issues=tuple(all_issues)
        )
        if audit_logger:
            audit_logger.log_validation(sql, result)
        return result

    # 6. SCHEMA_AP
    schema_ap_issues = validate_schema_anti_patterns(parsed)
    all_issues.extend(schema_ap_issues)

    # Filter by enabled rules in registry
    filtered_issues = [i for i in all_issues if registry.is_enabled(i.code)]
    has_errors = any(i.severity == Severity.ERROR for i in filtered_issues)
    has_warnings = any(i.severity == Severity.WARNING for i in filtered_issues)

    if has_errors:
        status = Status.INVALID
    elif has_warnings:
        status = Status.VALID_WITH_WARNINGS
    else:
        status = Status.VALID

    # Extract tables and columns touched
    tables_touched = frozenset(t.name.lower() for t in parsed.find_all(exp.Table) if t.name)
    columns_touched = frozenset(c.name.lower() for c in parsed.find_all(exp.Column) if c.name and c.name != "*")

    result = ValidationResult(
        status=status,
        statement_type=stmt_type,
        normalized_sql=parsed.sql(dialect=dialect),
        tables_touched=tables_touched,
        columns_touched=columns_touched,
        issues=tuple(filtered_issues)
    )

    if audit_logger:
        audit_logger.log_validation(sql, result)

    return result
