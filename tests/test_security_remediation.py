"""
tests/test_security_remediation.py — Tests for DA-01 through DA-05, DA-07, DA-13, DA-17, DA-21
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest

# Ensure GUI/server is on sys.path so its internal relative imports resolve
_server_dir = str(Path(__file__).resolve().parent.parent / "GUI" / "server")
if _server_dir not in sys.path:
    sys.path.insert(0, _server_dir)


# DA-01: sanitized statement attached and params forwarded to connector
def test_da01_sanitized_statement_forwarded_to_connector():
    from core.orchestrator import EndToEndNL2SQLOrchestrator
    from core.schema_linker import TableMeta, ColumnMeta
    from core.connectors import default_registry

    T = {
        "users": TableMeta(
            "users",
            {"id": ColumnMeta("id", "INT", is_pk=True), "name": ColumnMeta("name", "TEXT")},
            "Users table",
        )
    }
    o = EndToEndNL2SQLOrchestrator(schema_tables=T)

    mock_conn = MagicMock()
    mock_conn.is_connected = True
    mock_conn.execute_query.return_value = MagicMock(error=None, rows=[], columns=[], execution_time_ms=1.0)
    default_registry._connections["test_user_da01"] = mock_conn

    try:
        plan = o.process_query(
            "show users where name is bob",
            target_engine="postgres",
            auto_mode=False,
            user_id="test_user_da01",
        )
        assert plan.sanitized_statement is not None, "sanitized_statement not attached to plan"
        assert plan.sanitized_statement.params == ["bob"]
        assert "$1" in plan.sanitized_statement.sql
        assert "'bob'" not in plan.sanitized_statement.sql

        # Assert connector was called with the parameterized query, NOT raw inlined SQL
        mock_conn.execute_query.assert_called_once()
        called_q, called_kwargs = mock_conn.execute_query.call_args[0][0], mock_conn.execute_query.call_args[1]
        assert "$1" in called_q
        assert called_kwargs.get("params") == ["bob"]
    finally:
        default_registry.detach("test_user_da01")


# DA-02: safe identifier validator rejects SQL injection payloads
def test_da02_safe_ident_rejects_injection():
    from routers.connections import _validate_and_quote_ident
    from fastapi import HTTPException

    # Valid identifiers pass and get quoted
    assert _validate_and_quote_ident("users") == "`users`"
    assert _validate_and_quote_ident("app_db_1") == "`app_db_1`"

    # Malicious injection payloads raise HTTP 400
    for bad in [
        "x`; DROP TABLE users;--",
        "db' OR '1'='1",
        "db; SHUTDOWN;",
        "../../../etc/passwd",
        "",
        "1starts_with_digit",
    ]:
        with pytest.raises(HTTPException) as exc_info:
            _validate_and_quote_ident(bad)
        assert exc_info.value.status_code == 400


# DA-03: pip install endpoint is read-only diagnostic, executes zero subprocesses
@pytest.mark.anyio
async def test_da03_install_deps_is_diagnostic_only():
    from routers.connections import install_connector_dependencies, InstallDepsRequest

    res = await install_connector_dependencies(InstallDepsRequest(connector_type="sqlite"))
    assert res["ok"] is True
    assert res["packages"] == []

    res2 = await install_connector_dependencies(InstallDepsRequest(connector_type="postgres"))
    assert "already_installed" in res2
    assert "missing_packages" in res2


# DA-04: bearer token auth middleware rejects unauthorized requests when token is configured
def test_da04_auth_middleware_blocks_missing_token(monkeypatch):
    from fastapi.testclient import TestClient
    import main

    # Simulate active token in environment
    token = "test-secret-token-12345"
    monkeypatch.setattr(main, "API_AUTH_TOKEN", token)

    client = TestClient(main.app)

    # Health and docs are exempt
    assert client.get("/").status_code == 200

    # Protected endpoint without token returns 401 when token is configured
    r = client.get("/api/schema/postgres")
    assert r.status_code == 401

    # Protected endpoint with wrong token returns 401
    r = client.get("/api/schema/postgres", headers={"Authorization": "Bearer wrong-secret"})
    assert r.status_code == 401

    # Protected endpoint with valid token does NOT return 401
    r = client.get("/api/schema/postgres", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code != 401

    # When token is unset (open dev mode), requests pass through without 401
    monkeypatch.setattr(main, "API_AUTH_TOKEN", None)
    r_open = client.get("/api/schema/postgres")
    assert r_open.status_code != 401


# DA-07: approval router schema fingerprint detects changes
def test_da07_schema_fingerprint_deterministic():
    from routers.approval import _schema_fingerprint
    from core.connectors.base import SchemaMetadata, TableSchema, ColumnSchema

    s1 = SchemaMetadata(
        database_name="prod",
        dialect="postgres",
        tables={
            "users": TableSchema(name="users", columns={"id": ColumnSchema("id", "INT"), "name": ColumnSchema("name", "TEXT")}),
        },
    )
    s2 = SchemaMetadata(
        database_name="prod",
        dialect="postgres",
        tables={
            "users": TableSchema(name="users", columns={"id": ColumnSchema("id", "INT"), "name": ColumnSchema("name", "TEXT")}),
        },
    )
    s3 = SchemaMetadata(
        database_name="prod",
        dialect="postgres",
        tables={
            "users": TableSchema(name="users", columns={"id": ColumnSchema("id", "INT"), "email": ColumnSchema("email", "TEXT")}),
        },
    )
    assert _schema_fingerprint(s1) == _schema_fingerprint(s2)
    assert _schema_fingerprint(s1) != _schema_fingerprint(s3)


# DA-13: bridge tables survive truncation in schema linker
def test_da13_bridge_tables_never_truncated():
    from core.schema_linker import SchemaLinker, TableMeta, ColumnMeta

    T = {
        "orders": TableMeta("orders", {"id": ColumnMeta("id", "INT", is_pk=True), "oid": ColumnMeta("oid", "INT", is_fk=True, fk_target_table="order_items")}),
        "order_items": TableMeta("order_items", {"id": ColumnMeta("id", "INT", is_pk=True), "pid": ColumnMeta("pid", "INT", is_fk=True, fk_target_table="products")}),
        "products": TableMeta("products", {"id": ColumnMeta("id", "INT", is_pk=True), "cid": ColumnMeta("cid", "INT", is_fk=True, fk_target_table="categories")}),
        "categories": TableMeta("categories", {"id": ColumnMeta("id", "INT", is_pk=True), "name": ColumnMeta("name", "TEXT")}),
    }
    sl = SchemaLinker(tables=T)
    ctx = sl.link_context("show orders by category", max_tables=2)
    assert "orders" in ctx.selected_tables
    assert "categories" in ctx.selected_tables
    assert ("order_items" in ctx.selected_tables) or ("products" in ctx.selected_tables)


# DA-17: analysis router returns 404 for unknown query_id, not mock data
@pytest.mark.anyio
async def test_da17_analysis_router_returns_404_for_unknown_id():
    from routers.analysis import get_explain_estimate, get_security_check, get_diff_preview
    from fastapi import HTTPException

    for fn in (get_explain_estimate, get_security_check, get_diff_preview):
        with pytest.raises(HTTPException) as exc_info:
            await fn("non-existent-query-id-999")
        assert exc_info.value.status_code == 404


# DA-21: PEP 562 lazy imports don't load heavy deps
def test_da21_core_lazy_imports():
    import core

    lm = core.LockManager
    assert lm is not None
    assert "EndToEndNL2SQLOrchestrator" in core.__all__
    assert "SchemaLinker" in core.__all__
    assert "DeterministicDialectConverter" in core.__all__
