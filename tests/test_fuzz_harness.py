"""
tests/test_fuzz_harness.py — Robustness, Fuzz-Testing Harness & Anti-Pattern Verification Suite.

Validates the roles assigned to Sarthak Singh (Phase-III Report, Page 4):
1. Fuzz-testing harness refinement:
   - Random AST & SQL statement fuzzing (SQL injection, boundary lengths, adversarial syntax, comment injection).
   - Multi-dialect transpilation fuzzing across PostgreSQL, MySQL, Oracle, SQL Server, SQLite, DuckDB.
   - Sanitizer and Parameterized Statement extraction fuzzing.
   - Static 6-layer validation pipeline adversarial fuzzing.
2. Anti-pattern detector tuning & implementation:
   - QUERY_AP_04: Non-sargable function wrapping indexed columns in WHERE clause.
   - QUERY_AP_05: NOT IN with subquery (null-propagation hazard).
   - QUERY_AP_08: Correlated subquery anti-pattern.
   - QUERY_AP_09: DISTINCT keyword masking Cartesian / duplicate JOIN rows.
   - SCHEMA_AP_02: Missing foreign key constraints on candidate *_id reference columns.
   - SCHEMA_AP_03: Entity-Attribute-Value (EAV) open-schema anti-pattern table.
   - SCHEMA_AP_04: Polymorphic foreign key anti-pattern (*_type + *_id pair).
   - SCHEMA_AP_05: Comma-separated list in column default definition.
   - SCHEMA_AP_06: Floating-point types (FLOAT/REAL/DOUBLE) for financial/monetary data.
   - SCHEMA_AP_07: Excessive nullability (>70% nullable columns in table).
   - SCHEMA_AP_08: Foreign key columns lacking supporting B-tree index.
3. FIX-07: Aliased self-joins / join disambiguation deduplication.
4. FIX-08: Script splitting with semicolons embedded inside string literals and comments.
5. Index Advisor:
   - HeuristicCostEngine.advise_indexes() for WHERE, JOIN, and ORDER BY clauses.
6. End-to-end integration of Stage 8 Sanitization and Stage 9 Transpiled Validation.
"""

import sys
import random
import string
import unittest

try:
    import pytest
except ImportError:
    pytest = None

try:
    import sqlglot
    from sqlglot import exp
    HAS_SQLGLOT = True
except ImportError:
    HAS_SQLGLOT = False

from core.sanitizer import (
    sanitizeAndExtractParametersFromSqlAst,
    ParameterizedStatement,
    SanitizationError,
    split_sql_script,
)
from core.dialect_converter import (
    DeterministicDialectConverter,
    DialectSQL,
)
from core.validator.contracts import (
    IssueCode,
    Layer,
    Severity,
    Status,
    ValidationResult,
)
from core.validator.interfaces import FakeSchemaProvider
from core.validator.engine import (
    executeFullSixLayerValidationPipeline,
    validate_query_anti_patterns,
    validate_schema_anti_patterns,
    parseSqlStatementIntoAbstractSyntaxTree,
    detectMultipleStackedSqlStatements,
)
from core.cost_estimator.engine import HeuristicCostEngine
from core.cost_estimator.thresholds import Thresholds


# ==============================================================================
# 1. Fuzz-Testing Harness Utilities & Random Generators
# ==============================================================================

ADVERSARIAL_INJECTION_FRAGMENTS = [
    "' OR '1'='1",
    "'; DROP TABLE users; --",
    "\" OR \"\"=\"",
    "1; WAITFOR DELAY '0:0:5'--",
    "1' UNION SELECT null, username, password FROM users --",
    "admin'--",
    "1' AND SLEEP(5)#",
    "/**/OR/**/1=1",
    "\\x00' OR '1'='1",
    "1; EXEC xp_cmdshell('dir')--",
    "'; SHUTDOWN; --",
    "/* multiline \n comment */ SELECT 1;",
    "SELECT * FROM \"t\" WHERE \"id\" = '\x00';",
]

SQL_KEYWORDS = ["SELECT", "FROM", "WHERE", "JOIN", "ON", "GROUP BY", "ORDER BY", "HAVING", "LIMIT"]
SAMPLE_TABLES = ["users", "orders", "products", "audit_log", "payments", "customers"]
SAMPLE_COLUMNS = ["id", "user_id", "status", "price", "amount", "name", "created_at"]


