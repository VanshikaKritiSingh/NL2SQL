"""M9 core engine.

Implements the six-layer validation pipeline:

    PARSE → POLICY → SCHEMA → SEMANTIC → QUERY_AP → SCHEMA_AP

Each layer runs the enabled rules; the first layer that produces an error
stops the pipeline and the result is INVALID. Layers 5-6 produce warnings
only (except two anti-patterns promoted to error).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

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
from .interfaces import AuditLogger, FakeSchemaProvider, SchemaProvider


# ------------------------------------------------------------------
# ValidationContext
# ------------------------------------------------------------------

@dataclass
class ValidationContext:
    """Immutable-ish context threaded through the validation layers."""

    sql: str
    dialect: str = "postgres"
    schema: Optional[SchemaProvider] = None
    audit_logger: Optional[AuditLogger] = None
    rules: Optional[Any] = None  # RuleRegistry (passed via engine.run())
    config: Dict[str, Any] = field(default_factory=dict)
    # computed state
    parsed: Optional[exp.Expression] = None
    statement_type: StatementType = StatementType.UNKNOWN
    tables: Set[str] = field(default_factory=set)
    columns: Dict[str, Set[str]] = field(default_factory=dict)

    def add_table(self, table: str) -> None:
        self.tables.add(table)

    def add_column(self, table: str, column: str) -> None:
        self.columns.setdefault(table, set()).add(column)


# ------------------------------------------------------------------
# Issue helpers
# ------------------------------------------------------------------

def issue(code: str, layer: Layer, severity: Severity, message: str, **kw):
    return Issue(code=code, layer=layer, severity=severity, message=message, **kw)


def maybe_issue(code: str, layer: Layer, severity: Severity, enabled: bool, message: str, **kw):
    return issue(code, layer, severity, message, **kw) if enabled else None


# ------------------------------------------------------------------
# Layer 1 — PARSE
# ------------------------------------------------------------------

def validate_parse(sql: str) -> Tuple[List[Issue], Optional[exp.Expression]]:
    """Parse the SQL; reject unparseable / multi-statement input."""
    issues: List[Issue] = []

    stripped = sql.strip()
    if not stripped or stripped == ";":
        issues.append(issue(IssueCode.PARSE_02, Layer.PARSE, Severity.ERROR,
                            "Empty or whitespace-only SQL"))
        return issues, None

    # Multi-statement check
    statements = [s.strip() for s in stripped.split(";") if s.strip()]
    if len(statements) > 1:
        issues.append(issue(IssueCode.PARSE_01, Layer.PARSE, Severity.ERROR,
                            "Multiple statements detected; only single-statement SQL is allowed"))
        return issues, None

    try:
        parsed = sqlglot.parse_one(stripped, dialect="postgres")
    except Exception as exc:
        issues.append(issue(IssueCode.PARSE_02, Layer.PARSE, Severity.ERROR,
                            f"SQL is not valid for dialect 'postgres': {exc}"))
        return issues, None

    return issues, parsed


# ------------------------------------------------------------------
# Layer 2 — POLICY
# ------------------------------------------------------------------

def validate_policy(sql: str, parsed: exp.Expression) -> List[Issue]:
    """Statement-type classification + explicit allowlist + denylist."""
    issues: List[Issue] = []

    node = parsed

    # Extract the statement keyword (e.g. SELECT, INSERT, CREATE)
    if isinstance(node, exp.Command):
        stmt = node.name.upper()
    elif isinstance(node, exp.Expression):
        stmt = node.__class__.__name__.upper()
        # sqlglot expression classes are like "Select", "Insert", "Delete", "Create", "Alter"
    else:
        stmt = "UNKNOWN"

    if stmt == "STATEMENT":
        # Generic Command node
        stmt = node.name.upper()

    # Map expression classes to our types
    ALLOWED = {
        "SELECT": StatementType.READ,
        "INSERT": StatementType.WRITE,
        "UPDATE": StatementType.WRITE,
        "DELETE": StatementType.WRITE,
        "CREATE": StatementType.DDL,
        "ALTER": StatementType.DDL,
        "TRUNCATE": StatementType.DDL,
        "DROP": StatementType.DDL,
        "GRANT": StatementType.DDL,
        "REVOKE": StatementType.DDL,
    }

    if stmt not in ALLOWED:
        issues.append(issue(IssueCode.POLICY_01, Layer.POLICY, Severity.ERROR,
                            f"Statement type {stmt} is not recognized and is not in the allowlist"))
        return issues

    stmt_type = ALLOWED[stmt]

    # Explicit denylist
    DENY = {
        "DROP DATABASE": IssueCode.POLICY_02,
        "DROP SCHEMA": IssueCode.POLICY_02,
        "TRUNCATE": IssueCode.POLICY_02,
        "GRANT": IssueCode.POLICY_03,
        "REVOKE": IssueCode.POLICY_03,
        "COPY": None,  # handled separately
    }

    upper_sql = sql.upper()
    if "DROP DATABASE" in upper_sql or "DROP SCHEMA" in upper_sql:
        issues.append(issue(IssueCode.POLICY_02, Layer.POLICY, Severity.ERROR,
                            "DROP DATABASE / DROP SCHEMA is not allowed"))
    if "TRUNCATE" in upper_sql:
        issues.append(issue(IssueCode.POLICY_02, Layer.POLICY, Severity.ERROR,
                            "TRUNCATE is not allowed"))
    if "GRANT" in upper_sql or "REVOKE" in upper_sql:
        issues.append(issue(IssueCode.POLICY_03, Layer.POLICY, Severity.ERROR,
                            "GRANT / REVOKE are not allowed (handled by a dedicated security module)"))
    if "COPY" in upper_sql and "PROGRAM" in upper_sql:
        issues.append(issue(IssueCode.POLICY_04, Layer.POLICY, Severity.ERROR,
                            "COPY ... PROGRAM can execute arbitrary system commands and is not allowed"))

    # UPDATE / DELETE without WHERE -> error
    if stmt in ("UPDATE", "DELETE"):
        if node.args.get("where") is None:
            issues.append(issue(IssueCode.POLICY_05, Layer.POLICY, Severity.ERROR,
                                f"{stmt} without WHERE clause would affect all rows"))

    return issues
