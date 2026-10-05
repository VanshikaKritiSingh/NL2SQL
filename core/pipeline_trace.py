"""
core/pipeline_trace.py — Step-by-Step Sequential Pipeline Tracer

Traces and captures full execution details at each stage:
Stage 1: Intent & CLEF Paradigm Classification
Stage 2: Schema Context Retrieval & Steiner Minimal Tree
Stage 3: Qwen2.5-Coder + LoRA Model Generation
Stage 4: Deterministic Dialect Transpilation (PostgreSQL, MySQL, SQLite, DuckDB, ClickHouse, openCypher, MongoDB)
Stage 5: 6-Layer Static AST Validation
Stage 6: Heuristic Cost & Execution Routing
"""

import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

from core.dialect_converter import DeterministicDialectConverter
from core.paradigm_suggestor import DatabaseParadigm, SpeculativeParadigmSuggestor
from core.schema_linker import SchemaLinker, TableMeta, ColumnMeta
from validator.contracts import Severity, StatementType, Status
from validator.engine import run_validation
from validator.interfaces import FakeSchemaProvider
from cost_estimator.engine import HeuristicCostEngine


def build_default_demo_schema() -> Dict[str, TableMeta]:
    return {
        "customers": TableMeta(
            name="customers",
            description="Registered user accounts and demographics",
            columns={
                "customer_id": ColumnMeta(name="customer_id", dtype="INTEGER", is_pk=True),
                "name": ColumnMeta(name="name", dtype="VARCHAR(255)", categorical_values=["Alice Smith", "Bob Jones", "Charlie Brown"]),
                "email": ColumnMeta(name="email", dtype="VARCHAR(255)"),
                "country": ColumnMeta(name="country", dtype="VARCHAR(100)", categorical_values=["Germany", "United States", "Japan"]),
            }
        ),
        "orders": TableMeta(
            name="orders",
            description="Customer checkout orders",
            columns={
                "order_id": ColumnMeta(name="order_id", dtype="INTEGER", is_pk=True),
                "customer_id": ColumnMeta(name="customer_id", dtype="INTEGER", is_fk=True, fk_target_table="customers", fk_target_column="customer_id"),
                "order_date": ColumnMeta(name="order_date", dtype="TIMESTAMP"),
                "total_amount": ColumnMeta(name="total_amount", dtype="DECIMAL(10,2)"),
                "status": ColumnMeta(name="status", dtype="VARCHAR(50)", categorical_values=["completed", "pending", "cancelled"]),
            }
        ),
        "order_items": TableMeta(
            name="order_items",
            description="Line items within customer orders",
            columns={
                "item_id": ColumnMeta(name="item_id", dtype="INTEGER", is_pk=True),
                "order_id": ColumnMeta(name="order_id", dtype="INTEGER", is_fk=True, fk_target_table="orders", fk_target_column="order_id"),
                "product_id": ColumnMeta(name="product_id", dtype="INTEGER", is_fk=True, fk_target_table="products", fk_target_column="product_id"),
                "quantity": ColumnMeta(name="quantity", dtype="INTEGER"),
                "unit_price": ColumnMeta(name="unit_price", dtype="DECIMAL(10,2)"),
            }
        ),
        "products": TableMeta(
            name="products",
            description="Product inventory catalog",
            columns={
                "product_id": ColumnMeta(name="product_id", dtype="INTEGER", is_pk=True),
                "name": ColumnMeta(name="name", dtype="VARCHAR(255)", categorical_values=["MacBook Pro", "Wireless Mouse", "USB-C Hub"]),
                "category": ColumnMeta(name="category", dtype="VARCHAR(100)", categorical_values=["Electronics", "Accessories", "Laptops"]),
                "price": ColumnMeta(name="price", dtype="DECIMAL(10,2)"),
                "stock_quantity": ColumnMeta(name="stock_quantity", dtype="INTEGER"),
            }
        )
    }


