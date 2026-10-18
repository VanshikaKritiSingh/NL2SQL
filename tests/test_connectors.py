"""
tests/test_connectors.py — Unit tests for DBMS and Ollama LLM Connectors
"""

import pytest
import sqlglot
from sqlglot import exp

from core.connectors.ollama import OllamaConnector, OllamaGenerationResult, default_ollama
from core.connectors.sqlite import SQLiteConnector
from core.connectors.base import ConnectionConfig, ConnectorType


def test_ollama_online_and_list_models():
    connector = OllamaConnector()
    online = connector.is_online()
    assert online is True

    models = connector.list_models()
    assert len(models) > 0
    # Confirm models have required fields
    for m in models:
        assert "name" in m
        assert "is_generative" in m
        assert "supports_thinking" in m


def test_ollama_resolve_best_model():
    connector = OllamaConnector()
    best = connector.resolve_best_model()
    assert "coder" in best.lower() or "qwen" in best.lower() or "gemma" in best.lower()

    # If user requests auto
    resolved_auto = connector.resolve_best_model("auto")
    assert resolved_auto == best

    # If user requests non-chat model (like clef-flash), connector auto-routes to safe generative model
    resolved_clef = connector.resolve_best_model("clef-flash:latest")
    assert resolved_clef != "clef-flash:latest"


def test_ollama_clean_sql_and_extract_thought():
    connector = OllamaConnector()

    # 1. Markdown code fence stripping
    raw_markdown = "```sql\nSELECT user_id, username FROM users WHERE status = 'active';\n```"
    sql, thought = connector._clean_sql_and_extract_thought(raw_markdown)
    assert sql == "SELECT user_id, username FROM users WHERE status = 'active';"
    assert thought is None

    # 2. Thinking tag extraction
    raw_thinking = "<think>Filtering active users by status</think>\nSELECT * FROM users WHERE status = 'active';"
    sql, thought = connector._clean_sql_and_extract_thought(raw_thinking)
    assert sql == "SELECT * FROM users WHERE status = 'active';"
    assert thought == "Filtering active users by status"

    # 3. Conversational preamble stripping
    raw_conversational = "Here is the query you asked for:\n\nSELECT * FROM orders;\n\nExplanation: this fetches orders."
    sql, thought = connector._clean_sql_and_extract_thought(raw_conversational)
    assert sql == "SELECT * FROM orders;"

    # 4. Semicolon auto-append
    raw_no_semi = "SELECT COUNT(*) FROM products"
    sql, _ = connector._clean_sql_and_extract_thought(raw_no_semi)
    assert sql.endswith(";")


def test_ollama_live_generation_sql_syntax():
    schema = """
    CREATE TABLE users (user_id INT PRIMARY KEY, username VARCHAR(100), status VARCHAR(50));
    CREATE TABLE orders (order_id INT PRIMARY KEY, user_id INT REFERENCES users(user_id), total_amount DECIMAL(10,2));
    """
    res = default_ollama.generate_sql(
        query="List all active users who placed an order over 100",
        schema_ddl=schema,
        target_dialect="postgres",
    )
    assert res.success is True
    assert res.sql.rstrip().endswith(";")
    parsed = sqlglot.parse_one(res.sql)
    assert parsed is not None
    assert isinstance(parsed, exp.Select)
    assert "users" in res.sql.lower()


def test_sqlite_connector_in_memory():
    cfg = ConnectionConfig(connector_type=ConnectorType.SQLITE, database=":memory:")
    conn = SQLiteConnector(cfg)
    test_res = conn.test_connection()
    assert test_res["ok"] is True

    # Introspect empty
    schema = conn.introspect_schema(force_refresh=True)
    assert schema.database_name == ":memory:"

    # Execute DDL & query
    conn.execute_query("CREATE TABLE test_tbl (id INT PRIMARY KEY, name TEXT);", is_mutating=True)
    conn.execute_query("INSERT INTO test_tbl VALUES (1, 'Alice');", is_mutating=True)
    q_res = conn.execute_query("SELECT * FROM test_tbl;", is_mutating=False)
    assert q_res.row_count == 1
    assert q_res.rows[0]["name"] == "Alice"
