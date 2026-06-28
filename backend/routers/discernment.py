"""
discernment.py — 统一辨识内核 API（收敛层，前缀 /api/discernment）
  GET  /meta       可用透镜（lenses）
  POST /diagnose   统一诊断入口：{ lens, text, inputs?, use_ai? } → 归一化结果 + 写入成长事件
本路由不替换 /api/worldview、/api/gospel、/api/strongholds 等既有端点（仍可独立使用）。
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

try:
    from backend import discernment_core as dc
except Exception:  # pragma: no cover
    import discernment_core as dc  # type: ignore

from core.deps import get_session_user

router = APIRouter(prefix="/api/discernment", tags=["discernment"])


def _require(request: Request) -> dict:
    user = get_session_user(request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


class DiagnoseBody(BaseModel):
    lens: str = Field(default="worldview", max_length=20)
    text: str = Field(default="", max_length=8000)
    inputs: Optional[dict] = None
    source_type: str = Field(default="journal", max_length=40)
    locale: str = Field(default="zh-CN", max_length=16)
    use_ai: Optional[bool] = None


@router.get("/meta")
def get_meta() -> Any:
    return {"ok": True, **dc.meta()}


@router.post("/diagnose")
def post_diagnose(request: Request, body: DiagnoseBody) -> Any:
    email = _require(request)["email"]
    return dc.diagnose(email=email, lens=body.lens, text=body.text, inputs=body.inputs,
                       source_type=body.source_type, locale=body.locale, use_ai=body.use_ai)
