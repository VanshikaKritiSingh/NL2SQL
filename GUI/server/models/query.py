# models/query.py
from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict, Any
from enum import Enum


class TargetDialect(str, Enum):
    MYSQL = "mysql"
    ORACLE = "oracle"
    SQLSERVER = "sqlserver"
    ACCESS = "access"
    POSTGRES = "postgres"


class QueryRequest(BaseModel):
    user_id: str = Field(..., description="Unique user/session identifier (for M2 rate limiting and M3 audit)")
    query_text: str = Field(..., description="The natural language question")
    target_dialect: TargetDialect = Field(default=TargetDialect.MYSQL, description="Target DBMS dialect")


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


class HistoryItem(BaseModel):
    query_id: str
    query_text: str
    generated_sql: Optional[str] = None
    target_dialect: str
    status: str
    timestamp: str
    is_mutating: bool = False
