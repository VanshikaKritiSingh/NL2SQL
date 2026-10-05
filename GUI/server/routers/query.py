# routers/query.py
import asyncio
from datetime import datetime
from typing import List, Dict
from fastapi import APIRouter, BackgroundTasks, HTTPException
from models.query import QueryRequest, QueryResponse, HistoryItem
from mock_data.queries import classify_and_generate_mock
from services.pipeline_stub import simulate_pipeline_run

router = APIRouter(prefix="/query", tags=["Query Intake"])

# In-memory history store: user_id -> List[HistoryItem]
query_history: Dict[str, List[HistoryItem]] = {}
stored_responses: Dict[str, QueryResponse] = {}


@router.post("", response_model=QueryResponse)
async def submit_query(request: QueryRequest, background_tasks: BackgroundTasks):
    """Query Intake entry point: Receives natural language query, triggers pipeline."""
    
    # 1. Generate appropriate mock response (SELECT, UPDATE, or DDL)
    response = classify_and_generate_mock(request.query_text, request.target_dialect.value)
    stored_responses[response.query_id] = response

    # 2. Record to history
    is_mutating = response.status == "approval_required"
    history_entry = HistoryItem(
        query_id=response.query_id,
        query_text=request.query_text,
        generated_sql=response.generated_sql,
        target_dialect=request.target_dialect.value,
        status=response.status,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        is_mutating=is_mutating,
    )
    if request.user_id not in query_history:
        query_history[request.user_id] = []
    query_history[request.user_id].insert(0, history_entry)

    # 3. Trigger WebSocket pipeline stage simulation in background
    background_tasks.add_task(
        simulate_pipeline_run,
        query_id=response.query_id,
        user_id=request.user_id,
        is_mutating=is_mutating,
        approval_payload=response.approval_payload,
        delay=0.15,
    )

    return response


@router.get("/history/{user_id}", response_model=List[HistoryItem])
async def get_user_history(user_id: str):
    """Returns query history for the given user."""
    return query_history.get(user_id, [])
