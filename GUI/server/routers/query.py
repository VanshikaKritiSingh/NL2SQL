# routers/query.py
import asyncio
from datetime import datetime
import os
import sys
from typing import List, Dict, Any
from fastapi import APIRouter, BackgroundTasks, HTTPException
from models.query import QueryRequest, QueryResponse, ResultData, HistoryItem
from models.approval import ApprovalPayload, CostEstimate, SecurityCheck, ImpactedTable, DiffData, DmlRowDiff
from mock_data.diffs import get_mock_ddl_diff, get_mock_dml_diff
from services.pipeline_stub import simulate_pipeline_run

# Add repo root to sys.path so core and validator can be imported cleanly
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.orchestrator import EndToEndNL2SQLOrchestrator
from core.schema_linker import TableMeta, ColumnMeta
from validator.contracts import StatementType, Severity

router = APIRouter(prefix="/query", tags=["Query Intake"])

# Initialize default enterprise schema for orchestrator
DEFAULT_SCHEMA = {
    "users": TableMeta(
        name="users",
        description="Registered user accounts and demographics",
        columns={
            "user_id": ColumnMeta(name="user_id", dtype="INTEGER", is_pk=True),
            "username": ColumnMeta(name="username", dtype="VARCHAR(100)", categorical_values=["alice_w", "bob_k", "charlie_m"]),
            "email": ColumnMeta(name="email", dtype="VARCHAR(255)"),
            "status": ColumnMeta(name="status", dtype="VARCHAR(50)", categorical_values=["active", "inactive", "suspended"]),
            "created_at": ColumnMeta(name="created_at", dtype="TIMESTAMP"),
        }
    ),
    "orders": TableMeta(
        name="orders",
        description="Customer checkout orders",
        columns={
            "order_id": ColumnMeta(name="order_id", dtype="INTEGER", is_pk=True),
            "user_id": ColumnMeta(name="user_id", dtype="INTEGER", is_fk=True, fk_target_table="users", fk_target_column="user_id"),
            "order_date": ColumnMeta(name="order_date", dtype="TIMESTAMP"),
            "status": ColumnMeta(name="status", dtype="VARCHAR(50)", categorical_values=["DELIVERED", "SHIPPED", "PROCESSING", "PENDING"]),
            "total_amount": ColumnMeta(name="total_amount", dtype="DECIMAL(10,2)"),
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
            "name": ColumnMeta(name="name", dtype="VARCHAR(255)", categorical_values=["MacBook Pro", "Wireless Mouse", "USB-C Adapter"]),
            "category": ColumnMeta(name="category", dtype="VARCHAR(100)", categorical_values=["Electronics", "Accessories", "Laptops"]),
            "price": ColumnMeta(name="price", dtype="DECIMAL(10,2)"),
            "stock_quantity": ColumnMeta(name="stock_quantity", dtype="INTEGER"),
        }
    )
}

orchestrator = EndToEndNL2SQLOrchestrator(schema_tables=DEFAULT_SCHEMA)

# In-memory history store: user_id -> List[HistoryItem]
query_history: Dict[str, List[HistoryItem]] = {}
stored_responses: Dict[str, QueryResponse] = {}


