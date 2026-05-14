"""
MVFE API Routes
FastAPI router for the Formation Engine.
"""
import asyncio
import logging
from typing import Optional, Union

from fastapi import APIRouter, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mvfe", tags=["mvfe"])

# Module-level references (set during init)
_orchestrator = None
_db_pool = None
_prompt_engine = None


class ProcessRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    user_id: Union[str, int] = Field(default="default_user")


class StateRequest(BaseModel):
    user_id: Union[str, int] = Field(default="default_user")


if hasattr(router, "exception_handler"):
    @router.exception_handler(RequestValidationError)
    async def mvfe_validation_handler(request: Request, exc: RequestValidationError):
        body = exc.body if hasattr(exc, 'body') else 'unknown'
        logger.error(f"[mvfe-api] 422 validation error: {exc.errors()} body={body}")
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "body": str(body)}
        )


def init_mvfe_router(orchestrator, db_pool, prompt_engine):
    """Initialize the router with dependencies."""
    global _orchestrator, _db_pool, _prompt_engine
    _orchestrator = orchestrator
    _db_pool = db_pool
    _prompt_engine = prompt_engine
    logger.info("[mvfe-api] router initialized")


@router.post("/process")
async def process_input(req: ProcessRequest):
    """
    Main MVFE pipeline endpoint.
    Flow: input → emotion → attention → decision → memory → graph → formation → reflection → persist
    """
    if not _orchestrator:
        raise HTTPException(status_code=503, detail="MVFE not initialized")

    try:
        result = await asyncio.to_thread(
            _orchestrator.process, req.user_id, req.text
        )
        return result.to_dict()
    except Exception as e:
        import traceback
        logger.error(f"[mvfe-api] process failed: {type(e).__name__}: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {type(e).__name__}: {str(e)[:200]}")


@router.get("/state/{user_id}")
async def get_state(user_id: str):
    """Get current formation state for a user."""
    if not _db_pool:
        raise HTTPException(status_code=503, detail="MVFE database not available")

    from ..db.postgres import get_formation_state
    try:
        state = await asyncio.to_thread(get_formation_state, _db_pool, user_id)
        if not state:
            return {"user_id": user_id, "state": None, "message": "No formation data yet"}
        return {"user_id": user_id, "state": state}
    except Exception as e:
        logger.error(f"[mvfe-api] get_state failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{user_id}")
async def get_history(user_id: str, limit: int = 20):
    """Get event history for a user."""
    if not _db_pool:
        raise HTTPException(status_code=503, detail="MVFE database not available")

    from ..db.postgres import get_events_history
    try:
        events = await asyncio.to_thread(get_events_history, _db_pool, user_id, limit)
        return {"user_id": user_id, "events": events, "count": len(events)}
    except Exception as e:
        logger.error(f"[mvfe-api] get_history failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drift/{user_id}")
async def get_drift_metrics(user_id: str):
    """Get prompt drift metrics for a user."""
    if not _prompt_engine:
        return {"user_id": user_id, "drift": None, "message": "Prompt engine not active"}
    return {
        "user_id": user_id,
        "message": "Drift is computed per-process cycle. Check /process response for real-time drift.",
    }


@router.get("/dashboard/state")
async def get_dashboard_state(user_id: str = "default_user", hours: int = 168):
    """
    MVFE Runtime Dashboard — full time-series aggregation.
    Returns: emotion_series, attention_map, decision_flow, formation_curve
    """
    if not _db_pool:
        # Return mock data for dashboard preview when DB unavailable
        return _mock_dashboard_data()

    from ..db.postgres import get_dashboard_data
    try:
        data = await asyncio.to_thread(get_dashboard_data, _db_pool, user_id, hours)
        # If no real data, provide mock for preview
        if data["data_points"] == 0:
            return {**_mock_dashboard_data(), "is_mock": True}
        return data
    except Exception as e:
        logger.error(f"[mvfe-api] dashboard/state failed: {e}")
        return {**_mock_dashboard_data(), "is_mock": True, "error": str(e)}


def _mock_dashboard_data():
    """Synthetic data for dashboard preview."""
    import datetime
    now = datetime.datetime.utcnow()
    emotions = [
        {"timestamp": (now - datetime.timedelta(hours=168)).isoformat(), "primary_emotion": "anxiety", "intensity": 0.7, "uncertainty": 0.3},
        {"timestamp": (now - datetime.timedelta(hours=120)).isoformat(), "primary_emotion": "sadness", "intensity": 0.5, "uncertainty": 0.4},
        {"timestamp": (now - datetime.timedelta(hours=72)).isoformat(), "primary_emotion": "peace", "intensity": 0.6, "uncertainty": 0.2},
        {"timestamp": (now - datetime.timedelta(hours=48)).isoformat(), "primary_emotion": "hope", "intensity": 0.55, "uncertainty": 0.35},
        {"timestamp": (now - datetime.timedelta(hours=24)).isoformat(), "primary_emotion": "anxiety", "intensity": 0.65, "uncertainty": 0.3},
        {"timestamp": now.isoformat(), "primary_emotion": "peace", "intensity": 0.4, "uncertainty": 0.5},
    ]
    formation = [
        {"timestamp": e["timestamp"], "formation_score": 0.45 + i * 0.05, "drift_score": 0.1 + (i % 3) * 0.08}
        for i, e in enumerate(emotions)
    ]
    return {
        "emotion_series": emotions,
        "attention_map": {"career": 0.35, "relationship": 0.25, "finance": 0.2, "spirituality": 0.1, "health": 0.1},
        "decision_flow": [
            {"timestamp": emotions[0]["timestamp"], "type": "avoidance", "confidence": 0.6},
            {"timestamp": emotions[1]["timestamp"], "type": "avoidance", "confidence": 0.5},
            {"timestamp": emotions[2]["timestamp"], "type": "approach", "confidence": 0.4},
            {"timestamp": emotions[3]["timestamp"], "type": "approach", "confidence": 0.55},
            {"timestamp": emotions[4]["timestamp"], "type": "avoidance", "confidence": 0.7},
            {"timestamp": emotions[5]["timestamp"], "type": "approach", "confidence": 0.45},
        ],
        "formation_curve": formation,
        "data_points": len(emotions),
    }


@router.get("/health")
async def health_check():
    """MVFE health check."""
    return {
        "status": "ok",
        "orchestrator": _orchestrator is not None,
        "database": _db_pool is not None,
        "prompt_engine": _prompt_engine is not None,
    }
