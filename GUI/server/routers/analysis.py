# routers/analysis.py
from fastapi import APIRouter, HTTPException
from models.approval import CostEstimate, SecurityCheck, DiffData
from mock_data.telemetry import get_mock_update_telemetry
from mock_data.diffs import get_mock_dml_diff

router = APIRouter(tags=["Pre-flight Analysis"])


@router.get("/explain/{query_id}", response_model=CostEstimate)
async def get_explain_estimate(query_id: str):
    """Cost Estimator integration: EXPLAIN cost estimate."""
    cost, _ = get_mock_update_telemetry()
    return cost


@router.get("/security-check/{query_id}", response_model=SecurityCheck)
async def get_security_check(query_id: str):
    """Security check integration: Deadlock & concurrency flags."""
    _, security = get_mock_update_telemetry()
    return security


@router.get("/diff/{query_id}", response_model=DiffData)
async def get_diff_preview(query_id: str):
    """Module 15 integration: Dolt DDL/DML diff preview."""
    return get_mock_dml_diff()
