# routers/audit.py — Audit Log API Endpoint
from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any
from core.os_engine.audit_log import default_audit_log, AuditEvent

router = APIRouter(prefix="/audit", tags=["Audit Log & OS Concurrency"])
_audit_logger = default_audit_log


@router.get("", response_model=List[Dict[str, Any]])
async def get_audit_logs(
    user_id: Optional[str] = Query(None, description="Filter by user id"),
    operation: Optional[str] = Query(None, description="Filter by operation type"),
    limit: int = Query(100, ge=1, le=500, description="Max entries to return"),
):
    """Retrieve audit log events recorded by the OS engine and pipeline (newest first)."""
    events = _audit_logger.list_events(user_id=user_id, operation=operation, limit=limit)
    return [
        {
            "event_id": ev.event_id,
            "timestamp": ev.timestamp,
            "user_id": ev.user_id,
            "operation": ev.operation,
            "query_id": ev.query_id,
            "stage": ev.stage,
            "stage_name": ev.stage_name,
            "details": ev.details,
            "concurrency_tag": ev.concurrency_tag,
        }
        for ev in events
    ]
