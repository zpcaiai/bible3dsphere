"""
MVFE API Routes
FastAPI router for the Formation Engine.
"""
import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mvfe", tags=["mvfe"])

# Module-level references (set during init)
_orchestrator = None
_db_pool = None
_prompt_engine = None


class ProcessRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    user_id: str = Field(default="default_user")


class StateRequest(BaseModel):
    user_id: str = Field(default="default_user")


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
        logger.error(f"[mvfe-api] process failed: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


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


@router.get("/health")
async def health_check():
    """MVFE health check."""
    return {
        "status": "ok",
        "orchestrator": _orchestrator is not None,
        "database": _db_pool is not None,
        "prompt_engine": _prompt_engine is not None,
    }
