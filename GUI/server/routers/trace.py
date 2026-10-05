# GUI/server/routers/trace.py
import os
import sys
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.pipeline_trace import execute_pipeline_trace

router = APIRouter(prefix="/pipeline", tags=["Pipeline Tracing & Stepper"])


class TraceRequest(BaseModel):
    query_text: str
    target_dialect: Optional[str] = "postgres"


@router.post("/trace")
async def get_pipeline_step_trace(request: TraceRequest):
    """Executes full step-by-step pipeline trace for visualization."""
    return execute_pipeline_trace(request.query_text)
