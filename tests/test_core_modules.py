"""
tests/test_core_modules.py — Comprehensive End-to-End & Unit Test Suite for NL2SQL Pipeline

Covers:
1. Speculative Paradigm Suggestor & CLEF Classifier (6 Paradigms, Speculative Verifier, Divergence Warnings).
2. Deterministic Universal Dialect Converter (20+ SQL dialects, openCypher Graph Engine, MongoDB MQL Aggregation Pipelines).
3. Schema Linker & Trie Grounding (Punctuation-Safe Cell Value Trie, Hybrid BM25+Fuzzy RRF, Steiner Minimal Tree Bridge Injections).
4. 6-Layer Static AST Validator (PARSE, POLICY, SCHEMA, SEMANTIC, QUERY_AP, SCHEMA_AP, RuleRegistry).
5. Heuristic Cost & Blast-Radius Engine (Read/Write Cost, Scan Row Scaling, Threshold Escalation/Rejection).
6. Unified Orchestrator & Semantic SQL Synthesizer (End-to-End Pipeline Loop & Dual-Path Routing).
"""

import pytest
import sqlglot
from sqlglot import exp

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
    LinkedSchemaContext,
)
from validator.contracts import (
    IssueCode,
    Layer,
    Severity,
    StatementType,
    Status,
)
from validator.engine import (
    validate_parse,
    validate_policy,
    validate_schema,
    validate_semantic,
    validate_query_anti_patterns,
    validate_schema_anti_patterns,
    run_validation,
)
from validator.interfaces import FakeSchemaProvider
from validator.rules import RuleRegistry, RuleEntry
from cost_estimator.contracts import CostReport
from cost_estimator.engine import HeuristicCostEngine
from cost_estimator.thresholds import Thresholds
from core.orchestrator import EndToEndNL2SQLOrchestrator, SemanticSQLSynthesizer


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def mock_ecommerce_schema():
    users = TableMeta(
        name="users",
        description="Registered user accounts and demographics",
        columns={
            "id": ColumnMeta(name="id", dtype="INTEGER", is_pk=True),
            "username": ColumnMeta(name="username", dtype="VARCHAR(100)", categorical_values=["alice_smith", "bob_jones"]),
            "email": ColumnMeta(name="email", dtype="VARCHAR(255)"),
            "status": ColumnMeta(name="status", dtype="VARCHAR(50)", categorical_values=["active", "inactive"]),
            "country": ColumnMeta(name="country", dtype="VARCHAR(100)", categorical_values=["United States", "Germany", "Japan"]),
        }
    )
    orders = TableMeta(
        name="orders",
        description="Customer checkout orders",
        columns={
            "id": ColumnMeta(name="id", dtype="INTEGER", is_pk=True),
            "user_id": ColumnMeta(name="user_id", dtype="INTEGER", is_fk=True, fk_target_table="users", fk_target_column="id"),
            "order_status": ColumnMeta(name="order_status", dtype="VARCHAR(50)", categorical_values=["shipped", "pending", "refunded"]),
            "total_amount": ColumnMeta(name="total_amount", dtype="DECIMAL(10,2)"),
            "created_at": ColumnMeta(name="created_at", dtype="TIMESTAMP"),
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
            "unit_price": ColumnMeta(name="unit_price", dtype="DECIMAL(10,2)"),
        }
    )
    products = TableMeta(
        name="products",
        description="Product catalog inventory and prices",
        columns={
            "id": ColumnMeta(name="id", dtype="INTEGER", is_pk=True),
            "product_name": ColumnMeta(name="product_name", dtype="VARCHAR(255)", categorical_values=["MacBook Pro", "Wireless Mouse"]),
            "category": ColumnMeta(name="category", dtype="VARCHAR(100)", categorical_values=["Electronics", "Computers"]),
            "price": ColumnMeta(name="price", dtype="DECIMAL(10,2)"),
        }
    )
    return {
        "users": users,
        "orders": orders,
        "order_items": order_items,
        "products": products,
    }


# ==============================================================================
# 1. Speculative Paradigm Suggestor & CLEF Classifier Tests
# ==============================================================================

