"""Data contracts for M9.

Every field is typed. Every container is immutable (frozen dataclasses / NamedTuple).
No hidden state; nothing depends on a live database.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple

# ------------------------------------------------------------------
# Issue
# ------------------------------------------------------------------

class Severity(enum.Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Layer(enum.Enum):
    PARSE = 1
    POLICY = 2
    SCHEMA = 3
    SEMANTIC = 4
    QUERY_AP = 5
    SCHEMA_AP = 6


@dataclass(frozen=True, slots=True)
class Issue:
    """Single finding from one validation rule.

    Rules use IssueCode (str enum) for identity; messages stay human-readable
    for feedback formatting but are NOT parsed by downstream rules.
    """

    code: str  # e.g. PARSE_01
    layer: Layer
    severity: Severity
    applies_to: Tuple[str, ...] = ()  # READ / WRITE / DDL / UNKNOWN
    message: str = ""
    fix_hint: Optional[str] = None
    location: Optional[int] = None  # 1-based line (optional, from parser)


# ------------------------------------------------------------------
# Issue catalog — every known M9 code lives here
# ------------------------------------------------------------------

class IssueCode:
    """Static namespace of every check this validator knows about.

    Rules are registered by these codes; adding a new check means
    adding a new ID here and a function in rules/. No engine change.
    """

    # Layer 1 — PARSE
    PARSE_01 = "PARSE_01"  # multi-statement / stacked query
    PARSE_02 = "PARSE_02"  # unparseable / syntax error

    # Layer 2 — POLICY
    POLICY_01 = "POLICY_01"  # unrecognized statement type
    POLICY_02 = "POLICY_02"  # DROP DATABASE / TRUNCATE
    POLICY_03 = "POLICY_03"  # GRANT / REVOKE
    POLICY_04 = "POLICY_04"  # COPY ... PROGRAM (system command)
    POLICY_05 = "POLICY_05"  # UPDATE / DELETE without WHERE
    POLICY_06 = "POLICY_06"  # dangerous built-in / system fn

    # Layer 3 — SCHEMA
    SCHEMA_01 = "SCHEMA_01"  # unknown table
    SCHEMA_02 = "SCHEMA_02"  # unknown / misspelled column
    SCHEMA_03 = "SCHEMA_03"  # ambiguous column in multi-table query
    SCHEMA_04 = "SCHEMA_04"  # bad / unresolvable alias
    SCHEMA_05 = "SCHEMA_05"  # unknown function / operator
    SCHEMA_06 = "SCHEMA_06"  # type mismatch in comparison / join

    # Layer 4 — SEMANTIC
    SEM_01 = "SEM_01"  # non-aggregated column missing from GROUP BY
    SEM_02 = "SEM_02"  # aggregate used inside WHERE
    SEM_03 = "SEM_03"  # INSERT column/value count mismatch
    SEM_04 = "SEM_04"  # NOT NULL column missing on INSERT

    # Layer 5 — QUERY ANTI-PATTERN (mostly warnings; two promoted to error)
    QUERY_AP_01 = "QUERY_AP_01"  # SELECT * (warning)
    QUERY_AP_02 = "QUERY_AP_02"  # cartesian / missing JOIN condition (ERROR)
    QUERY_AP_03 = "QUERY_AP_03"  # leading-wildcard LIKE '%text' (warning)
    QUERY_AP_04 = "QUERY_AP_04"  # function wrapped on indexed col in WHERE (warning)
    QUERY_AP_05 = "QUERY_AP_05"  # NOT IN with nullable subquery (warning)
    QUERY_AP_06 = "QUERY_AP_06"  # ORDER BY without LIMIT on large-table query (warning)
    QUERY_AP_07 = "QUERY_AP_07"  # deep OFFSET (>10000) (warning)
    QUERY_AP_08 = "QUERY_AP_08"  # correlated subquery (warning)
    QUERY_AP_09 = "QUERY_AP_09"  # DISTINCT masking a bad JOIN (warning)

    # Layer 6 — SCHEMA ANTI-PATTERN (DDL only; all warnings)
    SCHEMA_AP_01 = "SCHEMA_AP_01"  # table without primary key
    SCHEMA_AP_02 = "SCHEMA_AP_02"  # missing foreign-key reference
    SCHEMA_AP_03 = "SCHEMA_AP_03"  # EAV-style table (entity-attr-value)
    SCHEMA_AP_04 = "SCHEMA_AP_04"  # polymorphic type + id columns
    SCHEMA_AP_05 = "SCHEMA_AP_05"  # comma-separated values in a column
    SCHEMA_AP_06 = "SCHEMA_AP_06"  # FLOAT used for monetary value
    SCHEMA_AP_07 = "SCHEMA_AP_07"  # excessive nullable columns (>70% of cols)
    SCHEMA_AP_08 = "SCHEMA_AP_08"  # FK column has no backing index


# ------------------------------------------------------------------
# ValidationResult — what M9 hands to M10 / M12
# ------------------------------------------------------------------

class Status(enum.Enum):
    VALID = "valid"  # zero errors, zero warnings
    VALID_WITH_WARNINGS = "valid_with_warnings"  # zero errors, 1+ warnings
    INVALID = "invalid"  # 1+ errors (always blocked)


class StatementType(enum.Enum):
    READ = "READ"
    WRITE = "WRITE"
    DDL = "DDL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ValidationResult:
    status: Status
    statement_type: StatementType
    normalized_sql: Optional[str] = None
    tables_touched: FrozenSet[str] = field(default_factory=frozenset)
    columns_touched: FrozenSet[str] = field(default_factory=frozenset)
    issues: Tuple[Issue, ...] = ()

    # Convenience helpers (derived, never mutated after creation)
    def errors(self) -> Tuple[Issue, ...]:
        return tuple(i for i in self.issues if i.severity == Severity.ERROR)

    def warnings(self) -> Tuple[Issue, ...]:
        return tuple(i for i in self.issues if i.severity == Severity.WARNING)

    def has_errors(self) -> bool:
        return bool(self.errors())


# ------------------------------------------------------------------
# RetryFeedback — what M9 returns to M6 (AI model) for retry context
# ------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class RetryFeedback:
    source: str  # "M9" or "M10"
    issues: Tuple[str, ...]  # compact issue codes only
    suggestion: str  # one-line, model-actionable hint
    did_you_mean: Tuple[str, ...] = ()  # fuzzy-match hints (optional)


# ------------------------------------------------------------------
# Schema snapshot helpers
# ------------------------------------------------------------------

SCHEMA_KEYS: FrozenSet[str] = frozenset(
    ("table", "columns", "pk", "fks", "indexes", "nullable", "row_count")
)


def parse_yaml_schema(text: str) -> Dict:
    """Placeholder: real loader parses YAML; stub validates key presence."""
    # This is a minimal stub — real work is done by FakeSchemaProvider.
    # We keep it here so contracts.py has no dependency on yaml package.
    return {"loaded": True, "raw": text}
