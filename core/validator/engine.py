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
import re
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


def createValidationIssue(code: str, layer: Layer, severity: Severity, message: str, fix_hint: str = "", applies_to: Tuple[str, ...] = ()) -> Issue:
    return Issue(code=code, layer=layer, severity=severity, message=message, fix_hint=fix_hint, applies_to=applies_to)


issue = createValidationIssue


# ------------------------------------------------------------------
# Layer 1 — PARSE
# ------------------------------------------------------------------

def executeParseLayerValidation(sql: str, dialect: str = "postgres") -> Tuple[List[Issue], Optional[exp.Expression]]:
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

    # Multi-statement check — use quote/comment-aware splitter instead of naive split(";")
    try:
        from core.sanitizer import split_sql_script
        statements = split_sql_script(stripped, dialect=dialect)
    except Exception:
        # Fallback to naive split only if the robust splitter is unavailable
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

def executePolicyLayerValidation(sql: str, parsed: exp.Expression) -> Tuple[List[Issue], StatementType]:
    """Statement-type classification, explicit allowlist, and policy guardrails."""
    issues: List[Issue] = []
    node = parsed

    if isinstance(node, exp.Command):
        stmt_keyword = node.name.upper().split()[0] if node.name else "COMMAND"
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
        "TRUNCATETABLE": StatementType.DDL,
        "GRANT": StatementType.DDL,
        "REVOKE": StatementType.DDL,
        # Introspection & Metadata discovery
        "SHOW": StatementType.READ,
        "DESCRIBE": StatementType.READ,
        "DESC": StatementType.READ,
        "EXPLAIN": StatementType.READ,
        "PRAGMA": StatementType.READ,
        # Session context
        "USE": StatementType.DDL,
        "SET": StatementType.DDL,
    }

    if stmt_keyword not in ALLOWED:
        issues.append(issue(
            IssueCode.POLICY_01, Layer.POLICY, Severity.ERROR,
            f"Statement type '{stmt_keyword}' is unrecognized or not in the allowlist",
            "Permitted statement types are SELECT, INSERT, UPDATE, DELETE, SHOW, DESCRIBE, EXPLAIN, and standard DDL",
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

    if stmt_keyword in ("TRUNCATE", "TRUNCATETABLE") or re.search(r"\bTRUNCATE\b", upper_sql):
        issues.append(issue(
            IssueCode.POLICY_02, Layer.POLICY, Severity.ERROR,
            "TRUNCATE is prohibited; use bounded DELETE with WHERE clause",
            "Rewrite using DELETE FROM <table> WHERE <conditions>",
            (stmt_type.value,)
        ))

    if stmt_keyword in ("GRANT", "REVOKE") or re.search(r"^\s*(GRANT|REVOKE)\b", upper_sql):
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

def executeSchemaLayerValidation(parsed: exp.Expression, schema: Optional[SchemaProvider]) -> List[Issue]:
    """Validates tables, columns, and aliases against SchemaProvider."""
    issues: List[Issue] = []
    if schema is None:
        return issues

    # USE statement switches database context; its identifier is a database name, not a table
    if isinstance(parsed, exp.Use):
        return issues

    known_tables = set(t.lower() for t in schema.get_tables())
    tables_in_query: Dict[str, str] = {}  # alias_or_name -> table_name

    # Collect CTE names (WITH clauses) so temporary CTE aliases don't trigger SCHEMA_01
    cte_names = set()
    for cte in parsed.find_all(exp.CTE):
        c_alias = (cte.alias or getattr(cte, "name", "")).lower()
        if c_alias:
            cte_names.add(c_alias)

    # Check table existence
    is_create_table = isinstance(parsed, exp.Create)
    for table_node in parsed.find_all(exp.Table):
        t_name = table_node.name.lower()
        if is_create_table or t_name in cte_names:
            alias = table_node.alias_or_name.lower()
            tables_in_query[alias] = t_name
            continue
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
    # FIX-07: Deduplicate by physical table identity to avoid false SCHEMA_03
    # on aliased JOINs. Track which physical table each alias maps to so that
    # aliases and table names resolving to the same physical table are not
    # counted as separate tables when checking for ambiguous columns.
    all_known_cols: Dict[str, Set[str]] = {}
    alias_to_physical: Dict[str, str] = {}  # alias_or_name -> physical table name
    for alias, t_name in tables_in_query.items():
        if t_name in known_tables:
            cols = {col_name.lower() for col_name, _ in schema.get_columns(t_name)}
            all_known_cols[alias] = cols
            all_known_cols[t_name] = cols
            alias_to_physical[alias] = t_name
            alias_to_physical[t_name] = t_name

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
                # FIX-07: Deduplicate by physical table to avoid false positives
                # when alias and table name both point to the same physical table
                matching_physical = set()
                for t in matching_tables:
                    phys = alias_to_physical.get(t, t)
                    matching_physical.add(phys)
                if len(matching_physical) == 0:
                    issues.append(issue(
                        IssueCode.SCHEMA_02, Layer.SCHEMA, Severity.ERROR,
                        f"Column '{c_name}' does not exist in any joined tables ({', '.join(tables_in_query.values())})",
                        "Verify column name against joined table schemas",
                        ("READ", "WRITE")
                    ))
                elif len(matching_physical) > 1:
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

def executeSemanticLayerValidation(parsed: exp.Expression) -> List[Issue]:
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

def executeQueryAntiPatternValidation(parsed: exp.Expression) -> List[Issue]:
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

        # 6. Function wrapping indexed column in WHERE (QUERY_AP_04)
        where_clause = parsed.args.get("where")
        if where_clause:
            _SARGABLE_BREAKING_FUNCS = {
                "upper", "lower", "trim", "ltrim", "rtrim", "coalesce",
                "cast", "convert", "substring", "substr", "left", "right",
                "replace", "concat", "date", "year", "month", "day",
                "extract", "to_char", "to_date", "abs", "round", "ceil",
                "floor", "length", "len", "char_length",
            }
            for func_node in where_clause.find_all(exp.Func):
                fname = (getattr(func_node, "name", None) or func_node.__class__.__name__).lower()
                if fname in _SARGABLE_BREAKING_FUNCS:
                    has_col_arg = any(
                        isinstance(a, exp.Column)
                        for a in func_node.args.values()
                        if isinstance(a, exp.Expression)
                    )
                    if has_col_arg:
                        issues.append(issue(
                            IssueCode.QUERY_AP_04, Layer.QUERY_AP, Severity.WARNING,
                            f"Function '{fname}()' wrapping column in WHERE clause prevents index scan",
                            "Rewrite predicate as sargable expression (apply function to value, not column)",
                            ("READ", "WRITE")
                        ))
                        break

        # 7. NOT IN with nullable subquery (QUERY_AP_05)
        for not_node in parsed.find_all(exp.Not):
            inner = not_node.this
            if isinstance(inner, exp.In):
                for child in inner.args.values():
                    if isinstance(child, exp.Expression) and child.find(exp.Select):
                        issues.append(issue(
                            IssueCode.QUERY_AP_05, Layer.QUERY_AP, Severity.WARNING,
                            "NOT IN with subquery risks returning empty set if subquery column is nullable",
                            "Use NOT EXISTS or ensure subquery columns are NOT NULL",
                            ("READ",)
                        ))
                        break

        # 8. Correlated subquery detection (QUERY_AP_08)
        outer_tables = {t.alias_or_name.lower() for t in parsed.find_all(exp.Table) if t.alias_or_name}
        for subquery in parsed.find_all(exp.Subquery):
            inner_select = subquery.find(exp.Select)
            if inner_select:
                inner_tables = {t.alias_or_name.lower() for t in inner_select.find_all(exp.Table) if t.alias_or_name}
                for col in inner_select.find_all(exp.Column):
                    if col.table and col.table.lower() in outer_tables and col.table.lower() not in inner_tables:
                        issues.append(issue(
                            IssueCode.QUERY_AP_08, Layer.QUERY_AP, Severity.WARNING,
                            f"Correlated subquery references outer table '{col.table}' — may execute once per row",
                            "Refactor to JOIN or Window Function for better performance",
                            ("READ",)
                        ))
                        break

        # 9. DISTINCT masking bad JOINs (QUERY_AP_09)
        is_distinct = parsed.args.get("distinct")
        has_joins = bool(parsed.args.get("joins"))
        if is_distinct and has_joins:
            issues.append(issue(
                IssueCode.QUERY_AP_09, Layer.QUERY_AP, Severity.WARNING,
                "DISTINCT used on a joined query may mask duplicate rows from incorrect JOIN cardinality",
                "Verify join cardinality and join keys; remove DISTINCT if duplicates are from bad JOINs",
                ("READ",)
            ))

    return issues


# ------------------------------------------------------------------
# Layer 6 — SCHEMA ANTI-PATTERNS (DDL Checks)
# ------------------------------------------------------------------

def executeSchemaAntiPatternValidation(parsed: exp.Expression) -> List[Issue]:
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

            # --- Remaining schema anti-pattern checks ---
            only_col_defs = [c for c in col_defs if isinstance(c, exp.ColumnDef)]
            col_names_lower = [c.name.lower() for c in only_col_defs]
            col_types_lower = {}
            for c in only_col_defs:
                c_type = str(c.kind).upper() if c.kind else ""
                col_types_lower[c.name.lower()] = c_type

            # SCHEMA_AP_02: Missing foreign-key reference
            # Columns that look like foreign keys (ending in _id) but have no FK constraint
            has_fk_constraint = set()
            for c in only_col_defs:
                for constraint in c.find_all(exp.Reference):
                    has_fk_constraint.add(c.name.lower())
            for fk_constraint in schema_def.find_all(exp.ForeignKey):
                for fk_expr in fk_constraint.expressions:
                    if hasattr(fk_expr, "name"):
                        has_fk_constraint.add(fk_expr.name.lower())

            pk_cols = set()
            if has_pk:
                for c in only_col_defs:
                    if any(isinstance(con, exp.PrimaryKeyColumnConstraint) for con in c.find_all(exp.PrimaryKeyColumnConstraint)):
                        pk_cols.add(c.name.lower())
                for pk_node in schema_def.find_all(exp.PrimaryKey):
                    for pk_expr in pk_node.expressions:
                        if hasattr(pk_expr, "name"):
                            pk_cols.add(pk_expr.name.lower())

            for cname in col_names_lower:
                if cname.endswith("_id") and cname not in pk_cols and cname not in has_fk_constraint:
                    issues.append(issue(
                        IssueCode.SCHEMA_AP_02, Layer.SCHEMA_AP, Severity.WARNING,
                        f"Column '{cname}' looks like a foreign key but has no FOREIGN KEY constraint",
                        f"Add FOREIGN KEY REFERENCES constraint for '{cname}'",
                        ("DDL",)
                    ))

            # SCHEMA_AP_03: EAV-style table (entity-attribute-value)
            eav_markers = {"entity_type", "attribute_name", "attribute_value"}
            if eav_markers.issubset(set(col_names_lower)):
                issues.append(issue(
                    IssueCode.SCHEMA_AP_03, Layer.SCHEMA_AP, Severity.WARNING,
                    f"Table '{schema_def.name}' appears to use Entity-Attribute-Value (EAV) anti-pattern",
                    "Consider using dedicated columns per attribute for type safety and query performance",
                    ("DDL",)
                ))

            # SCHEMA_AP_04: Polymorphic type columns (*_type + *_id together)
            type_cols = [cn for cn in col_names_lower if cn.endswith("_type")]
            for tc in type_cols:
                prefix = tc[:-5]  # strip "_type"
                if f"{prefix}_id" in col_names_lower:
                    issues.append(issue(
                        IssueCode.SCHEMA_AP_04, Layer.SCHEMA_AP, Severity.WARNING,
                        f"Columns '{tc}' + '{prefix}_id' suggest a polymorphic association anti-pattern",
                        "Use separate foreign key columns per referenced table or a join table",
                        ("DDL",)
                    ))

            # SCHEMA_AP_06: FLOAT used for monetary columns
            _MONETARY_KEYWORDS = {"price", "amount", "cost", "balance", "salary", "fee", "total", "revenue", "wage", "payment"}
            _FLOAT_TYPES = {"FLOAT", "REAL", "DOUBLE", "DOUBLE PRECISION", "FLOAT4", "FLOAT8"}
            for cname, ctype in col_types_lower.items():
                if any(mk in cname for mk in _MONETARY_KEYWORDS):
                    if any(ft in ctype for ft in _FLOAT_TYPES):
                        issues.append(issue(
                            IssueCode.SCHEMA_AP_06, Layer.SCHEMA_AP, Severity.WARNING,
                            f"Column '{cname}' uses {ctype} for monetary/currency data — precision loss risk",
                            "Use NUMERIC or DECIMAL type for monetary values",
                            ("DDL",)
                        ))

            # SCHEMA_AP_07: Excessive nullable columns (>70% of columns are nullable)
            if len(only_col_defs) >= 3:
                not_null_count = 0
                for c in only_col_defs:
                    has_not_null = any(
                        isinstance(con, exp.NotNullColumnConstraint)
                        for con in c.find_all(exp.NotNullColumnConstraint)
                    )
                    has_pk_constraint = any(
                        isinstance(con, exp.PrimaryKeyColumnConstraint)
                        for con in c.find_all(exp.PrimaryKeyColumnConstraint)
                    )
                    if has_not_null or has_pk_constraint or c.name.lower() in pk_cols:
                        not_null_count += 1

                nullable_count = len(only_col_defs) - not_null_count
                nullable_ratio = nullable_count / len(only_col_defs)
                if nullable_ratio > 0.70:
                    issues.append(issue(
                        IssueCode.SCHEMA_AP_07, Layer.SCHEMA_AP, Severity.WARNING,
                        f"Table '{schema_def.name}' has {nullable_count}/{len(only_col_defs)} nullable columns ({nullable_ratio:.0%})",
                        "Review column nullability; mark required columns NOT NULL for data integrity",
                        ("DDL",)
                    ))

            # SCHEMA_AP_05: Comma-separated values in column default
            # Detect columns whose DEFAULT contains commas — suggests storing lists in a single column
            for c in only_col_defs:
                for default_node in c.find_all(exp.ColumnConstraint):
                    default_kind = default_node.args.get("kind")
                    if isinstance(default_kind, exp.DefaultColumnConstraint):
                        default_val = default_kind.this
                        if default_val and isinstance(default_val, exp.Literal):
                            val_str = str(default_val.this or "")
                            if "," in val_str and len(val_str.split(",")) >= 2:
                                issues.append(issue(
                                    IssueCode.SCHEMA_AP_05, Layer.SCHEMA_AP, Severity.WARNING,
                                    f"Column '{c.name}' has a DEFAULT value with comma-separated data",
                                    "Store multi-value data in a separate normalized table, not as CSV in a single column",
                                    ("DDL",)
                                ))

            # SCHEMA_AP_08: FK column without backing index
            # Columns with FK constraints but no matching index defined in table constraints
            indexed_cols: Set[str] = set()
            for idx_node in schema_def.find_all(exp.Index):
                for idx_col in idx_node.find_all(exp.Column):
                    indexed_cols.add(idx_col.name.lower())
            # Also count PK columns as indexed
            indexed_cols.update(pk_cols)

            for fk_col_name in has_fk_constraint:
                if fk_col_name not in indexed_cols:
                    issues.append(issue(
                        IssueCode.SCHEMA_AP_08, Layer.SCHEMA_AP, Severity.WARNING,
                        f"Foreign key column '{fk_col_name}' has no backing index",
                        f"Create an index on '{fk_col_name}' to speed up JOIN and DELETE operations",
                        ("DDL",)
                    ))

    return issues


# ------------------------------------------------------------------
# Unified Engine Pipeline Entrypoint
# ------------------------------------------------------------------

def executeFullSixLayerValidationPipeline(
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

    # Fast-path 0A: Pure Comment Refusals
    stripped = sql.strip()
    if stripped.startswith("-- REFUSAL:") or stripped.startswith("-- CANNOT_GENERATE:"):
        result = ValidationResult(
            status=Status.VALID,
            statement_type=StatementType.READ,
            normalized_sql=stripped,
            tables_touched=frozenset(),
            columns_touched=frozenset(),
            issues=(),
        )
        if audit_logger:
            audit_logger.recordValidationAuditEntry(sql, result)
        return result

    # Fast-path 0B: Multi-Statement Scripts (DDL migrations & initial seed data)
    try:
        from core.sanitizer import split_sql_script
        read_d = dialect
        if "`" in stripped or re.search(r"\bUSE\s+", stripped, re.IGNORECASE) or "AUTO_INCREMENT" in stripped.upper():
            read_d = "mysql"

        raw_stmts = split_sql_script(stripped, dialect=read_d)
        if len(raw_stmts) > 1:
            parsed_stmts = []
            parse_errors = []
            for stmt_str in raw_stmts:
                parsed_node = None
                for d_try in (read_d, "mysql", "postgres", "sqlite"):
                    try:
                        p = sqlglot.parse_one(stmt_str, read=d_try)
                        if p is not None:
                            parsed_node = p
                            break
                    except Exception:
                        continue
                if parsed_node is not None:
                    parsed_stmts.append((stmt_str, parsed_node))
                else:
                    parse_errors.append(stmt_str)

            if parse_errors:
                result = ValidationResult(
                    status=Status.INVALID,
                    statement_type=StatementType.UNKNOWN,
                    normalized_sql=None,
                    issues=(issue(
                        IssueCode.PARSE_02, Layer.PARSE, Severity.ERROR,
                        f"SQL syntax error in statement: {parse_errors[0][:60]}",
                        "Check query grammar against SQL dialect standard"
                    ),)
                )
                if audit_logger:
                    audit_logger.recordValidationAuditEntry(sql, result)
                return result

            # Stacking queries with SELECT is a classic injection pattern; require single statements for queries
            has_select = any(isinstance(p, exp.Select) for _, p in parsed_stmts)
            if has_select:
                result = ValidationResult(
                    status=Status.INVALID,
                    statement_type=StatementType.UNKNOWN,
                    normalized_sql=None,
                    issues=(issue(
                        IssueCode.PARSE_01, Layer.PARSE, Severity.ERROR,
                        "Multiple statements detected; only single-statement SQL is permitted",
                        "Execute one SQL statement at a time"
                    ),)
                )
                if audit_logger:
                    audit_logger.recordValidationAuditEntry(sql, result)
                return result

            # Validate multi-statement DDL/script against safety policies
            script_issues: List[Issue] = []
            for stmt_str, p in parsed_stmts:
                upper_stmt = stmt_str.upper()
                if "DROP DATABASE" in upper_stmt or "DROP SCHEMA" in upper_stmt:
                    script_issues.append(issue(
                        IssueCode.POLICY_02, Layer.POLICY, Severity.ERROR,
                        "DROP DATABASE / DROP SCHEMA is prohibited by safety policy",
                        "Target specific tables or use sandbox test environment",
                        ("DDL",)
                    ))
                if isinstance(p, (exp.Update, exp.Delete)):
                    if not p.find(exp.Where):
                        script_issues.append(issue(
                            IssueCode.POLICY_05, Layer.POLICY, Severity.ERROR,
                            f"{p.key.upper()} statement missing WHERE clause",
                            "Add a WHERE predicate to scope modification",
                            ("WRITE",)
                        ))
                for func in p.find_all(exp.Anonymous, exp.Func):
                    func_name = (func.name or "").lower()
                    if func_name in {"pg_sleep", "sleep", "benchmark", "xp_cmdshell", "exec", "execute", "system", "sys_eval", "eval", "load_file", "into_outfile", "into_dumpfile"}:
                        script_issues.append(issue(
                            IssueCode.POLICY_06, Layer.POLICY, Severity.ERROR,
                            f"Prohibited system function '{func_name}' detected",
                            "Remove database engine internals access call",
                            ("WRITE", "DDL")
                        ))
                ap_issues = executeSchemaAntiPatternValidation(p)
                script_issues.extend(ap_issues)

            tables_touched = frozenset(
                t.name.lower()
                for _, p in parsed_stmts
                for t in p.find_all(exp.Table)
                if t.name
            )
            columns_touched = frozenset(
                c.name.lower()
                for _, p in parsed_stmts
                for c in p.find_all(exp.Column)
                if c.name and c.name != "*"
            )
            is_ddl = any(
                isinstance(p, (exp.Create, exp.Alter, exp.Drop, exp.Command, exp.Use)) or getattr(p, "kind", "").upper() in ("TABLE", "DATABASE", "SCHEMA")
                for _, p in parsed_stmts
            )
            stmt_type = StatementType.DDL if is_ddl else StatementType.WRITE
            filtered_issues = [i for i in script_issues if registry.is_enabled(i.code)]
            has_errors = any(i.severity == Severity.ERROR for i in filtered_issues)
            has_warnings = any(i.severity == Severity.WARNING for i in filtered_issues)
            status = Status.INVALID if has_errors else (Status.VALID_WITH_WARNINGS if has_warnings else Status.VALID)

            result = ValidationResult(
                status=status,
                statement_type=stmt_type,
                normalized_sql=stripped,
                tables_touched=tables_touched,
                columns_touched=columns_touched,
                issues=tuple(filtered_issues)
            )
            if audit_logger:
                audit_logger.recordValidationAuditEntry(sql, result)
            return result
    except Exception:
        pass

    # 1. PARSE
    parse_issues, parsed = executeParseLayerValidation(sql, dialect=dialect)
    all_issues.extend(parse_issues)
    if any(i.severity == Severity.ERROR for i in parse_issues) or parsed is None:
        result = ValidationResult(
            status=Status.INVALID,
            statement_type=StatementType.UNKNOWN,
            normalized_sql=None,
            issues=tuple(all_issues)
        )
        if audit_logger:
            audit_logger.recordValidationAuditEntry(sql, result)
        return result

    # 2. POLICY
    policy_issues, stmt_type = executePolicyLayerValidation(sql, parsed)
    all_issues.extend(policy_issues)
    if any(i.severity == Severity.ERROR for i in policy_issues):
        result = ValidationResult(
            status=Status.INVALID,
            statement_type=stmt_type,
            normalized_sql=parsed.sql(dialect=dialect),
            issues=tuple(all_issues)
        )
        if audit_logger:
            audit_logger.recordValidationAuditEntry(sql, result)
        return result

    # 3. SCHEMA
    schema_issues = executeSchemaLayerValidation(parsed, schema)
    all_issues.extend(schema_issues)
    if any(i.severity == Severity.ERROR for i in schema_issues):
        result = ValidationResult(
            status=Status.INVALID,
            statement_type=stmt_type,
            normalized_sql=parsed.sql(dialect=dialect),
            issues=tuple(all_issues)
        )
        if audit_logger:
            audit_logger.recordValidationAuditEntry(sql, result)
        return result

    # 4. SEMANTIC
    semantic_issues = executeSemanticLayerValidation(parsed)
    all_issues.extend(semantic_issues)
    if any(i.severity == Severity.ERROR for i in semantic_issues):
        result = ValidationResult(
            status=Status.INVALID,
            statement_type=stmt_type,
            normalized_sql=parsed.sql(dialect=dialect),
            issues=tuple(all_issues)
        )
        if audit_logger:
            audit_logger.recordValidationAuditEntry(sql, result)
        return result

    # 5. QUERY_AP
    query_ap_issues = executeQueryAntiPatternValidation(parsed)
    all_issues.extend(query_ap_issues)
    if any(i.severity == Severity.ERROR for i in query_ap_issues):
        result = ValidationResult(
            status=Status.INVALID,
            statement_type=stmt_type,
            normalized_sql=parsed.sql(dialect=dialect),
            issues=tuple(all_issues)
        )
        if audit_logger:
            audit_logger.recordValidationAuditEntry(sql, result)
        return result

    # 6. SCHEMA_AP
    schema_ap_issues = executeSchemaAntiPatternValidation(parsed)
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
        audit_logger.recordValidationAuditEntry(sql, result)

    return result


# Aliases for backward compatibility
validate_parse = executeParseLayerValidation
validate_policy = executePolicyLayerValidation
validate_schema = executeSchemaLayerValidation
validate_semantic = executeSemanticLayerValidation
validate_query_anti_patterns = executeQueryAntiPatternValidation
validate_schema_anti_patterns = executeSchemaAntiPatternValidation
run_validation = executeFullSixLayerValidationPipeline


__all__ = [
    "createValidationIssue",
    "executeParseLayerValidation",
    "executePolicyLayerValidation",
    "executeSchemaLayerValidation",
    "executeSemanticLayerValidation",
    "executeQueryAntiPatternValidation",
    "executeSchemaAntiPatternValidation",
    "executeFullSixLayerValidationPipeline",
    "issue",
    "validate_parse",
    "validate_policy",
    "validate_schema",
    "validate_semantic",
    "validate_query_anti_patterns",
    "validate_schema_anti_patterns",
    "run_validation",
]
