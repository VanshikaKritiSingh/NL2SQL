"""
core/connectors/redis_conn.py — Redis Key-Value Connector

Executes raw Redis commands / GET / SET / SCAN / HGETALL.
Introspects key counts, types, and DB size.
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
    import redis
    HAS_REDIS = True
except ImportError:
    redis = None
    HAS_REDIS = False

_MISSING = "redis not installed. Run: pip install redis"


class RedisConnector(BaseDBConnector):
    """
    Redis Key-Value store connector.
    execute_query: accepts space-separated redis command strings e.g. "HGETALL user:1001" or "KEYS *"
    """

    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self._r = None

    def connect(self) -> bool:
        if not HAS_REDIS:
            raise ImportError(_MISSING)
        try:
            port = self.config.port or 6379
            db_num = int(self.config.database) if self.config.database.isdigit() else 0
            self._r = redis.Redis(
                host=self.config.host,
                port=port,
                db=db_num,
                password=self.config.password or None,
                socket_timeout=self.config.timeout_s,
                decode_responses=True,
            )
            self._r.ping()
            self._is_connected = True
            return True
        except Exception as e:
            self._is_connected = False
            raise ConnectionError(f"Redis connection failed [{self.config.host}]: {e}")

    def disconnect(self) -> bool:
        if self._r:
            try:
                self._r.close()
            except Exception:
                pass
            finally:
                self._r = None
                self._is_connected = False
        return True

    def test_connection(self) -> Dict[str, Any]:
        start = time.perf_counter()
        if not HAS_REDIS:
            return {"ok": False, "latency_ms": 0.0, "dialect": "redis", "error": _MISSING}
        try:
            if not self.is_connected:
                self.connect()
            info = self._r.info("server")
            latency = (time.perf_counter() - start) * 1000
            return {
                "ok": True,
                "latency_ms": round(latency, 2),
                "dialect": "redis",
                "version": f"Redis {info.get('redis_version', 'unknown')}",
                "database": self.config.database,
            }
        except Exception as e:
            return {"ok": False, "latency_ms": (time.perf_counter() - start) * 1000, "dialect": "redis", "error": str(e)}

    def introspect_schema(self, force_refresh: bool = False) -> SchemaMetadata:
        if self._cached_schema and not force_refresh:
            return self._cached_schema
        if not self.is_connected:
            self.connect()

        tables_map: Dict[str, TableSchema] = {}
        try:
            keyspace = self._r.info("keyspace")
            # Sample top-level key patterns as virtual "tables"
            patterns: Dict[str, int] = {}
            for k in self._r.scan_iter(count=50):
                prefix = k.split(":")[0] if ":" in k else "root"
                patterns[prefix] = patterns.get(prefix, 0) + 1

            for prefix, count in patterns.items():
                tbl = TableSchema(
                    name=prefix,
                    table_type="KEYSPACE_NAMESPACE",
                    row_count_estimate=count,
                    columns={
                        "key": ColumnSchema(name="key", data_type="STRING", is_primary_key=True),
                        "value": ColumnSchema(name="value", data_type="STRING_OR_HASH"),
                    },
                    primary_keys=["key"],
                )
                tables_map[prefix] = tbl
        except Exception:
            pass

        schema_meta = SchemaMetadata(
            database_name=self.config.database or "db0",
            dialect="redis",
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
            parts = query.strip().split()
            cmd, args = parts[0].upper(), parts[1:]
            raw_res = self._r.execute_command(cmd, *args)
            exec_ms = (time.perf_counter() - start) * 1000

            if isinstance(raw_res, dict):
                rows = [{"field": k, "value": v} for k, v in raw_res.items()]
                cols = ["field", "value"]
            elif isinstance(raw_res, list):
                rows = [{"item": str(x)} for x in raw_res]
                cols = ["item"]
            else:
                rows = [{"result": str(raw_res)}]
                cols = ["result"]

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
        return {"ok": True, "dialect": "redis", "note": "Redis is in-memory O(1)/O(N); no query optimizer EXPLAIN."}