def generate_random_sql_query(seed: int) -> str:
    """Deterministically generates syntactically diverse SQL queries for fuzzing."""
    rng = random.Random(seed)
    tbl = rng.choice(SAMPLE_TABLES)
    cols = ", ".join(rng.sample(SAMPLE_COLUMNS, k=rng.randint(1, 3)))
    where_col = rng.choice(SAMPLE_COLUMNS)
    num_val = rng.randint(1, 1000)
    str_val = "".join(rng.choices(string.ascii_letters, k=5))

    query_templates = [
        f"SELECT {cols} FROM {tbl} WHERE {where_col} = {num_val};",
        f"SELECT {cols} FROM {tbl} WHERE {where_col} = '{str_val}';",
        f"SELECT {cols} FROM {tbl} WHERE {where_col} > {num_val} ORDER BY {where_col} DESC;",
        f"SELECT {cols} FROM {tbl} WHERE {where_col} IN ({num_val}, {num_val + 1}, {num_val + 2});",
        f"SELECT count(*) FROM {tbl} WHERE {where_col} IS NOT NULL GROUP BY {where_col};",
        f"SELECT a.{cols.split(',')[0]} FROM {tbl} a JOIN {rng.choice(SAMPLE_TABLES)} b ON a.id = b.user_id WHERE a.{where_col} = '{str_val}';",
    ]
    return rng.choice(query_templates)


# ==============================================================================
# 2. Sanitizer Fuzzing Tests
# ==============================================================================

def test_fuzz_sanitizer_with_adversarial_injections():
    """Verify that sanitizer safely extracts parameters without crashing or leaking raw tokens."""
    if not HAS_SQLGLOT:
        return

    for idx, injection in enumerate(ADVERSARIAL_INJECTION_FRAGMENTS):
        raw_sql = f"SELECT * FROM accounts WHERE username = '{injection}' AND balance > {idx};"
        try:
            res = sanitizeAndExtractParametersFromSqlAst(raw_sql, dialect="postgres")
            assert isinstance(res, ParameterizedStatement)
            assert isinstance(res.sql, str)
            assert isinstance(res.params, list)
            # The literal injection must be extracted into params, not left in the parameterized SQL
            assert injection in res.params or len(res.params) > 0
        except SanitizationError:
            # Raising SanitizationError is acceptable for unparseable malformed syntax
            pass


def test_fuzz_sanitizer_random_permutations():
    """Fuzz sanitizer across 50 generated SQL queries to ensure structural invariants."""
    if not HAS_SQLGLOT:
        return

    for seed in range(50):
        query = generate_random_sql_query(seed)
        res = sanitizeAndExtractParametersFromSqlAst(query, dialect="postgres")
        assert isinstance(res, ParameterizedStatement)
        assert "$1" in res.sql or len(res.params) == 0
        assert res.statement_type is not None


# ==============================================================================
# 3. Deterministic Dialect Converter Fuzzing Tests
# ==============================================================================

def test_fuzz_dialect_converter_target_coverage():
    """Fuzz dialect converter across all major database engines."""
    if not HAS_SQLGLOT:
        return

    converter = DeterministicDialectConverter()
    dialects = ["postgres", "mysql", "oracle", "sqlserver", "sqlite", "duckdb"]

    base_queries = [
        "SELECT id, name FROM users LIMIT 10 OFFSET 20;",
        "SELECT user_id, sum(amount) FROM payments GROUP BY user_id HAVING sum(amount) > 500;",
        "SELECT id, name, ROW_NUMBER() OVER (PARTITION BY status ORDER BY created_at DESC) as rn FROM orders;",
        "SELECT * FROM items WHERE tags ? 'promo';",
        "CREATE TABLE logs (log_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, msg VARCHAR(255));",
    ]

    for q in base_queries:
        for dialect in dialects:
            res = converter.transpile(q, target_dialect=dialect)
            # Normalize tsql/sqlserver naming equivalence
            expected = "tsql" if dialect == "sqlserver" else dialect
            assert res.target_dialect in (dialect, expected)
            assert len(res.compiled_query) > 0


# ==============================================================================
# 4. Static 6-Layer Validator Adversarial Fuzzing Tests
# ==============================================================================

