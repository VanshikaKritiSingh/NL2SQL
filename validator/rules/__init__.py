"""Rule registry for M9 — centralised collection of all validation rules.

Each rule is registered by its IssueCode and is toggled independently via
configuration. Adding a new check means adding a new Entry to this registry;
the engine never needs to know about individual rule implementations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ..contracts import (
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
    """Immutable definition of a single validation rule.

    Used by RuleRegistry to look up rules by code and to enable
    dynamic toggling (on/off) via configuration.
    """

    code: str  # e.g. "PARSE_01"
    layer: Layer
    severity: IssueSeverity
    applies_to: tuple[str, ...]  # (statement_type, maybe)
    message: str
    fix_hint: str = ""
    enabled: bool = True  # can be turned off via config


@dataclass(frozen=True, slots=True)
class RuleRegistry:
    """Centralised collection of all M9 validation rules.

    Provides:
    - lookup(code) → RuleEntry | None
    - enabled(rules) → dict of enabled entries
    - toggle(code, enabled) → bool
    - all_entries() → list of all entries
    """

    entries: list[RuleEntry] = field(default_factory=list)

    def lookup(self, code: str) -> RuleEntry | None:
        for e in self.entries:
            if e.code == code:
                return e
        return None

    def enabled(self, rules: dict[str, bool]) -> dict[str, bool]:
        """Filter entries according to a config dict (code → enabled)."""
        return {code: rules.get(code, True) for code in self.entries}

    def toggle(self, code: str, enabled: bool) -> bool:
        """Enable or disable a rule by code. Returns current state."""
        for i, e in enumerate(self.entries):
            if e.code == code:
                self.entries[i].enabled = enabled
                return e.enabled
        return False

    def all_entries(self) -> list[RuleEntry]:
        return list(self.entries)

    def __len__(self) -> int:
        return len(self.entries)
