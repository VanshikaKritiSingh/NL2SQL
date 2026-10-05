"""
tests/test_core_modules.py — Comprehensive Unit Tests for NL2SQL Core Modules

Tests:
1. Speculative Paradigm Suggestor (CLEF Drafter, Confidence Scheduler, Auto Mode, Divergence Warning).
2. Deterministic Dialect Converter (20+ SQL Dialects, openCypher for Neo4j/Neptune, MongoDB MQL).
3. Schema Linker (Trie Value Grounding, BM25 Schema Retrieval, Graph FK Bridge Injections).
"""

import pytest
from core.paradigm_suggestor import (
    DatabaseParadigm,
    SpeculativeParadigmSuggestor,
    CLEFDiscourseDrafter,
)
from core.dialect_converter import (
    DeterministicDialectConverter,
    InvalidASTSyntaxError,
    DialectFeatureUnsupportedError,
)
from core.schema_linker import (
    SchemaLinker,
    TableMeta,
    ColumnMeta,
    CategoricalValueTrie,
)


# ==============================================================================
# 1. Tests for Paradigm Suggestor & CLEF Classifier
# ==============================================================================

def test_clef_drafter_graph_intent():
    drafter = CLEFDiscourseDrafter()
    p, conf, reason, feat = drafter.draft("Find the shortest path and degrees of separation between Alice and Bob")
    assert p == DatabaseParadigm.GRAPH_OPENCYPHER
    assert conf >= 0.90
    assert "graph" in reason.lower()


def test_clef_drafter_document_intent():
    drafter = CLEFDiscourseDrafter()
    p, conf, reason, feat = drafter.draft("Retrieve users where profile.address.city is San Francisco with nested json profile")
    assert p == DatabaseParadigm.DOCUMENT_NOSQL
    assert conf >= 0.85


def test_clef_drafter_kv_intent():
    drafter = CLEFDiscourseDrafter()
    p, conf, reason, feat = drafter.draft("Fetch by key user_session_token_12948 from cache lookup")
    assert p == DatabaseParadigm.KEY_VALUE
    assert conf >= 0.90


def test_clef_drafter_olap_intent():
    drafter = CLEFDiscourseDrafter()
    p, conf, reason, feat = drafter.draft("Compute quarterly revenue and rolling avg across billions of rows")
    assert p == DatabaseParadigm.COLUMN_FAMILY_OLAP
    assert conf >= 0.88


def test_paradigm_suggestor_auto_mode():
    suggestor = SpeculativeParadigmSuggestor(confidence_threshold=0.80)
    result = suggestor.classify_and_route("Show all customers who placed an order in 2024", auto_mode=True)
    assert result.paradigm == DatabaseParadigm.RELATIONAL_SQL
    assert "PostgreSQL" in result.recommended_engines
    assert result.warning_message is None


def test_paradigm_suggestor_manual_divergence_warning():
    suggestor = SpeculativeParadigmSuggestor(confidence_threshold=0.80)
    # Query is graph-specific, but user selects PostgreSQL manually
    result = suggestor.classify_and_route(
        query="Find 3 degrees of separation and shortest path between company directors",
        user_selected_engine="PostgreSQL",
        auto_mode=False,
    )
    # Target engine must be honored
    assert result.paradigm == DatabaseParadigm.RELATIONAL_SQL
    assert result.warning_message is not None
    assert "Paradigm Divergence Warning" in result.warning_message
    assert "graph_opencypher" in result.warning_message


# ==============================================================================
# 2. Tests for Deterministic Dialect Converter
# ==============================================================================

def test_transpile_sql_to_multiple_dialects():
    converter = DeterministicDialectConverter()
    source_sql = "SELECT id, name, created_at FROM users WHERE age >= 18 ORDER BY created_at DESC LIMIT 10;"

    dialects = ["postgres", "mysql", "sqlite", "duckdb", "clickhouse", "snowflake", "bigquery", "tsql", "oracle"]
    for dialect in dialects:
        res = converter.transpile(source_sql, target_dialect=dialect)
        assert res.is_native_sql is True
        assert isinstance(res.compiled_query, str)
        assert len(res.compiled_query) > 0
        assert res.execution_time_ms < 50.0  # < 50ms


def test_transpile_sql_to_opencypher():
    converter = DeterministicDialectConverter()
    source_sql = "SELECT u.name, o.total FROM users AS u JOIN orders AS o ON u.id = o.user_id WHERE o.total > 100 LIMIT 5;"
    res = converter.transpile(source_sql, target_dialect="neo4j")

    assert res.is_native_sql is False
    assert res.target_dialect == "neo4j"
    assert isinstance(res.compiled_query, str)
    assert "MATCH (u:Users)-[:PLACED]->(o:Orders)" in res.compiled_query
    assert "WHERE o.total > 100" in res.compiled_query
    assert "RETURN u.name, o.total" in res.compiled_query
    assert "LIMIT 5" in res.compiled_query


