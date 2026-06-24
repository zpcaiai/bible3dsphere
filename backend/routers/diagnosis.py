"""
Unified Diagnosis router — 统一诊断面 (/api/diagnosis)

  GET /api/diagnosis/meta                引擎说明
  GET /api/diagnosis/sessions            本人诊断 session 列表（可按 engine 过滤）
  GET /api/diagnosis/findings            本人诊断发现列表（可按 category 过滤）
  GET /api/diagnosis/latest              最近一次 session + 其 findings

只读聚合层。诊断由既有引擎（gospel/checkup/...）经 diagnosis_hub 适配写入。
按 email 严格隔离。init 时同时注入 diagnosis_hub 的 DB 访问器。
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter(prefix="/api/diagnosis", tags=["diagnosis"])
_state: Dict[str, Any] = {}


def init_diagnosis_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())
    # 让适配层共享同一套 DB 访问器（生产环境的注入点）
    try:
        from diagnosis_hub import init_diagnosis_hub
        init_diagnosis_hub(get_db, release_db)
    except Exception:
        try:
            from backend.diagnosis_hub import init_diagnosis_hub
            init_diagnosis_hub(get_db, release_db)
        except Exception:
            pass


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@router.get("/meta")
def get_meta() -> dict:
    return {"ok": True, "engines": ["gospel", "checkup", "disciple", "worldview"],
            "risk_levels": ["low", "medium", "high", "critical"]}


@router.get("/sessions")
def sessions(request: Request, engine: Optional[str] = Query(default=None),
             limit: int = Query(default=20, ge=1, le=100)) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if engine:
                cur.execute(
                    "SELECT id, source_engine, primary_theme, risk_level, summary, created_at "
                    "FROM diagnostic_sessions WHERE email=%s AND source_engine=%s "
                    "ORDER BY created_at DESC LIMIT %s", (user["email"], engine, limit))
            else:
                cur.execute(
                    "SELECT id, source_engine, primary_theme, risk_level, summary, created_at "
                    "FROM diagnostic_sessions WHERE email=%s "
                    "ORDER BY created_at DESC LIMIT %s", (user["email"], limit))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    items = [{"id": r[0], "source_engine": r[1], "primary_theme": r[2], "risk_level": r[3],
              "summary": r[4], "created_at": to_iso(r[5])} for r in rows]
    return {"ok": True, "count": len(items), "items": items}


@router.get("/findings")
def findings(request: Request, category: Optional[str] = Query(default=None),
             limit: int = Query(default=50, ge=1, le=200)) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if category:
                cur.execute(
                    "SELECT id, session_id, category, finding_type, title, description, "
                    "gospel_truth, scripture_anchors, severity, risk_level, created_at "
                    "FROM diagnostic_findings WHERE email=%s AND category=%s "
                    "ORDER BY created_at DESC LIMIT %s", (user["email"], category, limit))
            else:
                cur.execute(
                    "SELECT id, session_id, category, finding_type, title, description, "
                    "gospel_truth, scripture_anchors, severity, risk_level, created_at "
                    "FROM diagnostic_findings WHERE email=%s "
                    "ORDER BY created_at DESC LIMIT %s", (user["email"], limit))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    items = [{"id": r[0], "session_id": r[1], "category": r[2], "finding_type": r[3],
              "title": r[4], "description": r[5], "gospel_truth": r[6],
              "scripture_anchors": r[7], "severity": r[8], "risk_level": r[9],
              "created_at": to_iso(r[10])} for r in rows]
    return {"ok": True, "count": len(items), "items": items}


@router.get("/latest")
def latest(request: Request) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, source_engine, primary_theme, risk_level, summary, created_at "
                "FROM diagnostic_sessions WHERE email=%s ORDER BY created_at DESC LIMIT 1",
                (user["email"],))
            s = cur.fetchone()
            if not s:
                return {"ok": True, "session": None, "findings": []}
            cur.execute(
                "SELECT category, finding_type, title, description, gospel_truth, "
                "scripture_anchors, severity, risk_level FROM diagnostic_findings "
                "WHERE session_id=%s ORDER BY severity DESC NULLS LAST", (s[0],))
            fr = cur.fetchall()
    finally:
        _state["release_db"](conn)
    session = {"id": s[0], "source_engine": s[1], "primary_theme": s[2], "risk_level": s[3],
               "summary": s[4], "created_at": to_iso(s[5])}
    flist = [{"category": r[0], "finding_type": r[1], "title": r[2], "description": r[3],
              "gospel_truth": r[4], "scripture_anchors": r[5], "severity": r[6],
              "risk_level": r[7]} for r in fr]
    return {"ok": True, "session": session, "findings": flist}
