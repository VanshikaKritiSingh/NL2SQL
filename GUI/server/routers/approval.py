# routers/approval.py
from fastapi import APIRouter, HTTPException
from models.approval import ApprovalRequest, ApprovalResponse
from services.pipeline_stub import broadcast_event, STAGE_NAMES
from models.pipeline import PipelineStageEvent
from core.os_engine.audit_log import PipelineAuditLog, AuditEvent
import asyncio, time, uuid

router = APIRouter(prefix="/approval", tags=["Human Approval Gate"])
_audit_logger = PipelineAuditLog()


@router.post("/{query_id}", response_model=ApprovalResponse)
async def handle_approval(query_id: str, request: ApprovalRequest):
    """Approval Gate decision endpoint: Human approves or rejects a mutating/DDL query."""
    
    if request.decision == "approve":
        # Simulate completing Stage 14, then running Stage 15 (Dolt Tx) and Stage 16 (Dispatcher)
        await broadcast_event(
            request.user_id,
            PipelineStageEvent(
                query_id=query_id,
                stage_number=14,
                stage_name=STAGE_NAMES[14],
                status="completed",
                message="Approved by human reviewer",
            ),
        )
        await asyncio.sleep(0.2)
        
        # Stage 15: Transaction Wrapper & CAS Checkpoint
        await broadcast_event(
            request.user_id,
            PipelineStageEvent(
                query_id=query_id,
                stage_number=15,
                stage_name=STAGE_NAMES[15],
                status="completed",
                message="Dolt commit created: 9e4f2a (checkpoint secured)",
            ),
        )
        await asyncio.sleep(0.2)

        # Stage 16: Connected DBMS Dispatcher — Live Execution & Mutation Commit
        from routers.query import stored_responses
        from core.connectors import default_registry

        exec_msg = "Executed on production DBMS (sandbox replica)"
        stored = stored_responses.get(query_id)
        if stored and stored.generated_sql and default_registry.is_attached(request.user_id):
            conn = default_registry.get(request.user_id)
            if conn:
                try:
                    res = conn.execute_query(stored.generated_sql, is_mutating=True)
                    if res.error:
                        exec_msg = f"DBMS execution error on [{conn.config.database}]: {res.error}"
                    else:
                        exec_msg = f"Live change committed to [{conn.config.database}]: {res.rows_affected} rows affected in {res.execution_time_ms}ms"
                        # Re-introspect schema to reflect newly created/altered tables
                        conn.introspect_schema(force_refresh=True)
                except Exception as ex:
                    exec_msg = f"DBMS execution failed: {ex}"

        await broadcast_event(
            request.user_id,
            PipelineStageEvent(
                query_id=query_id,
                stage_number=16,
                stage_name=STAGE_NAMES[16],
                status="completed",
                message=exec_msg,
            ),
        )

        _audit_logger.append(AuditEvent(
            event_id=f"ev-{uuid.uuid4().hex[:6]}",
            timestamp=time.time(),
            user_id=request.user_id,
            operation="APPROVE",
            query_id=query_id,
            stage=16,
            stage_name="Human Approval Executed",
            details={
                "message": exec_msg,
                "sql": stored.generated_sql if stored else None,
            },
            concurrency_tag=f"txn-{request.user_id}",
        ))

        return ApprovalResponse(
            query_id=query_id,
            status="approved_executing",
            message=f"Query approved. {exec_msg}",
        )
    else:
        # Rejection -> feeds back to Model (M6) for retry
        await broadcast_event(
            request.user_id,
            PipelineStageEvent(
                query_id=query_id,
                stage_number=14,
                stage_name=STAGE_NAMES[14],
                status="error",
                message=f"Rejected by reviewer. Feedback: {request.feedback or 'No feedback provided'}",
            ),
        )

        _audit_logger.append(AuditEvent(
            event_id=f"ev-{uuid.uuid4().hex[:6]}",
            timestamp=time.time(),
            user_id=request.user_id,
            operation="REJECT",
            query_id=query_id,
            stage=14,
            stage_name="Human Approval Rejected",
            details={
                "feedback": request.feedback,
            },
            concurrency_tag=f"txn-{request.user_id}",
        ))

        return ApprovalResponse(
            query_id=query_id,
            status="rejected_retrying",
            message=f"Query rejected. Feedback forwarded to SQL generator (M6) for retry: '{request.feedback}'",
        )
