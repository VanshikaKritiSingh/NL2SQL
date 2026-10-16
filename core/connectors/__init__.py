"""
core/connectors/__init__.py — Public surface for DBMS Connectors & Registry
"""

from core.connectors.base import (
    BaseDBConnector,
    ColumnSchema,
    ConnectionConfig,
    ConnectorType,
    QueryResult,
    SchemaMetadata,
    TableSchema,
)
from core.connectors.registry import (
    ConnectorRegistry,
    create_connector,
    default_registry,
    CONNECTOR_MAP,
)
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
from core.connectors.ollama import OllamaConnector, OllamaGenerationResult, default_ollama
from core.connectors.peft_connector import LocalPEFTEngine, default_peft_engine

__all__ = [
    "BaseDBConnector",
    "ColumnSchema",
    "ConnectionConfig",
    "ConnectorType",
    "QueryResult",
    "SchemaMetadata",
    "TableSchema",
    "ConnectorRegistry",
    "create_connector",
    "default_registry",
    "CONNECTOR_MAP",
    "SQLiteConnector",
    "PostgresConnector",
    "MySQLConnector",
    "DuckDBConnector",
    "ClickHouseConnector",
    "MongoDBConnector",
    "Neo4jConnector",
    "RedisConnector",
    "CassandraConnector",
    "DynamoDBConnector",
    "OllamaConnector",
    "OllamaGenerationResult",
    "default_ollama",
    "LocalPEFTEngine",
    "default_peft_engine",
]
