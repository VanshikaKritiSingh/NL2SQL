"""
core/connectors/base.py — Unified DBMS Connector Interface & Schema Contracts
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, List, Optional, Union


class ConnectorType(str, Enum):
    SQLITE = "sqlite"
    POSTGRES = "postgres"
    MYSQL = "mysql"
    DUCKDB = "duckdb"
    CLICKHOUSE = "clickhouse"
    MONGODB = "mongodb"
    NEO4J = "neo4j"
    REDIS = "redis"
    CASSANDRA = "cassandra"
    DYNAMODB = "dynamodb"


@dataclass
class ConnectionConfig:
    connector_type: ConnectorType
    database: str
    host: Optional[str] = "localhost"
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssl_mode: Optional[str] = None
    read_only: bool = False
    timeout_s: float = 15.0
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ColumnSchema:
    name: str
    data_type: str
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_key_target: Optional[str] = None  # e.g. "users.user_id"
    nullable: bool = True
    default_value: Optional[str] = None
    sample_values: List[Any] = field(default_factory=list)


@dataclass
class TableSchema:
    name: str
    table_type: str = "TABLE"  # "TABLE", "VIEW", "COLLECTION", "NODE_LABEL"
    columns: Dict[str, ColumnSchema] = field(default_factory=dict)
    primary_keys: List[str] = field(default_factory=list)
    foreign_keys: List[Dict[str, str]] = field(default_factory=list)
    row_count_estimate: Optional[int] = None
    comment: Optional[str] = None


@dataclass
class SchemaMetadata:
    database_name: str
    dialect: str
    tables: Dict[str, TableSchema] = field(default_factory=dict)
    relationships: List[Dict[str, str]] = field(default_factory=list)
    extracted_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "database_name": self.database_name,
            "dialect": self.dialect,
            "extracted_at": self.extracted_at,
            "tables": {
                t_name: {
                    "name": t.name,
                    "table_type": t.table_type,
                    "primary_keys": t.primary_keys,
                    "foreign_keys": t.foreign_keys,
                    "row_count_estimate": t.row_count_estimate,
                    "columns": {
                        c_name: {
                            "name": c.name,
                            "data_type": c.data_type,
                            "is_primary_key": c.is_primary_key,
                            "is_foreign_key": c.is_foreign_key,
                            "foreign_key_target": c.foreign_key_target,
                            "nullable": c.nullable,
                            "sample_values": c.sample_values,
                        }
                        for c_name, c in t.columns.items()
                    },
                }
                for t_name, t in self.tables.items()
            },
            "relationships": self.relationships,
        }


@dataclass
class QueryResult:
    columns: List[str] = field(default_factory=list)
    rows: List[Dict[str, Any]] = field(default_factory=list)
    row_count: int = 0
    rows_affected: int = 0
    execution_time_ms: float = 0.0
    is_mutating: bool = False
    warning: Optional[str] = None
    error: Optional[str] = None


class BaseDBConnector(ABC):
    """
    Abstract Base Class for all DBMS Connectors.
    Provides uniform connection lifecycle, schema introspection, execution, and EXPLAIN.
    """

    def __init__(self, config: ConnectionConfig):
        self.config = config
        self._is_connected = False
        self._cached_schema: Optional[SchemaMetadata] = None

    @property
    def connector_type(self) -> ConnectorType:
        return self.config.connector_type

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the target database."""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Close the connection cleanly."""
        pass

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """Ping database, measure roundtrip latency, return status dictionary."""
        pass

    @abstractmethod
    def introspect_schema(self, force_refresh: bool = False) -> SchemaMetadata:
        """Extract database metadata, tables, columns, foreign keys, and indexes."""
        pass

    def list_databases(self) -> List[str]:
        """List all accessible databases/schemas for the authenticated user."""
        return [self.config.database] if self.config.database else []

    @abstractmethod
    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        is_mutating: bool = False,
        timeout_s: Optional[float] = None,
    ) -> QueryResult:
        """Execute a query/command against the live database and return normalized QueryResult."""
        pass

    @abstractmethod
    def explain_query(self, query: str) -> Dict[str, Any]:
        """Generate and parse query execution plan (EXPLAIN / PROFILE)."""
        pass