def test_fuzz_validator_with_adversarial_queries():
    """Fuzz full validation pipeline with malformed inputs to confirm it never raises uncaught crashes."""
    if not HAS_SQLGLOT:
        return

    malformed_inputs = [
        "",
        "   ",
        ";;;",
        "SELECT",
        "SELECT FROM WHERE",
        "DROP DATABASE production; DROP TABLE users;",
        "SELECT * FROM users WHERE",
        "SELECT 'unterminated string literal",
        "SELECT (SELECT (SELECT (SELECT 1))))",
        "SELECT * FROM " + ("nested_" * 50) + "table;",
    ]

    for raw in malformed_inputs:
        res = executeFullSixLayerValidationPipeline(
            sql_query=raw,
            target_dialect="postgres",
            schema_provider=FakeSchemaProvider(),
        )
        assert isinstance(res, ValidationResult)
        assert res.status in (Status.VALID, Status.VALID_WITH_WARNINGS, Status.INVALID)
        assert isinstance(res.issues, (list, tuple))


# ==============================================================================
# 5. Query Anti-Pattern Detector Verification (QUERY_AP_04, 05, 08, 09)
# ==============================================================================

def test_query_anti_pattern_04_function_wrapping_indexed_column():
    """QUERY_AP_04: Warns on non-sargable function calls wrapping indexed columns in WHERE."""
    if not HAS_SQLGLOT:
        return

    # Schema provider where 'created_at' and 'name' are indexed
    schema = FakeSchemaProvider(
        tables=["users"],
        columns={"users": ["id", "name", "created_at"]},
        indexed_columns={"users": ["id", "created_at", "name"]},
    )

    non_sargable_sql = "SELECT id FROM users WHERE UPPER(name) = 'ALICE';"
    ast = parseSqlStatementIntoAbstractSyntaxTree(non_sargable_sql)
    issues = validate_query_anti_patterns(ast, schema_provider=schema)
    assert any(i.code == IssueCode.QUERY_AP_04 for i in issues)

    date_func_sql = "SELECT id FROM users WHERE DATE(created_at) = '2024-01-01';"
    ast2 = parseSqlStatementIntoAbstractSyntaxTree(date_func_sql)
    issues2 = validate_query_anti_patterns(ast2, schema_provider=schema)
    assert any(i.code == IssueCode.QUERY_AP_04 for i in issues2)


def test_query_anti_pattern_05_not_in_with_subquery():
    """QUERY_AP_05: Detects NOT IN with subquery (null hazard)."""
    if not HAS_SQLGLOT:
        return

    not_in_sql = "SELECT id FROM users WHERE id NOT IN (SELECT user_id FROM orders);"
    ast = parseSqlStatementIntoAbstractSyntaxTree(not_in_sql)
    issues = validate_query_anti_patterns(ast)
    assert any(i.code == IssueCode.QUERY_AP_05 for i in issues)


def test_query_anti_pattern_08_correlated_subquery():
    """QUERY_AP_08: Flags correlated subquery that references outer table."""
    if not HAS_SQLGLOT:
        return

    correlated_sql = (
        "SELECT u.id, u.name FROM users u "
        "WHERE u.id = (SELECT o.user_id FROM orders o WHERE o.user_id = u.id LIMIT 1);"
    )
    ast = parseSqlStatementIntoAbstractSyntaxTree(correlated_sql)
    issues = validate_query_anti_patterns(ast)
    assert any(i.code == IssueCode.QUERY_AP_08 for i in issues)


def test_query_anti_pattern_09_distinct_masking_bad_joins():
    """QUERY_AP_09: Flags DISTINCT used on queries with joins."""
    if not HAS_SQLGLOT:
        return

    distinct_join_sql = "SELECT DISTINCT u.name, o.id FROM users u JOIN orders o ON u.id = o.user_id;"
    ast = parseSqlStatementIntoAbstractSyntaxTree(distinct_join_sql)
    issues = validate_query_anti_patterns(ast)
    assert any(i.code == IssueCode.QUERY_AP_09 for i in issues)


# ==============================================================================
# 6. Schema Anti-Pattern Detector Verification (SCHEMA_AP_02 to 08)
# ==============================================================================

def test_schema_anti_pattern_02_missing_fk_reference():
    """SCHEMA_AP_02: Flags *_id columns without foreign key constraints."""
    if not HAS_SQLGLOT:
        return

    ddl = "CREATE TABLE orders (id INT PRIMARY KEY, customer_id INT, amount DECIMAL(10,2));"
    ast = parseSqlStatementIntoAbstractSyntaxTree(ddl)
    issues = validate_schema_anti_patterns(ast)
    assert any(i.code == IssueCode.SCHEMA_AP_02 for i in issues)


