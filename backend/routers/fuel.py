"""Fuel router — 养料库（按困扰组织） (/api/fuel). 无 DB；内容性接口。"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query

try:
    from backend import fuel_engine as engine
except Exception:  # pragma: no cover
    import fuel_engine as engine  # type: ignore
try:
    from backend.core.config import settings as _settings
except Exception:  # pragma: no cover
    try:
        from core.config import settings as _settings
    except Exception:
        _settings = None

router = APIRouter(prefix="/api/fuel", tags=["fuel"])
_state: Dict[str, Any] = {}


def init_fuel_router(**kwargs) -> None:
    _state.update(kwargs)


@router.get("/meta")
def get_meta() -> dict:
    return {"ok": True, **engine.meta()}


@router.get("/pack/{key}")
def get_pack(key: str, ai: int = Query(default=0)) -> dict:
    p = engine.assemble(key, settings=_settings, use_ai=bool(ai))
    if not p:
        raise HTTPException(status_code=404, detail="struggle not found")
    return {"ok": True, "pack": p}
