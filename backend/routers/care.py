"""
Care router — 小组长关怀面板 (/api/care)   Advanced Batch · Module 3

  GET  /api/care/meta                                  动作类型 + 边界说明
  GET  /api/care/groups/{church_id}/care-dashboard     关怀信号面板（仅授权摘要）
  POST /api/care/groups/{church_id}/signals            手动登记一条关怀信号
  POST /api/care/signals/{signal_id}/actions           记录一次关怀行动
  POST /api/care/signals/{signal_id}/resolve           标记信号已跟进

边界：只有 group_leader / pastor / owner / admin 可访问；只能访问自己负责的小组；
面板不显示私密日志全文、未授权诊断、属灵分数或排名；所有查看与行动写 audit_logs。
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

try:
    from backend import care_engine as ce  # type: ignore
except Exception:  # pragma: no cover
    import care_engine as ce  # type: ignore

router = APIRouter(prefix="/api/care", tags=["care"])
_state: Dict[str, Any] = {}


def init_care_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _ip(request: Request) -> str:
    try:
        return request.client.host if request.client else ""
    except Exception:
        return ""


class SignalBody(BaseModel):
    email: str = Field(max_length=255)               # member the signal is about
    signal_type: str = Field(max_length=40)
    signal_level: str = Field(default="low", max_length=12)
    title: str = Field(max_length=200)
    summary: str = Field(max_length=2000)
    suggested_action: str = Field(default="", max_length=500)
    consent_share: bool = True
    visible_to_pastor: bool = False
    requires_followup: bool = False


class ActionBody(BaseModel):
    action_type: str = Field(max_length=30)
    action_note: str = Field(default="", max_length=2000)
    followup_date: Optional[str] = Field(default=None, max_length=10)


@router.get("/meta")
def meta() -> dict:
    return {
        "ok": True,
        "action_types": sorted(ce.ACTION_TYPES),
        "care_roles": sorted(ce.CARE_ROLES),
        "high_touch_notice": ce.HIGH_TOUCH_NOTICE,
        "boundaries": [
            "AI 不是牧者，面板只提供关怀信号，不替代真实关怀。",
            "不显示私密日志全文、未授权诊断、属灵分数或排名。",
            "只显示成员授权的摘要或危机升级信号。",
        ],
    }


def _role_or_403(cur, email: str, church_id: int) -> str:
    role = ce.member_role(cur, email, church_id)
    if not ce.can_view_care(role):
        raise HTTPException(status_code=403, detail="Not authorized for this group's care dashboard")
    return role


@router.get("/groups/{church_id}/care-dashboard")
def care_dashboard(church_id: int, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            role = _role_or_403(cur, user["email"], church_id)
            payload = ce.build_dashboard(cur, church_id, role, to_iso=_state["to_shanghai_iso"])
            ce.write_audit(cur, actor_email=user["email"], action="care_dashboard.view",
                           resource_type="church", resource_id=str(church_id), church_id=church_id,
                           detail={"items": len(payload["items"]), "role": role}, ip=_ip(request))
        conn.commit()
        return {"ok": True, **payload}
    finally:
        _state["release_db"](conn)


@router.post("/groups/{church_id}/signals")
def create_signal(church_id: int, body: SignalBody, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            role = _role_or_403(cur, user["email"], church_id)
            sid = ce.create_signal(
                cur, email=body.email, church_id=church_id, signal_type=body.signal_type,
                signal_level=body.signal_level, title=body.title, summary=body.summary,
                suggested_action=body.suggested_action, source_type="manual",
                source_id=user["email"], consent_share=body.consent_share,
                visible_to_group_leader=True, visible_to_pastor=body.visible_to_pastor,
                requires_followup=body.requires_followup,
            )
            ce.write_audit(cur, actor_email=user["email"], action="care_signal.create",
                           subject_email=body.email, resource_type="care_signal", resource_id=sid,
                           church_id=church_id, detail={"type": body.signal_type, "role": role},
                           ip=_ip(request))
        conn.commit()
        return {"ok": True, "signal_id": sid}
    finally:
        _state["release_db"](conn)


def _load_signal(cur, signal_id: str):
    cur.execute("SELECT email, church_id FROM care_signals WHERE id=%s", (signal_id,))
    return cur.fetchone()


@router.post("/signals/{signal_id}/actions")
def add_action(signal_id: str, body: ActionBody, request: Request) -> dict:
    user = _require_user(request)
    if body.action_type not in ce.ACTION_TYPES:
        raise HTTPException(status_code=400, detail="invalid action_type")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            sig = _load_signal(cur, signal_id)
            if not sig:
                raise HTTPException(status_code=404, detail="signal not found")
            target_email, church_id = sig
            _role_or_403(cur, user["email"], church_id)
            aid = ce.record_action(
                cur, care_signal_id=signal_id, actor_email=user["email"],
                target_email=target_email, church_id=church_id, action_type=body.action_type,
                action_note=body.action_note, followup_date=body.followup_date or None,
            )
            ce.write_audit(cur, actor_email=user["email"], action="care_action.create",
                           subject_email=target_email, resource_type="care_action", resource_id=aid,
                           church_id=church_id, detail={"action": body.action_type}, ip=_ip(request))
        conn.commit()
        return {"ok": True, "action_id": aid}
    finally:
        _state["release_db"](conn)


@router.post("/signals/{signal_id}/resolve")
def resolve(signal_id: str, request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            sig = _load_signal(cur, signal_id)
            if not sig:
                raise HTTPException(status_code=404, detail="signal not found")
            target_email, church_id = sig
            _role_or_403(cur, user["email"], church_id)
            ce.resolve_signal(cur, signal_id, user["email"])
            ce.write_audit(cur, actor_email=user["email"], action="care_signal.resolve",
                           subject_email=target_email, resource_type="care_signal",
                           resource_id=signal_id, church_id=church_id, ip=_ip(request))
        conn.commit()
        return {"ok": True, "resolved": True}
    finally:
        _state["release_db"](conn)
