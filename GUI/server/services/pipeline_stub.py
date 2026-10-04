# services/pipeline_stub.py
import asyncio
import json
from typing import Dict, Optional
from fastapi import WebSocket
from models.pipeline import PipelineStageEvent

# In-memory registry of active WebSocket connections: user_id -> WebSocket
active_connections: Dict[str, WebSocket] = {}

STAGE_NAMES = {
    1: "Natural Language Query Intake",
    2: "Per-User Rate Limiter",
    3: "Independent Observability Store & Audit Logger",
    4: "Semantic Cache",
    5: "RAG-Based Schema Linker",
    6: "Deep Learning SQL Generator",
    7: "Parameterized Query Sanitizer",
    8: "Multi-Dialect Converter & Normalizer",
    9: "Static Validator & Anti-Pattern Detector",
    10: "EXPLAIN-Style Cost Estimator",
    11: "Deadlock, Concurrency & Security Checker",
    12: "Dual-Path Execution Router",
    13: "Read-Only Sandbox Replica",
    14: "ER Diagram Visualizer & Human Approval Gate",
    15: "Transaction Wrapper & CAS Checkpoint (Dolt)",
    16: "Connected DBMS Dispatcher & Response Formatter",
}


async def register_connection(user_id: str, websocket: WebSocket):
    active_connections[user_id] = websocket


async def unregister_connection(user_id: str):
    if user_id in active_connections:
        del active_connections[user_id]


async def broadcast_event(user_id: str, event: PipelineStageEvent):
    ws = active_connections.get(user_id)
    if ws:
        try:
            await ws.send_text(json.dumps(event.model_dump()))
        except Exception:
            await unregister_connection(user_id)


async def simulate_pipeline_run(
    query_id: str,
    user_id: str,
    is_mutating: bool,
    approval_payload: Optional[dict] = None,
    delay: float = 0.2,
):
    """Simulates pipeline execution stage-by-stage with WebSocket events."""
    
    # Common stages 1 to 12
    for stage_num in range(1, 13):
        stage_name = STAGE_NAMES[stage_num]
        
        # Stage started
        await broadcast_event(
            user_id,
            PipelineStageEvent(
                query_id=query_id,
                stage_number=stage_num,
                stage_name=stage_name,
                status="started",
                message=f"Executing {stage_name}...",
            ),
        )
        await asyncio.sleep(delay)

        # Stage completed
        msg = "OK"
        if stage_num == 4:
            msg = "Cache miss — proceeding to generation"
        elif stage_num == 5:
            msg = "Linked 3 tables via Steiner Minimal Tree"
        elif stage_num == 8:
            msg = "Normalized SQL AST via sqlglot"
        elif stage_num == 10:
            msg = "Cost estimated via EXPLAIN dry-run"
        elif stage_num == 12:
            msg = "Mutating query routed to Approval Gate" if is_mutating else "Read-only query routed to Sandbox"

        await broadcast_event(
            user_id,
            PipelineStageEvent(
                query_id=query_id,
                stage_number=stage_num,
                stage_name=stage_name,
                status="completed",
                message=msg,
            ),
        )

    if not is_mutating:
        # Read-only path: Stage 13 (Sandbox Replica) -> Stage 16 (Dispatcher)
        for stage_num in [13, 16]:
            stage_name = STAGE_NAMES[stage_num]
            await broadcast_event(
                user_id,
                PipelineStageEvent(
                    query_id=query_id,
                    stage_number=stage_num,
                    stage_name=stage_name,
                    status="started",
                    message=f"Executing {stage_name}...",
                ),
            )
            await asyncio.sleep(delay)
            await broadcast_event(
                user_id,
                PipelineStageEvent(
                    query_id=query_id,
                    stage_number=stage_num,
                    stage_name=stage_name,
                    status="completed",
                    message="Query executed successfully",
                ),
            )
    else:
        # Mutating path: Halts at Stage 14 for human approval
        await broadcast_event(
            user_id,
            PipelineStageEvent(
                query_id=query_id,
                stage_number=14,
                stage_name=STAGE_NAMES[14],
                status="started",
                message="Awaiting human approval before database execution",
                data={"approval_payload": approval_payload},
            ),
        )
