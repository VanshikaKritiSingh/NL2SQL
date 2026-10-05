# models/query.py
from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict, Any
from enum import Enum


class TargetDialect(str, Enum):
    AUTO = "auto"
    POSTGRES = "postgres"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    ORACLE = "oracle"
    SQLSERVER = "sqlserver"
    MARIADB = "mariadb"
    DUCKDB = "duckdb"
    SNOWFLAKE = "snowflake"
    BIGQUERY = "bigquery"
    CLICKHOUSE = "clickhouse"
    ACCESS = "access"
    MONGODB = "mongodb"
    COUCHBASE = "couchbase"
    OPENCYPHER = "opencypher"
    INFLUXQL = "influxql"
    TIMESCALEDB = "timescaledb"


class QueryRequest(BaseModel):
    user_id: str = Field(..., description="Unique user/session identifier (for M2 rate limiting and M3 audit)")
    query_text: str = Field(..., description="The natural language question")
    target_dialect: TargetDialect = Field(default=TargetDialect.AUTO, description="Target DBMS dialect or Auto mode")
    database_profile: Optional[str] = Field(default="master_enterprise", description="Target database/schema profile for this session")
    dry_run_only: bool = Field(default=False, description="Whether to run in dry-run/preview mode without execution gating")


class ResultData(BaseModel):
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int


class QueryResponse(BaseModel):
    query_id: str
    status: Literal["processing", "completed", "approval_required", "error", "rate_limited"]
    generated_sql: Optional[str] = None
    result_data: Optional[ResultData] = None
    approval_payload: Optional[Dict[str, Any]] = None  # Full ApprovalPayload dict when status == "approval_required"
    error_message: Optional[str] = None
    cache_hit: bool = False
    database_profile: Optional[str] = "master_enterprise"
    is_live_db_connected: bool = False
    execution_mode: str = "preview_sandbox"  # preview_sandbox | dry_run | live_connected


class HistoryItem(BaseModel):
    query_id: str
    query_text: str
    generated_sql: Optional[str] = None
    target_dialect: str
    status: str
    timestamp: str
    is_mutating: bool = False
    database_profile: Optional[str] = "master_enterprise"
