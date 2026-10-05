"""validator — Static Validator & Anti-Pattern Detector.

Pure checker: takes normalized SQL plus a schema snapshot and decides:
(1) whether the statement is valid/safe/sensible WITHOUT executing anything, and
(2) what the result is so cost estimation and execution gates can route it.

Never connects to a database. Never modifies anything.
"""

from __future__ import annotations

from .contracts import (
    Issue,
    IssueCode,
    Layer,
    Severity,
    StatementType,
    Status,
    ValidationResult,
)
from .engine import (
    validate_parse,
    validate_policy,
    validate_schema,
    validate_semantic,
    validate_query_anti_patterns,
    validate_schema_anti_patterns,
    run_validation,
)
from .rules import RuleRegistry, RuleEntry, DEFAULT_RULES
from .interfaces import AuditLogger, SchemaProvider, FakeSchemaProvider, ListAuditLogger

__all__ = [
    "Issue",
    "IssueCode",
    "Layer",
    "Severity",
    "StatementType",
    "Status",
    "ValidationResult",
    "RuleRegistry",
    "RuleEntry",
    "DEFAULT_RULES",
    "validate_parse",
    "validate_policy",
    "validate_schema",
    "validate_semantic",
    "validate_query_anti_patterns",
    "validate_schema_anti_patterns",
    "run_validation",
    "AuditLogger",
    "ListAuditLogger",
    "SchemaProvider",
    "FakeSchemaProvider",
]
__version__ = "0.2.0"