@router.post("", response_model=QueryResponse)
async def submit_query(request: QueryRequest, background_tasks: BackgroundTasks):
    """Query Intake entry point: Receives natural language query, executes orchestrator pipeline."""
    
    # 1. Run full 16-stage orchestrator pipeline
    plan = orchestrator.process_query(
        query=request.query_text,
        target_engine=request.target_dialect.value,
        auto_mode=True,
    )

    compiled_sql = plan.transpilation_result.compiled_query
    if isinstance(compiled_sql, dict):
        sql_str = compiled_sql.get("mql_string", str(compiled_sql))
    else:
        sql_str = str(compiled_sql)

    is_mutating = plan.requires_human_approval or plan.statement_type in (StatementType.WRITE, StatementType.DDL)

    # 2. Build Response based on Execution Route
    if not plan.is_valid:
        error_msgs = [f"[{i.code}] {i.message}" for i in plan.validation_issues if i.severity == Severity.ERROR]
        response = QueryResponse(
            query_id=plan.query_id,
            status="error",
            generated_sql=sql_str,
            result_data=None,
            approval_payload=None,
            error_message="; ".join(error_msgs) if error_msgs else "Validation policy rejected statement.",
            cache_hit=False,
        )
    elif is_mutating:
        # Generate approval payload
        cost_rep = plan.cost_report
        risk = "critical" if plan.statement_type == StatementType.DDL else "high"
        
        impacted = []
        for t in plan.linked_context.selected_tables:
            impacted.append(ImpactedTable(name=t, impact_level="direct" if t == plan.linked_context.selected_tables[0] else "referenced", operation=plan.statement_type.value))

        diff = get_mock_ddl_diff() if plan.statement_type == StatementType.DDL else get_mock_dml_diff()

        approval_payload = ApprovalPayload(
            query_id=plan.query_id,
            generated_sql=sql_str,
            target_dialect=request.target_dialect.value,
            risk_tier=risk,
            impacted_tables=impacted if impacted else [ImpactedTable(name="products", impact_level="direct", operation="UPDATE")],
            cost_estimate=CostEstimate(
                estimated_rows=cost_rep.estimated_rows_affected or 100,
                estimated_cost=cost_rep.estimated_cost or 50.0,
                scan_type="index_scan" if cost_rep.index_used else "full_table_scan",
                warnings=cost_rep.reasons,
            ),
            security_check=SecurityCheck(
                deadlock_risk="low",
                lock_level="table" if plan.statement_type == StatementType.DDL else "row",
                privilege_ok=True,
                flags=[i.code for i in plan.validation_issues],
            ),
            diff_data=diff,
        )

        response = QueryResponse(
            query_id=plan.query_id,
            status="approval_required",
            generated_sql=sql_str,
            result_data=None,
            approval_payload=approval_payload.model_dump(),
            error_message=None,
            cache_hit=False,
        )
    else:
        # READ Query -> completed with tabular results
        rows = [
            {"user_id": 101, "username": "alice_w", "order_date": "2025-05-10 14:22:00", "status": "DELIVERED", "total_amount": 149.99},
            {"user_id": 102, "username": "bob_k", "order_date": "2025-05-12 09:15:30", "status": "SHIPPED", "total_amount": 89.50},
            {"user_id": 103, "username": "charlie_m", "order_date": "2025-05-15 18:44:12", "status": "PROCESSING", "total_amount": 299.00},
            {"user_id": 104, "username": "diana_p", "order_date": "2025-05-18 11:05:00", "status": "DELIVERED", "total_amount": 45.20},
            {"user_id": 105, "username": "evan_r", "order_date": "2025-05-20 16:30:45", "status": "PENDING", "total_amount": 120.00},
        ]
        response = QueryResponse(
            query_id=plan.query_id,
            status="completed",
            generated_sql=sql_str,
            result_data=ResultData(
                columns=list(rows[0].keys()),
                rows=rows,
                row_count=len(rows),
            ),
            approval_payload=None,
            error_message=None,
            cache_hit=False,
        )

    stored_responses[response.query_id] = response

    # 3. Record to history
    history_entry = HistoryItem(
        query_id=response.query_id,
        query_text=request.query_text,
        generated_sql=response.generated_sql,
        target_dialect=request.target_dialect.value,
        status=response.status,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        is_mutating=is_mutating,
    )
    if request.user_id not in query_history:
        query_history[request.user_id] = []
    query_history[request.user_id].insert(0, history_entry)

    # 4. Trigger WebSocket pipeline stage simulation in background
    background_tasks.add_task(
        simulate_pipeline_run,
        query_id=response.query_id,
        user_id=request.user_id,
        is_mutating=is_mutating,
        approval_payload=response.approval_payload,
        delay=0.10,
    )

    return response


@router.get("/history/{user_id}", response_model=List[HistoryItem])
async def get_user_history(user_id: str):
    """Returns query history for the given user."""
    return query_history.get(user_id, [])
