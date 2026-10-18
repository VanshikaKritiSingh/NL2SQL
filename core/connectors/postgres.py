"""
core/connectors/postgres.py — PostgreSQL Relational DBMS Connector
"""

import time
from typing import Any, Dict, List, Optional

from core.connectors.base import (
    BaseDBConnector,
    ColumnSchema,
    ConnectionConfig,
    QueryResult,
    SchemaMetadata,
    TableSchema,
)

# Optional imports for psycopg2 / psycopg / asyncpg
psycopg_driver = None
try:
    import psycopg2
    import psycopg2.extras
    psycopg_driver = "psycopg2"
except ImportError:
    try:
        import psycopg
        psycopg_driver = "psycopg3"
    except ImportError:
        psycopg_driver = None


class PostgresConnector(BaseDBConnector):
    """
    PostgreSQL enterprise connector.
    Introspects information_schema & pg_catalog, runs EXPLAIN (FORMAT JSON),
    supports read-only replicas and transactional DML.
    """

    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self._conn = None

    def connect(self) -> bool:
        if not psycopg_driver:
            raise ImportError("PostgreSQL driver (psycopg2 or psycopg) is not installed.")
        try:
            port = self.config.port or 5432
            if psycopg_driver == "psycopg2":
                self._conn = psycopg2.connect(
                    host=self.config.host,
                    port=port,
                    dbname=self.config.database,
                    user=self.config.username,
                    password=self.config.password,
                    connect_timeout=int(self.config.timeout_s),
                    sslmode=self.config.ssl_mode or "prefer",
                )
                self._conn.autocommit = not self.config.read_only
            else:
                self._conn = psycopg.connect(
                    f"postgresql://{self.config.username}:{self.config.password}@{self.config.host}:{port}/{self.config.database}"
                )
            self._is_connected = True
            return True
        except Exception as e:
            self._is_connected = False
            self._conn = None
            raise ConnectionError(f"PostgreSQL connection failed [{self.config.host}:{self.config.port}/{self.config.database}]: {e}")

    def disconnect(self) -> bool:
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            finally:
                self._conn = None
                self._is_connected = False
        return True

    def test_connection(self) -> Dict[str, Any]:
        start = time.perf_counter()
        if not psycopg_driver:
            return {
                "ok": False,
                "latency_ms": 0.0,
                "dialect": "postgres",
                "error": "psycopg2/psycopg not installed in environment",
            }
        try:
            if not self.is_connected or not self._conn:
                self.connect()
            cursor = self._conn.cursor()
            cursor.execute("SELECT version();")
            ver = cursor.fetchone()[0]
            cursor.close()
            latency = (time.perf_counter() - start) * 1000
            return {
                "ok": True,
                "latency_ms": round(latency, 2),
                "dialect": "postgres",
                "version": ver.split(",")[0],
                "database": self.config.database,
            }
        except Exception as e:
            return {
                "ok": False,
                "latency_ms": (time.perf_counter() - start) * 1000,
                "dialect": "postgres",
                "error": str(e),
                "database": self.config.database,
            }

    def list_databases(self) -> List[str]:
        if not self.is_connected or not self._conn:
            self.connect()
        cursor = self._conn.cursor()
        try:
            cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false AND has_database_privilege(current_user, datname, 'CONNECT') ORDER BY datname;")
            return [r[0] for r in cursor.fetchall()]
        finally:
            cursor.close()

    def introspect_schema(self, force_refresh: bool = False) -> SchemaMetadata:
        if self._cached_schema and not force_refresh:
            return self._cached_schema

        if not self.is_connected or not self._conn:
            self.connect()

        tables_map: Dict[str, TableSchema] = {}
        relationships: List[Dict[str, str]] = []

        cursor = self._conn.cursor()

        # 1. Fetch tables
        cursor.execute("""
            SELECT table_name, table_type 
            FROM information_schema.tables 
            WHERE table_schema = 'public';
        """)
        for r in cursor.fetchall():
            tbl_name, tbl_type = r[0], r[1]
            tables_map[tbl_name] = TableSchema(name=tbl_name, table_type=tbl_type)

        # 2. Fetch columns
        cursor.execute("""
            SELECT table_name, column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public';
        """)
        for r in cursor.fetchall():
            t_name, c_name, d_type, is_null, dflt = r
            if t_name in tables_map:
                tables_map[t_name].columns[c_name] = ColumnSchema(
                    name=c_name,
                    data_type=d_type.upper(),
                    nullable=(is_null == "YES"),
                    default_value=str(dflt) if dflt is not None else None,
                )

        # 3. Fetch Primary Keys
        cursor.execute("""
            SELECT kcu.table_name, kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_schema = 'public';
        """)
        for r in cursor.fetchall():
            t_name, c_name = r
            if t_name in tables_map:
                tables_map[t_name].primary_keys.append(c_name)
                if c_name in tables_map[t_name].columns:
                    tables_map[t_name].columns[c_name].is_primary_key = True

        # 4. Fetch Foreign Keys
        cursor.execute("""
            SELECT
                tc.table_name AS from_table,
                kcu.column_name AS from_column,
                ccu.table_name AS to_table,
                ccu.column_name AS to_column
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
              AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public';
        """)
        for r in cursor.fetchall():
            from_t, from_c, to_t, to_c = r
            if from_t in tables_map and from_c in tables_map[from_t].columns:
                tables_map[from_t].columns[from_c].is_foreign_key = True
                tables_map[from_t].columns[from_c].foreign_key_target = f"{to_t}.{to_c}"
                fk_info = {"from_table": from_t, "from_column": from_c, "to_table": to_t, "to_column": to_c}
                tables_map[from_t].foreign_keys.append(fk_info)
                relationships.append(fk_info)

        cursor.close()

        schema_meta = SchemaMetadata(
            database_name=self.config.database,
            dialect="postgres",
            tables=tables_map,
            relationships=relationships,
        )
        self._cached_schema = schema_meta
        return schema_meta

    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        is_mutating: bool = False,
        timeout_s: Optional[float] = None,
    ) -> QueryResult:
        if not self.is_connected or not self._conn:
            self.connect()

        start = time.perf_counter()
        clean_q = query.strip().rstrip(";")
        cursor = self._conn.cursor()

        try:
            if params:
                cursor.execute(clean_q, params)
            else:
                cursor.execute(clean_q)

            exec_ms = (time.perf_counter() - start) * 1000

            if cursor.description:
                cols = [d[0] for d in cursor.description]
                raw_rows = cursor.fetchall()
                rows = [dict(zip(cols, row)) for row in raw_rows]
                cursor.close()
                return QueryResult(
                    columns=cols,
                    rows=rows,
                    row_count=len(rows),
                    rows_affected=0,
                    execution_time_ms=round(exec_ms, 2),
                    is_mutating=False,
                )
            else:
                affected = cursor.rowcount
                cursor.close()
                return QueryResult(
                    columns=[],
                    rows=[],
                    row_count=0,
                    rows_affected=affected if affected >= 0 else 0,
                    execution_time_ms=round(exec_ms, 2),
                    is_mutating=True,
                )
        except Exception as e:
            exec_ms = (time.perf_counter() - start) * 1000
            try:
                self._conn.rollback()
                cursor.close()
            except Exception:
                pass
            return QueryResult(
                columns=[],
                rows=[],
                row_count=0,
                rows_affected=0,
                execution_time_ms=round(exec_ms, 2),
                is_mutating=is_mutating,
                error=str(e),
            )

    def explain_query(self, query: str) -> Dict[str, Any]:
        if not self.is_connected or not self._conn:
            self.connect()

        cursor = self._conn.cursor()
        clean_q = query.strip().rstrip(";")
        try:
            cursor.execute(f"EXPLAIN (FORMAT JSON, COSTS ON) {clean_q};")
            plan_json = cursor.fetchone()[0]
            cursor.close()
            return {"ok": True, "dialect": "postgres", "plan": plan_json}
        except Exception as e:
            try:
                cursor.close()
            except Exception:
                pass
            return {"ok": False, "dialect": "postgres", "error": str(e)}

    # Aliases for Java-style camelCase naming convention
    establishDatabaseConnection = connect
    terminateDatabaseConnection = disconnect
    verifyDatabaseConnectionStatus = test_connection
    listAccessibleDatabaseNames = list_databases
    introspectDatabaseCatalogSchema = introspect_schema
    executeQueryAgainstDatabaseEngine = execute_query
    generateQueryExecutionPlan = explain_query
