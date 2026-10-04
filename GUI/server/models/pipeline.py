# models/pipeline.py
from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any

PipelineStageStatus = Literal["pending", "started", "completed", "skipped", "error"]


class PipelineStageEvent(BaseModel):
    query_id: str
    stage_number: int          # 1-16
    stage_name: str
    status: PipelineStageStatus
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None   # stage-specific payload
