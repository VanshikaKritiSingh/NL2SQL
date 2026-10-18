"""
tests/test_centralized_core_architecture.py — Verification of Centralized Core Engine & Subsystems.

Verifies:
1. All engine functional domains export cleanly from root `core`.
2. Root shims `validator` and `cost_estimator` redirect to `core.validator` and `core.cost_estimator`.
3. Unified AST parser in `core.sanitizer` and `core.validator.interfaces`.
4. Unified SchemaProvider interface supporting both `get_rows` and `get_row_count`.
5. PipelineAuditLog integration with validation audit logging.
"""

import pytest
import core
from core import (
    EndToEndNL2SQLOrchestrator,
    SemanticSQLSynthesizer,
    SchemaLinker,
    SpeculativeParadigmSuggestor,
    DeterministicDialectConverter,
    sanitizeAndExtractParametersFromSqlAst,
    parseSqlStatementIntoAbstractSyntaxTree,
    detectMultipleStackedSqlStatements,
    executeFullSixLayerValidationPipeline,
    HeuristicCostEngine,
    CostReport,
    WFQScheduler,
    WaitForGraph,
    DeadlockDetector,
    LockManager,
    WorkingSetPager,
    PipelineAuditLog,
    AuditEvent,
    default_registry,
    FakeSchemaProvider,
    ValidationResult,
    Status,
)


def testCorePackageCentralizedSubsystemExports():
    """Verify that core package exposes all 9 functional subsystems directly."""
    assert EndToEndNL2SQLOrchestrator is not None
    assert SemanticSQLSynthesizer is not None
    assert SchemaLinker is not None
    assert SpeculativeParadigmSuggestor is not None
    assert DeterministicDialectConverter is not None
    assert sanitizeAndExtractParametersFromSqlAst is not None
    assert executeFullSixLayerValidationPipeline is not None
    assert HeuristicCostEngine is not None
    assert WFQScheduler is not None
    assert default_registry is not None


def testRootCompatibilityShimsForValidatorAndCostEstimator():
    """Verify root validator and cost_estimator packages cleanly forward to core."""
    import validator
    import cost_estimator
    from validator.contracts import Issue, Layer, Severity
    from validator.engine import run_validation
    from cost_estimator.contracts import CostReport as ShimCostReport
    from cost_estimator.engine import HeuristicCostEngine as ShimHeuristicCostEngine

    assert validator.executeFullSixLayerValidationPipeline is executeFullSixLayerValidationPipeline
    assert validator.run_validation is run_validation
    assert ShimCostReport is CostReport
    assert ShimHeuristicCostEngine is HeuristicCostEngine


def testUnifiedAstParsingAndStackedStatementDetection():
    """Verify AST parser correctly detects single vs multiple statements and parses into AST."""
    single_sql = "SELECT id, username FROM users WHERE active = true;"
    multi_sql = "SELECT id FROM users; DELETE FROM orders;"

    assert detectMultipleStackedSqlStatements(single_sql) is False
    assert detectMultipleStackedSqlStatements(multi_sql) is True

    ast = parseSqlStatementIntoAbstractSyntaxTree(single_sql)
    assert ast is not None

    with pytest.raises(ValueError):
        parseSqlStatementIntoAbstractSyntaxTree(multi_sql)


def testUnifiedSchemaProviderRowCountAliases():
    """Verify FakeSchemaProvider supports get_rows, get_row_count, and retrieveEstimatedTableRowCount."""
    schema_spec = {
        "tables": [
            {
                "name": "accounts",
                "columns": {"id": "INTEGER", "balance": "DECIMAL"},
                "pk": ["id"],
                "row_count": 12500,
            }
        ]
    }
    provider = FakeSchemaProvider(schema_spec)
    assert provider.retrieveEstimatedTableRowCount("accounts") == 12500
    assert provider.get_rows("accounts") == 12500
    assert provider.get_row_count("accounts") == 12500
    assert provider.retrieveAllCatalogTableNames() == ("accounts",)
    assert provider.get_tables() == ("accounts",)


def testPipelineAuditLogValidationRecordingIntegration(tmp_path):
    """Verify PipelineAuditLog logs validation events conforming to AuditLogger."""
    test_log_path = str(tmp_path / "test_audit.jsonl")
    audit_log = PipelineAuditLog(path=test_log_path)

    fake_result = ValidationResult(status=Status.VALID, statement_type=core.StatementType.READ, issues=())
    audit_log.recordValidationAuditEntry(
        sql="SELECT 1;",
        result=fake_result,
        user_id="integration_tester",
        query_id="qid_12345",
    )

    events = audit_log.retrieveAuditEventsForQueryIdentifier("qid_12345")
    assert len(events) == 1
    assert events[0].operation == "VALIDATE"
    assert events[0].user_id == "integration_tester"
    assert events[0].details["status"].lower() == "valid"
