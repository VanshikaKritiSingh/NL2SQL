"""
core/os_engine/audit_log.py — Persistent OS-backed audit log for NL2SQL pipeline
Records every query submission, approval/rejection, execution, rollback,
and concurrency event using the OS time + operation context.
"""
import json, time, os, datetime
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
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")

    def listAuditTrailEventRecords(self, user_id: Optional[str] = None, operation: Optional[str] = None, limit: int = 100) -> List[AuditEvent]:
        events: List[AuditEvent] = []
        if not os.path.exists(self.path):
            return events

        with open(self.path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                ev = AuditEvent(**d)
                if user_id and ev.user_id != user_id:
                    continue
                if operation and ev.operation != operation:
                    continue
                events.append(ev)
                if len(events) >= limit:
                    break
            except Exception:
                continue
        return events

    def retrieve_query_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Reconstructs historical user queries and executed SQL from persistent audit records."""
        if not os.path.exists(self.path):
            return []

        with open(self.path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        # Pass 1: Discover QID to transaction tag correlations
        qid_to_tag: Dict[str, str] = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                tag = d.get("concurrency_tag")
                qid = d.get("query_id")
                if tag and tag.startswith("txn-") and len(tag) > 12 and qid:
                    qid_to_tag[qid] = tag
            except Exception:
                continue

        tx_map: Dict[str, Dict[str, Any]] = {}
        ordered_keys: List[str] = []

        # Pass 2: Reconstruct unified transactions from newest to oldest
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                if user_id and d.get("user_id") != user_id:
                    continue

                tag = d.get("concurrency_tag")
                qid = d.get("query_id")

                key = None
                if tag and tag.startswith("txn-") and len(tag) > 12:
                    key = tag
                elif qid and qid in qid_to_tag:
                    key = qid_to_tag[qid]
                elif qid:
                    key = qid
                elif tag:
                    key = tag

                if not key:
                    continue

                details = d.get("details", {})
                q = details.get("query") or details.get("query_text")
                sql = details.get("canonical_sql") or details.get("sql")

                if key not in tx_map:
                    ts_float = d.get("timestamp", 0)
                    try:
                        ts_str = datetime.datetime.fromtimestamp(ts_float).strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        ts_str = ""

                    tx_map[key] = {
                        "query_id": qid or key,
                        "query_text": q or "",
                        "generated_sql": sql or None,
                        "target_dialect": details.get("target_engine") or details.get("target_dialect") or "auto",
                        "status": "completed",
                        "timestamp": ts_str,
                        "timestamp_raw": ts_float,
                        "is_mutating": False,
                        "database_profile": details.get("database") or details.get("target_db") or None,
                        "selected_dialect": details.get("selected_dialect") or None,
                        "dialect_reason": details.get("dialect_reason") or None,
                        "command_blocks": details.get("command_blocks") or None,
                    }
                    ordered_keys.append(key)

                rec = tx_map[key]
                dialect = details.get("target_engine") or details.get("target_dialect")
                op = d.get("operation")

                if q and not rec["query_text"]:
                    rec["query_text"] = q
                if sql and not rec["generated_sql"]:
                    rec["generated_sql"] = sql
                if dialect and rec["target_dialect"] == "auto":
                    rec["target_dialect"] = dialect
                if details.get("database") and not rec["database_profile"]:
                    rec["database_profile"] = details.get("database")
                if details.get("command_blocks") and not rec["command_blocks"]:
                    rec["command_blocks"] = details.get("command_blocks")
                if details.get("selected_dialect") and not rec["selected_dialect"]:
                    rec["selected_dialect"] = details.get("selected_dialect")

                if op in ("APPROVE", "EXECUTE"):
                    rec["status"] = "completed"
                elif op == "ROUTED" and details.get("requires_human_approval") and rec["status"] != "completed":
                    rec["status"] = "approval_required"
                    rec["is_mutating"] = True
                elif op == "REJECT":
                    rec["status"] = "rejected"
            except Exception:
                continue

        history: List[Dict[str, Any]] = []
        for k in ordered_keys:
            rec = tx_map[k]
            if not rec["query_text"] and not rec["generated_sql"]:
                continue
            if not rec["query_text"]:
                rec["query_text"] = f"Executed Query ({rec['query_id']})"
            history.append(rec)
            if len(history) >= limit:
                break

        return history

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


# Singleton audit logger instance
default_audit_log = PipelineAuditLog()
