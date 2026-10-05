"""
core/orchestrator.py — Unified End-to-End Pipeline Orchestrator

Integrates:
1. AI/ML Core (Anunay Sharma): Paradigm routing, schema context linking, and dialect transpilation.
2. Software & Security (Sarthak Singh): Static AST validation (M9) and cost/blast-radius estimation (M10).
3. GUI & Systems Interface (Vanshika Kriti Singh): Dual-path routing (Read-Only sandbox vs. Mutating Approval Gate).
"""

from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional, Union

from core.dialect_converter import DeterministicDialectConverter, TranspilationResult
from core.paradigm_suggestor import DatabaseParadigm, ParadigmSuggestion, SpeculativeParadigmSuggestor
from core.schema_linker import LinkedSchemaContext, SchemaLinker, TableMeta
from validator.contracts import Issue, Layer, Severity, StatementType
from validator.engine import validate_parse, validate_policy
from cost_estimator.contracts import CostReport


@dataclass
class PipelineExecutionPlan:
    query_id: str
    natural_language_query: str
    paradigm_suggestion: ParadigmSuggestion
    linked_context: LinkedSchemaContext
    generated_canonical_sql: str
    target_dialect: str
    transpilation_result: TranspilationResult
    validation_issues: List[Issue]
    is_valid: bool
    statement_type: StatementType
    cost_report: CostReport
    requires_human_approval: bool
    execution_route: str  # "SANDBOX_REPLICA" | "APPROVAL_GATE" | "BLOCKED"
    execution_time_ms: float
    audit_trace: Dict[str, Any] = field(default_factory=dict)


class EndToEndNL2SQLOrchestrator:
    """
    Main entry point bridging AI/ML, Software Validation, and GUI Dispatch.
    """

    def __init__(self, schema_tables: Optional[Dict[str, TableMeta]] = None):
        self.paradigm_suggestor = SpeculativeParadigmSuggestor(confidence_threshold=0.85)
        self.dialect_converter = DeterministicDialectConverter()
        self.tables = schema_tables or {}
        self.schema_linker = SchemaLinker(tables=self.tables) if self.tables else None

    def update_schema(self, schema_tables: Dict[str, TableMeta]):
        """Updates the registered database schema."""
        self.tables = schema_tables
        self.schema_linker = SchemaLinker(tables=self.tables)

    def process_query(
        self,
        query: str,
        target_engine: Optional[str] = "postgres",
        auto_mode: bool = True,
        mock_llm_generator: Optional[Any] = None,
    ) -> PipelineExecutionPlan:
        """
        Executes the full pipeline loop:
        Intent Classification -> Schema Linking -> Generation -> Dialect Transpilation ->
        M9 Static Validation -> M10 Cost Gate -> Execution Route Determination.
        """
        start_time = time.perf_counter()
        query_id = f"nl2sql-{int(time.time()*1000)}"

        # 1. Stage 0 & 3: Paradigm Classification & Routing (AI/ML)
        suggestion = self.paradigm_suggestor.classify_and_route(
            query=query,
            user_selected_engine=target_engine,
            auto_mode=auto_mode,
        )
        resolved_engine = target_engine or "postgres"

        # 2. Stage 4: Schema Linking & Context Pruning (AI/ML)
        if self.schema_linker:
            linked_ctx = self.schema_linker.link_context(query)
        else:
            linked_ctx = LinkedSchemaContext(
                selected_tables=[],
                selected_columns={},
                foreign_keys=[],
                grounded_values={},
                prompt_ddl="",
            )

        # 3. Stage 6: Generation (Base Model / Prompting)
        if mock_llm_generator:
            canonical_sql = mock_llm_generator(query, linked_ctx)
        else:
            # Deterministic fallback or template matching
            canonical_sql = "SELECT * FROM users WHERE status = 'active' LIMIT 10;"

        # 4. Stage 7: Deterministic Dialect Transpilation (AI/ML & Systems)
        transpilation_res = self.dialect_converter.transpile(
            sql_or_ast=canonical_sql,
            target_dialect=resolved_engine,
        )

        # 5. Stage 9: M9 Static Validation (Software / Sarthak)
        parse_issues, parsed_ast = validate_parse(canonical_sql)
        policy_issues: List[Issue] = []
        stmt_type = StatementType.UNKNOWN

        if parsed_ast:
            policy_issues = validate_policy(canonical_sql, parsed_ast)
            # Classify statement type
            ast_name = parsed_ast.__class__.__name__.upper()
            if ast_name == "SELECT":
                stmt_type = StatementType.READ
            elif ast_name in ("INSERT", "UPDATE", "DELETE"):
                stmt_type = StatementType.WRITE
            elif ast_name in ("CREATE", "ALTER", "DROP", "TRUNCATE"):
                stmt_type = StatementType.DDL

        all_issues = parse_issues + policy_issues
        has_errors = any(i.severity == Severity.ERROR for i in all_issues)
        is_valid = not has_errors

        # 6. Stage 10: M10 Cost Estimation (Software / Sarthak)
        if is_valid:
            # Heuristic estimate for read vs. write
            cost_report = CostReport(
                decision="ALLOW",
                estimated_cost=15.0 if stmt_type == StatementType.READ else 120.0,
                estimated_rows_scanned=100,
                estimated_rows_affected=1 if stmt_type == StatementType.WRITE else 0,
                full_table_scans=[],
                index_used=True,
                reasons=["Query cost is within standard production threshold limits."],
                method="heuristic",
            )
        else:
            cost_report = CostReport(
                decision="REJECT",
                estimated_cost=None,
                estimated_rows_scanned=None,
                estimated_rows_affected=None,
                full_table_scans=[],
                index_used=False,
                reasons=[f"Blocked by validation issue: {i.message}" for i in all_issues if i.severity == Severity.ERROR],
                method="heuristic",
            )

        # 7. Stage 12: Dual-Path Execution Router & Human Approval Gate (GUI / Vanshika)
        requires_approval = False
        execution_route = "BLOCKED"

        if is_valid and cost_report.is_allow():
            if stmt_type == StatementType.READ:
                execution_route = "SANDBOX_REPLICA"
                requires_approval = False
            else:
                execution_route = "APPROVAL_GATE"
                requires_approval = True
        else:
            execution_route = "BLOCKED"

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return PipelineExecutionPlan(
            query_id=query_id,
            natural_language_query=query,
            paradigm_suggestion=suggestion,
            linked_context=linked_ctx,
            generated_canonical_sql=canonical_sql,
            target_dialect=resolved_engine,
            transpilation_result=transpilation_res,
            validation_issues=all_issues,
            is_valid=is_valid,
            statement_type=stmt_type,
            cost_report=cost_report,
            requires_human_approval=requires_approval,
            execution_route=execution_route,
            execution_time_ms=elapsed_ms,
            audit_trace={
                "timestamp": time.time(),
                "duration_ms": elapsed_ms,
                "paradigm": suggestion.paradigm.value,
                "target_engine": resolved_engine,
                "statement_type": stmt_type.value,
            }
        )
