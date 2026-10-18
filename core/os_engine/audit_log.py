"""
core/os_engine/audit_log.py — Persistent OS-backed audit log for NL2SQL pipeline
Records every query submission, approval/rejection, execution, rollback,
and concurrency event using the OS time + operation context.
"""
import json, time, os
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

AUDIT_LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "audit_log.jsonl")


@dataclass
class AuditEvent:
    event_id: str
    timestamp: float
    user_id: str
    operation: str  # SUBMIT, APPROVE, REJECT, EXECUTE, ROLLBACK, LOCK_ACQUIRE, LOCK_RELEASE, SCHEMA_REFRESH
    query_id: Optional[str] = None
    stage: Optional[int] = None
    stage_name: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    concurrency_tag: Optional[str] = None


class PipelineAuditLog:
    def __init__(self, path: str = AUDIT_LOG_PATH):
        self.path = path
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        if not os.path.exists(self.path):
            with open(self.path, "w") as f:
                pass

    def appendAuditTrailEventRecord(self, event: AuditEvent):
        with open(self.path, "a") as f:
            f.write(json.dumps(asdict(event)) + "\n")

    def listAuditTrailEventRecords(self, user_id: Optional[str] = None, operation: Optional[str] = None, limit: int = 100) -> List[AuditEvent]:
        events: List[AuditEvent] = []
        with open(self.path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                ev = AuditEvent(**d)
                if user_id and ev.user_id != user_id:
                    continue
                if operation and ev.operation != operation:
                    continue
                events.append(ev)
                if len(events) >= limit:
                    break
        return events

    def retrieveAuditEventsForQueryIdentifier(self, query_id: str) -> List[AuditEvent]:
        return [ev for ev in self.listAuditTrailEventRecords() if ev.query_id == query_id]

    def recordValidationAuditEntry(self, sql: str, result: Any, user_id: str = "system", query_id: Optional[str] = None) -> None:
        """Bridge method allowing PipelineAuditLog to act as an AuditLogger for the validation engine."""
        issues_summary = [
            {"code": getattr(issue, "code", ""), "severity": str(getattr(issue, "severity", "")), "message": getattr(issue, "message", "")}
            for issue in getattr(result, "issues", [])
        ]
        status_val = getattr(getattr(result, "status", None), "value", str(getattr(result, "status", "UNKNOWN")))
        event = AuditEvent(
            event_id=f"val_{int(time.time() * 1000)}",
            timestamp=time.time(),
            user_id=user_id,
            operation="VALIDATE",
            query_id=query_id,
            stage=6,
            stage_name="ValidationEngine",
            details={
                "sql": sql,
                "status": status_val,
                "issues": issues_summary,
            }
        )
        self.appendAuditTrailEventRecord(event)

    # Aliases for backward compatibility
    append = appendAuditTrailEventRecord
    list_events = listAuditTrailEventRecords
    last_for_query = retrieveAuditEventsForQueryIdentifier
    log_validation = recordValidationAuditEntry