def test_transpile_sql_to_mongodb_mql():
    converter = DeterministicDialectConverter()
    source_sql = "SELECT department, COUNT(*) AS emp_count, AVG(salary) AS avg_sal FROM employees WHERE status = 'active' GROUP BY department ORDER BY emp_count DESC LIMIT 5;"
    res = converter.transpile(source_sql, target_dialect="mongodb")

    assert res.is_native_sql is False
    assert res.target_dialect == "mongodb"
    assert isinstance(res.compiled_query, dict)
    pipeline = res.compiled_query["pipeline"]
    assert len(pipeline) == 4  # $match, $group, $sort, $limit
    assert pipeline[0]["$match"] == {"status": "active"}
    assert "_id" in pipeline[1]["$group"]
    assert "emp_count" in pipeline[1]["$group"]


def test_transpile_invalid_sql():
    converter = DeterministicDialectConverter()
    with pytest.raises(InvalidASTSyntaxError):
        converter.transpile("SELECT FROM WHERE WHERE", target_dialect="postgres")


# ==============================================================================
# 3. Tests for Schema Linker & Trie Value Grounding
# ==============================================================================

@pytest.fixture
def mock_ecommerce_schema():
    users = TableMeta(
        name="users",
        description="Registered user accounts and demographics",
        columns={
            "id": ColumnMeta(name="id", dtype="INTEGER", is_pk=True),
            "username": ColumnMeta(name="username", dtype="TEXT", categorical_values=["alice_smith", "bob_jones"]),
            "email": ColumnMeta(name="email", dtype="TEXT"),
            "country": ColumnMeta(name="country", dtype="TEXT", categorical_values=["United States", "Germany", "Japan"]),
        }
    )
    orders = TableMeta(
        name="orders",
        description="Customer checkout orders",
        columns={
            "id": ColumnMeta(name="id", dtype="INTEGER", is_pk=True),
            "user_id": ColumnMeta(name="user_id", dtype="INTEGER", is_fk=True, fk_target_table="users", fk_target_column="id"),
            "order_status": ColumnMeta(name="order_status", dtype="TEXT", categorical_values=["shipped", "pending", "refunded"]),
            "total_amount": ColumnMeta(name="total_amount", dtype="DECIMAL(10,2)"),
        }
    )
    order_items = TableMeta(
        name="order_items",
        description="Individual line items within each order",
        columns={
            "id": ColumnMeta(name="id", dtype="INTEGER", is_pk=True),
            "order_id": ColumnMeta(name="order_id", dtype="INTEGER", is_fk=True, fk_target_table="orders", fk_target_column="id"),
            "product_id": ColumnMeta(name="product_id", dtype="INTEGER", is_fk=True, fk_target_table="products", fk_target_column="id"),
            "quantity": ColumnMeta(name="quantity", dtype="INTEGER"),
        }
    )
    products = TableMeta(
        name="products",
        description="Product catalog inventory and prices",
        columns={
            "id": ColumnMeta(name="id", dtype="INTEGER", is_pk=True),
            "product_name": ColumnMeta(name="product_name", dtype="TEXT", categorical_values=["MacBook Pro", "Wireless Mouse"]),
            "price": ColumnMeta(name="price", dtype="DECIMAL(10,2)"),
        }
    )
    return {
        "users": users,
        "orders": orders,
        "order_items": order_items,
        "products": products,
    }


def test_categorical_value_trie():
    trie = CategoricalValueTrie()
    trie.insert("Germany", "users.country")
    trie.insert("MacBook Pro", "products.product_name")

    matches = trie.search_query_matches("Find customers in Germany who ordered a MacBook Pro")
    assert "germany" in matches
    assert matches["germany"] == "users.country"
    assert "macbook pro" in matches
    assert matches["macbook pro"] == "products.product_name"


def test_schema_linker_steiner_bridge(mock_ecommerce_schema):
    linker = SchemaLinker(tables=mock_ecommerce_schema)
    # Query mentions users and products -> Linker must automatically inject intermediate tables 'orders' & 'order_items'
    ctx = linker.link_context(
        query="List all users who purchased a MacBook Pro in Germany",
        max_tables=4,
    )

    assert "users" in ctx.selected_tables
    assert "products" in ctx.selected_tables
    # Bridge tables injected via graph shortest path
    assert "orders" in ctx.selected_tables
    assert "order_items" in ctx.selected_tables
    assert "germany" in ctx.grounded_values or "macbook pro" in ctx.grounded_values
    assert "CREATE TABLE users" in ctx.prompt_ddl
    assert "CREATE TABLE products" in ctx.prompt_ddl
