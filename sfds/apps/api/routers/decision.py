"""
Decision Router — orchestration gateway for SFDS analysis pipeline.
All business logic lives in services/core-engine.
"""

from fastapi import APIRouter, Depends, HTTPException
from packages.shared_types.decision import DecisionRequest
from services.core_engine.engine import CoreEngine, get_core_engine

router = APIRouter()


@router.post("/create", response_model=dict)
async def create_decision(
    req: DecisionRequest,
    engine: CoreEngine = Depends(get_core_engine),
):
    """
    Create and analyze a decision.
    Runs full 5-layer SFDS pipeline: semantic → graph → temporal → reasoning → formation.
    """
    try:
        result = await engine.analyze(req)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/analyze", response_model=dict)
async def analyze_decision(
    req: DecisionRequest,
    engine: CoreEngine = Depends(get_core_engine),
):
    """
    Re-analyze an existing decision (e.g. after user adds reflection notes).
    """
    try:
        result = await engine.analyze(req)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{decision_id}/confirm")
async def confirm_decision(
    decision_id: str,
    engine: CoreEngine = Depends(get_core_engine),
):
    """
    Mark decision as confirmed — triggers write-back to all persistence layers.
    """
    try:
        await engine.write_back(decision_id)
        return {"decision_id": decision_id, "status": "confirmed"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
