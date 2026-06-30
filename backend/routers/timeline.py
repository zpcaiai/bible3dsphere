"""
Biblical Theology Timeline router — 圣经神学时间线 (/api/timeline)

  GET  /api/timeline/eras            救赎历史各时代(按序)
  GET  /api/timeline/covenants       盟约档案
  POST /api/timeline/theme-trace     沿救赎历史追踪一个主题（{theme}）
  GET  /api/timeline/overview        救赎历史总览

把圣经读成一个故事:创造→堕落→应许→盟约→国度→被掳→基督→教会→新创造。email 标识用户。
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/timeline", tags=["timeline"])

_state: Dict[str, Any] = {}

_THEME_NAMES = {
    "creation": "创造", "fall": "堕落", "sin": "罪", "promise": "应许", "covenant": "盟约",
    "exodus": "出埃及", "law": "律法", "holiness": "圣洁", "temple": "圣殿", "priesthood": "祭司",
    "sacrifice": "献祭", "kingdom": "国度", "messiah": "弥赛亚", "exile": "被掳", "remnant": "余民",
    "return": "归回", "wisdom": "智慧", "spirit": "圣灵", "mission": "使命", "salvation": "救恩",
    "judgment": "审判", "new_creation": "新创造",
}


def init_timeline_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
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


@router.get("/eras")
def list_eras(request: Request) -> dict:
    _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT era_key, display_name, description, canonical_order, testament, theological_summary, "
                        "major_themes, key_scripture_refs, formation_relevance FROM biblical_timeline_eras ORDER BY canonical_order")
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "eras": [
        {"era_key": r[0], "display_name": r[1], "description": r[2] or "", "canonical_order": r[3],
         "testament": r[4], "theological_summary": r[5] or "", "major_themes": _jl(r[6]),
         "key_scripture_refs": _jl(r[7]), "formation_relevance": r[8] or ""} for r in rows
    ]}


@router.get("/covenants")
def list_covenants(request: Request) -> dict:
    _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT covenant_key, display_name, covenant_type, description, parties, promises, signs, "
                        "scripture_refs, fulfillment_notes FROM covenant_profiles ORDER BY sort_order")
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "covenants": [
        {"covenant_key": r[0], "display_name": r[1], "covenant_type": r[2], "description": r[3] or "",
         "parties": _jl(r[4]), "promises": _jl(r[5]), "signs": _jl(r[6]), "scripture_refs": _jl(r[7]),
         "fulfillment_notes": r[8] or ""} for r in rows
    ]}


class ThemeTrace(BaseModel):
    theme: str = Field(..., max_length=30)


@router.post("/theme-trace")
def theme_trace(request: Request, body: ThemeTrace) -> dict:
    _require_user(request)
    theme = (body.theme or "").strip().lower()
    # 允许中文主题名 → 反查 key
    if theme in _THEME_NAMES.values():
        theme = next(k for k, v in _THEME_NAMES.items() if v == theme)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT era_key, display_name, theological_summary, major_themes, canonical_order "
                        "FROM biblical_timeline_eras ORDER BY canonical_order")
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    trace = [{"era": r[1], "era_key": r[0], "summary": r[2] or ""} for r in rows if theme in [str(x).lower() for x in _jl(r[3])]]
    if not trace:
        return {"ok": True, "theme": theme, "trace": [],
                "available_themes": sorted(set(_THEME_NAMES.keys())),
                "note": "未找到该主题。可试:" + "、".join(list(_THEME_NAMES.values())[:10])}
    return {"ok": True, "theme": theme, "theme_name": _THEME_NAMES.get(theme, theme), "trace": trace,
            "formation_relevance": "顺着这个主题读整本圣经,看见神在历史中一致的心意,塑造你的盼望与敬拜。"}


@router.get("/overview")
def overview(request: Request) -> dict:
    _require_user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT era_key, display_name, theological_summary, testament FROM biblical_timeline_eras ORDER BY canonical_order")
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)
    return {"ok": True, "arc": [{"era_key": r[0], "display_name": r[1], "summary": r[2] or "", "testament": r[3]} for r in rows],
            "big_story": "创造 → 堕落 → 应许 → 盟约 → 出埃及 → 国度 → 被掳与归回 → 基督(道成肉身/十架/复活) → 圣灵与教会 → 新创造。",
            "center": "整本圣经的中心是耶稣基督——一切应许、盟约、预表都指向他、在他里面成全。"}
