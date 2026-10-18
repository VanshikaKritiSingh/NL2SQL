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

    def establishDatabaseConnection(self) -> bool:
        """Establish connection to the target database."""
        if type(self).connect is not BaseDBConnector.connect:
            return self.connect()
        raise NotImplementedError(f"{type(self).__name__} must implement establishDatabaseConnection() or connect()")

    def terminateDatabaseConnection(self) -> bool:
        """Close the connection cleanly."""
        if type(self).disconnect is not BaseDBConnector.disconnect:
            return self.disconnect()
        raise NotImplementedError(f"{type(self).__name__} must implement terminateDatabaseConnection() or disconnect()")

    def verifyDatabaseConnectionStatus(self) -> Dict[str, Any]:
        """Ping database, measure roundtrip latency, return status dictionary."""
        if type(self).test_connection is not BaseDBConnector.test_connection:
            return self.test_connection()
        raise NotImplementedError(f"{type(self).__name__} must implement verifyDatabaseConnectionStatus() or test_connection()")

    def introspectDatabaseCatalogSchema(self, force_refresh: bool = False) -> SchemaMetadata:
        """Extract database metadata, tables, columns, foreign keys, and indexes."""
        if type(self).introspect_schema is not BaseDBConnector.introspect_schema:
            return self.introspect_schema(force_refresh=force_refresh)
        raise NotImplementedError(f"{type(self).__name__} must implement introspectDatabaseCatalogSchema() or introspect_schema()")

    def listAccessibleDatabaseNames(self) -> List[str]:
        """List all accessible databases/schemas for the authenticated user."""
        if type(self).list_databases is not BaseDBConnector.list_databases:
            return self.list_databases()
        return [self.config.database] if self.config.database else []

    def executeQueryAgainstDatabaseEngine(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        is_mutating: bool = False,
        timeout_s: Optional[float] = None,
    ) -> QueryResult:
        """Execute a query/command against the live database and return normalized QueryResult."""
        if type(self).execute_query is not BaseDBConnector.execute_query:
            return self.execute_query(
                query=query, params=params, is_mutating=is_mutating, timeout_s=timeout_s
            )
        raise NotImplementedError(f"{type(self).__name__} must implement executeQueryAgainstDatabaseEngine() or execute_query()")

    def generateQueryExecutionPlan(self, query: str) -> Dict[str, Any]:
        """Generate and parse query execution plan (EXPLAIN / PROFILE)."""
        if type(self).explain_query is not BaseDBConnector.explain_query:
            return self.explain_query(query)
        raise NotImplementedError(f"{type(self).__name__} must implement generateQueryExecutionPlan() or explain_query()")

    # Aliases for backward compatibility
    def connect(self) -> bool:
        if type(self).establishDatabaseConnection is not BaseDBConnector.establishDatabaseConnection:
            return self.establishDatabaseConnection()
        raise NotImplementedError(f"{type(self).__name__} must implement establishDatabaseConnection() or connect()")

    def disconnect(self) -> bool:
        if type(self).terminateDatabaseConnection is not BaseDBConnector.terminateDatabaseConnection:
            return self.terminateDatabaseConnection()
        raise NotImplementedError(f"{type(self).__name__} must implement terminateDatabaseConnection() or disconnect()")

    def test_connection(self) -> Dict[str, Any]:
        if type(self).verifyDatabaseConnectionStatus is not BaseDBConnector.verifyDatabaseConnectionStatus:
            return self.verifyDatabaseConnectionStatus()
        raise NotImplementedError(f"{type(self).__name__} must implement verifyDatabaseConnectionStatus() or test_connection()")

    def introspect_schema(self, force_refresh: bool = False) -> SchemaMetadata:
        if type(self).introspectDatabaseCatalogSchema is not BaseDBConnector.introspectDatabaseCatalogSchema:
            return self.introspectDatabaseCatalogSchema(force_refresh=force_refresh)
        raise NotImplementedError(f"{type(self).__name__} must implement introspectDatabaseCatalogSchema() or introspect_schema()")

    def list_databases(self) -> List[str]:
        if type(self).listAccessibleDatabaseNames is not BaseDBConnector.listAccessibleDatabaseNames:
            return self.listAccessibleDatabaseNames()
        return [self.config.database] if self.config.database else []

    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        is_mutating: bool = False,
        timeout_s: Optional[float] = None,
    ) -> QueryResult:
        if type(self).executeQueryAgainstDatabaseEngine is not BaseDBConnector.executeQueryAgainstDatabaseEngine:
            return self.executeQueryAgainstDatabaseEngine(
                query=query, params=params, is_mutating=is_mutating, timeout_s=timeout_s
            )
        raise NotImplementedError(f"{type(self).__name__} must implement executeQueryAgainstDatabaseEngine() or execute_query()")

    def explain_query(self, query: str) -> Dict[str, Any]:
        if type(self).generateQueryExecutionPlan is not BaseDBConnector.generateQueryExecutionPlan:
            return self.generateQueryExecutionPlan(query)
        raise NotImplementedError(f"{type(self).__name__} must implement generateQueryExecutionPlan() or explain_query()")
