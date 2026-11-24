"""
core — Centralized NL2SQL Pipeline and Engine Subsystem.

Organized by functional domains:
1. Orchestration & Execution Tracing:
   - EndToEndNL2SQLOrchestrator, SemanticSQLSynthesizer, execute_pipeline_trace
2. Schema Linking & Categorical Value Grounding:
   - SchemaLinker, CategoricalValueTrie, LinkedSchemaContext, TableMeta, ColumnMeta
3. Multi-Paradigm Routing & Semantic Decomposition:
   - SpeculativeParadigmSuggestor, DatabaseParadigm, CLEFDiscourseDrafter, ParadigmSuggestion
   - SemanticDecomposer, SemanticIntentClassifier, SchemaMismatchGuard, NLArchitectureParser
4. Deterministic Dialect Conversion & Transpilation:
   - DeterministicDialectConverter, TranspilationResult, DialectSQL, convertSqlStatementToTargetDialects
5. AST Sanitization & Parameter Extraction:
   - sanitizeAndExtractParametersFromSqlAst, parseSqlStatementIntoAbstractSyntaxTree, detectMultipleStackedSqlStatements
6. 6-Layer Static AST Validation Engine:
   - executeFullSixLayerValidationPipeline (run_validation), ValidationResult, Issue, RuleRegistry, SchemaProvider
7. Heuristic Cost & Blast-Radius Engine:
   - HeuristicCostEngine, CostReport, Thresholds
8. Operating System Concurrency Engine:
   - WFQScheduler, WaitForGraph, DeadlockDetector, LockManager, WorkingSetPager, PipelineAuditLog
9. DBMS Connectors & Connection Registry:
   - default_registry, BaseDBConnector, ConnectionConfig, SchemaMetadata, QueryResult

Import policy (DA-21)
=====================
This package uses PEP 562 module-level ``__getattr__`` to import lazily. Importing
a stdlib-only submodule such as ``core.os_engine.lock_manager`` must NOT drag in
``sqlglot`` and the rest of the heavy pipeline. No eager third-party import lives
in this file; every symbol resolves on first attribute access.
"""

from __future__ import annotations

import importlib
from typing import Any, Dict, Tuple

# module path -> names re-exported from it
_EXPORTS_BY_MODULE: Dict[str, Tuple[str, ...]] = {
    # 1. Orchestration & Tracing
    "core.orchestrator": (
        "EndToEndNL2SQLOrchestrator",
        "SemanticSQLSynthesizer",
    ),
    "core.pipeline_trace": (
        "execute_pipeline_trace",
        "build_default_demo_schema",
    ),
    # 2. Schema Linking & Trie Grounding
    "core.schema_linker": (
        "SchemaLinker",
        "CategoricalValueTrie",
        "LinkedSchemaContext",
        "TableMeta",
        "ColumnMeta",
    ),
    # 3. Multi-Paradigm Routing & Semantic Decomposition
    "core.paradigm_suggestor": (
        "SpeculativeParadigmSuggestor",
        "DatabaseParadigm",
        "CLEFDiscourseDrafter",
        "ParadigmSuggestion",
    ),
    "core.semantic_decomposer": (
        "SemanticDecomposer",
        "SemanticIntentClassifier",
        "SchemaMismatchGuard",
        "NLArchitectureParser",
        "IntentResult",
        "EntitySpec",
        "ArchitectureResult",
    ),
    # 4. Dialect Conversion & Transpilation
    "core.dialect_converter": (
        "DeterministicDialectConverter",
        "TranspilationResult",
        "DialectSQL",
        "convertSqlStatementToTargetDialects",
        "convertSqlStatementToPostgreSqlDialect",
        "convertSqlStatementToMySqlDialect",
        "convertSqlStatementToOracleDialect",
        "convertSqlStatementToMicrosoftSqlServerDialect",
        "convertSqlStatementToMicrosoftAccessDialect",
        "convert_sql",
    ),
    # 5. AST Sanitization & Parameter Extraction
    "core.sanitizer": (
        "sanitizeAndExtractParametersFromSqlAst",
        "sanitizeAndParameterizePostgreSqlStatement",
        "verifyAbstractSyntaxTreeContainsNoRawLiterals",
        "parseSqlStatementIntoAbstractSyntaxTree",
        "detectMultipleStackedSqlStatements",
        "ParameterizedStatement",
        "SanitizationError",
        "sanitize_sql",
        "parse_sql",
        "is_multi_statement",
    ),
    # 6. Static AST Validation
    "core.validator": (
        "executeFullSixLayerValidationPipeline",
        "executeParseLayerValidation",
        "executePolicyLayerValidation",
        "executeSchemaLayerValidation",
        "executeSemanticLayerValidation",
        "executeQueryAntiPatternValidation",
        "executeSchemaAntiPatternValidation",
        "createValidationIssue",
        "run_validation",
        "validate_parse",
        "validate_policy",
        "validate_schema",
        "validate_semantic",
        "validate_query_anti_patterns",
        "validate_schema_anti_patterns",
        "issue",
        "ValidationResult",
        "Issue",
        "IssueCode",
        "Layer",
        "Severity",
        "StatementType",
        "Status",
        "RuleRegistry",
        "RuleEntry",
        "DEFAULT_RULES",
        "FakeSchemaProvider",
        "AuditLogger",
        "ListAuditLogger",
    ),
    # 7. Heuristic Cost & Blast-Radius Engine
    "core.cost_estimator": (
        "HeuristicCostEngine",
        "CostReport",
        "Thresholds",
        "DEFAULT_THRESHOLDS",
    ),
    # 8. OS Concurrency Engine
    "core.os_engine": (
        "WFQScheduler",
        "WaitForGraph",
        "DeadlockDetector",
        "LockManager",
        "LockMode",
        "WorkingSetPager",
        "PipelineAuditLog",
        "AuditEvent",
    ),
    # 9. DBMS Connectors
    "core.connectors": (
        "default_registry",
        "BaseDBConnector",
        "ConnectionConfig",
        "SchemaMetadata",
        "QueryResult",
    ),
}

# name -> module path, flattened for O(1) lookup
_LAZY_EXPORTS: Dict[str, str] = {
    name: mod_path
    for mod_path, names in _EXPORTS_BY_MODULE.items()
    for name in names
}

# Alias for the validator's SchemaProvider, kept under a distinct local name.
_ALIASES: Dict[str, str] = {"ValidatorSchemaProvider": "core.validator"}

__all__ = sorted([*_LAZY_EXPORTS, *_ALIASES])


def __getattr__(name: str) -> Any:
    """PEP 562 lazy attribute access — import a submodule only when first used."""
    mod_path = _LAZY_EXPORTS.get(name) or _ALIASES.get(name)
    if mod_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = importlib.import_module(mod_path)
    if name == "ValidatorSchemaProvider":
        value = getattr(module, "SchemaProvider")
    else:
        value = getattr(module, name)

    globals()[name] = value  # cache so subsequent access is a plain dict hit
    return value


def __dir__() -> list:
    return sorted(set(globals()) | set(__all__))