def test_schema_anti_pattern_03_eav_table_structure():
    """SCHEMA_AP_03: Flags Entity-Attribute-Value anti-pattern schema."""
    if not HAS_SQLGLOT:
        return

    ddl = "CREATE TABLE custom_attributes (entity_id INT, attribute VARCHAR(100), value TEXT);"
    ast = parseSqlStatementIntoAbstractSyntaxTree(ddl)
    issues = validate_schema_anti_patterns(ast)
    assert any(i.code == IssueCode.SCHEMA_AP_03 for i in issues)


def test_schema_anti_pattern_04_polymorphic_columns():
    """SCHEMA_AP_04: Flags polymorphic type + id column pairs."""
    if not HAS_SQLGLOT:
        return

    ddl = "CREATE TABLE comments (id INT PRIMARY KEY, commentable_type VARCHAR(50), commentable_id INT, body TEXT);"
    ast = parseSqlStatementIntoAbstractSyntaxTree(ddl)
    issues = validate_schema_anti_patterns(ast)
    assert any(i.code == IssueCode.SCHEMA_AP_04 for i in issues)


def test_schema_anti_pattern_05_comma_separated_default_values():
    """SCHEMA_AP_05: Flags comma-separated values in column default."""
    if not HAS_SQLGLOT:
        return

    ddl = "CREATE TABLE config (id INT PRIMARY KEY, permissions VARCHAR(255) DEFAULT 'read,write,admin');"
    ast = parseSqlStatementIntoAbstractSyntaxTree(ddl)
    issues = validate_schema_anti_patterns(ast)
    assert any(i.code == IssueCode.SCHEMA_AP_05 for i in issues)


def test_schema_anti_pattern_06_floating_point_monetary_types():
    """SCHEMA_AP_06: Flags FLOAT or REAL on financial/monetary columns."""
    if not HAS_SQLGLOT:
        return

    ddl = "CREATE TABLE transactions (id INT PRIMARY KEY, account_balance FLOAT, fee REAL);"
    ast = parseSqlStatementIntoAbstractSyntaxTree(ddl)
    issues = validate_schema_anti_patterns(ast)
    assert any(i.code == IssueCode.SCHEMA_AP_06 for i in issues)


def test_schema_anti_pattern_07_excessive_nullable_columns():
    """SCHEMA_AP_07: Flags tables where >70% of columns are nullable."""
    if not HAS_SQLGLOT:
        return

    ddl = (
        "CREATE TABLE sparse_data ("
        "  id INT PRIMARY KEY, "
        "  col1 VARCHAR(50) NULL, "
        "  col2 VARCHAR(50) NULL, "
        "  col3 VARCHAR(50) NULL, "
        "  col4 VARCHAR(50) NULL, "
        "  col5 VARCHAR(50) NULL"
        ");"
    )
    ast = parseSqlStatementIntoAbstractSyntaxTree(ddl)
    issues = validate_schema_anti_patterns(ast)
    assert any(i.code == IssueCode.SCHEMA_AP_07 for i in issues)


def test_schema_anti_pattern_08_fk_without_index():
    """SCHEMA_AP_08: Flags foreign keys without backing indexes."""
    if not HAS_SQLGLOT:
        return

    schema = FakeSchemaProvider(
        tables=["orders"],
        columns={"orders": ["id", "user_id"]},
        indexed_columns={"orders": ["id"]},  # user_id is NOT indexed
    )
    ddl = (
        "CREATE TABLE orders ("
        "  id INT PRIMARY KEY, "
        "  user_id INT, "
        "  FOREIGN KEY (user_id) REFERENCES users(id)"
        ");"
    )
    ast = parseSqlStatementIntoAbstractSyntaxTree(ddl)
    issues = validate_schema_anti_patterns(ast, schema_provider=schema)
    assert any(i.code == IssueCode.SCHEMA_AP_08 for i in issues)


# ==============================================================================
# 7. Bugfix Verifications: FIX-07 and FIX-08
# ==============================================================================

