"""
core/connectors/duckdb_conn.py — High-Performance DuckDB OLAP Analytical Connector
"""

import os
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

try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    duckdb = None
    HAS_DUCKDB = False


class DuckDBConnector(BaseDBConnector):
    """
    DuckDB OLAP Analytical Connector.
    Supports in-memory (`:memory:`) or persistent `.duckdb` analytical catalogs.
    """

    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self._conn = None

    def connect(self) -> bool:
        if not HAS_DUCKDB:
            raise ImportError("DuckDB driver is not installed. Run `pip install duckdb`.")
        try:
            db_path = self.config.database
            if db_path != ":memory:":
                if not os.path.isabs(db_path):
                    db_path = os.path.abspath(db_path)
                create_if_missing = self.config.extra_params.get("create_if_missing", False)
                if not os.path.exists(db_path) and not create_if_missing:
                    raise FileNotFoundError(f"DuckDB database file not found: {db_path}")

            read_only = self.config.read_only
            self._conn = duckdb.connect(database=db_path, read_only=read_only)
            self._is_connected = True
            return True
        except Exception as e:
            self._is_connected = False
            self._conn = None
            raise ConnectionError(f"Failed to connect to DuckDB [{self.config.database}]: {e}")

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
        if not HAS_DUCKDB:
            return {
                "ok": False,
                "latency_ms": 0.0,
                "dialect": "duckdb",
                "error": "duckdb package not installed in environment",
            }
        try:
            if not self.is_connected or not self._conn:
                self.connect()
            res = self._conn.execute("SELECT version();").fetchone()
            latency = (time.perf_counter() - start) * 1000
            return {
                "ok": True,
                "latency_ms": round(latency, 2),
                "dialect": "duckdb",
                "version": f"DuckDB {res[0]}",
                "database": self.config.database,
            }
        except Exception as e:
            return {
                "ok": False,
                "latency_ms": (time.perf_counter() - start) * 1000,
                "dialect": "duckdb",
                "error": str(e),
                "database": self.config.database,
            }

    def introspect_schema(self, force_refresh: bool = False) -> SchemaMetadata:
        if self._cached_schema and not force_refresh:
            return self._cached_schema

        if not self.is_connected or not self._conn:
            self.connect()

        tables_map: Dict[str, TableSchema] = {}
        relationships: List[Dict[str, str]] = []

        tables_df = self._conn.execute(
            "SELECT table_name, table_type FROM information_schema.tables WHERE table_schema = 'main';"
        ).fetchall()

        for t_row in tables_df:
            tbl_name = t_row[0]
            tbl_type = t_row[1]
            tbl_schema = TableSchema(name=tbl_name, table_type=tbl_type)

            col_rows = self._conn.execute(
                f"SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = '{tbl_name}';"
            ).fetchall()

            for col in col_rows:
                c_name = col[0]
                c_type = col[1]
                c_null = (col[2] == "YES")

                tbl_schema.columns[c_name] = ColumnSchema(
                    name=c_name,
                    data_type=c_type.upper(),
                    nullable=c_null,
                )

            # Row count
            try:
                cnt = self._conn.execute(f"SELECT COUNT(*) FROM \"{tbl_name}\";").fetchone()[0]
                tbl_schema.row_count_estimate = cnt
            except Exception:
                pass

            tables_map[tbl_name] = tbl_schema

        schema_meta = SchemaMetadata(
            database_name=self.config.database,
            dialect="duckdb",
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
        try:
            rel = self._conn.execute(clean_q)
            exec_ms = (time.perf_counter() - start) * 1000

            if rel.description:
                cols = [d[0] for d in rel.description]
                raw_rows = rel.fetchall()
                rows = [dict(zip(cols, row)) for row in raw_rows]
                return QueryResult(
                    columns=cols,
                    rows=rows,
                    row_count=len(rows),
                    rows_affected=0,
                    execution_time_ms=round(exec_ms, 2),
                    is_mutating=False,
                )
            else:
                return QueryResult(
                    columns=[],
                    rows=[],
                    row_count=0,
                    rows_affected=1,
                    execution_time_ms=round(exec_ms, 2),
                    is_mutating=True,
                )
        except Exception as e:
            exec_ms = (time.perf_counter() - start) * 1000
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

        clean_q = query.strip().rstrip(";")
        try:
            res = self._conn.execute(f"EXPLAIN {clean_q};").fetchall()
            return {
                "ok": True,
                "dialect": "duckdb",
                "explain_plan": [{"type": r[0], "plan": r[1]} for r in res] if res else [],
            }
        except Exception as e:
            return {"ok": False, "dialect": "duckdb", "error": str(e)}