def execute_pipeline_trace(query: str, schema_dict: Optional[Dict[str, TableMeta]] = None) -> Dict[str, Any]:
    """Executes the full pipeline step-by-step and returns structured tracing data."""
    schema = schema_dict or build_default_demo_schema()
    start_total = time.perf_counter()

    # Step 1: CLEF Discourse & Paradigm Classification
    t0 = time.perf_counter()
    suggestor = SpeculativeParadigmSuggestor(confidence_threshold=0.85)
    paradigm_res = suggestor.classify_and_route(query, auto_mode=True)
    t1 = time.perf_counter()

    step1_data = {
        "step_number": 1,
        "step_name": "CLEF Discourse & Paradigm Classification",
        "duration_ms": round((t1 - t0) * 1000, 2),
        "input": {"natural_language_query": query},
        "output": {
            "paradigm": paradigm_res.paradigm.value,
            "confidence": paradigm_res.confidence,
            "recommended_engines": paradigm_res.recommended_engines,
            "reasoning": paradigm_res.reasoning,
            "is_verified_by_llm": paradigm_res.is_verified_by_llm,
        }
    }

    # Step 2: Schema Linking & Steiner Tree Graph Closure
    t0 = time.perf_counter()
    linker = SchemaLinker(tables=schema, rrf_k=60)
    linked_ctx = linker.link_context(query)
    t1 = time.perf_counter()

    step2_data = {
        "step_number": 2,
        "step_name": "RAG Schema Linker & Steiner Minimal Tree",
        "duration_ms": round((t1 - t0) * 1000, 2),
        "input": {"query": query, "candidate_tables": list(schema.keys())},
        "output": {
            "selected_tables": linked_ctx.selected_tables,
            "selected_columns": linked_ctx.selected_columns,
            "grounded_values": linked_ctx.grounded_values,
            "foreign_key_bridges": [f"{s_t}.{s_c} -> {t_t}.{t_c}" for s_t, s_c, t_t, t_c in linked_ctx.foreign_keys],
            "prompt_ddl": linked_ctx.prompt_ddl,
        }
    }

    # Step 3: Qwen2.5-Coder + LoRA Generation (Canonical AST Synthesis)
    t0 = time.perf_counter()
    from core.orchestrator import SemanticSQLSynthesizer
    synthesizer = SemanticSQLSynthesizer()
    canonical_sql = synthesizer.synthesize(query, linked_ctx)
    t1 = time.perf_counter()

    step3_data = {
        "step_number": 3,
        "step_name": "Qwen2.5-Coder + LoRA Fine-Tuned Generation",
        "duration_ms": round((t1 - t0) * 1000, 2),
        "input": {
            "system_prompt": "Expert Text-to-Universal-SQL Compiler (ChatML format)",
            "context_ddl": linked_ctx.prompt_ddl,
            "user_question": query,
            "lora_adapter": "qwen2.5-coder-7b-qlora (r=16, alpha=32)",
        },
        "output": {
            "canonical_sql": canonical_sql,
            "ast_format": "PostgreSQL / ANSI SQL Canonical AST",
        }
    }

    # Step 4: Deterministic Dialect Converter (Multi-Query Language Transpilation)
    t0 = time.perf_counter()
    converter = DeterministicDialectConverter()
    dialects = ["postgres", "mysql", "sqlite", "duckdb", "clickhouse", "opencypher", "mongodb"]
    transpiled_outputs = {}

    for d in dialects:
        try:
            res = converter.transpile(canonical_sql, target_dialect=d)
            transpiled_outputs[d] = {
                "query": res.compiled_query,
                "is_native_sql": res.is_native_sql,
                "execution_time_ms": res.execution_time_ms,
            }
        except Exception as e:
            transpiled_outputs[d] = {
                "query": f"-- Error: {str(e)}",
                "is_native_sql": True,
                "execution_time_ms": 0.0,
            }
    t1 = time.perf_counter()

    step4_data = {
        "step_number": 4,
        "step_name": "Deterministic Universal Dialect Converter",
        "duration_ms": round((t1 - t0) * 1000, 2),
        "input": {"canonical_sql": canonical_sql},
        "output": {
            "dialects_generated": list(transpiled_outputs.keys()),
            "transpiled_queries": transpiled_outputs,
        }
    }

    # Step 5: 6-Layer Static AST Validator
    t0 = time.perf_counter()
    fake_tables = []
    for t_name, t_meta in schema.items():
        cols = {c_name: c_meta.dtype for c_name, c_meta in t_meta.columns.items()}
        pks = [c_name for c_name, c_meta in t_meta.columns.items() if c_meta.is_pk]
        fks = {c_name: (c_meta.fk_target_table, c_meta.fk_target_column or "id") for c_name, c_meta in t_meta.columns.items() if c_meta.is_fk and c_meta.fk_target_table}
        fake_tables.append({"name": t_name, "columns": cols, "pk": pks, "fks": fks, "indexes": {}, "row_count": 50000, "nullable": {}})
    schema_provider = FakeSchemaProvider({"tables": fake_tables})

    val_res = run_validation(canonical_sql, dialect="postgres", schema=schema_provider)
    t1 = time.perf_counter()

    step5_data = {
        "step_number": 5,
        "step_name": "6-Layer Static AST Validator",
        "duration_ms": round((t1 - t0) * 1000, 2),
        "input": {"sql": canonical_sql},
        "output": {
            "status": val_res.status.value,
            "statement_type": val_res.statement_type.value,
            "is_valid": val_res.status != Status.INVALID,
            "issues": [
                {"code": i.code, "layer": i.layer.name, "severity": i.severity.value, "message": i.message, "fix_hint": i.fix_hint}
                for i in val_res.issues
            ]
        }
    }

    # Step 6: Heuristic Cost & Blast-Radius Engine
    t0 = time.perf_counter()
    cost_engine = HeuristicCostEngine()
    cost_report = cost_engine.estimate_cost(canonical_sql, dialect="postgres")
    is_valid = val_res.status != Status.INVALID

    if is_valid and cost_report.is_allow():
        route = "SANDBOX_REPLICA" if val_res.statement_type == StatementType.READ else "APPROVAL_GATE"
    elif is_valid and cost_report.is_escalate():
        route = "APPROVAL_GATE"
    else:
        route = "BLOCKED"
    t1 = time.perf_counter()

    step6_data = {
        "step_number": 6,
        "step_name": "Heuristic Cost & Execution Gate Router",
        "duration_ms": round((t1 - t0) * 1000, 2),
        "input": {"sql": canonical_sql, "statement_type": val_res.statement_type.value},
        "output": {
            "decision": cost_report.decision,
            "estimated_cost": cost_report.estimated_cost,
            "estimated_rows_scanned": cost_report.estimated_rows_scanned,
            "estimated_rows_affected": cost_report.estimated_rows_affected,
            "execution_route": route,
            "requires_human_approval": (route == "APPROVAL_GATE"),
            "reasons": cost_report.reasons,
        }
    }

    total_duration_ms = round((time.perf_counter() - start_total) * 1000, 2)

    return {
        "query": query,
        "total_duration_ms": total_duration_ms,
        "steps": [step1_data, step2_data, step3_data, step4_data, step5_data, step6_data],
        "final_summary": {
            "paradigm": paradigm_res.paradigm.value,
            "canonical_sql": canonical_sql,
            "target_route": route,
            "validation_status": val_res.status.value,
        }
    }
