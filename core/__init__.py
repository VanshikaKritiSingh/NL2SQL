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
"""

from __future__ import annotations

# 1. Orchestration & Tracing
from core.orchestrator import EndToEndNL2SQLOrchestrator, SemanticSQLSynthesizer
from core.pipeline_trace import execute_pipeline_trace, build_default_demo_schema

# 2. Schema Linking & Trie Grounding
from core.schema_linker import (
    SchemaLinker,
    CategoricalValueTrie,
    LinkedSchemaContext,
    TableMeta,
    ColumnMeta,
)

# 3. Multi-Paradigm Routing & Semantic Decomposition
from core.paradigm_suggestor import (
    SpeculativeParadigmSuggestor,
    DatabaseParadigm,
    CLEFDiscourseDrafter,
    ParadigmSuggestion,
)
from core.semantic_decomposer import (
    SemanticDecomposer,
    SemanticIntentClassifier,
    SchemaMismatchGuard,
    NLArchitectureParser,
    IntentResult,
    EntitySpec,
    ArchitectureResult,
)

# 4. Dialect Conversion & Transpilation
from core.dialect_converter import (
    DeterministicDialectConverter,
    TranspilationResult,
    DialectSQL,
    convertSqlStatementToTargetDialects,
    convertSqlStatementToPostgreSqlDialect,
    convertSqlStatementToMySqlDialect,
    convertSqlStatementToOracleDialect,
    convertSqlStatementToMicrosoftSqlServerDialect,
    convertSqlStatementToMicrosoftAccessDialect,
    convert_sql,
)

# 5. AST Sanitization & Parameter Extraction
from core.sanitizer import (
    sanitizeAndExtractParametersFromSqlAst,
    sanitizeAndParameterizePostgreSqlStatement,
    verifyAbstractSyntaxTreeContainsNoRawLiterals,
    parseSqlStatementIntoAbstractSyntaxTree,
    detectMultipleStackedSqlStatements,
    ParameterizedStatement,
    SanitizationError,
    sanitize_sql,
    parse_sql,
    is_multi_statement,
)

# 6. Static AST Validation
from core.validator import (
    executeFullSixLayerValidationPipeline,
    executeParseLayerValidation,
    executePolicyLayerValidation,
    executeSchemaLayerValidation,
    executeSemanticLayerValidation,
    executeQueryAntiPatternValidation,
    executeSchemaAntiPatternValidation,
    createValidationIssue,
    run_validation,
    validate_parse,
    validate_policy,
    validate_schema,
    validate_semantic,
    validate_query_anti_patterns,
    validate_schema_anti_patterns,
    issue,
    ValidationResult,
    Issue,
    IssueCode,
    Layer,
    Severity,
    StatementType,
    Status,
    RuleRegistry,
    RuleEntry,
    DEFAULT_RULES,
    SchemaProvider as ValidatorSchemaProvider,
    FakeSchemaProvider,
    AuditLogger,
    ListAuditLogger,
)

# 7. Heuristic Cost & Blast-Radius Engine
from core.cost_estimator import (
    HeuristicCostEngine,
    CostReport,
    Thresholds,
    DEFAULT_THRESHOLDS,
)

# 8. OS Concurrency Engine
from core.os_engine import (
    WFQScheduler,
    WaitForGraph,
    DeadlockDetector,
    LockManager,
    LockMode,
    WorkingSetPager,
    PipelineAuditLog,
    AuditEvent,
)

# 9. DBMS Connectors
from core.connectors import (
    default_registry,
    BaseDBConnector,
    ConnectionConfig,
    SchemaMetadata,
    QueryResult,
)

__all__ = [
    # 1. Orchestration
    "EndToEndNL2SQLOrchestrator",
    "SemanticSQLSynthesizer",
    "execute_pipeline_trace",
    "build_default_demo_schema",
    # 2. Schema Linking
    "SchemaLinker",
    "CategoricalValueTrie",
    "LinkedSchemaContext",
    "TableMeta",
    "ColumnMeta",
    # 3. Paradigms & Decomposition
    "SpeculativeParadigmSuggestor",
    "DatabaseParadigm",
    "CLEFDiscourseDrafter",
    "ParadigmSuggestion",
    "SemanticDecomposer",
    "SemanticIntentClassifier",
    "SchemaMismatchGuard",
    "NLArchitectureParser",
    "IntentResult",
    "EntitySpec",
    "ArchitectureResult",
    # 4. Dialect Conversion
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
    # 5. Sanitization
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
    # 6. Validation
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
    "ValidatorSchemaProvider",
    "FakeSchemaProvider",
    "AuditLogger",
    "ListAuditLogger",
    # 7. Cost Estimation
    "HeuristicCostEngine",
    "CostReport",
    "Thresholds",
    "DEFAULT_THRESHOLDS",
    # 8. OS Engine
    "WFQScheduler",
    "WaitForGraph",
    "DeadlockDetector",
    "LockManager",
    "LockMode",
    "WorkingSetPager",
    "PipelineAuditLog",
    "AuditEvent",
    # 9. Connectors
    "default_registry",
    "BaseDBConnector",
    "ConnectionConfig",
    "SchemaMetadata",
    "QueryResult",
]
