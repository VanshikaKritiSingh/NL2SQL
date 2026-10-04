# routers/approval.py
from fastapi import APIRouter, HTTPException
from models.approval import ApprovalRequest, ApprovalResponse
from services.pipeline_stub import broadcast_event, STAGE_NAMES
from models.pipeline import PipelineStageEvent
import asyncio

router = APIRouter(prefix="/approval", tags=["Human Approval Gate (M14)"])


@router.post("/{query_id}", response_model=ApprovalResponse)
async def handle_approval(query_id: str, request: ApprovalRequest):
    """Module 14 decision endpoint: Human approves or rejects a mutating/DDL query."""
    
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

        # Stage 16: Connected DBMS Dispatcher
        await broadcast_event(
            request.user_id,
            PipelineStageEvent(
                query_id=query_id,
                stage_number=16,
                stage_name=STAGE_NAMES[16],
                status="completed",
                message="Executed on production DBMS",
            ),
        )

        return ApprovalResponse(
            query_id=query_id,
            status="approved_executing",
            message="Query approved. Dolt transaction checkpointed and dispatched to DBMS.",
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

        return ApprovalResponse(
            query_id=query_id,
            status="rejected_retrying",
            message=f"Query rejected. Feedback forwarded to SQL generator (M6) for retry: '{request.feedback}'",
        )
