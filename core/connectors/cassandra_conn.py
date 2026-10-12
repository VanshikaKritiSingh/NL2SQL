"""
core/connectors/cassandra_conn.py — Apache Cassandra CQL Connector

Executes CQL queries via the official DataStax cassandra-driver.
Introspects keyspaces, column families, partition keys, and clustering columns.
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

try:
    from cassandra.cluster import Cluster
    from cassandra.auth import PlainTextAuthProvider
    HAS_CASSANDRA = True
except ImportError:
    Cluster = None
    HAS_CASSANDRA = False

_MISSING = "cassandra-driver not installed. Run: pip install cassandra-driver"


class CassandraConnector(BaseDBConnector):
    """
    Apache Cassandra / ScyllaDB CQL Connector.
    """

    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self._cluster = None
        self._session = None

    def connect(self) -> bool:
        if not HAS_CASSANDRA:
            raise ImportError(_MISSING)
        try:
            port = self.config.port or 9042
            auth = None
            if self.config.username and self.config.password:
                auth = PlainTextAuthProvider(username=self.config.username, password=self.config.password)

            self._cluster = Cluster(
                contact_points=[self.config.host or "127.0.0.1"],
                port=port,
                auth_provider=auth,
                connect_timeout=self.config.timeout_s,
            )
            self._session = self._cluster.connect(self.config.database or None)
            self._is_connected = True
            return True
        except Exception as e:
            self._is_connected = False
            raise ConnectionError(f"Cassandra connection failed [{self.config.host}]: {e}")

    def disconnect(self) -> bool:
        if self._cluster:
            try:
                self._cluster.shutdown()
            except Exception:
                pass
            finally:
                self._cluster = None
                self._session = None
                self._is_connected = False
        return True

    def test_connection(self) -> Dict[str, Any]:
        start = time.perf_counter()
        if not HAS_CASSANDRA:
            return {"ok": False, "latency_ms": 0.0, "dialect": "cassandra", "error": _MISSING}
        try:
            if not self.is_connected:
                self.connect()
            row = self._session.execute("SELECT release_version FROM system.local;").one()
            ver = row.release_version if row else "unknown"
            latency = (time.perf_counter() - start) * 1000
            return {
                "ok": True,
                "latency_ms": round(latency, 2),
                "dialect": "cassandra",
                "version": f"Cassandra {ver}",
                "database": self.config.database,
            }
        except Exception as e:
            return {"ok": False, "latency_ms": (time.perf_counter() - start) * 1000, "dialect": "cassandra", "error": str(e)}

    def introspect_schema(self, force_refresh: bool = False) -> SchemaMetadata:
        if self._cached_schema and not force_refresh:
            return self._cached_schema
        if not self.is_connected:
            self.connect()

        tables_map: Dict[str, TableSchema] = {}
        ks = self.config.database

        try:
            meta = self._cluster.metadata.keyspaces.get(ks)
            if meta:
                for t_name, t_meta in meta.tables.items():
                    tbl = TableSchema(name=t_name, table_type="COLUMN_FAMILY")
                    for pk_col in t_meta.primary_key:
                        tbl.primary_keys.append(pk_col.name)
                    for col_name, col_meta in t_meta.columns.items():
                        tbl.columns[col_name] = ColumnSchema(
                            name=col_name,
                            data_type=str(col_meta.cql_type).upper(),
                            is_primary_key=(col_name in tbl.primary_keys),
                        )
                    tables_map[t_name] = tbl
        except Exception:
            pass

        schema_meta = SchemaMetadata(
            database_name=self.config.database,
            dialect="cassandra",
            tables=tables_map,
            relationships=[],
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
        if not self.is_connected:
            self.connect()
        start = time.perf_counter()
        try:
            res = self._session.execute(query.strip().rstrip(";"))
            rows = [dict(r._asdict()) for r in res.current_rows]
            cols = list(res.column_names) if res.column_names else []
            exec_ms = (time.perf_counter() - start) * 1000
            return QueryResult(
                columns=cols,
                rows=rows,
                row_count=len(rows),
                rows_affected=0,
                execution_time_ms=round(exec_ms, 2),
                is_mutating=is_mutating,
            )
        except Exception as e:
            exec_ms = (time.perf_counter() - start) * 1000
            return QueryResult(columns=[], rows=[], row_count=0, rows_affected=0,
                               execution_time_ms=round(exec_ms, 2), is_mutating=is_mutating, error=str(e))

    def explain_query(self, query: str) -> Dict[str, Any]:
        return {"ok": True, "dialect": "cassandra", "note": "Use TRACING ON in cqlsh for Cassandra execution plan traces."}
