"""
core/connectors/neo4j_conn.py — Neo4j Graph Database Connector

Executes openCypher queries produced by the dialect converter via the Bolt driver.
Introspects node labels and relationship types via db.schema.visualization.
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
    import neo4j
    from neo4j import GraphDatabase
    HAS_NEO4J = True
except ImportError:
    neo4j = None
    HAS_NEO4J = False

_MISSING = "neo4j not installed. Run: pip install neo4j"


class Neo4jConnector(BaseDBConnector):
    """
    Neo4j Graph DBMS connector.
    Directly runs openCypher emitted by dialect converter.
    """

    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self._driver = None

    def connect(self) -> bool:
        if not HAS_NEO4J:
            raise ImportError(_MISSING)
        try:
            port = self.config.port or 7687
            uri = f"bolt://{self.config.host}:{port}"
            auth = (self.config.username or "neo4j", self.config.password or "")
            self._driver = GraphDatabase.driver(uri, auth=auth)
            self._driver.verify_connectivity()
            self._is_connected = True
            return True
        except Exception as e:
            self._is_connected = False
            raise ConnectionError(f"Neo4j connection failed [{self.config.host}]: {e}")

    def disconnect(self) -> bool:
        if self._driver:
            try:
                self._driver.close()
            except Exception:
                pass
            finally:
                self._driver = None
                self._is_connected = False
        return True

    def test_connection(self) -> Dict[str, Any]:
        start = time.perf_counter()
        if not HAS_NEO4J:
            return {"ok": False, "latency_ms": 0.0, "dialect": "neo4j", "error": _MISSING}
        try:
            if not self.is_connected:
                self.connect()
            with self._driver.session(database=self.config.database or "neo4j") as s:
                ver = s.run("CALL dbms.components() YIELD name, versions RETURN name, versions[0] AS v").single()
            latency = (time.perf_counter() - start) * 1000
            v_str = ver["v"] if ver else "unknown"
            return {
                "ok": True,
                "latency_ms": round(latency, 2),
                "dialect": "neo4j",
                "version": f"Neo4j {v_str}",
                "database": self.config.database or "neo4j",
            }
        except Exception as e:
            return {"ok": False, "latency_ms": (time.perf_counter() - start) * 1000, "dialect": "neo4j", "error": str(e)}

    def introspect_schema(self, force_refresh: bool = False) -> SchemaMetadata:
        if self._cached_schema and not force_refresh:
            return self._cached_schema
        if not self.is_connected:
            self.connect()

        tables_map: Dict[str, TableSchema] = {}
        relationships: List[Dict[str, str]] = []

        with self._driver.session(database=self.config.database or "neo4j") as s:
            # Labels → TableSchema (treat node labels as "tables")
            labels = [r["label"] for r in s.run("CALL db.labels() YIELD label")]
            for lbl in labels:
                tbl = TableSchema(name=lbl, table_type="NODE_LABEL")
                # Sample 1 node to get property names
                try:
                    sample = s.run(f"MATCH (n:`{lbl}`) RETURN n LIMIT 1").single()
                    if sample:
                        props = dict(sample["n"])
                        for prop_name, val in props.items():
                            tbl.columns[prop_name] = ColumnSchema(
                                name=prop_name,
                                data_type=type(val).__name__.upper(),
                            )
                except Exception:
                    pass
                tables_map[lbl] = tbl

            # Relationship types
            try:
                rel_records = s.run("CALL db.relationshipTypes() YIELD relationshipType").values()
                for r in rel_records:
                    relationships.append({"rel_type": r[0]})
            except Exception:
                pass

        schema_meta = SchemaMetadata(
            database_name=self.config.database or "neo4j",
            dialect="neo4j",
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
        if not self.is_connected:
            self.connect()
        start = time.perf_counter()
        try:
            with self._driver.session(database=self.config.database or "neo4j") as s:
                result = s.run(query, params or {})
                records = [dict(r) for r in result]
                cols = list(records[0].keys()) if records else []
                exec_ms = (time.perf_counter() - start) * 1000
                return QueryResult(
                    columns=cols,
                    rows=records,
                    row_count=len(records),
                    rows_affected=0,
                    execution_time_ms=round(exec_ms, 2),
                    is_mutating=is_mutating,
                )
        except Exception as e:
            exec_ms = (time.perf_counter() - start) * 1000
            return QueryResult(columns=[], rows=[], row_count=0, rows_affected=0,
                               execution_time_ms=round(exec_ms, 2), is_mutating=is_mutating, error=str(e))

    def explain_query(self, query: str) -> Dict[str, Any]:
        try:
            with self._driver.session(database=self.config.database or "neo4j") as s:
                plan = s.run(f"EXPLAIN {query}").consume().plan
                return {"ok": True, "dialect": "neo4j", "plan": str(plan)}
        except Exception as e:
            return {"ok": False, "dialect": "neo4j", "error": str(e)}

    # Aliases for Java-style camelCase naming convention
    establishDatabaseConnection = connect
    terminateDatabaseConnection = disconnect
    verifyDatabaseConnectionStatus = test_connection
    introspectDatabaseCatalogSchema = introspect_schema
    executeQueryAgainstDatabaseEngine = execute_query
    generateQueryExecutionPlan = explain_query
