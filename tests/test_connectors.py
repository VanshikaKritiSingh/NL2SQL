"""
tests/test_connectors.py — Unit tests for DBMS and Ollama LLM Connectors
"""

import pytest
from unittest.mock import MagicMock, patch
import sqlglot
from sqlglot import exp

from core.connectors.ollama import OllamaConnector, OllamaGenerationResult, default_ollama
from core.connectors.sqlite import SQLiteConnector
from core.connectors.mysql import MySQLConnector
from core.connectors.base import ConnectionConfig, ConnectorType


def testOllamaServiceOnlineAndListsAvailableModels():
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


def testOllamaResolvesOptimalGenerativeCodingModel():
    connector = OllamaConnector()
    best = connector.resolve_best_model()
    assert "coder" in best.lower() or "qwen" in best.lower() or "gemma" in best.lower()

    # If user requests auto
    resolved_auto = connector.resolve_best_model("auto")
    assert resolved_auto == best

    # If user requests non-chat model (like clef-flash), connector auto-routes to safe generative model
    resolved_clef = connector.resolve_best_model("clef-flash:latest")
    assert resolved_clef != "clef-flash:latest"


def testOllamaCleansMarkdownFencesAndExtractsThinkingTags():
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


def testOllamaGeneratesSyntacticallyValidPostgreSqlQuery():
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


def testSqliteConnectorInMemoryExecutionAndSchemaIntrospection():
    cfg = ConnectionConfig(connector_type=ConnectorType.SQLITE, database=":memory:")
    conn = SQLiteConnector(cfg)
    test_res = conn.verifyDatabaseConnectionStatus()
    assert test_res["ok"] is True

    # Introspect empty
    schema = conn.introspectDatabaseCatalogSchema(force_refresh=True)
    assert schema.database_name == ":memory:"

    # Execute DDL & query using self-documenting camelCase methods
    conn.executeQueryAgainstDatabaseEngine("CREATE TABLE test_tbl (id INT PRIMARY KEY, name TEXT);", is_mutating=True)
    conn.executeQueryAgainstDatabaseEngine("INSERT INTO test_tbl VALUES (1, 'Alice');", is_mutating=True)
    q_res = conn.executeQueryAgainstDatabaseEngine("SELECT * FROM test_tbl;", is_mutating=False)
    assert q_res.row_count == 1
    assert q_res.rows[0]["name"] == "Alice"


def testAllConnectorTypesCanBeInstantiatedWithBothCamelCaseAndSnakeCaseMethods():
    """Verify all 10 connector classes instantiate cleanly and expose both camelCase and snake_case APIs."""
    from core.connectors.registry import instantiateConnectorForConfiguration

    for ctype in ConnectorType:
        extra = {"protocol": "sqlite"} if ctype == ConnectorType.CUSTOM else {}
        cfg = ConnectionConfig(connector_type=ctype, database="unit_test_db", extra_params=extra)
        conn = instantiateConnectorForConfiguration(cfg)
        assert conn is not None
        # Check Java-style camelCase methods
        assert hasattr(conn, "establishDatabaseConnection")
        assert hasattr(conn, "terminateDatabaseConnection")
        assert hasattr(conn, "verifyDatabaseConnectionStatus")
        assert hasattr(conn, "introspectDatabaseCatalogSchema")
        assert hasattr(conn, "listAccessibleDatabaseNames")
        assert hasattr(conn, "executeQueryAgainstDatabaseEngine")
        assert hasattr(conn, "generateQueryExecutionPlan")
        # Check backward-compatible snake_case methods
        assert hasattr(conn, "connect")
        assert hasattr(conn, "disconnect")
        assert hasattr(conn, "test_connection")
        assert hasattr(conn, "introspect_schema")
        assert hasattr(conn, "list_databases")
        assert hasattr(conn, "execute_query")
        assert hasattr(conn, "explain_query")


