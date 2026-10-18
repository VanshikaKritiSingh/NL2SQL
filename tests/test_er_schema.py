"""test_er_schema.py — Unit test for live schema introspection & ER diagram contract."""

import os
import sys

# Ensure repository root and GUI/server are on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SERVER_ROOT = os.path.abspath(os.path.join(REPO_ROOT, "GUI", "server"))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if SERVER_ROOT not in sys.path:
    sys.path.insert(0, SERVER_ROOT)

from core.connectors import default_registry, ConnectionConfig, ConnectorType
from routers.schema import _build_schema_from_connection


def testEntityRelationshipSchemaIntrospectionLifecycle():
    user_id = "test_er_user"
    # Use in-memory SQLite to test lifecycle: create table -> add 2nd table with FK -> insert data
    config = ConnectionConfig(
        connector_type=ConnectorType.SQLITE,
        database=":memory:",
        timeout_s=5.0,
    )
    conn = default_registry.attach(user_id, config)
    assert conn.is_connected, "SQLite in-memory should connect immediately"

    # Step 1: Empty database
    schema0 = _build_schema_from_connection(conn, "sqlite")
    assert schema0 is None or len(schema0.tables) == 0, f"Expected 0 tables, got {schema0}"

    # Step 2: CREATE TABLE users (1 table)
    conn.execute_query(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(50) NOT NULL,
            email VARCHAR(100) UNIQUE
        );
    """,
        is_mutating=True,
    )

    schema1 = _build_schema_from_connection(conn, "sqlite")
    assert schema1 is not None, "Schema should not be None"
    assert len(schema1.tables) == 1, f"Expected 1 table, got {len(schema1.tables)}"
    assert schema1.tables[0].name == "users"
    assert len(schema1.tables[0].columns) == 3
    # Check PK
    pk_cols = [c.name for c in schema1.tables[0].columns if c.is_primary_key]
    assert "id" in pk_cols, f"id should be PK, got {pk_cols}"

    # Step 3: CREATE TABLE orders with FOREIGN KEY (2 tables, 1 FK relation)
    conn.execute_query(
        """
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """,
        is_mutating=True,
    )

    schema2 = _build_schema_from_connection(conn, "sqlite")
    assert schema2 is not None
    assert len(schema2.tables) == 2, f"Expected 2 tables, got {len(schema2.tables)}"
    tbl_names = {t.name for t in schema2.tables}
    assert tbl_names == {"users", "orders"}, f"Expected users and orders, got {tbl_names}"
    # Check FK relationship
    assert len(schema2.foreign_keys) == 1, f"Expected 1 FK, got {len(schema2.foreign_keys)}"
    fk = schema2.foreign_keys[0]
    assert fk.from_table == "orders" and fk.from_column == "user_id"
    assert fk.to_table == "users" and fk.to_column == "id"

    # Step 4: INSERT DATA into users and orders
    conn.execute_query(
        "INSERT INTO users (name, email) VALUES ('Alice', 'alice@test.com');",
        is_mutating=True,
    )
    conn.execute_query(
        "INSERT INTO users (name, email) VALUES ('Bob', 'bob@test.com');",
        is_mutating=True,
    )
    conn.execute_query(
        "INSERT INTO orders (user_id, total_amount) VALUES (1, 99.99);",
        is_mutating=True,
    )

    schema3 = _build_schema_from_connection(conn, "sqlite")
    assert schema3 is not None
    users_tbl = next(t for t in schema3.tables if t.name == "users")
    orders_tbl = next(t for t in schema3.tables if t.name == "orders")
    assert users_tbl.row_count == 2, f"Expected 2 users, got {users_tbl.row_count}"
    assert orders_tbl.row_count == 1, f"Expected 1 order, got {orders_tbl.row_count}"

    # Check sample values in users table
    name_col = next(c for c in users_tbl.columns if c.name == "name")
    assert (
        "Alice" in name_col.sample_values or "Bob" in name_col.sample_values
    ), f"Expected sample values, got {name_col.sample_values}"

    default_registry.detach(user_id)


if __name__ == "__main__":
    testEntityRelationshipSchemaIntrospectionLifecycle()
    print("✓ All ER schema lifecycle tests passed.")
