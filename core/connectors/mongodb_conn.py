"""
core/connectors/mongodb_conn.py — MongoDB Document Store Connector

Executes MQL aggregation pipelines produced by the dialect converter.
Introspects collection metadata via collStats / $sample.
"""

import json
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
    import pymongo
    import pymongo.errors
    HAS_PYMONGO = True
except ImportError:
    pymongo = None
    HAS_PYMONGO = False

_MISSING = "pymongo not installed. Run: pip install pymongo"


class MongoDBConnector(BaseDBConnector):
    """
    MongoDB connector.
    - execute_query: accepts either a JSON aggregation pipeline string OR a
      find-style dict string e.g. '{"collection":"orders","filter":{"status":"DELIVERED"}}'
    - The dialect converter emits MQL in that format already.
    """

    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self._client = None
        self._db = None

    def connect(self) -> bool:
        if not HAS_PYMONGO:
            raise ImportError(_MISSING)
        try:
            port = self.config.port or 27017
            scheme = "mongodb"
            if self.config.username and self.config.password:
                uri = f"{scheme}://{self.config.username}:{self.config.password}@{self.config.host}:{port}/{self.config.database}"
            else:
                uri = f"{scheme}://{self.config.host}:{port}"
            self._client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=int(self.config.timeout_s * 1000))
            self._client.admin.command("ping")  # validate connection
            self._db = self._client[self.config.database]
            self._is_connected = True
            return True
        except Exception as e:
            self._is_connected = False
            raise ConnectionError(f"MongoDB connection failed [{self.config.host}]: {e}")

    def disconnect(self) -> bool:
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            finally:
                self._client = None
                self._db = None
                self._is_connected = False
        return True

    def test_connection(self) -> Dict[str, Any]:
        start = time.perf_counter()
        if not HAS_PYMONGO:
            return {"ok": False, "latency_ms": 0.0, "dialect": "mongodb", "error": _MISSING}
        try:
            if not self.is_connected:
                self.connect()
            info = self._client.server_info()
            latency = (time.perf_counter() - start) * 1000
            return {
                "ok": True,
                "latency_ms": round(latency, 2),
                "dialect": "mongodb",
                "version": f"MongoDB {info.get('version', 'unknown')}",
                "database": self.config.database,
            }
        except Exception as e:
            return {"ok": False, "latency_ms": (time.perf_counter() - start) * 1000, "dialect": "mongodb", "error": str(e)}

    def list_databases(self) -> List[str]:
        if not self.is_connected or not self._client:
            self.connect()
        return self._client.list_database_names()

    def introspect_schema(self, force_refresh: bool = False) -> SchemaMetadata:
        if self._cached_schema and not force_refresh:
            return self._cached_schema
        if not self.is_connected:
            self.connect()

        tables_map: Dict[str, TableSchema] = {}

        for coll_name in self._db.list_collection_names():
            tbl = TableSchema(name=coll_name, table_type="COLLECTION")

            # Sample one document to infer field types
            try:
                sample = list(self._db[coll_name].aggregate([{"$sample": {"size": 1}}]))
                if sample:
                    doc = sample[0]
                    for field_name, val in doc.items():
                        tbl.columns[field_name] = ColumnSchema(
                            name=field_name,
                            data_type=type(val).__name__.upper(),
                            is_primary_key=(field_name == "_id"),
                        )
                    if "_id" in tbl.columns:
                        tbl.primary_keys.append("_id")
            except Exception:
                pass

            # Row count estimate
            try:
                tbl.row_count_estimate = self._db[coll_name].estimated_document_count()
            except Exception:
                pass

            tables_map[coll_name] = tbl

        schema_meta = SchemaMetadata(
            database_name=self.config.database,
            dialect="mongodb",
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
        """
        Accepts the MQL envelope produced by dialect converter:
          '{"collection":"orders","pipeline":[...]}'
        or a simple find:
          '{"collection":"orders","filter":{...},"limit":100}'
        """
        if not self.is_connected:
            self.connect()
        start = time.perf_counter()
        try:
            payload = json.loads(query) if isinstance(query, str) else query
            coll_name = payload.get("collection", "")
            coll = self._db[coll_name]

            if "pipeline" in payload:
                # Aggregation pipeline
                cursor = coll.aggregate(payload["pipeline"])
            else:
                # Simple find
                flt = payload.get("filter", {})
                limit = int(payload.get("limit", 200))
                proj = payload.get("projection", None)
                cursor = coll.find(flt, proj).limit(limit)

            rows = [
                {k: (str(v) if str(type(v)) == "<class 'bson.objectid.ObjectId'>" else v)
                 for k, v in doc.items()}
                for doc in cursor
            ]
            cols = list(rows[0].keys()) if rows else []
            exec_ms = (time.perf_counter() - start) * 1000

            return QueryResult(
                columns=cols,
                rows=rows,
                row_count=len(rows),
                rows_affected=0,
                execution_time_ms=round(exec_ms, 2),
                is_mutating=False,
            )
        except Exception as e:
            exec_ms = (time.perf_counter() - start) * 1000
            return QueryResult(columns=[], rows=[], row_count=0, rows_affected=0,
                               execution_time_ms=round(exec_ms, 2), is_mutating=is_mutating, error=str(e))

    def explain_query(self, query: str) -> Dict[str, Any]:
        try:
            payload = json.loads(query) if isinstance(query, str) else query
            coll_name = payload.get("collection", "")
            coll = self._db[coll_name]
            pipeline = payload.get("pipeline", [{"$match": payload.get("filter", {})}])
            plan = coll.aggregate(pipeline, explain=True)
            return {"ok": True, "dialect": "mongodb", "plan": plan}
        except Exception as e:
            return {"ok": False, "dialect": "mongodb", "error": str(e)}
