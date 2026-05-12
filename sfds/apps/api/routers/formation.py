"""
Formation Router — Layer 5: long-term character trajectory API.
"""

from fastapi import APIRouter, Depends, HTTPException
from services.formation_engine.engine import FormationEngine, get_formation_engine

router = APIRouter()


@router.get("/profile/{user_id}")
async def get_formation_profile(
    user_id: str,
    engine: FormationEngine = Depends(get_formation_engine),
):
    """
    Return the accumulated 8-dimension FormationStateVector for a user.
    Includes trajectory direction, dominant loop, drift analysis.
    """
    try:
        return await engine.get_profile(user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/state/{user_id}")
async def get_formation_state(
    user_id: str,
    engine: FormationEngine = Depends(get_formation_engine),
):
    """
    Lightweight formation state — returns just the 8-dimension vector.
    """
    try:
        profile = await engine.get_profile(user_id)
        return {
            "user_id":      user_id,
            "state_vector": profile.get("state_vector", {}),
            "formation_arc":profile.get("formation_arc", "unknown"),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/dimensions")
async def get_formation_dimensions():
    """
    Returns metadata for all 8 formation dimensions.
    Used by frontend Formation Profile UI renderer.
    """
    from services.formation_engine.dimensions import DIMENSION_METADATA
    return {
        "schema": "v3.1",
        "dimensions": DIMENSION_METADATA,
        "note": (
            "Formation dimensions describe tendencies, not identities. "
            "All values are trajectory signals, not moral scores."
        ),
    }
