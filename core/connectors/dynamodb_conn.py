"""
core/connectors/dynamodb_conn.py — AWS DynamoDB Key-Value / Document Connector

Executes PartiQL SQL-compatible statements (SELECT / INSERT / UPDATE / DELETE) via boto3.
Introspects tables, partition keys, sort keys, and global secondary indexes.
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
    import boto3
    from botocore.config import Config as BotoConfig
    HAS_BOTO3 = True
except ImportError:
    boto3 = None
    HAS_BOTO3 = False

_MISSING = "boto3 not installed. Run: pip install boto3"


class DynamoDBConnector(BaseDBConnector):
    """
    AWS DynamoDB / LocalStack Connector.
    Uses PartiQL (SQL-compatible syntax on DynamoDB) for query execution.
    """

    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self._client = None

    def connect(self) -> bool:
        if not HAS_BOTO3:
            raise ImportError(_MISSING)
        try:
            endpoint = f"http://{self.config.host}:{self.config.port}" if self.config.port else None
            region = self.config.extra_params.get("region", "us-east-1")
            self._client = boto3.client(
                "dynamodb",
                region_name=region,
                endpoint_url=endpoint,
                aws_access_key_id=self.config.username or "dummy",
                aws_secret_access_key=self.config.password or "dummy",
            )
            self._client.list_tables()
            self._is_connected = True
            return True
        except Exception as e:
            self._is_connected = False
            raise ConnectionError(f"DynamoDB connection failed: {e}")

    def disconnect(self) -> bool:
        self._client = None
        self._is_connected = False
        return True

    def test_connection(self) -> Dict[str, Any]:
        start = time.perf_counter()
        if not HAS_BOTO3:
            return {"ok": False, "latency_ms": 0.0, "dialect": "dynamodb", "error": _MISSING}
        try:
            if not self.is_connected:
                self.connect()
            resp = self._client.list_tables()
            latency = (time.perf_counter() - start) * 1000
            return {
                "ok": True,
                "latency_ms": round(latency, 2),
                "dialect": "dynamodb",
                "table_count": len(resp.get("TableNames", [])),
                "database": self.config.database,
            }
        except Exception as e:
            return {"ok": False, "latency_ms": (time.perf_counter() - start) * 1000, "dialect": "dynamodb", "error": str(e)}

    def introspect_schema(self, force_refresh: bool = False) -> SchemaMetadata:
        if self._cached_schema and not force_refresh:
            return self._cached_schema
        if not self.is_connected:
            self.connect()

        tables_map: Dict[str, TableSchema] = {}
        resp = self._client.list_tables()
        for t_name in resp.get("TableNames", []):
            tbl = TableSchema(name=t_name, table_type="DYNAMODB_TABLE")
            desc = self._client.describe_table(TableName=t_name).get("Table", {})
            tbl.row_count_estimate = desc.get("ItemCount", 0)

            for key in desc.get("KeySchema", []):
                k_name = key["AttributeName"]
                tbl.primary_keys.append(k_name)

            for attr in desc.get("AttributeDefinitions", []):
                a_name = attr["AttributeName"]
                tbl.columns[a_name] = ColumnSchema(
                    name=a_name,
                    data_type=attr["AttributeType"],
                    is_primary_key=(a_name in tbl.primary_keys),
                )
            tables_map[t_name] = tbl

        schema_meta = SchemaMetadata(
            database_name=self.config.database or "dynamodb",
            dialect="dynamodb",
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
        """Executes PartiQL SQL statement on DynamoDB."""
        if not self.is_connected:
            self.connect()
        start = time.perf_counter()
        try:
            resp = self._client.execute_statement(Statement=query.strip().rstrip(";"))
            items = resp.get("Items", [])

            # Unmarshal DynamoDB JSON {S: 'val', N: '123'}
            def unmarshal(item):
                return {k: list(v.values())[0] for k, v in item.items()}

            rows = [unmarshal(it) for it in items]
            cols = list(rows[0].keys()) if rows else []
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
        return {"ok": True, "dialect": "dynamodb", "note": "PartiQL uses DynamoDB primary key and GSI routing directly."}

    # Aliases for Java-style camelCase naming convention
    establishDatabaseConnection = connect
    terminateDatabaseConnection = disconnect
    verifyDatabaseConnectionStatus = test_connection
    introspectDatabaseCatalogSchema = introspect_schema
    executeQueryAgainstDatabaseEngine = execute_query
    generateQueryExecutionPlan = explain_query
