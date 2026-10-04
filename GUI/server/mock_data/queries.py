# mock_data/queries.py
import uuid
from datetime import datetime
from models.query import QueryResponse, ResultData, HistoryItem
from models.approval import ApprovalPayload, ImpactedTable
from .diffs import get_mock_ddl_diff, get_mock_dml_diff
from .telemetry import get_mock_select_telemetry, get_mock_update_telemetry, get_mock_ddl_telemetry


def create_mock_select_response(query_text: str, dialect: str) -> QueryResponse:
    query_id = str(uuid.uuid4())
    sql = """SELECT 
    o.order_id,
    u.username,
    o.order_date,
    o.status,
    o.total_amount
FROM orders o
JOIN users u ON o.user_id = u.user_id
WHERE o.order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH)
ORDER BY o.order_date DESC
LIMIT 5;"""

    rows = [
        {"order_id": 1001, "username": "alice_w", "order_date": "2025-05-10 14:22:00", "status": "DELIVERED", "total_amount": 149.99},
        {"order_id": 1002, "username": "bob_k", "order_date": "2025-05-12 09:15:30", "status": "SHIPPED", "total_amount": 89.50},
        {"order_id": 1003, "username": "charlie_m", "order_date": "2025-05-15 18:44:12", "status": "PROCESSING", "total_amount": 299.00},
        {"order_id": 1004, "username": "diana_p", "order_date": "2025-05-18 11:05:00", "status": "DELIVERED", "total_amount": 45.20},
        {"order_id": 1005, "username": "evan_r", "order_date": "2025-05-20 16:30:45", "status": "PENDING", "total_amount": 120.00},
    ]

    return QueryResponse(
        query_id=query_id,
        status="completed",
        generated_sql=sql,
        result_data=ResultData(
            columns=["order_id", "username", "order_date", "status", "total_amount"],
            rows=rows,
            row_count=len(rows),
        ),
        approval_payload=None,
        error_message=None,
        cache_hit=False,
    )


def create_mock_update_response(query_text: str, dialect: str) -> QueryResponse:
    query_id = str(uuid.uuid4())
    sql = """UPDATE products 
SET price = ROUND(price * 1.10, 2)
WHERE category = 'Electronics' OR category = 'Accessories';"""

    cost, security = get_mock_update_telemetry()
    diff = get_mock_dml_diff()

    approval_payload = ApprovalPayload(
        query_id=query_id,
        generated_sql=sql,
        target_dialect=dialect,
        risk_tier="high",
        impacted_tables=[
            ImpactedTable(name="products", impact_level="direct", operation="UPDATE"),
            ImpactedTable(name="order_items", impact_level="referenced", operation=None),
        ],
        cost_estimate=cost,
        security_check=security,
        diff_data=diff,
    )

    return QueryResponse(
        query_id=query_id,
        status="approval_required",
        generated_sql=sql,
        result_data=None,
        approval_payload=approval_payload.model_dump(),
        error_message=None,
        cache_hit=False,
    )


def create_mock_ddl_response(query_text: str, dialect: str) -> QueryResponse:
    query_id = str(uuid.uuid4())
    sql = """ALTER TABLE orders 
ADD COLUMN discount_code VARCHAR(30) DEFAULT NULL 
AFTER total_amount;"""

    cost, security = get_mock_ddl_telemetry()
    diff = get_mock_ddl_diff()

    approval_payload = ApprovalPayload(
        query_id=query_id,
        generated_sql=sql,
        target_dialect=dialect,
        risk_tier="critical",
        impacted_tables=[
            ImpactedTable(name="orders", impact_level="direct", operation="ALTER"),
            ImpactedTable(name="order_items", impact_level="referenced", operation=None),
            ImpactedTable(name="users", impact_level="referenced", operation=None),
        ],
        cost_estimate=cost,
        security_check=security,
        diff_data=diff,
    )

    return QueryResponse(
        query_id=query_id,
        status="approval_required",
        generated_sql=sql,
        result_data=None,
        approval_payload=approval_payload.model_dump(),
        error_message=None,
        cache_hit=False,
    )


def classify_and_generate_mock(query_text: str, dialect: str) -> QueryResponse:
    q = query_text.lower()
    if any(k in q for k in ["alter", "add column", "drop", "create", "schema", "table"]):
        return create_mock_ddl_response(query_text, dialect)
    elif any(k in q for k in ["update", "increase", "change", "modify", "set", "delete", "insert"]):
        return create_mock_update_response(query_text, dialect)
    else:
        return create_mock_select_response(query_text, dialect)
