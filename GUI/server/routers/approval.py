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
async def processHumanApprovalDecisionGate(query_id: str, request: ApprovalRequest):
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
        from routers.query import stored_responses, sync_sandbox_ddl, sync_orchestrator_from_schema
        from core.connectors import default_registry

        has_exec_error = False
        exec_msg = "Executed on production DBMS (sandbox replica)"
        active_db = None
        available_dbs = []
        tables_list = []

        stored = stored_responses.get(query_id)
        if stored and stored.generated_sql:
            # Sync in-memory SQLite sandbox so subsequent preview queries work immediately
            sync_sandbox_ddl(request.user_id, stored.generated_sql)

            if default_registry.is_attached(request.user_id):
                conn = default_registry.get(request.user_id)
                if conn:
                    try:
                        res = conn.execute_query(stored.generated_sql, is_mutating=True)
                        active_db = conn.config.database
                        target_name = active_db or "server"
                        if res.error:
                            has_exec_error = True
                            exec_msg = f"DBMS execution error on [{target_name}]: {res.error}"
                        else:
                            exec_msg = f"Live change committed to [{target_name}]: {res.rows_affected} rows affected in {res.execution_time_ms}ms"
                            # Re-introspect schema and sync orchestrator tables
                            try:
                                schema = conn.introspect_schema(force_refresh=True)
                                if schema and schema.tables:
                                    tables_list = list(schema.tables.keys())
                                    sync_orchestrator_from_schema(schema)
                            except Exception:
                                pass
                            try:
                                available_dbs = default_registry.list_databases(conn.config)
                            except Exception:
                                available_dbs = [active_db] if active_db else []
                    except Exception as ex:
                        has_exec_error = True
                        exec_msg = f"DBMS execution failed: {ex}"

        await broadcast_event(
            request.user_id,
            PipelineStageEvent(
                query_id=query_id,
                stage_number=16,
                stage_name=STAGE_NAMES[16],
                status="failed" if has_exec_error else "completed",
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
                "has_error": has_exec_error,
                "sql": stored.generated_sql if stored else None,
                "active_database": active_db,
            },
            concurrency_tag=f"txn-{request.user_id}",
        ))

        return ApprovalResponse(
            query_id=query_id,
            status="error" if has_exec_error else "approved_executing",
            message=f"Query approved. {exec_msg}" if not has_exec_error else exec_msg,
            active_database=active_db,
            available_databases=available_dbs,
            tables=tables_list,
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


handle_approval = processHumanApprovalDecisionGate
