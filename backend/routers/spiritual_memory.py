"""
Spiritual Memory router — 属灵记忆库 (/api/spiritual-memory)

  GET    /api/spiritual-memory/profile        成长画像(无则建默认)
  PATCH  /api/spiritual-memory/profile        更新画像
  GET    /api/spiritual-memory/consent        记忆同意规则
  PATCH  /api/spiritual-memory/consent        更新同意规则
  GET    /api/spiritual-memory/items          记忆条目列表
  POST   /api/spiritual-memory/items          新增记忆条目(危机扫描)
  PATCH  /api/spiritual-memory/items/{id}     更新条目
  DELETE /api/spiritual-memory/items/{id}     归档/删除条目
  POST   /api/spiritual-memory/search         关键词检索
  GET    /api/spiritual-memory/summary        给 AI 导师的安全接地摘要(受 consent 控制)

记忆是仆人不是主人:用户拥有、可编辑、可删除自己的记忆;
敏感/危机条目默认不外泄、不喂 LLM(exclude_sensitive 默认开)。email 标识用户。
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/spiritual-memory", tags=["spiritual-memory"])

_state: Dict[str, Any] = {}


def init_spiritual_memory_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _scan(text: str):
    try:
        from safety_scan import scan_crisis
        return scan_crisis(text)
    except Exception:
        return None


# ---------- profile / consent helpers ----------
def _ensure_profile(cur, email: str) -> None:
    cur.execute("INSERT INTO spiritual_profiles(email) VALUES (%s) ON CONFLICT (email) DO NOTHING", (email,))


def _ensure_consent(cur, email: str) -> None:
    cur.execute("INSERT INTO memory_consent_rules(email) VALUES (%s) ON CONFLICT (email) DO NOTHING", (email,))


def _profile_row(cur, email: str) -> dict:
    _ensure_profile(cur, email)
    cur.execute("SELECT email,current_season,primary_focus,practice_style,caution_flags,summary_text,updated_at "
                "FROM spiritual_profiles WHERE email=%s", (email,))
    r = cur.fetchone()
    to_iso = _state["to_shanghai_iso"]
    return {"email": r[0], "current_season": r[1] or "", "primary_focus": r[2] or "",
            "practice_style": r[3] or {}, "caution_flags": r[4] or [],
            "summary_text": r[5] or "", "updated_at": to_iso(r[6]) if r[6] else None}


def _consent_row(cur, email: str) -> dict:
    _ensure_consent(cur, email)
    cur.execute("SELECT allow_ai_tutor,allow_mentor,allow_group,exclude_sensitive,updated_at "
                "FROM memory_consent_rules WHERE email=%s", (email,))
    r = cur.fetchone()
    to_iso = _state["to_shanghai_iso"]
    return {"allow_ai_tutor": bool(r[0]), "allow_mentor": bool(r[1]), "allow_group": bool(r[2]),
            "exclude_sensitive": bool(r[3]), "updated_at": to_iso(r[4]) if r[4] else None}


# ---------- profile ----------
@router.get("/profile")
def get_profile(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            p = _profile_row(cur, user["email"])
            conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "profile": p}


class ProfilePatch(BaseModel):
    current_season: Optional[str] = Field(default=None, max_length=60)
    primary_focus: Optional[str] = Field(default=None, max_length=120)
    practice_style: Optional[dict] = None
    caution_flags: Optional[list] = None


@router.patch("/profile")
def patch_profile(request: Request, body: ProfilePatch) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _ensure_profile(cur, user["email"])
            sets: List[str] = []
            params: List[Any] = []
            if body.current_season is not None:
                sets.append("current_season=%s"); params.append(body.current_season)
            if body.primary_focus is not None:
                sets.append("primary_focus=%s"); params.append(body.primary_focus)
            if body.practice_style is not None:
                sets.append("practice_style=%s"); params.append(json.dumps(body.practice_style, ensure_ascii=False))
            if body.caution_flags is not None:
                sets.append("caution_flags=%s"); params.append(json.dumps(body.caution_flags, ensure_ascii=False))
            if sets:
                sets.append("updated_at=now()")
                params.append(user["email"])
                cur.execute("UPDATE spiritual_profiles SET " + ", ".join(sets) + " WHERE email=%s", params)
            p = _profile_row(cur, user["email"])
            conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "profile": p}


# ---------- consent ----------
@router.get("/consent")
def get_consent(request: Request) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            c = _consent_row(cur, user["email"]); conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "consent": c}


class ConsentPatch(BaseModel):
    allow_ai_tutor: Optional[bool] = None
    allow_mentor: Optional[bool] = None
    allow_group: Optional[bool] = None
    exclude_sensitive: Optional[bool] = None


@router.patch("/consent")
def patch_consent(request: Request, body: ConsentPatch) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            _ensure_consent(cur, user["email"])
            sets: List[str] = []
            params: List[Any] = []
            for f in ("allow_ai_tutor", "allow_mentor", "allow_group", "exclude_sensitive"):
                v = getattr(body, f)
                if v is not None:
                    sets.append(f + "=%s"); params.append(bool(v))
            if sets:
                sets.append("updated_at=now()"); params.append(user["email"])
                cur.execute("UPDATE memory_consent_rules SET " + ", ".join(sets) + " WHERE email=%s", params)
            c = _consent_row(cur, user["email"]); conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "consent": c}


# ---------- items ----------
_ITEM_COLS = "id,memory_type,title,content,source_module,sensitivity,importance,active,created_at"


def _item_dict(r, to_iso) -> dict:
    return {"id": r[0], "memory_type": r[1], "title": r[2] or "", "content": r[3],
            "source_module": r[4], "sensitivity": r[5], "importance": r[6],
            "active": bool(r[7]), "created_at": to_iso(r[8]) if r[8] else None}


@router.get("/items")
def list_items(request: Request, memory_type: str = Query(default="", max_length=40),
               include_inactive: bool = Query(default=False)) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            sql = "SELECT " + _ITEM_COLS + " FROM spiritual_memory_items WHERE email=%s"
            params: List[Any] = [user["email"]]
            if not include_inactive:
                sql += " AND active=TRUE"
            if memory_type:
                sql += " AND memory_type=%s"; params.append(memory_type)
            sql += " ORDER BY importance DESC, created_at DESC LIMIT 300"
            cur.execute(sql, params)
            items = [_item_dict(r, to_iso) for r in cur.fetchall()]
    finally:
        _state["release_db"](conn)
    return {"ok": True, "items": items, "count": len(items)}


class ItemCreate(BaseModel):
    content: str = Field(..., max_length=4000)
    title: str = Field(default="", max_length=200)
    memory_type: str = Field(default="insight", max_length=40)
    source_module: str = Field(default="manual", max_length=40)
    sensitivity: str = Field(default="normal", max_length=20)
    importance: int = Field(default=3, ge=1, le=5)


@router.post("/items")
def create_item(request: Request, body: ItemCreate) -> dict:
    user = _require_user(request)
    crisis = _scan((body.content or "") + " " + (body.title or ""))
    sensitivity = body.sensitivity
    if crisis and sensitivity == "normal":
        sensitivity = "crisis"   # 危机内容默认提高敏感级 → 不会喂给 LLM
    iid = uuid.uuid4().hex
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO spiritual_memory_items"
                        "(id,email,memory_type,title,content,source_module,sensitivity,importance) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                        (iid, user["email"], body.memory_type, body.title, body.content,
                         body.source_module, sensitivity, body.importance))
            conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "id": iid, "sensitivity": sensitivity, "crisis": crisis}


class ItemPatch(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    content: Optional[str] = Field(default=None, max_length=4000)
    memory_type: Optional[str] = Field(default=None, max_length=40)
    sensitivity: Optional[str] = Field(default=None, max_length=20)
    importance: Optional[int] = Field(default=None, ge=1, le=5)
    active: Optional[bool] = None


@router.patch("/items/{item_id}")
def patch_item(request: Request, item_id: str, body: ItemPatch) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM spiritual_memory_items WHERE id=%s AND email=%s", (item_id, user["email"]))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Not found")
            sets: List[str] = []
            params: List[Any] = []
            for f in ("title", "content", "memory_type", "sensitivity", "importance", "active"):
                v = getattr(body, f)
                if v is not None:
                    sets.append(f + "=%s"); params.append(v)
            if sets:
                sets.append("updated_at=now()")
                params.extend([item_id, user["email"]])
                cur.execute("UPDATE spiritual_memory_items SET " + ", ".join(sets) + " WHERE id=%s AND email=%s", params)
                conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "id": item_id}


@router.delete("/items/{item_id}")
def delete_item(request: Request, item_id: str, hard: bool = Query(default=False)) -> dict:
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if hard:
                cur.execute("DELETE FROM spiritual_memory_items WHERE id=%s AND email=%s", (item_id, user["email"]))
            else:
                cur.execute("UPDATE spiritual_memory_items SET active=FALSE, updated_at=now() "
                            "WHERE id=%s AND email=%s", (item_id, user["email"]))
            conn.commit()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "id": item_id, "deleted": hard}


class SearchBody(BaseModel):
    query: str = Field(..., max_length=200)


@router.post("/search")
def search_items(request: Request, body: SearchBody) -> dict:
    user = _require_user(request)
    to_iso = _state["to_shanghai_iso"]
    like = "%" + (body.query or "").strip() + "%"
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT " + _ITEM_COLS + " FROM spiritual_memory_items "
                        "WHERE email=%s AND active=TRUE AND (title ILIKE %s OR content ILIKE %s) "
                        "ORDER BY importance DESC, created_at DESC LIMIT 100",
                        (user["email"], like, like))
            items = [_item_dict(r, to_iso) for r in cur.fetchall()]
    finally:
        _state["release_db"](conn)
    return {"ok": True, "items": items, "count": len(items)}


@router.get("/summary")
def summary(request: Request) -> dict:
    """给 AI 导师的安全接地摘要:仅活跃、(默认)非敏感的记忆;受 allow_ai_tutor 控制。"""
    user = _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            prof = _profile_row(cur, user["email"])
            consent = _consent_row(cur, user["email"])
            exclude_sensitive = consent["exclude_sensitive"]
            sql = ("SELECT title,content,memory_type FROM spiritual_memory_items "
                   "WHERE email=%s AND active=TRUE")
            if exclude_sensitive:
                sql += " AND sensitivity='normal'"
            sql += " ORDER BY importance DESC, created_at DESC LIMIT 12"
            cur.execute(sql, (user["email"],))
            rows = cur.fetchall()
            conn.commit()
    finally:
        _state["release_db"](conn)
    lines = []
    for t, c, mt in rows:
        snippet = ((t + ": ") if t else "") + (c[:160] if c else "")
        lines.append({"type": mt, "text": snippet})
    return {"ok": True,
            "profile": {"current_season": prof["current_season"],
                        "primary_focus": prof["primary_focus"],
                        "caution_flags": prof["caution_flags"]},
            "memory_lines": lines,
            "shareable_with_tutor": consent["allow_ai_tutor"],
            "excluded_sensitive": exclude_sensitive,
            "note": "仅活跃、非敏感的记忆默认进入接地摘要;你可在记忆库随时编辑或删除。"}
