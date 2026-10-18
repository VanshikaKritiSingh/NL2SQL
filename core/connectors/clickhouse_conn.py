"""
core/connectors/clickhouse_conn.py — ClickHouse Analytical DBMS Connector (HTTP & Native)
"""

import json
import time
from typing import Any, Dict, List, Optional
import urllib.parse
import urllib.request

from core.connectors.base import (
    BaseDBConnector,
    ColumnSchema,
    ConnectionConfig,
    QueryResult,
    SchemaMetadata,
    TableSchema,
)


class ClickHouseConnector(BaseDBConnector):
    """
    ClickHouse Columnar Analytics Connector via fast HTTP API.
    Zero-heavy-dependency: Uses standard HTTP JSON interfaces.
    """

    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self._base_url = ""

    def connect(self) -> bool:
        port = self.config.port or 8123
        host = self.config.host or "localhost"
        self._base_url = f"http://{host}:{port}/"
        self._is_connected = True
        return True

    def disconnect(self) -> bool:
        self._is_connected = False
        return True

    def _execute_http(self, query: str) -> Dict[str, Any]:
        if not self._base_url:
            self.connect()

        params = {
            "database": self.config.database or "default",
            "default_format": "JSON",
        }
        if self.config.username:
            params["user"] = self.config.username
        if self.config.password:
            params["password"] = self.config.password

        url = f"{self._base_url}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(
            url,
            data=query.encode("utf-8"),
            headers={"Content-Type": "text/plain; charset=utf-8"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.config.timeout_s) as resp:
            data = resp.read().decode("utf-8")
            if data.strip():
                return json.loads(data)
            return {}

    def test_connection(self) -> Dict[str, Any]:
        start = time.perf_counter()
        try:
            res = self._execute_http("SELECT version()")
            ver = res.get("data", [{}])[0].get("version()", "Unknown")
            db_name = self.config.database
            if db_name and db_name not in ("default", "system"):
                db_chk = self._execute_http(f"SELECT count() as cnt FROM system.databases WHERE name = '{db_name}';")
                cnt = db_chk.get("data", [{}])[0].get("cnt", 0)
                if int(cnt) == 0:
                    raise ValueError(f"Database '{db_name}' does not exist on ClickHouse server")
            latency = (time.perf_counter() - start) * 1000
            return {
                "ok": True,
                "latency_ms": round(latency, 2),
                "dialect": "clickhouse",
                "version": f"ClickHouse {ver}",
                "database": self.config.database,
            }
        except Exception as e:
            return {
                "ok": False,
                "latency_ms": (time.perf_counter() - start) * 1000,
                "dialect": "clickhouse",
                "error": str(e),
                "database": self.config.database,
            }

    def list_databases(self) -> List[str]:
        res = self._execute_http("SHOW DATABASES;")
        return [r.get("name") for r in res.get("data", []) if r.get("name")]

    def introspect_schema(self, force_refresh: bool = False) -> SchemaMetadata:
        if self._cached_schema and not force_refresh:
            return self._cached_schema

        tables_map: Dict[str, TableSchema] = {}
        relationships: List[Dict[str, str]] = []
        db_name = self.config.database or "default"

        try:
            tbl_res = self._execute_http(f"SELECT name, engine, total_rows FROM system.tables WHERE database = '{db_name}';")
            for r in tbl_res.get("data", []):
                t_name = r.get("name")
                t_engine = r.get("engine", "MergeTree")
                t_rows = r.get("total_rows")
                tables_map[t_name] = TableSchema(
                    name=t_name,
                    table_type=f"ENGINE_{t_engine}",
                    row_count_estimate=int(t_rows) if t_rows is not None else None,
                )

            col_res = self._execute_http(f"SELECT table, name, type, is_in_primary_key FROM system.columns WHERE database = '{db_name}';")
            for c in col_res.get("data", []):
                t_name = c.get("table")
                c_name = c.get("name")
                c_type = c.get("type", "String")
                is_pk = bool(c.get("is_in_primary_key", 0))

                if t_name in tables_map:
                    if is_pk:
                        tables_map[t_name].primary_keys.append(c_name)
                    tables_map[t_name].columns[c_name] = ColumnSchema(
                        name=c_name,
                        data_type=c_type.upper(),
                        is_primary_key=is_pk,
                    )
        except Exception:
            pass

        schema_meta = SchemaMetadata(
            database_name=db_name,
            dialect="clickhouse",
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
        start = time.perf_counter()
        clean_q = query.strip().rstrip(";")
        try:
            res = self._execute_http(clean_q)
            exec_ms = (time.perf_counter() - start) * 1000

            data = res.get("data", [])
            meta = res.get("meta", [])
            cols = [m.get("name") for m in meta] if meta else (list(data[0].keys()) if data else [])

            return QueryResult(
                columns=cols,
                rows=data,
                row_count=len(data),
                rows_affected=res.get("rows_written", 0),
                execution_time_ms=round(exec_ms, 2),
                is_mutating=is_mutating,
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
        clean_q = query.strip().rstrip(";")
        try:
            res = self._execute_http(f"EXPLAIN {clean_q}")
            return {"ok": True, "dialect": "clickhouse", "plan": res.get("data", [])}
        except Exception as e:
            return {"ok": False, "dialect": "clickhouse", "error": str(e)}

    # Aliases for Java-style camelCase naming convention
    establishDatabaseConnection = connect
    terminateDatabaseConnection = disconnect
    verifyDatabaseConnectionStatus = test_connection
    listAccessibleDatabaseNames = list_databases
    introspectDatabaseCatalogSchema = introspect_schema
    executeQueryAgainstDatabaseEngine = execute_query
    generateQueryExecutionPlan = explain_query
