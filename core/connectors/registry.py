"""
core/connectors/registry.py — In-Memory Session-Bound Database Connector Registry

Lifecycle:
  - Per-user session registry: user attaches a DB (ephemeral credentials in memory only).
  - Automatically disconnects on detach or session eviction.
  - Zero server-side persistence of credentials.
"""

import threading
from typing import Any, Dict, List, Optional

from core.connectors.base import BaseDBConnector, ConnectionConfig, ConnectorType
from core.connectors.sqlite import SQLiteConnector
from core.connectors.postgres import PostgresConnector
from core.connectors.mysql import MySQLConnector
from core.connectors.duckdb_conn import DuckDBConnector
from core.connectors.clickhouse_conn import ClickHouseConnector
from core.connectors.mongodb_conn import MongoDBConnector
from core.connectors.neo4j_conn import Neo4jConnector
from core.connectors.redis_conn import RedisConnector
from core.connectors.cassandra_conn import CassandraConnector
from core.connectors.dynamodb_conn import DynamoDBConnector

CONNECTOR_MAP = {
    ConnectorType.SQLITE: SQLiteConnector,
    ConnectorType.POSTGRES: PostgresConnector,
    ConnectorType.MYSQL: MySQLConnector,
    ConnectorType.DUCKDB: DuckDBConnector,
    ConnectorType.CLICKHOUSE: ClickHouseConnector,
    ConnectorType.MONGODB: MongoDBConnector,
    ConnectorType.NEO4J: Neo4jConnector,
    ConnectorType.REDIS: RedisConnector,
    ConnectorType.CASSANDRA: CassandraConnector,
    ConnectorType.DYNAMODB: DynamoDBConnector,
}


def create_connector(config: ConnectionConfig) -> BaseDBConnector:
    """Factory function: instantiates the appropriate connector for the given config."""
    cls = CONNECTOR_MAP.get(config.connector_type)
    if not cls:
        raise ValueError(f"Unsupported connector type: {config.connector_type}")
    return cls(config)


class ConnectorRegistry:
    """
    Thread-safe in-memory registry holding active DB connections per user session.
    """

    def __init__(self):
        self._connections: Dict[str, BaseDBConnector] = {}
        self._lock = threading.Lock()

    def attach(self, user_id: str, config: ConnectionConfig) -> BaseDBConnector:
        """
        Instantiates connector, verifies connection via test_connection,
        and binds it to user_id. Replaces any existing connection for that user.
        Raises ConnectionError if connection test/verification fails.
        """
        conn = create_connector(config)
        conn.connect()
        ping = conn.test_connection()
        if not ping.get("ok"):
            conn.disconnect()
            raise ConnectionError(
                f"Connection verification failed for {config.connector_type.value} [{config.database}]: "
                f"{ping.get('error', 'Ping test failed')}"
            )
        with self._lock:
            # Clean up previous connection if any
            prev = self._connections.get(user_id)
            if prev:
                try:
                    prev.disconnect()
                except Exception:
                    pass
            self._connections[user_id] = conn
        return conn

    def detach(self, user_id: str) -> bool:
        """Closes and removes the user's connection."""
        with self._lock:
            conn = self._connections.pop(user_id, None)
        if conn:
            try:
                conn.disconnect()
            except Exception:
                pass
            return True
        return False

    def get(self, user_id: str) -> Optional[BaseDBConnector]:
        """Returns the active connector for user_id if present and connected."""
        with self._lock:
            return self._connections.get(user_id)

    def is_attached(self, user_id: str) -> bool:
        with self._lock:
            conn = self._connections.get(user_id)
            return conn is not None and conn.is_connected

    def list_attached_users(self) -> List[str]:
        with self._lock:
            return list(self._connections.keys())

    @staticmethod
    def test_config(config: ConnectionConfig) -> Dict[str, Any]:
        """Test connection parameters without registering to a session."""
        conn = create_connector(config)
        try:
            return conn.test_connection()
        finally:
            conn.disconnect()

    @staticmethod
    def list_databases(config: ConnectionConfig) -> List[str]:
        """Validates credentials and returns accessible databases for the user."""
        conn = create_connector(config)
        conn.connect()
        try:
            return conn.list_databases()
        finally:
            conn.disconnect()


# Global singleton instance for the process
default_registry = ConnectorRegistry()