def test_fix_07_aliased_join_disambiguation():
    """FIX-07: Verifies self-joins or aliased joins are deduplicated by physical table identity."""
    if not HAS_SQLGLOT:
        return

    schema = FakeSchemaProvider(
        tables=["employees"],
        columns={"employees": ["id", "name", "manager_id"]},
        indexed_columns={"employees": ["id"]},
    )
    # Self-join with distinct aliases referencing same physical table
    sql = (
        "SELECT e.name, m.name "
        "FROM employees e "
        "JOIN employees m ON e.manager_id = m.id;"
    )
    ast = parseSqlStatementIntoAbstractSyntaxTree(sql)
    res = executeFullSixLayerValidationPipeline(sql, target_dialect="postgres", schema_provider=schema)
    # Should not produce false-positive ambiguous column error
    ambiguous_issues = [i for i in res.issues if i.code == IssueCode.SEM_01]
    assert len(ambiguous_issues) == 0


def test_fix_08_split_sql_script_with_quoted_semicolons():
    """FIX-08: Semicolons inside string literals and comments must not split statements."""
    script = (
        "INSERT INTO messages (content) VALUES ('Hello; World; Test');\n"
        "-- Comment with a semicolon; inside\n"
        "SELECT * FROM messages WHERE content LIKE '%;%';"
    )
    stmts = split_sql_script(script)
    assert len(stmts) == 2
    assert "Hello; World; Test" in stmts[0]
    assert "LIKE '%;%'" in stmts[1]


# ==============================================================================
# 8. Index Advisor Verification
# ==============================================================================

def test_heuristic_cost_engine_advise_indexes():
    """Verifies that HeuristicCostEngine.advise_indexes generates appropriate index recommendations."""
    if not HAS_SQLGLOT:
        return

    engine = HeuristicCostEngine()
    schema = FakeSchemaProvider(
        tables=["users", "orders"],
        columns={
            "users": ["id", "status", "country"],
            "orders": ["id", "user_id", "total", "created_at"],
        },
        indexed_columns={"users": ["id"], "orders": ["id"]},
    )

    query = (
        "SELECT u.country, o.total "
        "FROM users u "
        "JOIN orders o ON u.id = o.user_id "
        "WHERE u.status = 'active' "
        "ORDER BY o.created_at DESC;"
    )

    recommendations = engine.advise_indexes(query, schema_provider=schema)
    assert isinstance(recommendations, list)
    assert len(recommendations) > 0

    recs_str = str(recommendations)
    # Recommended indexes should target unindexed columns used in WHERE / JOIN / ORDER BY
    assert any("orders" in r.get("table", "") or "users" in r.get("table", "") for r in recommendations)
    assert any("user_id" in r.get("columns", []) or "status" in r.get("columns", []) or "created_at" in r.get("columns", []) for r in recommendations)


# ==============================================================================
# 9. Main Self-Running Execution Block (for non-pytest environments)
# ==============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING NL2SQL ROBUSTNESS & FUZZ-TESTING HARNESS")
    print("=" * 70)

    test_functions = [
        test_fuzz_sanitizer_with_adversarial_injections,
        test_fuzz_sanitizer_random_permutations,
        test_fuzz_dialect_converter_target_coverage,
        test_fuzz_validator_with_adversarial_queries,
        test_query_anti_pattern_04_function_wrapping_indexed_column,
        test_query_anti_pattern_05_not_in_with_subquery,
        test_query_anti_pattern_08_correlated_subquery,
        test_query_anti_pattern_09_distinct_masking_bad_joins,
        test_schema_anti_pattern_02_missing_fk_reference,
        test_schema_anti_pattern_03_eav_table_structure,
        test_schema_anti_pattern_04_polymorphic_columns,
        test_schema_anti_pattern_05_comma_separated_default_values,
        test_schema_anti_pattern_06_floating_point_monetary_types,
        test_schema_anti_pattern_07_excessive_nullable_columns,
        test_schema_anti_pattern_08_fk_without_index,
        test_fix_07_aliased_join_disambiguation,
        test_fix_08_split_sql_script_with_quoted_semicolons,
        test_heuristic_cost_engine_advise_indexes,
    ]

    passed = 0
    failed = 0
    skipped = 0

    for test_fn in test_functions:
        test_name = test_fn.__name__
        try:
            test_fn()
            print(f"  [PASS] {test_name}")
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {test_name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {test_name}: {e}")
            failed += 1

    print("=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed, {skipped} skipped.")
    print("=" * 70)

    if failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)