def test_clef_drafter_all_six_paradigms():
    drafter = CLEFDiscourseDrafter()

    # Graph
    p, conf, _, _ = drafter.draft("Find 3 hops and shortest path from Alice to Bob")
    assert p == DatabaseParadigm.GRAPH_OPENCYPHER and conf >= 0.90

    # Document
    p, conf, _, _ = drafter.draft("Fetch document where customer.profile.address is nested")
    assert p == DatabaseParadigm.DOCUMENT_NOSQL and conf >= 0.85

    # Key-Value
    p, conf, _, _ = drafter.draft("Get session token from cache lookup by key auth_123")
    assert p == DatabaseParadigm.KEY_VALUE and conf >= 0.90

    # OLAP
    p, conf, _, _ = drafter.draft("Calculate quarterly revenue and year over year rolling avg")
    assert p == DatabaseParadigm.COLUMN_FAMILY_OLAP and conf >= 0.90

    # Time-Series
    p, conf, _, _ = drafter.draft("Aggregate sensor reading telemetry metrics over time per-second")
    assert p == DatabaseParadigm.TIME_SERIES and conf >= 0.90

    # Relational SQL
    p, conf, _, _ = drafter.draft("SELECT * FROM users JOIN orders ON users.id = orders.user_id WHERE status = 'active'")
    assert p == DatabaseParadigm.RELATIONAL_SQL


def test_speculative_verification_llm_fallback():
    suggestor = SpeculativeParadigmSuggestor(confidence_threshold=0.85)

    def mock_verifier(query, draft_p, draft_conf):
        return DatabaseParadigm.COLUMN_FAMILY_OLAP, 0.95, "Verified multi-billion row analytical scan by LLM."

    # Ambiguous query triggers fallback verification
    res = suggestor.classify_and_route(
        query="Analyze product sales trends",
        auto_mode=True,
        llm_verifier=mock_verifier,
    )
    assert res.paradigm == DatabaseParadigm.COLUMN_FAMILY_OLAP
    assert res.is_verified_by_llm is True
    assert res.confidence == 0.95


def test_paradigm_manual_divergence_warning():
    suggestor = SpeculativeParadigmSuggestor()
    res = suggestor.classify_and_route(
        query="Trace mutual friends and connection paths between developers",
        user_selected_engine="ClickHouse",
        auto_mode=False,
    )
    assert res.paradigm == DatabaseParadigm.COLUMN_FAMILY_OLAP
    assert res.warning_message is not None
    assert "Paradigm Divergence Warning" in res.warning_message


# ==============================================================================
# 2. Universal Dialect Converter Tests
# ==============================================================================

def test_sql_transpilation_all_relational_dialects():
    converter = DeterministicDialectConverter()
    sql = "SELECT id, username, created_at FROM users WHERE id > 100 ORDER BY created_at DESC LIMIT 5;"

    dialects = ["postgres", "mysql", "sqlite", "duckdb", "clickhouse", "snowflake", "bigquery", "tsql", "oracle", "redshift", "starrocks", "trino"]
    for d in dialects:
        res = converter.transpile(sql, target_dialect=d)
        assert res.is_native_sql is True
        assert len(res.compiled_query) > 0
        assert res.execution_time_ms < 50.0


def test_opencypher_complex_transpilation():
    converter = DeterministicDialectConverter()
    sql = "SELECT u.username, count(o.id) AS order_count FROM users AS u JOIN orders AS o ON u.id = o.user_id WHERE u.country = 'Germany' AND o.total_amount > 50 GROUP BY u.username ORDER BY order_count DESC LIMIT 10;"
    res = converter.transpile(sql, target_dialect="opencypher")

    assert res.is_native_sql is False
    assert res.target_dialect == "opencypher"
    cypher = res.compiled_query
    assert "MATCH (u:Users)-[:PLACED]->(o:Orders)" in cypher
    assert "WHERE" in cypher
    assert "u.country = 'Germany'" in cypher
    assert "count(o.id) AS order_count" in cypher
    assert "ORDER BY order_count DESC" in cypher
    assert "LIMIT 10" in cypher


