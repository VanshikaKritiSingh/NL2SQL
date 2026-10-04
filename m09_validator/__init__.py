"""M9 — Static Validator & Anti-Pattern Detector.

Pure checker: takes normalized SQL plus a schema snapshot and decides
(1) whether the statement is valid/safe/sensible WITHOUT executing anything, and
(2) what the result is so M10/M12 can route it.

Never connects to a database. Never modifies anything.
"""

from __future__ import annotations

from .contracts import (
    Issue,
    IssueCode,
    RetryFeedback,
    ValidationResult,
    parse_yaml_schema,
)
from .engine import (
    RuleRegistry,
    StaticValidator,
    ValidationContext,
    validate,
    validator,
)
from .interfaces import AuditLogger, SchemaProvider

__all__ = [
    "Issue",
    "IssueCode",
    "RetryFeedback",
    "ValidationResult",
    "parse_yaml_schema",
    "RuleRegistry",
    "StaticValidator",
    "ValidationContext",
    "validate",
    "validator",
    "AuditLogger",
    "SchemaProvider",
]
__version__ = "0.1.0a"
