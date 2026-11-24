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
import re
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.connectors import (
    ConnectionConfig,
    ConnectorType,
    default_registry,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connections", tags=["DBMS Connectors & Sockets"])

# Safe identifier: letters/digits/underscore/dollar/hyphen, 1-64 chars, must start with letter or _
_SAFE_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$-]{0,63}$")


def _validate_and_quote_ident(name: str, quote_char: str = "`", label: str = "identifier") -> str:
    """Validate a SQL identifier against a strict allowlist pattern and double-quote it."""
    if not name or not _SAFE_IDENT_RE.match(name):
        raise HTTPException(
            status_code=400,
            detail=f"Unsafe SQL {label} rejected: {name!r} — must match [A-Za-z_][A-Za-z0-9_$-]{{1,64}}"
        )
    escaped = name.replace(quote_char, quote_char * 2)
    return f"{quote_char}{escaped}{quote_char}"


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


class SwitchDatabaseRequest(BaseModel):
    user_id: str = Field(..., description="User session ID")
    database: str = Field(..., description="Target database to switch to")


class ExecuteDirectRequest(BaseModel):
    user_id: str = Field(..., description="User session ID")
    query: str = Field(..., description="Raw SQL query or DDL/DML statement to execute")


@router.post("/attach")
async def attachDatabaseConnectionToUserSession(req: AttachRequest):
    """Binds a live database socket to the specified user session in-memory."""
    raw_db = req.database or ""
    clean_db = "" if raw_db in ("__none__", "none", "(none)", "(None / New Database)", "scratch") else raw_db.strip()
    config = ConnectionConfig(
        connector_type=req.connector_type,
        database=clean_db,
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
            "database": config.database or "(None / Scratch)",
            "ping": ping,
            "message": f"Connected to {req.connector_type.value} [{config.database or 'scratch'}] successfully.",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to attach database: {e}")


attach_connection = attachDatabaseConnectionToUserSession


@router.delete("/{user_id}")
async def detachDatabaseConnectionFromUserSession(user_id: str):
    """Closes and removes the user's active database socket."""
    detached = default_registry.detach(user_id)
    try:
        from routers.query import orchestrator
        orchestrator.update_schema({})
    except Exception as exc:
        logger.warning("Suppressed non-fatal error in connections.py: %s", exc, exc_info=True)
    return {
        "ok": True,
        "user_id": user_id,
        "detached": detached,
        "message": "Database disconnected cleanly." if detached else "No active connection found for this user.",
    }


detach_connection = detachDatabaseConnectionFromUserSession


@router.post("/test")
async def testDatabaseConnectionParameters(req: TestRequest):
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


test_connection_params = testDatabaseConnectionParameters


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


# ─── Dependency Map: Connector → pip packages ───────────────────────────────
CONNECTOR_DEPS = {
    "sqlite": [],  # stdlib, no extra deps
    "duckdb": ["duckdb"],
    "postgres": ["psycopg2-binary"],
    "mysql": ["pymysql"],
    "clickhouse": [],  # uses stdlib urllib (HTTP API)
    "mongodb": ["pymongo"],
    "neo4j": ["neo4j"],
    "redis": ["redis"],
    "cassandra": ["cassandra-driver"],
    "dynamodb": ["boto3"],
    "custom": [],  # uses resolved protocol driver
}


class InstallDepsRequest(BaseModel):
    connector_type: str = Field(..., description="Target connector type (e.g. mysql, postgres)")


@router.post("/install-deps")
async def install_connector_dependencies(req: InstallDepsRequest):
    """
    DEPRECATED (DA-03): This endpoint no longer executes pip at runtime.

    Returns a read-only diagnostic report of installed vs. missing packages
    and the manual pip command the user should run in their terminal.
    All dependencies are already declared in requirements.txt; there is no
    need to install drivers dynamically from an HTTP route.
    """
    ct = req.connector_type.lower().strip()
    if ct not in CONNECTOR_DEPS:
        raise HTTPException(status_code=400, detail=f"Unknown connector type: '{ct}'. Supported: {list(CONNECTOR_DEPS.keys())}")

    packages = CONNECTOR_DEPS[ct]
    if not packages:
        return {
            "ok": True,
            "connector_type": ct,
            "packages": [],
            "message": f"No external dependencies needed for {ct} — it uses Python stdlib or built-in HTTP.",
            "already_installed": True,
        }

    already = []
    missing = []
    for pkg in packages:
        import_name = pkg.replace("-", "_").replace("psycopg2_binary", "psycopg2")
        try:
            __import__(import_name)
            already.append(pkg)
        except ImportError:
            missing.append(pkg)

    return {
        "ok": len(missing) == 0,
        "connector_type": ct,
        "already_installed": already,
        "missing_packages": missing,
        "install_command": f"pip install {' '.join(missing)}" if missing else None,
        "message": (
            f"All {ct} dependencies installed." if not missing
            else f"Run: pip install {' '.join(missing)}"
        ),
    }


@router.get("/check-deps/{connector_type}")
async def check_connector_dependencies(connector_type: str):
    """
    Checks whether the Python driver packages for a given connector type are installed.
    Returns installed/missing status for each package.
    """
    ct = connector_type.lower().strip()
    if ct not in CONNECTOR_DEPS:
        raise HTTPException(status_code=400, detail=f"Unknown connector type: '{ct}'")

    packages = CONNECTOR_DEPS[ct]
    if not packages:
        return {
            "ok": True,
            "connector_type": ct,
            "all_installed": True,
            "packages": [],
            "message": f"{ct} uses Python stdlib — no external packages needed.",
        }

    status_list = []
    all_ok = True
    for pkg in packages:
        import_name = pkg.replace("-", "_").replace("psycopg2_binary", "psycopg2")
        try:
            mod = __import__(import_name)
            ver = getattr(mod, "__version__", getattr(mod, "version", "unknown"))
            status_list.append({"package": pkg, "installed": True, "version": str(ver)})
        except ImportError:
            status_list.append({"package": pkg, "installed": False, "version": None})
            all_ok = False

    return {
        "ok": True,
        "connector_type": ct,
        "all_installed": all_ok,
        "packages": status_list,
        "message": "All dependencies ready." if all_ok else f"Missing packages: {', '.join(p['package'] for p in status_list if not p['installed'])}",
    }


@router.get("/models")
async def list_available_models():
    """Lists available local LLM models dynamically from local PEFT engine (A2.5C0.5, Q2.5C0.5, A2.5C1.5, Q2.5C1.5) and the Ollama daemon."""
    from core.connectors.ollama import default_ollama
    from core.connectors.peft_connector import default_peft_engine

    models = []
    model_details = []

    # 1. Native PEFT field-test models (all sizes: 0.5B and 1.5B)
    try:
        peft_models = default_peft_engine.list_available_models()
        for pm in peft_models:
            models.append(pm["name"])
            model_details.append(pm)
    except Exception as exc:
        logger.warning("Suppressed non-fatal error in connections.py: %s", exc, exc_info=True)

    # 2. Local Ollama models
    ollama_online = False
    try:
        if default_ollama.is_online():
            ollama_online = True
            all_models = default_ollama.list_models()
            chat_models = [m for m in all_models if m.get("is_generative", True)]
            for cm in chat_models:
                if cm["name"] not in models:
                    models.append(cm["name"])
                    model_details.append(cm)
    except Exception as exc:
        logger.warning("Suppressed non-fatal error in connections.py: %s", exc, exc_info=True)

    # Prefer 1.5B AdaLoRA as default when available (better quality, still consumer CPU)
    preferred = ["A2.5C1.5", "Q2.5C1.5", "A2.5C0.5", "Q2.5C0.5"]
    default_model = next((m for m in preferred if m in models), models[0] if models else "offline_synthesizer")

    return {
        "ok": True,
        "online": (ollama_online or len(models) > 0),
        "models": models,
        "model_details": model_details,
        "default": default_model,
    }


@router.get("/status/{user_id}")
async def get_connection_status(user_id: str):
    """Checks whether the user currently has an active connected socket."""
    is_attached = default_registry.is_attached(user_id)
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
    if req.database in ("__none__", "", "none", "(none)"):
        conn.config.database = ""
        conn._cached_schema = None
        try:
            from routers.query import orchestrator
            orchestrator.update_schema({})
        except Exception as exc:
            logger.warning("Suppressed non-fatal error in connections.py: %s", exc, exc_info=True)
        return {
            "ok": True,
            "user_id": req.user_id,
            "database": "",
            "tables": [],
            "message": "Switched to clean scratch context (no database selected).",
        }
    try:
        safe_db = _validate_and_quote_ident(req.database, quote_char="`", label="database name")
        conn.execute_query(f"USE {safe_db}")
        conn.config.database = req.database
        schema = conn.introspect_schema(force_refresh=True)
        try:
            from routers.query import sync_orchestrator_from_schema
            sync_orchestrator_from_schema(schema)
        except Exception as exc:
            logger.warning("Suppressed non-fatal error in connections.py: %s", exc, exc_info=True)
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
    """Executes a SQL query or mutation directly on the attached database socket or in-memory preview sandbox."""
    conn = default_registry.get(req.user_id)
    if conn and conn.is_connected:
        clean_q = req.query.strip().rstrip(";")
        is_write = any(clean_q.upper().startswith(kw) for kw in ("INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "TRUNCATE", "REPLACE", "USE"))
        res = conn.execute_query(clean_q, is_mutating=is_write)
        if is_write:
            try:
                schema = conn.introspect_schema(force_refresh=True)
                try:
                    from routers.query import sync_orchestrator_from_schema
                    sync_orchestrator_from_schema(schema)
                except Exception as exc:
                    logger.warning("Suppressed non-fatal error in connections.py: %s", exc, exc_info=True)
            except Exception as exc:
                logger.warning("Suppressed non-fatal error in connections.py: %s", exc, exc_info=True)
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
            "target": "live_socket",
        }

    # Offline in-memory sandbox execution fallback
    import time
    start_t = time.perf_counter()
    from routers.query import get_session_sandbox, sync_sandbox_ddl
    db = get_session_sandbox(req.user_id)
    clean_q = req.query.strip()
    is_write = any(clean_q.upper().startswith(kw) for kw in ("INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "TRUNCATE", "REPLACE", "USE"))
    try:
        if is_write and any(clean_q.upper().startswith(kw) for kw in ("CREATE", "ALTER", "DROP")):
            sync_sandbox_ddl(req.user_id, clean_q)
        cur = db.cursor()
        cur.execute(clean_q)
        elapsed = round((time.perf_counter() - start_t) * 1000, 2)
        if cur.description:
            cols = [d[0] for d in cur.description]
            raw_rows = cur.fetchmany(100)
            rows = [dict(zip(cols, r)) for r in raw_rows]
            return {
                "ok": True,
                "columns": cols,
                "rows": rows,
                "row_count": len(rows),
                "rows_affected": None,
                "execution_time_ms": elapsed,
                "is_mutating": False,
                "error": None,
                "database": "sandbox (:memory:)",
                "target": "preview_sandbox",
            }
        else:
            db.commit()
            return {
                "ok": True,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "rows_affected": cur.rowcount if cur.rowcount >= 0 else 1,
                "execution_time_ms": elapsed,
                "is_mutating": True,
                "error": None,
                "database": "sandbox (:memory:)",
                "target": "preview_sandbox",
            }
    except Exception as e:
        elapsed = round((time.perf_counter() - start_t) * 1000, 2)
        return {
            "ok": False,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "rows_affected": 0,
            "execution_time_ms": elapsed,
            "is_mutating": is_write,
            "error": str(e),
            "database": "sandbox (:memory:)",
            "target": "preview_sandbox",
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
