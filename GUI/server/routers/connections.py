"""
GUI/server/routers/connections.py — Live Database Socket & Connector Management Endpoints

Endpoints:
  POST   /api/connections/attach   — attach a live DBMS socket to user session
  DELETE /api/connections/{user_id} — detach and cleanly disconnect socket
  POST   /api/connections/test     — test connection params without attaching
  GET    /api/connections/status/{user_id} — return connection health & version
  GET    /api/connections/schema/{user_id} — live schema introspection from connected socket
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.connectors import (
    ConnectionConfig,
    ConnectorType,
    default_registry,
)

router = APIRouter(prefix="/connections", tags=["DBMS Connectors & Sockets"])


class AttachRequest(BaseModel):
    user_id: str = Field(..., description="User / session ID")
    connector_type: ConnectorType = Field(..., description="Target DBMS type")
    database: str = Field(..., description="Database / Keyspace / Catalog name or file path")
    host: Optional[str] = "localhost"
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssl_mode: Optional[str] = None
    read_only: bool = False
    timeout_s: float = 15.0
    extra_params: Dict[str, Any] = Field(default_factory=dict)


class TestRequest(BaseModel):
    connector_type: ConnectorType
    database: str
    host: Optional[str] = "localhost"
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssl_mode: Optional[str] = None
    timeout_s: float = 10.0
    extra_params: Dict[str, Any] = Field(default_factory=dict)


class ListDatabasesRequest(BaseModel):
    connector_type: ConnectorType
    host: Optional[str] = "localhost"
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssl_mode: Optional[str] = None
    timeout_s: float = 8.0
    extra_params: Dict[str, Any] = Field(default_factory=dict)


# In-memory tracking of users who explicitly chose to detach their database
EXPLICITLY_DETACHED = set()


def try_auto_attach_internal_mysql(user_id: str) -> bool:
    """Attempts to auto-attach the laptop's internal MariaDB (bhuknu@127.0.0.1:3306/test)."""
    if user_id in EXPLICITLY_DETACHED:
        return False
    if default_registry.is_attached(user_id):
        return True
    try:
        config = ConnectionConfig(
            connector_type=ConnectorType.MYSQL,
            database="test",
            host="127.0.0.1",
            port=3306,
            username="bhuknu",
            password="",
            timeout_s=3.0,
            read_only=False,
        )
        conn = default_registry.attach(user_id, config)
        return conn.is_connected
    except Exception:
        return False


class SwitchDatabaseRequest(BaseModel):
    user_id: str = Field(..., description="User session ID")
    database: str = Field(..., description="Target database to switch to")


class ExecuteDirectRequest(BaseModel):
    user_id: str = Field(..., description="User session ID")
    query: str = Field(..., description="Raw SQL query or DDL/DML statement to execute")


@router.post("/attach")
async def attach_connection(req: AttachRequest):
    """Binds a live database socket to the specified user session in-memory."""
    EXPLICITLY_DETACHED.discard(req.user_id)
    config = ConnectionConfig(
        connector_type=req.connector_type,
        database=req.database,
        host=req.host,
        port=req.port,
        username=req.username,
        password=req.password,
        ssl_mode=req.ssl_mode,
        read_only=req.read_only,
        timeout_s=req.timeout_s,
        extra_params=req.extra_params,
    )
    try:
        conn = default_registry.attach(req.user_id, config)
        ping = conn.test_connection()
        return {
            "ok": True,
            "user_id": req.user_id,
            "connector_type": req.connector_type.value,
            "database": req.database,
            "ping": ping,
            "message": f"Connected to {req.connector_type.value} [{req.database}] successfully.",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to attach database: {e}")


@router.delete("/{user_id}")
async def detach_connection(user_id: str):
    """Closes and removes the user's active database socket (marks as explicitly detached)."""
    EXPLICITLY_DETACHED.add(user_id)
    detached = default_registry.detach(user_id)
    return {
        "ok": True,
        "user_id": user_id,
        "detached": detached,
        "message": "Database disconnected cleanly." if detached else "No active connection found for this user.",
    }


@router.post("/test")
async def test_connection_params(req: TestRequest):
    """Pings the target database with provided parameters without registering a session."""
    config = ConnectionConfig(
        connector_type=req.connector_type,
        database=req.database,
        host=req.host,
        port=req.port,
        username=req.username,
        password=req.password,
        ssl_mode=req.ssl_mode,
        timeout_s=req.timeout_s,
        extra_params=req.extra_params,
    )
    res = default_registry.test_config(config)
    if not res.get("ok"):
        raise HTTPException(
            status_code=400,
            detail=res.get("error", "Database connection test failed"),
        )
    return res


@router.post("/databases")
async def list_accessible_databases(req: ListDatabasesRequest):
    """
    Validates user credentials and lists all databases visible and accessible
    to that authenticated user account.
    """
    config = ConnectionConfig(
        connector_type=req.connector_type,
        database="",
        host=req.host,
        port=req.port,
        username=req.username,
        password=req.password,
        ssl_mode=req.ssl_mode,
        timeout_s=req.timeout_s,
        extra_params=req.extra_params,
    )
    try:
        dbs = default_registry.list_databases(config)
        return {
            "ok": True,
            "connector_type": req.connector_type.value,
            "databases": dbs,
            "count": len(dbs),
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Authentication or database enumeration failed: {e}",
        )


@router.get("/models")
async def list_available_models():
    """Lists available local LLM models from Ollama daemon."""
    import urllib.request
    import json
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode())
            models = [m.get("name") for m in data.get("models", []) if m.get("name")]
            return {
                "ok": True,
                "online": True,
                "models": models if models else ["qwen2.5:0.5b"],
                "default": "qwen2.5:0.5b" if "qwen2.5:0.5b" in models else (models[0] if models else "qwen2.5:0.5b"),
            }
    except Exception as e:
        return {
            "ok": True,
            "online": False,
            "models": ["qwen2.5:0.5b", "gemma:latest"],
            "default": "qwen2.5:0.5b",
            "error": str(e),
        }


