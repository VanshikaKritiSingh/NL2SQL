"""
core/connectors/custom_conn.py — Generic / Custom User-Defined DBMS Connector

Allows users to connect their personal or custom database management system
(e.g., CockroachDB, TiDB, MariaDB, TimescaleDB, Yugabyte, Redshift, Turso,
or custom local/remote SQL sockets) without being limited to built-in types.

Dispatches to the matching wire-protocol engine based on config.extra_params["protocol"]:
  - "postgres"  — PostgreSQL-wire compatible (CockroachDB, Redshift, Timescale, Supabase, etc.)
  - "mysql"     — MySQL-wire compatible (MariaDB, TiDB, SingleStore, Percona, etc.)
  - "sqlite"    — SQLite / file-based / LibSQL
  - "duckdb"    — DuckDB in-process columnar
  - "mongodb"   — MongoDB wire / Document NoSQL
"""

from typing import Any, Dict, List, Optional
from core.connectors.base import (
    BaseDBConnector,
    ConnectionConfig,
    ConnectorType,
    QueryResult,
    SchemaMetadata,
)


class CustomConnector(BaseDBConnector):
    """
    Polymorphic connector for user-defined personal DBMS endpoints.
    Delegates network wire communication and SQL execution to the matching protocol engine.
    """

    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self.custom_label: str = config.extra_params.get("custom_name") or "Custom DBMS"
        self.protocol: str = (config.extra_params.get("protocol") or "postgres").lower().strip()
        self._delegate: BaseDBConnector = self._create_delegate()

    def _create_delegate(self) -> BaseDBConnector:
        proto_map = {
            "postgres": ConnectorType.POSTGRES,
            "postgresql": ConnectorType.POSTGRES,
            "mysql": ConnectorType.MYSQL,
            "mariadb": ConnectorType.MYSQL,
            "sqlite": ConnectorType.SQLITE,
            "duckdb": ConnectorType.DUCKDB,
            "clickhouse": ConnectorType.CLICKHOUSE,
            "mongodb": ConnectorType.MONGODB,
            "neo4j": ConnectorType.NEO4J,
            "redis": ConnectorType.REDIS,
            "cassandra": ConnectorType.CASSANDRA,
        }
        resolved_type = proto_map.get(self.protocol, ConnectorType.POSTGRES)

        # Build sub-config with resolved connector type
        sub_config = ConnectionConfig(
            connector_type=resolved_type,
            database=self.config.database,
            host=self.config.host,
            port=self.config.port,
            username=self.config.username,
            password=self.config.password,
            ssl_mode=self.config.ssl_mode,
            read_only=self.config.read_only,
            timeout_s=self.config.timeout_s,
            extra_params=self.config.extra_params,
        )

        from core.connectors.registry import instantiateConnectorForConfiguration
        return instantiateConnectorForConfiguration(sub_config)

    @property
    def is_connected(self) -> bool:
        return self._delegate.is_connected if self._delegate else False

    def connect(self) -> bool:
        res = self._delegate.connect()
        self._is_connected = self._delegate.is_connected
        return res

    def disconnect(self) -> bool:
        res = self._delegate.disconnect()
        self._is_connected = False
        return res

    def test_connection(self) -> Dict[str, Any]:
        info = self._delegate.test_connection()
        info["custom_name"] = self.custom_label
        info["protocol"] = self.protocol
        return info

    def introspect_schema(self, force_refresh: bool = False) -> SchemaMetadata:
        schema = self._delegate.introspect_schema(force_refresh=force_refresh)
        return schema

    def list_databases(self) -> List[str]:
        return self._delegate.list_databases()

    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        is_mutating: bool = False,
        timeout_s: Optional[float] = None,
    ) -> QueryResult:
        return self._delegate.execute_query(
            query=query, params=params, is_mutating=is_mutating, timeout_s=timeout_s
        )

    def explain_query(self, query: str) -> Dict[str, Any]:
        return self._delegate.explain_query(query)
