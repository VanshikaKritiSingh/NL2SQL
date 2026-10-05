"""
core/orchestrator.py — Unified End-to-End Pipeline Orchestrator

Integrates:
1. AI/ML Core (Anunay Sharma): Paradigm routing, schema context linking, semantic query synthesis / LLM generation, and dialect transpilation.
2. Software & Security (Sarthak Singh): 6-Layer Static AST validation and heuristic cost/blast-radius estimation.
3. GUI & Systems Interface (Vanshika Kriti Singh): Dual-path routing (Read-Only sandbox vs. Mutating Approval Gate).
"""

from dataclasses import dataclass, field
import json
import re
import time
from typing import Any, Callable, Dict, List, Optional, Union

import sqlglot
from sqlglot import exp

from core.dialect_converter import DeterministicDialectConverter, TranspilationResult
from core.paradigm_suggestor import DatabaseParadigm, ParadigmSuggestion, SpeculativeParadigmSuggestor
from core.schema_linker import LinkedSchemaContext, SchemaLinker, TableMeta
from validator.contracts import Issue, Layer, Severity, StatementType, Status, ValidationResult
from validator.engine import run_validation
from validator.interfaces import FakeSchemaProvider
from cost_estimator.contracts import CostReport
from cost_estimator.engine import HeuristicCostEngine