@router.get("/status/{user_id}")
async def get_connection_status(user_id: str):
    """Checks whether the user currently has an active connected socket, auto-attaching internal MySQL if eligible."""
    is_attached = default_registry.is_attached(user_id)
    if not is_attached and user_id not in EXPLICITLY_DETACHED:
        is_attached = try_auto_attach_internal_mysql(user_id)
    if not is_attached:
        return {"attached": False, "connected": False, "user_id": user_id, "databases": [], "tables": []}
    conn = default_registry.get(user_id)
    ping = conn.test_connection() if conn else {}
    dbs = []
    tables = []
    if conn:
        try:
            dbs = default_registry.list_databases(conn.config)
        except Exception:
            dbs = [conn.config.database]
        try:
            schema = conn.introspect_schema(force_refresh=False)
            if schema and schema.tables:
                tables = list(schema.tables.keys())
        except Exception:
            tables = []
    return {
        "attached": True,
        "connected": True,
        "user_id": user_id,
        "connector_type": conn.connector_type.value if conn else None,
        "database": conn.config.database if conn else None,
        "host": conn.config.host if conn else None,
        "username": conn.config.username if conn else None,
        "ping": ping,
        "databases": dbs,
        "tables": tables,
    }


@router.post("/switch-database")
async def switch_database(req: SwitchDatabaseRequest):
    """Changes the active database for the user's connected socket and refreshes schema."""
    conn = default_registry.get(req.user_id)
    if not conn or not conn.is_connected:
        raise HTTPException(status_code=404, detail=f"No active database socket attached for user '{req.user_id}'")
    try:
        conn.execute_query(f"USE `{req.database}`")
        conn.config.database = req.database
        schema = conn.introspect_schema(force_refresh=True)
        return {
            "ok": True,
            "user_id": req.user_id,
            "database": req.database,
            "tables": list(schema.tables.keys()),
            "message": f"Switched to database '{req.database}' successfully.",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to switch database: {e}")


@router.post("/execute")
async def execute_direct_query(req: ExecuteDirectRequest):
    """Executes a SQL query or mutation directly on the attached database socket."""
    conn = default_registry.get(req.user_id)
    if not conn or not conn.is_connected:
        raise HTTPException(status_code=404, detail=f"No active database socket attached for user '{req.user_id}'")
    clean_q = req.query.strip().rstrip(";")
    is_write = any(clean_q.upper().startswith(kw) for kw in ("INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "TRUNCATE", "REPLACE", "USE"))
    res = conn.execute_query(clean_q, is_mutating=is_write)
    if is_write:
        try:
            conn.introspect_schema(force_refresh=True)
        except Exception:
            pass
    return {
        "ok": not bool(res.error),
        "columns": res.columns,
        "rows": res.rows,
        "row_count": res.row_count,
        "rows_affected": res.rows_affected,
        "execution_time_ms": res.execution_time_ms,
        "is_mutating": res.is_mutating,
        "error": res.error,
        "database": conn.config.database,
    }


@router.get("/schema/{user_id}")
async def introspect_connected_schema(user_id: str, force_refresh: bool = False):
    """Extracts live schema metadata (tables, columns, foreign keys, row counts) from connected socket."""
    conn = default_registry.get(user_id)
    if not conn or not conn.is_connected:
        raise HTTPException(status_code=404, detail=f"No active database attached for user '{user_id}'")
    try:
        schema = conn.introspect_schema(force_refresh=force_refresh)
        return schema.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Schema introspection failed: {e}")
