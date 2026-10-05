"""Rule registry for M9 — centralised collection of all validation rules.

Each rule is registered by its IssueCode and is toggled independently via
configuration. Adding a new check means adding a new Entry to this registry;
the engine never needs to know about individual rule implementations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..contracts import (
    IssueCode,
    Layer,
    Severity,
)


class IssueType(str, Enum):
    PARSE = "PARSE"
    POLICY = "POLICY"
    SCHEMA = "SCHEMA"
    SEMANTIC = "SEMANTIC"
    QUERY_AP = "QUERY_AP"
    SCHEMA_AP = "SCHEMA_AP"


class IssueSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Policy:
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    REJECT = "REJECT"


@dataclass(frozen=True, slots=True)
class RuleEntry:
    """Immutable definition of a single validation rule."""
    code: str  # e.g. "PARSE_01"
    layer: Layer
    severity: Severity
    applies_to: Tuple[str, ...]  # ("READ", "WRITE", "DDL", "UNKNOWN")
    message: str
    fix_hint: str = ""
    enabled: bool = True


DEFAULT_RULES: List[RuleEntry] = [
    # Layer 1 — PARSE
    RuleEntry(IssueCode.PARSE_01, Layer.PARSE, Severity.ERROR, ("READ", "WRITE", "DDL"), "Multiple statements detected; only single-statement SQL allowed", "Split into single statements"),
    RuleEntry(IssueCode.PARSE_02, Layer.PARSE, Severity.ERROR, ("READ", "WRITE", "DDL"), "SQL syntax error or unparseable AST", "Check SQL syntax against dialect grammar"),

    # Layer 2 — POLICY
    RuleEntry(IssueCode.POLICY_01, Layer.POLICY, Severity.ERROR, ("UNKNOWN",), "Statement type not recognized or disallowed", "Ensure statement is standard SELECT, INSERT, UPDATE, DELETE, or DDL"),
    RuleEntry(IssueCode.POLICY_02, Layer.POLICY, Severity.ERROR, ("DDL", "WRITE"), "DROP DATABASE / DROP SCHEMA / TRUNCATE disallowed", "Use scoped table operations"),
    RuleEntry(IssueCode.POLICY_03, Layer.POLICY, Severity.ERROR, ("DDL",), "GRANT / REVOKE security operations disallowed", "Manage permissions via IAM / Security module"),
    RuleEntry(IssueCode.POLICY_04, Layer.POLICY, Severity.ERROR, ("READ", "WRITE", "DDL"), "COPY ... PROGRAM disallowed due to arbitrary command execution risk", "Use standard file import mechanisms"),
    RuleEntry(IssueCode.POLICY_05, Layer.POLICY, Severity.ERROR, ("WRITE",), "UPDATE / DELETE without WHERE clause affects all rows", "Add explicit WHERE filter clause"),
    RuleEntry(IssueCode.POLICY_06, Layer.POLICY, Severity.ERROR, ("READ", "WRITE", "DDL"), "Dangerous system function execution detected", "Remove system administration function calls"),

    # Layer 3 — SCHEMA
    RuleEntry(IssueCode.SCHEMA_01, Layer.SCHEMA, Severity.ERROR, ("READ", "WRITE", "DDL"), "Unknown table reference", "Verify table name in database schema catalog"),
    RuleEntry(IssueCode.SCHEMA_02, Layer.SCHEMA, Severity.ERROR, ("READ", "WRITE", "DDL"), "Unknown or misspelled column reference", "Verify column name against table schema"),
    RuleEntry(IssueCode.SCHEMA_03, Layer.SCHEMA, Severity.ERROR, ("READ", "WRITE"), "Ambiguous column reference in multi-table join", "Qualify column with table name or alias"),
    RuleEntry(IssueCode.SCHEMA_04, Layer.SCHEMA, Severity.ERROR, ("READ", "WRITE"), "Unresolvable table alias reference", "Ensure alias is defined in FROM/JOIN clause"),
    RuleEntry(IssueCode.SCHEMA_05, Layer.SCHEMA, Severity.WARNING, ("READ", "WRITE"), "Unknown function or dialect-specific operator", "Use standard ANSI SQL functions"),
    RuleEntry(IssueCode.SCHEMA_06, Layer.SCHEMA, Severity.WARNING, ("READ", "WRITE"), "Type mismatch in comparison or join expression", "Cast types explicitly"),

    # Layer 4 — SEMANTIC
    RuleEntry(IssueCode.SEM_01, Layer.SEMANTIC, Severity.ERROR, ("READ",), "Non-aggregated column missing from GROUP BY clause", "Add unaggregated column to GROUP BY or wrap in aggregate"),
    RuleEntry(IssueCode.SEM_02, Layer.SEMANTIC, Severity.ERROR, ("READ",), "Aggregate function used inside WHERE clause", "Use HAVING clause for aggregate conditions"),
    RuleEntry(IssueCode.SEM_03, Layer.SEMANTIC, Severity.ERROR, ("WRITE",), "INSERT column count does not match VALUES count", "Align column and value lists"),
    RuleEntry(IssueCode.SEM_04, Layer.SEMANTIC, Severity.WARNING, ("WRITE",), "NOT NULL column missing in INSERT statement", "Provide value for required NOT NULL column"),

    # Layer 5 — QUERY ANTI-PATTERNS
    RuleEntry(IssueCode.QUERY_AP_01, Layer.QUERY_AP, Severity.WARNING, ("READ",), "SELECT * projection in production query", "Explicitly name projected columns"),
    RuleEntry(IssueCode.QUERY_AP_02, Layer.QUERY_AP, Severity.ERROR, ("READ", "WRITE"), "Cartesian product / CROSS JOIN without join condition", "Add explicit ON join condition"),
    RuleEntry(IssueCode.QUERY_AP_03, Layer.QUERY_AP, Severity.WARNING, ("READ", "WRITE"), "Leading-wildcard LIKE pattern invalidates B-tree index", "Avoid leading % wildcard or use full-text index"),
    RuleEntry(IssueCode.QUERY_AP_04, Layer.QUERY_AP, Severity.WARNING, ("READ", "WRITE"), "Function wrapping indexed column in WHERE clause prevents index scan", "Rewrite predicate as sargable expression"),
    RuleEntry(IssueCode.QUERY_AP_05, Layer.QUERY_AP, Severity.WARNING, ("READ",), "NOT IN with nullable subquery risks returning empty set", "Use NOT EXISTS or ensure subquery columns are NOT NULL"),
    RuleEntry(IssueCode.QUERY_AP_06, Layer.QUERY_AP, Severity.WARNING, ("READ",), "ORDER BY without LIMIT on large table scan", "Add LIMIT clause to bounded sort"),
    RuleEntry(IssueCode.QUERY_AP_07, Layer.QUERY_AP, Severity.WARNING, ("READ",), "Deep OFFSET (>10,000) causes performance degradation", "Use keyset pagination / cursor"),
    RuleEntry(IssueCode.QUERY_AP_08, Layer.QUERY_AP, Severity.WARNING, ("READ",), "Correlated subquery may execute once per row", "Refactor to JOIN or Window Function"),
    RuleEntry(IssueCode.QUERY_AP_09, Layer.QUERY_AP, Severity.WARNING, ("READ",), "DISTINCT used on joined tables may mask duplicate rows", "Verify join cardinality and join keys"),

    # Layer 6 — SCHEMA ANTI-PATTERNS
    RuleEntry(IssueCode.SCHEMA_AP_01, Layer.SCHEMA_AP, Severity.WARNING, ("DDL",), "Table defined without primary key", "Add PRIMARY KEY constraint"),
    RuleEntry(IssueCode.SCHEMA_AP_02, Layer.SCHEMA_AP, Severity.WARNING, ("DDL",), "Missing foreign-key constraint", "Add FOREIGN KEY REFERENCES constraint"),
    RuleEntry(IssueCode.SCHEMA_AP_06, Layer.SCHEMA_AP, Severity.WARNING, ("DDL",), "FLOAT type used for monetary/currency columns", "Use NUMERIC or DECIMAL"),
    RuleEntry(IssueCode.SCHEMA_AP_08, Layer.SCHEMA_AP, Severity.WARNING, ("DDL",), "Foreign key column has no backing index", "Create index on foreign key column"),
]


class RuleRegistry:
    """Centralised collection of all M9 validation rules."""

    def __init__(self, entries: Optional[List[RuleEntry]] = None):
        self._entries: Dict[str, RuleEntry] = {}
        self._toggles: Dict[str, bool] = {}
        for e in (entries or DEFAULT_RULES):
            self.register(e)

    def register(self, entry: RuleEntry):
        self._entries[entry.code] = entry
        if entry.code not in self._toggles:
            self._toggles[entry.code] = entry.enabled

    def lookup(self, code: str) -> Optional[RuleEntry]:
        return self._entries.get(code)

    def is_enabled(self, code: str) -> bool:
        return self._toggles.get(code, True)

    def toggle(self, code: str, enabled: bool) -> bool:
        """Enable or disable a rule by code. Returns current state."""
        if code in self._entries:
            self._toggles[code] = enabled
            return enabled
        return False

    def all_entries(self) -> List[RuleEntry]:
        return list(self._entries.values())

    def enabled_rules(self) -> List[RuleEntry]:
        return [e for e in self._entries.values() if self._toggles.get(e.code, True)]

    def __len__(self) -> int:
        return len(self._entries)
