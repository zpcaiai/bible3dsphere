"""Virtues router — 信望爱星系 / Faith-Hope-Love (/api/virtues). 无 DB；按八维评估。"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

try:
    from backend import virtues_engine as engine
except Exception:  # pragma: no cover
    import virtues_engine as engine  # type: ignore
try:
    from backend.core.config import settings as _settings
except Exception:  # pragma: no cover
    try:
        from core.config import settings as _settings
    except Exception:
        _settings = None

router = APIRouter(prefix="/api/virtues", tags=["virtues"])
_state: Dict[str, Any] = {}


def init_virtues_router(*, get_session_user) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


class EvalBody(BaseModel):
    state_vector: Dict[str, float] = Field(default_factory=dict)
    use_ai: bool = True


@router.post("/evaluate")
def evaluate(request: Request, body: EvalBody) -> dict:
    _require_user(request)
    result = engine.analyze(body.state_vector, settings=_settings, use_ai=body.use_ai)
    return {"ok": True, **result}