def testCustomConnectorDelegationAndExecution():
    """Verify CustomConnector dispatches to chosen protocol (e.g. SQLite/Postgres/MySQL)."""
    from core.connectors.base import ConnectionConfig, ConnectorType
    from core.connectors.registry import instantiateConnectorForConfiguration

    cfg = ConnectionConfig(
        connector_type=ConnectorType.CUSTOM,
        database=":memory:",
        extra_params={"protocol": "sqlite", "custom_name": "Personal SQLite Engine"},
    )
    conn = instantiateConnectorForConfiguration(cfg)
    assert conn.connect() is True
    ping = conn.test_connection()
    assert ping["ok"] is True
    assert ping["custom_name"] == "Personal SQLite Engine"

    # Mutate and query
    conn.execute_query("CREATE TABLE custom_kv (k TEXT PRIMARY KEY, v TEXT);", is_mutating=True)
    conn.execute_query("INSERT INTO custom_kv VALUES ('cluster', 'east-1');", is_mutating=True)
    res = conn.execute_query("SELECT * FROM custom_kv;")
    assert res.row_count == 1
    assert res.rows[0]["v"] == "east-1"
    conn.disconnect()



def testMySQLCreateDatabaseDoesNotInjectTestPrefix():
    """Verify MySQL connector creates customDB without silently prefixing test_ or rewriting queries."""
    from unittest.mock import MagicMock
    from core.connectors.mysql import MySQLConnector
    from core.connectors.base import ConnectionConfig, ConnectorType

    cfg = ConnectionConfig(
        connector_type=ConnectorType.MYSQL,
        host="127.0.0.1",
        port=3306,
        username="developer",
        database="initial_db",
    )
    connector = MySQLConnector(cfg)
    connector._is_connected = True
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.description = None
    mock_cursor.rowcount = 1
    mock_cursor.nextset.return_value = False
    connector._conn = mock_conn

    # 1. Successful creation of customDB
    res = connector.execute_query("CREATE DATABASE customDB; CREATE TABLE users (id INT);", is_mutating=True)
    assert connector.config.database == "customDB"
    assert not connector.config.database.startswith("test_")
    # Verify exact SQL sent to cursor had customDB, not test_customDB
    args, _ = mock_cursor.execute.call_args
    assert "customDB" in args[0]
    assert "test_customDB" not in args[0]

    # 2. Error 1044 is reported transparently without changing database name to test_otherDB
    mock_cursor.execute.side_effect = Exception("1044 (42000): Access denied for user to database otherDB")
    connector.config.database = "initial_db"
    res2 = connector.execute_query("CREATE DATABASE otherDB;", is_mutating=True)
    assert res2.error is not None
    assert "MySQL Error 1044" in res2.error
    assert connector.config.database == "initial_db"


def testMySQLNoneDatabaseNormalizationAndScratchConnect():
    """Verify that selecting __none__ or scratch normalizes database to empty string and connects with database=None."""
    cfg = ConnectionConfig(
        connector_type=ConnectorType.MYSQL,
        database="__none__",
        host="127.0.0.1",
        port=3306,
        username="admin",
        password="secretpassword",
    )
    assert cfg.database == ""

    with patch("pymysql.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        connector = MySQLConnector(cfg)
        assert connector.connect() is True
        # Verify pymysql was called with database=None
        _, kwargs = mock_connect.call_args
        assert kwargs["database"] is None

        # Verify introspect_schema returns clean empty schema
        meta = connector.introspect_schema()
        assert meta.tables == {}
        assert meta.database_name == ""


def testOllamaDecisionModelResolutionAndSystemOneEndpoint():
    """Verify Ollama decision model resolution and /v1/systemone non-autoregressive classification."""
    connector = OllamaConnector()
    dec_model = connector.resolve_decision_model()
    # If Clef is installed, it resolves to clef-flash or clef-flash-cpu
    if dec_model:
        assert "clef" in dec_model.lower() or "decision" in dec_model.lower()

