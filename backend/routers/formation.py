"""
formation.py — 统一成长闭环 API（整合层 Phase 0，前缀 /api/formation）
  GET  /timeline   成长时间轴（神的带领）
  GET  /state      当前画像（焦点 / 偶像 / 风险 / 各源计数）
  GET  /next       节律引擎：今日该做的一件事
  POST /event      通用事件写入（前端 / 各模块）
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

try:  # 兼容 backend.* 与顶层导入
    from backend import formation_events as fe
except Exception:  # pragma: no cover
    import formation_events as fe  # type: ignore

try:
    from backend import discernment_core as dc
except Exception:  # pragma: no cover
    import discernment_core as dc  # type: ignore

from core.deps import get_session_user

router = APIRouter(prefix="/api/formation", tags=["formation"])


def _require(request: Request) -> dict:
    user = get_session_user(request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


class EventBody(BaseModel):
    source: str = Field(min_length=1, max_length=40)
    event_type: str = Field(min_length=1, max_length=40)
    domain: Optional[str] = Field(default=None, max_length=60)
    title: Optional[str] = Field(default=None, max_length=300)
    summary: Optional[str] = None
    severity: Optional[str] = Field(default=None, max_length=10)
    refs: list = Field(default_factory=list)
    payload: dict = Field(default_factory=dict)
    ref_id: Optional[str] = Field(default=None, max_length=120)


class BaselineBody(BaseModel):
    text: str = Field(default="", max_length=8000)
    checkup: Optional[dict] = None  # {symptomKey: 0-10}（可选心灵体检）
    use_ai: Optional[bool] = None


@router.get("/timeline")
def get_timeline(request: Request, limit: int = Query(100, ge=1, le=500),
                 source: Optional[str] = Query(None, max_length=40),
                 type: Optional[str] = Query(None, max_length=40)) -> Any:
    email = _require(request)["email"]
    return {"ok": True, "events": fe.timeline(email, limit=limit, source=source, event_type=type)}


@router.get("/state")
def get_state(request: Request) -> Any:
    email = _require(request)["email"]
    return {"ok": True, "state": fe.growth_state(email)}


@router.get("/next")
def get_next(request: Request) -> Any:
    email = _require(request)["email"]
    return {"ok": True, "next": fe.next_step(email)}


@router.get("/curve")
def get_curve(request: Request, days: int = Query(90, ge=7, le=365),
              bucket: str = Query("week", max_length=8)) -> Any:
    email = _require(request)["email"]
    return {"ok": True, **fe.curve(email, days=days, bucket=bucket)}


@router.post("/event")
def post_event(request: Request, body: EventBody) -> Any:
    email = _require(request)["email"]
    eid = fe.record_event(email, body.source, body.event_type, domain=body.domain,
                          title=body.title, summary=body.summary, severity=body.severity,
                          refs=body.refs, payload=body.payload, ref_id=body.ref_id)
    return {"ok": True, "id": eid}


@router.post("/baseline")
def post_baseline(request: Request, body: BaselineBody) -> Any:
    """统一入门漏斗：一次基线诊断 → 写入事件并据当前画像生成个性化路径（plan）。"""
    email = _require(request)["email"]
    out: dict = {"ok": True}
    if (body.text or "").strip():
        try:
            out["diagnosis"] = dc.diagnose(email=email, lens="worldview", text=body.text,
                                           source_type="onboarding", use_ai=body.use_ai)
        except Exception as exc:  # pragma: no cover
            out["diagnosis"] = {"ok": False, "error": str(exc)}
    if body.checkup:
        try:
            out["checkup"] = dc.diagnose(email=email, lens="checkup", inputs=body.checkup,
                                         source_type="onboarding", use_ai=body.use_ai)
        except Exception as exc:  # pragma: no cover
            out["checkup"] = {"ok": False, "error": str(exc)}
    try:
        _sum = ((out.get("diagnosis") or {}).get("summary") or "")[:300] or "已完成入门基线"
        fe.record_event(email, "onboarding", "baseline", title="完成基线属灵诊断",
                        summary=_sum, severity="green", ref_id="baseline:%s" % email)
    except Exception:
        pass
    state = fe.growth_state(email)
    out["state"] = state
    out["plan"] = fe.next_step(email, state)
    return out
