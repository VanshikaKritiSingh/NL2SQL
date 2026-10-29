# routers/query.py
import asyncio
from datetime import datetime
import os
import re
import sys
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException
from models.query import QueryRequest, QueryResponse, ResultData, HistoryItem, TargetDialect
from models.approval import ApprovalPayload, CostEstimate, SecurityCheck, ImpactedTable, DiffData, DmlRowDiff
from mock_data.diffs import get_mock_ddl_diff, get_mock_dml_diff
from services.pipeline_stub import simulate_pipeline_run

# Add repo root to sys.path so core and validator can be imported cleanly
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.orchestrator import EndToEndNL2SQLOrchestrator
from core.schema_linker import TableMeta, ColumnMeta
from core.validator.contracts import StatementType, Severity

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

import sqlite3

_sandbox_dbs: Dict[str, sqlite3.Connection] = {}

def get_session_sandbox(user_id: str) -> sqlite3.Connection:
    if user_id not in _sandbox_dbs:
        db = sqlite3.connect(":memory:", check_same_thread=False)
        db.row_factory = sqlite3.Row
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            email TEXT,
            country TEXT,
            status TEXT,
            created_at TEXT
        );
        INSERT OR IGNORE INTO users VALUES
        (1, 'alice_w', 'alice@example.com', 'Germany', 'active', '2024-01-15'),
        (2, 'bob_k', 'bob@example.com', 'USA', 'active', '2024-02-20'),
        (3, 'charlie_m', 'charlie@example.com', 'Germany', 'inactive', '2024-03-10');

        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY,
            name TEXT,
            category TEXT,
            price REAL,
            stock_quantity INTEGER
        );
        INSERT OR IGNORE INTO products VALUES
        (1, 'MacBook Pro', 'Laptops', 1999.0, 15),
        (2, 'Wireless Mouse', 'Accessories', 29.99, 120),
        (3, 'USB-C Adapter', 'Accessories', 19.99, 85);

        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY,
            user_id INTEGER,
            order_date TEXT,
            status TEXT,
            total_amount REAL
        );
        INSERT OR IGNORE INTO orders VALUES
        (1, 1, '2025-05-10 14:22:00', 'DELIVERED', 149.99),
        (2, 2, '2025-05-12 09:15:30', 'SHIPPED', 89.50),
        (3, 3, '2025-05-15 18:44:12', 'PROCESSING', 299.00),
        (4, 1, '2025-05-18 11:05:00', 'DELIVERED', 45.20),
        (5, 2, '2025-05-20 16:30:45', 'PENDING', 120.00);
        """)
        _sandbox_dbs[user_id] = db
    return _sandbox_dbs[user_id]


def sync_sandbox_ddl(user_id: str, sql_str: str):
    """Executes DDL statements on the in-memory SQLite sandbox so preview queries can resolve."""
    try:
        from core.dialect_converter import DeterministicDialectConverter
        conv = DeterministicDialectConverter()
        res = conv.transpile(sql_str, target_dialect="sqlite")
        db = get_session_sandbox(user_id)
        clean_sqlite = re.sub(r"\bUSE\s+[^;]+;", "", res.compiled_query, flags=re.IGNORECASE)
        clean_sqlite = re.sub(r"CREATE\s+DATABASE\s+[^;]+;", "", clean_sqlite, flags=re.IGNORECASE).strip()
        if clean_sqlite:
            db.executescript(clean_sqlite)
            for m_tbl in re.finditer(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([`\"\w]+)", clean_sqlite, re.IGNORECASE):
                t_name = m_tbl.group(1).strip("`\"'")
                cur = db.cursor()
                try:
                    cur.execute(f"SELECT COUNT(*) FROM `{t_name}`")
                    cnt = cur.fetchone()[0]
                    if cnt == 0:
                        cur.execute(f"PRAGMA table_info(`{t_name}`)")
                        cols = cur.fetchall()
                        if cols:
                            for i in range(1, 4):
                                vals = []
                                for c in cols:
                                    cid, cname, ctype, notnull, dflt, pk = c
                                    clow = cname.lower()
                                    if pk:
                                        vals.append(i)
                                    elif "roll" in clow:
                                        vals.append(f"R-{100 + i}")
                                    elif "name" in clow or "title" in clow:
                                        vals.append(f"{t_name.capitalize()} {i}")
                                    elif "duration" in clow or "quantity" in clow:
                                        vals.append(30 * i)
                                    elif "price" in clow or "amount" in clow:
                                        vals.append(19.99 * i)
                                    elif "status" in clow:
                                        vals.append("ACTIVE")
                                    elif "email" in clow:
                                        vals.append(f"user{i}@example.com")
                                    elif "int" in str(ctype).lower():
                                        vals.append(i * 10)
                                    else:
                                        vals.append(f"Sample {cname} {i}")
                                placeholders = ", ".join(["?"] * len(vals))
                                col_str = ", ".join(f"`{c[1]}`" for c in cols)
                                db.execute(f"INSERT INTO `{t_name}` ({col_str}) VALUES ({placeholders})", vals)
                            db.commit()
                except Exception:
                    pass
    except Exception:
        pass


def sync_orchestrator_from_schema(schema_meta):
    """Refreshes orchestrator tables from introspected schema metadata."""
    if not schema_meta or not schema_meta.tables:
        return
    live_tables = {}
    for t_name, t_schema in schema_meta.tables.items():
        col_metas = {}
        for c_name, c_schema in t_schema.columns.items():
            fk_tbl, fk_col = None, None
            if c_schema.foreign_key_target and "." in c_schema.foreign_key_target:
                fk_tbl, fk_col = c_schema.foreign_key_target.split(".", 1)
            col_metas[c_name] = ColumnMeta(
                name=c_name,
                dtype=c_schema.data_type,
                is_pk=c_schema.is_primary_key or (c_name in t_schema.primary_keys),
                is_fk=c_schema.is_foreign_key,
                fk_target_table=fk_tbl,
                fk_target_column=fk_col,
            )
        live_tables[t_name] = TableMeta(
            name=t_name,
            description=t_schema.description or f"Table {t_name}",
            columns=col_metas,
        )
    orchestrator.update_schema(live_tables)


@router.post("", response_model=QueryResponse)
async def submitNaturalLanguageQueryForProcessing(request: QueryRequest, background_tasks: BackgroundTasks):
    """Query Intake entry point: Receives natural language or SQL query, compiles via LLM and executes against live DB or orchestrator."""
    from core.connectors import default_registry

    # 0. Sync schema with connected live DBMS if attached
    is_none_db = request.database_profile in ("__none__", "", "none", "(none)", None)
    is_attached = default_registry.is_attached(request.user_id)
    conn = default_registry.get(request.user_id) if is_attached else None

    if is_none_db:
        # User selected clean scratch / new database context: no prior tables attached
        orchestrator.update_schema({})
    elif is_attached and conn and conn.is_connected:
        try:
            schema_meta = conn.introspect_schema(force_refresh=False)
            if schema_meta and schema_meta.tables:
                live_tables = {}
                for t_name, t_schema in schema_meta.tables.items():
                    col_metas = {}
                    for c_name, c_schema in t_schema.columns.items():
                        fk_tbl, fk_col = None, None
                        if c_schema.foreign_key_target and "." in c_schema.foreign_key_target:
                            fk_tbl, fk_col = c_schema.foreign_key_target.split(".", 1)
                        col_metas[c_name] = ColumnMeta(
                            name=c_name,
                            dtype=c_schema.data_type,
                            is_pk=c_schema.is_primary_key or (c_name in t_schema.primary_keys),
                            is_fk=c_schema.is_foreign_key,
                            fk_target_table=fk_tbl,
                            fk_target_column=fk_col,
                            categorical_values=c_schema.sample_values or [],
                        )
                    live_tables[t_name] = TableMeta(
                        name=t_name,
                        description=t_schema.comment or f"Live table {t_name}",
                        columns=col_metas,
                    )
                if live_tables:
                    orchestrator.update_schema(live_tables)
        except Exception:
            pass
    else:
        if orchestrator.tables != DEFAULT_SCHEMA:
            orchestrator.update_schema(DEFAULT_SCHEMA)

    # 1. Run full 16-stage orchestrator pipeline with direct Ollama LLM grounding
    target_engine = request.target_dialect.value if isinstance(request.target_dialect, TargetDialect) else str(request.target_dialect)
    is_auto = (target_engine == "auto")

    # If auto dialect and live DBMS is connected, ground target dialect on connected DBMS
    if is_auto and is_attached and conn and conn.config:
        conn_type = conn.config.connector_type
        c_str = conn_type.value if hasattr(conn_type, "value") else str(conn_type)
        if c_str and c_str.lower() != "auto":
            target_engine = c_str.lower()
            is_auto = False
    
    plan = orchestrator.process_query(
        query=request.query_text,
        target_engine=target_engine,
        auto_mode=is_auto,
        user_id=request.user_id,
        user_role="analyst",
        model_name=request.model_name,
        thinking_enabled=request.thinking_enabled,
    )

    compiled_sql = plan.transpilation_result.compiled_query
    if isinstance(compiled_sql, dict):
        sql_str = compiled_sql.get("mql_string", str(compiled_sql))
    else:
        sql_str = str(compiled_sql)

    # Determine resolved active database profile name
    m_new_db = re.search(r"CREATE\s+DATABASE\s+(?:IF\s+NOT\s+EXISTS\s+)?([`\"\w]+)", sql_str, re.IGNORECASE)
    if is_none_db:
        active_db_name = m_new_db.group(1).strip("`\"'") if m_new_db else "(None / New Database)"
    elif is_attached and conn and conn.config and conn.config.database:
        active_db_name = conn.config.database
    else:
        active_db_name = request.database_profile or "master_enterprise"

    is_mutating = plan.requires_human_approval or plan.statement_type in (StatementType.WRITE, StatementType.DDL)

    # 2. Build Response based on Execution Route
    if plan.execution_route == "REFUSAL" or sql_str.strip().startswith("-- REFUSAL:"):
        lines = [l.strip() for l in sql_str.splitlines() if l.strip()]
        expl = ""
        for l in lines:
            if "EXPLANATION:" in l:
                expl = l.split("EXPLANATION:", 1)[1].strip()
                break
        if not expl and len(lines) > 1:
            expl = lines[1].lstrip("- ").strip()
        if not expl and lines:
            expl = lines[0].lstrip("- ").strip()

        response = QueryResponse(
            query_id=plan.query_id,
            status="refusal",
            generated_sql=sql_str,
            result_data=None,
            approval_payload=None,
            error_message=expl or "Model or schema guard declined SQL generation for this request.",
            cache_hit=False,
            database_profile=active_db_name,
            is_live_db_connected=False,
            execution_mode="preview_sandbox",
            model_name=plan.model_name or request.model_name or "auto",
        )
    elif not plan.is_valid:
        error_msgs = [f"[{i.code}] {i.message}" for i in plan.validation_issues if i.severity == Severity.ERROR]
        response = QueryResponse(
            query_id=plan.query_id,
            status="error",
            generated_sql=sql_str,
            result_data=None,
            approval_payload=None,
            error_message="; ".join(error_msgs) if error_msgs else "Validation policy rejected statement.",
            cache_hit=False,
            database_profile=active_db_name,
            is_live_db_connected=False,
            execution_mode="preview_sandbox",
            model_name=plan.model_name or request.model_name or "auto",
        )
    elif is_mutating and not request.dry_run_only:
        # Generate approval payload for mutating statements
        cost_rep = plan.cost_report
        risk = "critical" if plan.statement_type == StatementType.DDL else "high"
        
        impacted = []
        # Priority 1: Tables directly touched by the generated SQL AST
        selected_tbls = list(plan.tables_touched) if plan.tables_touched else []
        # Fallback to linked context only if tables_touched is completely empty
        if not selected_tbls and plan.linked_context and hasattr(plan.linked_context, "selected_tables"):
            selected_tbls = list(plan.linked_context.selected_tables)

        # Determine specific operation per table (CREATE, DROP, ALTER, INSERT, UPDATE, DELETE)
        table_ops = {}
        try:
            import sqlglot
            from sqlglot import exp
            stmts = [s for s in sqlglot.parse(sql_str) if s is not None]
            for s in stmts:
                if isinstance(s, exp.Create):
                    tbl = s.find(exp.Table)
                    if tbl and tbl.name:
                        table_ops[tbl.name.lower()] = "CREATE"
                elif isinstance(s, exp.Drop):
                    tbl = s.find(exp.Table)
                    if tbl and tbl.name:
                        table_ops[tbl.name.lower()] = "DROP"
                elif isinstance(s, exp.Alter):
                    tbl = s.find(exp.Table)
                    if tbl and tbl.name:
                        table_ops[tbl.name.lower()] = "ALTER"
                elif isinstance(s, exp.Insert):
                    tbl = s.find(exp.Table)
                    if tbl and tbl.name and tbl.name.lower() not in table_ops:
                        table_ops[tbl.name.lower()] = "INSERT"
                elif isinstance(s, exp.Update):
                    tbl = s.find(exp.Table)
                    if tbl and tbl.name and tbl.name.lower() not in table_ops:
                        table_ops[tbl.name.lower()] = "UPDATE"
                elif isinstance(s, exp.Delete):
                    tbl = s.find(exp.Table)
                    if tbl and tbl.name and tbl.name.lower() not in table_ops:
                        table_ops[tbl.name.lower()] = "DELETE"
        except Exception:
            pass

        for t in selected_tbls:
            op = table_ops.get(t.lower(), plan.statement_type.value)
            impacted.append(ImpactedTable(name=t, impact_level="direct" if t == selected_tbls[0] else "referenced", operation=op))

        if plan.statement_type == StatementType.DDL:
            diff = DiffData(
                diff_type="ddl",
                ddl_before="-- Current Schema State",
                ddl_after=sql_str,
                dml_rows=None,
            )
        else:
            diff = get_mock_dml_diff()

        approval_payload = ApprovalPayload(
            query_id=plan.query_id,
            generated_sql=sql_str,
            target_dialect=plan.target_dialect,
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

        is_attached = default_registry.is_attached(request.user_id)
        conn = default_registry.get(request.user_id) if is_attached else None
        active_db_name = conn.config.database if conn else (request.database_profile or "master_enterprise")

        response = QueryResponse(
            query_id=plan.query_id,
            status="approval_required",
            generated_sql=sql_str,
            result_data=None,
            approval_payload=approval_payload.model_dump(),
            error_message=None,
            cache_hit=False,
            database_profile=active_db_name,
            is_live_db_connected=is_attached,
            execution_mode="live_connected" if is_attached else "preview_sandbox",
            model_name=plan.model_name or request.model_name or "auto",
        )
    else:
        # READ Query -> live results if socket attached, else sandbox preview
        if plan.live_query_result and not plan.live_query_result.error:
            lr = plan.live_query_result
            res_data = ResultData(
                columns=lr.columns,
                rows=lr.rows,
                row_count=lr.row_count,
            )
            is_live = True
            exec_mode = "live_database"
        elif plan.live_query_result and plan.live_query_result.error:
            # Live execution error from DB engine
            response = QueryResponse(
                query_id=plan.query_id,
                status="error",
                generated_sql=sql_str,
                result_data=None,
                approval_payload=None,
                error_message=f"Live database execution error: {plan.live_query_result.error}",
                cache_hit=False,
                database_profile=active_db_name,
                is_live_db_connected=True,
                execution_mode="live_database",
            )
            stored_responses[response.query_id] = response
            return response
        else:
            # Sandbox preview execution using session SQLite sandbox
            try:
                from core.dialect_converter import DeterministicDialectConverter
                conv = DeterministicDialectConverter()
                res_sqlite = conv.transpile(sql_str, target_dialect="sqlite")
                db = get_session_sandbox(request.user_id)
                clean_q = re.sub(r"\bUSE\s+[^;]+;", "", res_sqlite.compiled_query, flags=re.IGNORECASE)
                clean_q = re.sub(r"CREATE\s+DATABASE\s+[^;]+;", "", clean_q, flags=re.IGNORECASE).strip()
                cur = db.cursor()
                cur.execute(clean_q)
                if cur.description:
                    s_cols = [d[0] for d in cur.description]
                    s_rows = [dict(zip(s_cols, r)) for r in cur.fetchall()]
                    res_data = ResultData(columns=s_cols, rows=s_rows, row_count=len(s_rows))
                else:
                    res_data = ResultData(columns=["status"], rows=[{"status": "OK"}], row_count=1)
            except Exception:
                matched_cols = []
                for t in (plan.tables_touched or []):
                    if t in orchestrator.tables:
                        matched_cols.extend(list(orchestrator.tables[t].columns.keys()))
                if not matched_cols:
                    matched_cols = ["id", "name", "created_at"]
                matched_cols = list(dict.fromkeys(matched_cols))
                sample_rows = [
                    {c: (i if "id" in c.lower() else f"Sample {c} {i}") for c in matched_cols}
                    for i in range(1, 6)
                ]
                res_data = ResultData(columns=matched_cols, rows=sample_rows, row_count=len(sample_rows))
            is_live = False
            exec_mode = "preview_sandbox"

        response = QueryResponse(
            query_id=plan.query_id,
            status="completed",
            generated_sql=sql_str,
            result_data=res_data,
            approval_payload=None,
            error_message=None,
            cache_hit=False,
            database_profile=active_db_name,
            is_live_db_connected=is_live,
            execution_mode=exec_mode,
            model_name=plan.model_name or request.model_name or "auto",
        )

    stored_responses[response.query_id] = response

    # 3. Record to history
    history_entry = HistoryItem(
        query_id=response.query_id,
        query_text=request.query_text,
        generated_sql=response.generated_sql,
        target_dialect=plan.target_dialect,
        status=response.status,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        is_mutating=is_mutating,
        database_profile=active_db_name,
    )
    if request.user_id not in query_history:
        query_history[request.user_id] = []
    query_history[request.user_id].insert(0, history_entry)

    # 4. Record to history and return response
    return response


submit_query = submitNaturalLanguageQueryForProcessing


@router.get("/history/{user_id}", response_model=List[HistoryItem])
async def retrieveQueryHistoryForUserSession(user_id: str):
    """Returns query history for the given user."""
    return query_history.get(user_id, [])


get_user_history = retrieveQueryHistoryForUserSession


@router.delete("/history/{user_id}/{query_id}")
async def deleteSingleQueryHistoryRecord(user_id: str, query_id: str):
    """Deletes a single history item for the specified user."""
    if user_id in query_history:
        query_history[user_id] = [item for item in query_history[user_id] if item.query_id != query_id]
        if query_id in stored_responses:
            del stored_responses[query_id]
        return {"status": "success", "message": f"Query {query_id} deleted"}
    return {"status": "not_found", "message": "User history not found"}


delete_user_history_item = deleteSingleQueryHistoryRecord


@router.delete("/history/{user_id}")
async def clearAllQueryHistoryRecordsForUserSession(user_id: str):
    """Clears all query history for the specified user."""
    if user_id in query_history:
        query_history[user_id] = []
    return {"status": "success", "message": f"History cleared for user {user_id}"}


clear_user_history = clearAllQueryHistoryRecordsForUserSession
