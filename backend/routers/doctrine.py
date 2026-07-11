"""
Doctrine Learning Path router — 教义学习路径 (/api/doctrine)

  GET  /api/doctrine/topics            教义主题库（?area=&difficulty=）
  GET  /api/doctrine/topics/{key}      单个主题
  GET  /api/doctrine/paths             学习路径
  POST /api/doctrine/recommend         按目标/挣扎推荐路径
  POST /api/doctrine/progress          更新学习进度
  GET  /api/doctrine/progress          我的进度
  POST /api/doctrine/reflections       写反思

区分经文/教义/传统/应用;有争议教义给多视角与传统注记;教义连接到成长操练。email 标识用户。
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/doctrine", tags=["doctrine"])

_state: Dict[str, Any] = {}

_GOAL_PATH = [
    (["新信", "初信", "new", "信主"], "new_believer_core"),
    (["羞耻", "表现", "不配", "shame", "称义"], "shame_to_grace"),
    (["圣洁", "成圣", "holiness", "圣灵"], "holiness_and_spirit"),
    (["苦难", "受苦", "盼望", "suffering"], "suffering_and_hope"),
    (["领袖", "带领", "leadership"], "leadership_theology"),
]
_TOPIC_COLS = ("topic_key, display_name, doctrine_area, difficulty, summary, scripture_refs, key_terms, "
               "common_misunderstandings, formation_relevance, linked_modules")


def init_doctrine_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _jl(v):
    if v is None: return []
    if isinstance(v, (list, dict)): return v
    try: return json.loads(v)
    except Exception: return []


def _topic(r) -> dict:
    return {"topic_key": r[0], "display_name": r[1], "doctrine_area": r[2], "difficulty": r[3],
            "summary": r[4] or "", "scripture_refs": _jl(r[5]), "key_terms": _jl(r[6]),
            "common_misunderstandings": _jl(r[7]), "formation_relevance": r[8] or "", "linked_modules": _jl(r[9])}


@router.get("/topics")
def list_topics(request: Request, area: str = Query(default="", max_length=24), difficulty: str = Query(default="", max_length=12)) -> dict:
    _require_user(request)
    where, params = [], []
    if area: where.append("doctrine_area=%s"); params.append(area)
    if difficulty: where.append("difficulty=%s"); params.append(difficulty)
    sql = f"SELECT {_TOPIC_COLS} FROM doctrine_topics"
    if where: sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY sort_order"
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "topics": [_topic(r) for r in rows]}


@router.get("/topics/{key}")
def get_topic(key: str, request: Request) -> dict:
    _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT {_TOPIC_COLS} FROM doctrine_topics WHERE topic_key=%s", (key,))
            r = cur.fetchone()
    finally:
        _state["release_db"](conn)
    if not r:
        raise HTTPException(status_code=404, detail="topic not found")
    return {"ok": True, "topic": _topic(r)}


@router.get("/paths")
def list_paths(request: Request) -> dict:
    _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT path_key, title, description, path_type, topic_keys FROM doctrine_path_templates WHERE public=TRUE ORDER BY sort_order")
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "paths": [
        {"path_key": r[0], "title": r[1], "description": r[2] or "", "path_type": r[3], "topic_keys": _jl(r[4])} for r in rows
    ]}


class RecommendBody(BaseModel):
    goal: str = Field(default="", max_length=200)


@router.post("/recommend")
def recommend(request: Request, body: RecommendBody) -> dict:
    _require_user(request)
    g = (body.goal or "").lower()
    path_key = "beginner_foundations"
    for kws, pk in _GOAL_PATH:
        if any(k.lower() in g for k in kws):
            path_key = pk; break
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT path_key, title, description, topic_keys FROM doctrine_path_templates WHERE path_key=%s", (path_key,))
            p = cur.fetchone()
            topics = []
            if p:
                keys = _jl(p[3])
                if keys:
                    cur.execute(f"SELECT {_TOPIC_COLS} FROM doctrine_topics WHERE topic_key IN %s", (tuple(keys),))
                    by = {r[0]: _topic(r) for r in cur.fetchall()}
                    topics = [by[k] for k in keys if k in by]
    finally:
        _state["release_db"](conn)
    return {"ok": True, "recommended_path": {"path_key": p[0], "title": p[1], "description": p[2] or ""} if p else None,
            "topics": topics}


class ProgressUpdate(BaseModel):
    topic_key: str = Field(..., max_length=40)
    path_key: str = Field(default="", max_length=40)
    status: str = Field(default="in_progress", max_length=12)
    notes: str = Field(default="", max_length=2000)


@router.post("/progress")
def update_progress(request: Request, body: ProgressUpdate) -> dict:
    user = _require_user(request); email = user["email"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM user_doctrine_progress WHERE email=%s AND topic_key=%s", (email, body.topic_key))
            row = cur.fetchone()
            completed = "completed_at=NOW()" if body.status == "completed" else "completed_at=completed_at"
            if row:
                cur.execute(f"UPDATE user_doctrine_progress SET status=%s, notes=%s, {completed}, updated_at=NOW() WHERE id=%s",
                            (body.status, body.notes, row[0]))
            else:
                cur.execute("INSERT INTO user_doctrine_progress (id, email, topic_key, path_key, status, notes, completed_at) "
                            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                            (uuid.uuid4().hex, email, body.topic_key, body.path_key, body.status, body.notes,
                             None if body.status != "completed" else __import__("datetime").datetime.utcnow()))
            conn.commit()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail="progress failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True}


@router.get("/progress")
def get_progress(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT topic_key, path_key, status FROM user_doctrine_progress WHERE email=%s ORDER BY updated_at DESC", (user["email"],))
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "progress": [{"topic_key": r[0], "path_key": r[1] or "", "status": r[2]} for r in rows]}


class ReflectionCreate(BaseModel):
    topic_key: str = Field(..., max_length=40)
    reflection_text: str = Field(default="", max_length=4000)
    formation_application: str = Field(default="", max_length=2000)


@router.post("/reflections")
def add_reflection(request: Request, body: ReflectionCreate) -> dict:
    user = _require_user(request)
    rid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO doctrine_reflections (id, email, topic_key, reflection_text, formation_application) "
                        "VALUES (%s,%s,%s,%s,%s)", (rid, user["email"], body.topic_key, body.reflection_text, body.formation_application))
            conn.commit()
    except Exception as exc:
        try: conn.rollback()
        except Exception: pass
        raise HTTPException(status_code=500, detail="reflection failed")
    finally:
        _state["release_db"](conn)
    return {"ok": True, "id": rid}