class SemanticSQLSynthesizer:
    """
    Intelligent offline AST-driven SQL synthesizer for natural language queries.
    Constructs deterministic, schema-grounded SQL queries based on the linked schema context,
    grounded values, intent verbs, and projection requests when offline or without an active LLM daemon.
    """

    def synthesize(self, query: str, context: LinkedSchemaContext) -> str:
        q_lower = query.lower().strip()
        tables = context.selected_tables or ["users"]
        primary_table = tables[0]
        pk_col = self._get_primary_key(context, primary_table)

        # 1. Detect Mutating DML / DDL operations
        if re.search(r"\b(delete|remove|purge|erase)\b", q_lower):
            where_part = self._build_where_clause(q_lower, context, primary_table, pk_col)
            return f"DELETE FROM {primary_table} WHERE {where_part};"

        if re.search(r"\b(update|change|modify|increase|set)\b", q_lower):
            set_expr = "status = 'active'"
            if "price" in q_lower:
                if "10%" in q_lower or "10 percent" in q_lower:
                    set_expr = "price = ROUND(price * 1.10, 2)"
                else:
                    set_expr = "price = ROUND(price * 1.05, 2)"
            elif primary_table in context.selected_columns:
                for c in context.selected_columns[primary_table]:
                    if c in q_lower and c != pk_col:
                        set_expr = f"{c} = 'updated'"
                        break

            where_part = self._build_where_clause(q_lower, context, primary_table, pk_col)
            return f"UPDATE {primary_table} SET {set_expr} WHERE {where_part};"

        if re.search(r"\b(alter|add\b.*?\bcolumn)\b", q_lower) or ("add" in q_lower and "column" in q_lower):
            col_match = re.search(r"\badd\s+(?:a\s+)?([a-z0-9_]+)\s+column\b", q_lower)
            col_name = col_match.group(1) if col_match else "discount_code"
            target_table = primary_table
            for t in tables:
                if t in q_lower:
                    target_table = t
                    break
            return f"ALTER TABLE {target_table} ADD COLUMN {col_name} VARCHAR(50) DEFAULT NULL;"

        if re.search(r"\b(drop database|drop schema)\b", q_lower):
            return "DROP DATABASE production;"

        if re.search(r"\b(drop table)\b", q_lower):
            return f"DROP TABLE {primary_table};"

        # 2. SELECT Projections
        projections: List[str] = []
        is_count = bool(re.search(r"\b(count|how many|number of)\b", q_lower))
        is_avg = bool(re.search(r"\b(average|avg|mean)\b", q_lower))
        is_sum = bool(re.search(r"\b(sum|total amount|total)\b", q_lower))

        if is_count:
            projections.append("COUNT(*)")
        elif is_avg:
            projections.append("AVG(salary)" if "salary" in q_lower else "AVG(price)" if "price" in q_lower else "AVG(total_amount)")
        elif is_sum:
            projections.append("SUM(total_amount)" if "total" in q_lower or "amount" in q_lower else "SUM(price)")
        else:
            # Pick projected columns from primary table first
            cols = context.selected_columns.get(primary_table, [])
            for c in cols:
                if c in q_lower or len(projections) < 3:
                    projections.append(f"{primary_table}.{c}" if len(tables) > 1 else c)
            if not projections:
                projections = ["*"]

        # 3. Spanning JOIN Tree from Primary Table
        join_clauses = []
        visited_tables = {primary_table}
        if len(tables) > 1 and context.foreign_keys:
            # Iteratively connect remaining tables
            while len(visited_tables) < len(tables):
                added_any = False
                for src_t, src_c, tgt_t, tgt_c in context.foreign_keys:
                    if src_t in visited_tables and tgt_t in tables and tgt_t not in visited_tables:
                        join_clauses.append(f"JOIN {tgt_t} ON {src_t}.{src_c} = {tgt_t}.{tgt_c}")
                        visited_tables.add(tgt_t)
                        added_any = True
                        break
                    elif tgt_t in visited_tables and src_t in tables and src_t not in visited_tables:
                        join_clauses.append(f"JOIN {src_t} ON {tgt_t}.{tgt_c} = {src_t}.{src_c}")
                        visited_tables.add(src_t)
                        added_any = True
                        break
                if not added_any:
                    break

        join_str = (" " + " ".join(join_clauses)) if join_clauses else ""

        # 4. WHERE Filter
        where_conds = []
        # Add grounded values
        for val, col_ref in context.grounded_values.items():
            t, c = col_ref.split(".")
            ref = f"{t}.{c}" if len(tables) > 1 else c
            where_conds.append(f"{ref} = '{val}'")

        # Additional semantic filter checks
        if "active" in q_lower and not context.grounded_values:
            where_conds.append(f"{primary_table}.status = 'active'" if len(tables) > 1 else "status = 'active'")
        if re.search(r"\bage\s*(>|>=|<|<=|=|\babove\b|\bover\b)\s*(\d+)", q_lower):
            m = re.search(r"\bage\s*(?:>|>=|<|<=|=|\babove\b|\bover\b)\s*(\d+)", q_lower)
            if m:
                where_conds.append(f"age >= {m.group(1)}")

        where_str = f" WHERE {' AND '.join(where_conds)}" if where_conds else ""

        # 5. GROUP BY
        group_str = ""
        if (is_count or is_avg or is_sum) and len(projections) > 1:
            group_cols = [p for p in projections if not any(fn in p for fn in ["COUNT", "AVG", "SUM", "MIN", "MAX"])]
            if group_cols:
                group_str = f" GROUP BY {', '.join(group_cols)}"

        # 6. ORDER BY & LIMIT
        order_str = ""
        if "latest" in q_lower or "recent" in q_lower:
            order_str = " ORDER BY created_at DESC"
        elif "top" in q_lower or "highest" in q_lower:
            order_str = " ORDER BY total_amount DESC"

        limit_match = re.search(r"\b(?:top|limit|first)\s+(\d+)\b", q_lower)
        limit_val = limit_match.group(1) if limit_match else ("10" if not is_count else "")
        limit_str = f" LIMIT {limit_val}" if limit_val else ""

        proj_str = ", ".join(projections)
        return f"SELECT {proj_str} FROM {primary_table}{join_str}{where_str}{group_str}{order_str}{limit_str};".strip()

    def _get_primary_key(self, context: LinkedSchemaContext, primary_table: str) -> str:
        cols = context.selected_columns.get(primary_table, [])
        for c in cols:
            if "id" in c:
                return c
        return cols[0] if cols else "id"

    def _build_where_clause(self, q_lower: str, context: LinkedSchemaContext, primary_table: str, pk_col: str) -> str:
        for val, col_ref in context.grounded_values.items():
            t, c = col_ref.split(".")
            if t == primary_table:
                return f"{c} = '{val}'"
        if "inactive" in q_lower:
            return "status = 'inactive'"
        if "id" in q_lower:
            m = re.search(r"\bid\s*(?:=|\bis\b)\s*(\d+)", q_lower)
            if m:
                return f"{pk_col} = {m.group(1)}"
        return f"{pk_col} > 0"


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
        self.synthesizer = SemanticSQLSynthesizer()
        self.cost_engine = HeuristicCostEngine()
        self.tables = schema_tables or {}
        self.schema_linker = SchemaLinker(tables=self.tables) if self.tables else None
        self._schema_provider = self._build_fake_schema_provider() if self.tables else None

    def _build_fake_schema_provider(self) -> FakeSchemaProvider:
        raw_tables = []
        for t_name, t_meta in self.tables.items():
            cols = {c_name: c_meta.dtype for c_name, c_meta in t_meta.columns.items()}
            pks = [c_name for c_name, c_meta in t_meta.columns.items() if c_meta.is_pk]
            fks = {c_name: (c_meta.fk_target_table, c_meta.fk_target_column or "id") for c_name, c_meta in t_meta.columns.items() if c_meta.is_fk and c_meta.fk_target_table}
            raw_tables.append({
                "name": t_name,
                "columns": cols,
                "pk": pks,
                "fks": fks,
                "indexes": {},
                "row_count": 50000,
                "nullable": {},
            })
        return FakeSchemaProvider({"tables": raw_tables})

    def update_schema(self, schema_tables: Dict[str, TableMeta]):
        """Updates the registered database schema."""
        self.tables = schema_tables
        self.schema_linker = SchemaLinker(tables=self.tables)
        self._schema_provider = self._build_fake_schema_provider()

    def process_query(
        self,
        query: str,
        target_engine: Optional[str] = "postgres",
        auto_mode: bool = True,
        mock_llm_generator: Optional[Callable[[str, LinkedSchemaContext], str]] = None,
    ) -> PipelineExecutionPlan:
        """
        Executes the full 16-stage human-supervised pipeline loop:
        Intent Classification -> Schema Linking -> Generation -> Dialect Transpilation ->
        M9 Static Validation -> M10 Cost Gate -> Execution Route Determination.
        """
        start_time = time.perf_counter()
        query_id = f"nl2sql-{int(time.time()*1000)}"

        # 1. Stage 0 & 3: Paradigm Classification & Routing (AI/ML)
        is_auto = (target_engine == "auto" or auto_mode or not target_engine)
        suggestion = self.paradigm_suggestor.classify_and_route(
            query=query,
            user_selected_engine=None if target_engine == "auto" else target_engine,
            auto_mode=is_auto,
        )
        if target_engine == "auto" or not target_engine:
            rec = suggestion.recommended_engines[0].lower() if suggestion.recommended_engines else "postgres"
            if "neo4j" in rec or "opencypher" in rec or "graph" in rec:
                resolved_engine = "opencypher"
            elif "mongo" in rec or "document" in rec:
                resolved_engine = "mongodb"
            elif "duck" in rec:
                resolved_engine = "duckdb"
            elif "click" in rec:
                resolved_engine = "clickhouse"
            elif "mysql" in rec:
                resolved_engine = "mysql"
            elif "sqlite" in rec:
                resolved_engine = "sqlite"
            elif "oracle" in rec:
                resolved_engine = "oracle"
            elif "sqlserver" in rec or "sql server" in rec:
                resolved_engine = "sqlserver"
            else:
                resolved_engine = "postgres"
        else:
            resolved_engine = target_engine

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

        # 3. Stage 6: Generation (Base Model / Prompting / Semantic Synthesizer)
        if mock_llm_generator:
            canonical_sql = mock_llm_generator(query, linked_ctx)
        else:
            canonical_sql = self.synthesizer.synthesize(query, linked_ctx)

        # 4. Stage 7: Deterministic Dialect Transpilation (AI/ML & Systems)
        try:
            transpilation_res = self.dialect_converter.transpile(
                sql_or_ast=canonical_sql,
                target_dialect=resolved_engine,
            )
        except Exception as e:
            transpilation_res = TranspilationResult(
                target_dialect=resolved_engine,
                compiled_query=canonical_sql,
                execution_time_ms=0.0,
                source_ast_type="Unknown",
                is_native_sql=True,
                metadata={"error": str(e)}
            )

        # 5. Stage 9: 6-Layer Static Validation (Software / Sarthak)
        validation_res: ValidationResult = run_validation(
            sql=canonical_sql,
            dialect="postgres",
            schema=self._schema_provider,
        )

        all_issues = list(validation_res.issues)
        stmt_type = validation_res.statement_type
        is_valid = validation_res.status != Status.INVALID

        # 6. Stage 10: Cost Estimation & Blast Radius (Software / Sarthak)
        if is_valid:
            cost_report = self.cost_engine.estimate_cost(canonical_sql, dialect="postgres")
        else:
            cost_report = CostReport(
                decision="REJECT",
                estimated_cost=None,
                estimated_rows_scanned=None,
                estimated_rows_affected=None,
                full_table_scans=[],
                index_used=False,
                reasons=[f"Blocked by static validation: {i.message}" for i in all_issues if i.severity == Severity.ERROR],
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
        elif is_valid and cost_report.is_escalate():
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
                "validation_status": validation_res.status.value,
                "cost_decision": cost_report.decision,
            }
        )
