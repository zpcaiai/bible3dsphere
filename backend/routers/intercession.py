"""
Intercession router — 代祷名单 / 代祷追踪 (/api/intercession)

为人、家庭、教会、事工、城市、国家、个人负担维护代祷名单：
  POST /api/intercession/targets            添加代祷对象
  GET  /api/intercession/targets            列出对象
  POST /api/intercession/requests           添加代祷事项（隐私 + 危机扫描）
  GET  /api/intercession/requests           列出事项（?status=）
  GET  /api/intercession/requests/{id}      详情（含更新与代祷记录）
  PATCH/api/intercession/requests/{id}      更新事项
  POST /api/intercession/requests/{id}/updates    添加进展
  POST /api/intercession/requests/{id}/answered   标记蒙应允
  POST /api/intercession/requests/{id}/pray       记录一次代祷
  GET  /api/intercession/today              今日建议代祷（紧急/到期/久未代祷优先）

隐私优先：默认 private；group/public 可见时提醒匿名化，不鼓励属灵八卦。
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/intercession", tags=["intercession"])

_state: Dict[str, Any] = {}

_TARGET_COLS = "id, email, target_type, display_name, relationship, privacy_level, notes, active, created_at"
_REQ_COLS = ("id, email, target_id, title, description, category, urgency, privacy_level, status, "
             "answered_summary, answered_at, next_pray_at, last_prayed_at, pray_count, created_at")

_PRIVACY_GROUP = {"group_visible", "public_anonymized"}


def init_intercession_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _privacy_warning(privacy_level: str, text: str) -> Optional[str]:
    if (privacy_level or "private") in _PRIVACY_GROUP and text and len(text.strip()) > 20:
        return "此事项设为群组/公开可见。请避免写出他人的隐私细节或可指认信息，建议匿名化（如「一位朋友」）。"
    return None


def _target_row(r, to_iso) -> dict:
    return {"id": r[0], "email": r[1], "target_type": r[2], "display_name": r[3],
            "relationship": r[4] or "", "privacy_level": r[5], "notes": r[6] or "",
            "active": bool(r[7]), "created_at": to_iso(r[8])}


def _req_row(r, to_iso) -> dict:
    return {"id": r[0], "email": r[1], "target_id": r[2] or "", "title": r[3],
            "description": r[4] or "", "category": r[5], "urgency": r[6],
            "privacy_level": r[7], "status": r[8], "answered_summary": r[9] or "",
            "answered_at": to_iso(r[10]) if r[10] else None,
            "next_pray_at": to_iso(r[11]) if r[11] else None,
            "last_prayed_at": to_iso(r[12]) if r[12] else None,
            "pray_count": r[13] or 0, "created_at": to_iso(r[14])}


# ── 对象 ──────────────────────────────────────────────────────────────────────

class TargetCreate(BaseModel):
    target_type: str = Field(default="person", max_length=24)
    display_name: str = Field(..., max_length=160)
    relationship: str = Field(default="", max_length=120)
    privacy_level: str = Field(default="private", max_length=24)
    notes: str = Field(default="", max_length=2000)


@router.post("/targets")
def create_target(request: Request, body: TargetCreate) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    tid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO intercession_targets (id, email, target_type, display_name, relationship, privacy_level, notes) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (tid, user["email"], body.target_type, body.display_name, body.relationship, body.privacy_level, body.notes),
            )
            conn.commit()
            cur.execute(f"SELECT {_TARGET_COLS} FROM intercession_targets WHERE id=%s", (tid,))
            row = cur.fetchone()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail="create failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "target": _target_row(row, to_iso)}


@router.get("/targets")
def list_targets(request: Request) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_TARGET_COLS} FROM intercession_targets WHERE email=%s AND active=TRUE "
                        "ORDER BY created_at DESC", (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "targets": [_target_row(r, to_iso) for r in rows]}


# ── 事项 ──────────────────────────────────────────────────────────────────────

class RequestCreate(BaseModel):
    target_id: str = Field(default="", max_length=64)
    title: str = Field(..., max_length=200)
    description: str = Field(default="", max_length=4000)
    category: str = Field(default="other", max_length=24)
    urgency: str = Field(default="normal", max_length=12)
    privacy_level: str = Field(default="private", max_length=24)


@router.post("/requests")
def create_request(request: Request, body: RequestCreate) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    rid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO intercession_requests "
                "(id, email, target_id, title, description, category, urgency, privacy_level, next_pray_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s, NOW())",
                (rid, user["email"], body.target_id, body.title, body.description,
                 body.category, body.urgency, body.privacy_level),
            )
            conn.commit()
            cur.execute(f"SELECT {_REQ_COLS} FROM intercession_requests WHERE id=%s", (rid,))
            row = cur.fetchone()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail="create failed")
    finally:
        _state["release_db"](conn)
    out = {"ok": True, "request": _req_row(row, to_iso)}
    pw = _privacy_warning(body.privacy_level, body.description)
    if pw:
        out["privacy_warning"] = pw
    try:
        from safety_scan import scan_crisis
        c = scan_crisis(body.description, body.title)
        if c:
            out["crisis"] = c
    except Exception:
        pass
    return out


@router.get("/requests")
def list_requests(request: Request, status: str = Query(default="active", max_length=12)) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if status == "all":
                cur.execute(f"SELECT {_REQ_COLS} FROM intercession_requests WHERE email=%s "
                            "ORDER BY created_at DESC", (user["email"],))
            else:
                cur.execute(f"SELECT {_REQ_COLS} FROM intercession_requests WHERE email=%s AND status=%s "
                            "ORDER BY created_at DESC", (user["email"], status))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "requests": [_req_row(r, to_iso) for r in rows]}


@router.get("/requests/{rid}")
def get_request(rid: str, request: Request) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_REQ_COLS} FROM intercession_requests WHERE id=%s AND email=%s", (rid, user["email"]))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="request not found")
            cur.execute("SELECT id, update_type, update_text, created_at FROM intercession_request_updates "
                        "WHERE request_id=%s ORDER BY created_at DESC LIMIT 50", (rid,))
            updates = [{"id": u[0], "update_type": u[1], "update_text": u[2] or "", "created_at": to_iso(u[3])} for u in cur.fetchall()]
            cur.execute("SELECT id, prayer_text, burden_before, burden_after, prayed_at FROM intercession_prayer_logs "
                        "WHERE request_id=%s ORDER BY prayed_at DESC LIMIT 50", (rid,))
            logs = [{"id": l[0], "prayer_text": l[1] or "", "burden_before": l[2], "burden_after": l[3], "prayed_at": to_iso(l[4])} for l in cur.fetchall()]
    except HTTPException:
        raise
    finally:
        _state["release_db"](conn)
    return {"ok": True, "request": _req_row(row, to_iso), "updates": updates, "prayer_logs": logs}


class RequestUpdate(BaseModel):
    status: Optional[str] = Field(default=None, max_length=12)
    urgency: Optional[str] = Field(default=None, max_length=12)
    title: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=4000)


@router.patch("/requests/{rid}")
def update_request(rid: str, request: Request, body: RequestUpdate) -> dict:
    user = _require_user(request)
    sets, params = [], []
    for col, val in (("status", body.status), ("urgency", body.urgency), ("title", body.title), ("description", body.description)):
        if val is not None:
            sets.append(f"{col}=%s"); params.append(val)
    if not sets:
        return {"ok": True, "unchanged": True}
    sets.append("updated_at=NOW()")
    params.extend([rid, user["email"]])
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE intercession_requests SET {', '.join(sets)} WHERE id=%s AND email=%s", tuple(params))
            conn.commit()
            n = cur.rowcount
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail="update failed")
    finally:
        _state["release_db"](conn)
    if not n:
        raise HTTPException(status_code=404, detail="request not found")
    return {"ok": True}


class UpdateCreate(BaseModel):
    update_type: str = Field(default="status_update", max_length=20)
    update_text: str = Field(..., max_length=4000)


@router.post("/requests/{rid}/updates")
def add_update(rid: str, request: Request, body: UpdateCreate) -> dict:
    user = _require_user(request)
    uid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM intercession_requests WHERE id=%s AND email=%s", (rid, user["email"]))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="request not found")
            cur.execute("INSERT INTO intercession_request_updates (id, email, request_id, update_type, update_text) "
                        "VALUES (%s,%s,%s,%s,%s)", (uid, user["email"], rid, body.update_type, body.update_text))
            cur.execute("UPDATE intercession_requests SET updated_at=NOW() WHERE id=%s", (rid,))
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail="update failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "id": uid}


class AnsweredBody(BaseModel):
    answered_summary: str = Field(default="", max_length=4000)


@router.post("/requests/{rid}/answered")
def mark_answered(rid: str, request: Request, body: AnsweredBody) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE intercession_requests SET status='answered', answered_summary=%s, "
                        "answered_at=NOW(), updated_at=NOW() WHERE id=%s AND email=%s",
                        (body.answered_summary, rid, user["email"]))
            if not cur.rowcount:
                raise HTTPException(status_code=404, detail="request not found")
            cur.execute("INSERT INTO intercession_request_updates (id, email, request_id, update_type, update_text) "
                        "VALUES (%s,%s,%s,'answered',%s)", (uuid.uuid4().hex, user["email"], rid, body.answered_summary))
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail="answered failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True}


class PrayBody(BaseModel):
    prayer_text: str = Field(default="", max_length=4000)
    burden_before: Optional[int] = Field(default=None, ge=0, le=10)
    burden_after: Optional[int] = Field(default=None, ge=0, le=10)
    next_in_days: int = Field(default=3, ge=0, le=90)


@router.post("/requests/{rid}/pray")
def pray(rid: str, request: Request, body: PrayBody) -> dict:
    user = _require_user(request)
    lid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM intercession_requests WHERE id=%s AND email=%s", (rid, user["email"]))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="request not found")
            cur.execute("INSERT INTO intercession_prayer_logs (id, email, request_id, prayer_text, burden_before, burden_after) "
                        "VALUES (%s,%s,%s,%s,%s,%s)", (lid, user["email"], rid, body.prayer_text, body.burden_before, body.burden_after))
            cur.execute("UPDATE intercession_requests SET pray_count=pray_count+1, last_prayed_at=NOW(), "
                        "next_pray_at = NOW() + (%s || ' days')::interval, updated_at=NOW() WHERE id=%s",
                        (str(body.next_in_days), rid))
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail="pray failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "id": lid}


@router.get("/today")
def today(request: Request, limit: int = Query(default=10, ge=1, le=50)) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_REQ_COLS} FROM intercession_requests WHERE email=%s AND status='active' "
                "ORDER BY (CASE urgency WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END), "
                "(CASE WHEN next_pray_at IS NULL OR next_pray_at <= NOW() THEN 0 ELSE 1 END), "
                "COALESCE(last_prayed_at, to_timestamp(0)) ASC LIMIT %s",
                (user["email"], limit),
            )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    items = []
    for r in rows:
        d = _req_row(r, to_iso)
        d["prayer_direction"] = "为他们求智慧、忍耐与基督的安慰；把结果交托给神，而非替神断定。"
        items.append(d)
    return {"ok": True, "requests": items}
