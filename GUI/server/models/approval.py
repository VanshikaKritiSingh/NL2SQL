# models/approval.py
from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict, Any


RiskTier = Literal["low", "medium", "high", "critical"]


class ImpactedTable(BaseModel):
    name: str
    impact_level: Literal["direct", "referenced"]  # direct = red border, referenced = yellow
    operation: Optional[str] = None   # "INSERT", "UPDATE", "DELETE", "ALTER", "DROP"


class CostEstimate(BaseModel):
    estimated_rows: int
    estimated_cost: float
    scan_type: str       # "full_table_scan", "index_scan", "index_only"
    warnings: List[str] = Field(default_factory=list)


class SecurityCheck(BaseModel):
    deadlock_risk: Literal["none", "low", "medium", "high"]
    lock_level: str      # "row", "table", "schema"
    privilege_ok: bool
    flags: List[str] = Field(default_factory=list)     # ["FK_CASCADE_DELETE", "TRIGGERS_AFFECTED", etc.]


class DmlRowDiff(BaseModel):
    row_id: Any
    columns: Dict[str, Dict[str, Any]]  # {"price": {"before": 49.99, "after": 54.99}}
    change_type: Literal["insert", "update", "delete"]


class DiffData(BaseModel):
    diff_type: Literal["ddl", "dml", "none"]
    ddl_before: Optional[str] = None   # SQL DDL before the change
    ddl_after: Optional[str] = None    # SQL DDL after the change
    dml_rows: Optional[List[DmlRowDiff]] = None


class ApprovalPayload(BaseModel):
    query_id: str
    generated_sql: str
    target_dialect: str
    risk_tier: RiskTier
    impacted_tables: List[ImpactedTable]
    cost_estimate: CostEstimate
    security_check: SecurityCheck
    diff_data: DiffData


class ApprovalRequest(BaseModel):
    query_id: str
    decision: Literal["approve", "reject"]
    feedback: Optional[str] = None
    user_id: str


class ApprovalResponse(BaseModel):
    query_id: str
    status: Literal["approved_executing", "rejected_retrying", "rejected_final"]
    message: str
