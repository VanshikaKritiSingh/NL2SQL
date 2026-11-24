# routers/analysis.py
"""
Pre-flight analysis endpoints: cost estimate, security check, and change diff.

DA-17: These endpoints previously returned hardcoded mock telemetry for every
query_id. They now serve the real AnalysisPayload captured during the pipeline
run and stored alongside the query response, returning 404 for unknown IDs.
"""
from fastapi import APIRouter, HTTPException

from models.approval import CostEstimate, SecurityCheck, DiffData

router = APIRouter(tags=["Pre-flight Analysis"])


def _get_stored_or_404(query_id: str):
    """Fetch the stored QueryResponse for a query_id, or raise 404."""
    # Imported lazily to avoid a circular import (routers.query imports nothing
    # from routers.analysis, but both are mounted by main.py).
    from routers.query import stored_responses

    item = stored_responses.get(query_id)
    if item is None:
        raise HTTPException(
            status_code=404,
            detail=f"No execution plan found for query_id '{query_id}'.",
        )
    return item


def _payload_or_404(query_id: str):
    item = _get_stored_or_404(query_id)
    payload = getattr(item, "approval_payload", None)
    if not payload:
        raise HTTPException(
            status_code=404,
            detail=f"No pre-flight analysis available for query_id '{query_id}'.",
        )
    return payload


@router.get("/explain/{query_id}", response_model=CostEstimate)
async def get_explain_estimate(query_id: str):
    """Cost estimate captured during Stage 10 of the pipeline for this query."""
    payload = _payload_or_404(query_id)
    cost = payload.get("cost_estimate") if isinstance(payload, dict) else getattr(payload, "cost_estimate", None)
    if not cost:
        raise HTTPException(status_code=404, detail="Cost estimate unavailable for this query.")
    return cost


@router.get("/security-check/{query_id}", response_model=SecurityCheck)
async def get_security_check(query_id: str):
    """Deadlock / privilege flags captured during the pipeline for this query."""
    payload = _payload_or_404(query_id)
    security = payload.get("security_check") if isinstance(payload, dict) else getattr(payload, "security_check", None)
    if not security:
        raise HTTPException(status_code=404, detail="Security check unavailable for this query.")
    return security


@router.get("/diff/{query_id}", response_model=DiffData)
async def get_diff_preview(query_id: str):
    """DDL/DML change preview captured during the pipeline for this query."""
    payload = _payload_or_404(query_id)
    diff = payload.get("diff_data") if isinstance(payload, dict) else getattr(payload, "diff_data", None)
    if not diff:
        raise HTTPException(status_code=404, detail="Diff preview unavailable for this query.")
    return diff