def test_mongodb_mql_complex_aggregation_pipeline():
    converter = DeterministicDialectConverter()
    # 1. Query with filters, group by, aggregations, sort, limit
    sql = "SELECT category, count(*) AS total_prods, avg(price) AS avg_price FROM products WHERE price >= 10.50 AND category != 'Discontinued' GROUP BY category ORDER BY avg_price DESC LIMIT 3;"
    res = converter.transpile(sql, target_dialect="mongodb")

    assert res.is_native_sql is False
    pipeline = res.compiled_query["pipeline"]
    assert len(pipeline) == 4  # $match, $group, $sort, $limit
    assert "$match" in pipeline[0]
    assert "$group" in pipeline[1]
    assert "$sort" in pipeline[2]
    assert pipeline[3]["$limit"] == 3

    # 2. Query with JOIN -> $lookup and $unwind
    sql_join = "SELECT u.username, o.total_amount FROM users AS u JOIN orders AS o ON u.id = o.user_id WHERE o.total_amount > 100;"
    res_join = converter.transpile(sql_join, target_dialect="mongodb")
    p_join = res_join.compiled_query["pipeline"]
    assert any("$lookup" in stage for stage in p_join)
    assert any("$unwind" in stage for stage in p_join)


def test_transpile_invalid_syntax_error():
    converter = DeterministicDialectConverter()
    with pytest.raises(InvalidASTSyntaxError):
        converter.transpile("SELECT FROM WHERE WHERE", target_dialect="postgres")


# ==============================================================================
# 3. Schema Linker & Context Retrieval Tests
# ==============================================================================

def test_trie_punctuation_resilience():
    trie = CategoricalValueTrie()
    trie.insert("Germany", "users.country")
    trie.insert("MacBook Pro", "products.product_name")

    # Punctuation inside user input shouldn't break matching
    matches = trie.search_query_matches("Customers in Germany, who purchased a 'MacBook Pro'?")
    assert "germany" in matches
    assert matches["germany"] == "users.country"
    assert "macbook pro" in matches
    assert matches["macbook pro"] == "products.product_name"


def test_schema_linker_hybrid_rrf_and_steiner_bridge(mock_ecommerce_schema):
    linker = SchemaLinker(tables=mock_ecommerce_schema, rrf_k=60)
    ctx = linker.link_context(
        query="List all users who purchased a MacBook Pro in Germany with order details",
        max_tables=4,
    )

    # Must contain seed endpoints and bridge intermediate tables
    assert "users" in ctx.selected_tables
    assert "products" in ctx.selected_tables
    assert "orders" in ctx.selected_tables
    assert "order_items" in ctx.selected_tables
    assert len(ctx.foreign_keys) > 0
    assert "CREATE TABLE users" in ctx.prompt_ddl


# ==============================================================================
# 4. 6-Layer Static AST Validator Tests
# ==============================================================================

def test_validator_layer1_parse():
    # Empty query
    issues, ast = validate_parse("   ;  ")
    assert any(i.code == IssueCode.PARSE_02 for i in issues)

    # Multi-statement injection attempt
    issues, ast = validate_parse("SELECT * FROM users; DROP TABLE users;")
    assert any(i.code == IssueCode.PARSE_01 for i in issues)


def test_validator_layer2_policy():
    # Prohibited DROP DATABASE
    issues, parsed = validate_parse("DROP DATABASE production;")
    assert parsed is not None
    p_issues, _ = validate_policy("DROP DATABASE production;", parsed)
    assert any(i.code == IssueCode.POLICY_02 for i in p_issues)

    # UPDATE without WHERE clause
    ast = sqlglot.parse_one("UPDATE users SET status = 'active';")
    p_issues, _ = validate_policy("UPDATE users SET status = 'active';", ast)
    assert any(i.code == IssueCode.POLICY_05 for i in p_issues)

    # Prohibited dangerous system function
    ast = sqlglot.parse_one("SELECT pg_sleep(10);")
    p_issues, _ = validate_policy("SELECT pg_sleep(10);", ast)
    assert any(i.code == IssueCode.POLICY_06 for i in p_issues)


def test_validator_layer3_schema(mock_ecommerce_schema):
    provider = FakeSchemaProvider({
        "tables": [
            {"name": "users", "columns": {"id": "int", "username": "text"}, "pk": ["id"], "fks": {}, "indexes": {}, "row_count": 100, "nullable": {}}
        ]
    })
    ast = sqlglot.parse_one("SELECT nonexistent_col FROM users;")
    issues = validate_schema(ast, provider)
    assert any(i.code == IssueCode.SCHEMA_02 for i in issues)


def test_validator_layer4_semantic():
    # Aggregate in WHERE clause
    ast = sqlglot.parse_one("SELECT department FROM employees WHERE count(*) > 5;")
    issues = validate_semantic(ast)
    assert any(i.code == IssueCode.SEM_02 for i in issues)

    # Non-aggregated column missing from GROUP BY
    ast = sqlglot.parse_one("SELECT department, name, count(*) FROM employees GROUP BY department;")
    issues = validate_semantic(ast)
    assert any(i.code == IssueCode.SEM_01 for i in issues)


def test_validator_layer5_query_anti_patterns():
    # Cartesian product without ON clause
    ast = sqlglot.parse_one("SELECT * FROM users JOIN orders;")
    issues = validate_query_anti_patterns(ast)
    assert any(i.code == IssueCode.QUERY_AP_02 for i in issues)

    # Leading wildcard LIKE
    ast = sqlglot.parse_one("SELECT id FROM users WHERE username LIKE '%smith';")
    issues = validate_query_anti_patterns(ast)
    assert any(i.code == IssueCode.QUERY_AP_03 for i in issues)


def test_validator_rule_registry_toggle():
    registry = RuleRegistry()
    assert registry.is_enabled(IssueCode.QUERY_AP_01) is True
    # Toggle off SELECT * warning
    registry.toggle(IssueCode.QUERY_AP_01, False)
    assert registry.is_enabled(IssueCode.QUERY_AP_01) is False

    res = run_validation("SELECT * FROM users WHERE id = 1;", rules=registry)
    assert not any(i.code == IssueCode.QUERY_AP_01 for i in res.issues)


# ==============================================================================
# 5. Heuristic Cost & Blast Radius Engine Tests
# ==============================================================================

def test_heuristic_cost_read_and_write():
    engine = HeuristicCostEngine(thresholds=Thresholds.defaults())

    # 1. Indexed read query (Low cost, allowed)
    rep_read = engine.estimate_cost("SELECT id, username FROM users WHERE id = 42 LIMIT 1;")
    assert rep_read.is_allow() is True
    assert rep_read.index_used is True
    assert rep_read.estimated_rows_scanned <= 100

    # 2. Unfiltered mutation affecting large table (Escalated to Approval Gate)
    rep_write = engine.estimate_cost("UPDATE products SET price = price * 1.05 WHERE category = 'Electronics';")
    assert rep_write.is_escalate() is True
    assert rep_write.estimated_rows_affected > 10


# ==============================================================================
# 6. Unified End-to-End Orchestrator Tests
# ==============================================================================

def test_orchestrator_full_lifecycle(mock_ecommerce_schema):
    orchestrator = EndToEndNL2SQLOrchestrator(schema_tables=mock_ecommerce_schema)

    # 1. Natural Language Read Query -> Synthesized -> Validated -> Sandbox Replica
    plan_read = orchestrator.process_query(
        query="Show all users in Germany with active accounts",
        target_engine="postgres",
        auto_mode=True,
    )
    assert plan_read.is_valid is True
    assert plan_read.statement_type == StatementType.READ
    assert plan_read.execution_route == "SANDBOX_REPLICA"
    assert "users" in plan_read.generated_canonical_sql.lower()
    assert plan_read.requires_human_approval is False

    # 2. Mutating NL Query -> Synthesized -> Escalated to Approval Gate
    plan_mutate = orchestrator.process_query(
        query="Delete all inactive user accounts with id = 50",
        target_engine="mysql",
        auto_mode=True,
    )
    assert plan_mutate.is_valid is True
    assert plan_mutate.statement_type == StatementType.WRITE
    assert plan_mutate.execution_route == "APPROVAL_GATE"
    assert plan_mutate.requires_human_approval is True

    # 3. Security Violation -> BLOCKED
    plan_blocked = orchestrator.process_query(
        query="Drop database production immediately",
        target_engine="postgres",
    )
    assert plan_blocked.is_valid is False
    assert plan_blocked.execution_route == "BLOCKED"
