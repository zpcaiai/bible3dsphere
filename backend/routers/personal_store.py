"""
个人数据存储 —— 聚会纪要历史 + 背经卡云同步。

  POST /api/minutes              保存一份通话/祷告会纪要
  GET  /api/minutes?limit=30     我的纪要历史（小组中心展示）
  GET  /api/memory-cards         拉取我的背经卡组（换设备恢复）
  PUT  /api/memory-cards         全量上传卡组（last-write-wins，≤500 张）
"""
from __future__ import annotations

import json
import re
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter(prefix="/api", tags=["personal-store"])
_state: dict = {}

_TABLES = """
CREATE TABLE IF NOT EXISTS call_minutes_history (
  id SERIAL PRIMARY KEY,
  email TEXT NOT NULL,
  title TEXT NOT NULL DEFAULT '',
  summary TEXT NOT NULL DEFAULT '',
  prayer_items JSONB NOT NULL DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_minutes_email ON call_minutes_history(email);
CREATE TABLE IF NOT EXISTS memory_decks (
  email TEXT PRIMARY KEY,
  cards JSONB NOT NULL DEFAULT '[]',
  updated_at TIMESTAMPTZ DEFAULT now()
);
"""


def init_personal_store_router(*, get_db, release_db, get_session_user) -> None:
    _state.update(get_db=get_db, release_db=release_db, get_session_user=get_session_user)
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(_TABLES)
        conn.commit()
    except Exception as exc:  # pragma: no cover
        print(f"[personal-store] ensure_tables warning: {exc}", flush=True)
    finally:
        release_db(conn)


def _user(request: Request) -> str:
    u = _state["get_session_user"](request)
    if not u:
        raise HTTPException(status_code=401, detail="请先登录")
    return u["email"]


@router.post("/minutes")
async def save_minutes(request: Request) -> dict[str, Any]:
    email = _user(request)
    body = await request.json()
    title = re.sub(r"[\x00-\x1f<>]", "", str(body.get("title") or ""))[:80]
    summary = str(body.get("summary") or "")[:8000]
    items = [str(x)[:200] for x in (body.get("prayer_items") or []) if str(x).strip()][:20]
    if not summary.strip():
        raise HTTPException(status_code=400, detail="纪要内容为空")
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO call_minutes_history (email,title,summary,prayer_items) "
                "VALUES (%s,%s,%s,%s) RETURNING id",
                (email, title, summary, json.dumps(items, ensure_ascii=False)))
            mid = cur.fetchone()[0]
        conn.commit()
        return {"success": True, "data": {"id": mid}}
    finally:
        _state["release_db"](conn)


@router.get("/minutes")
def list_minutes(request: Request, limit: int = Query(30, ge=1, le=100)) -> dict[str, Any]:
    email = _user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, summary, prayer_items, created_at FROM call_minutes_history "
                "WHERE email=%s ORDER BY id DESC LIMIT %s", (email, limit))
            data = [{
                "id": r[0], "title": r[1], "summary": r[2],
                "prayerItems": r[3] if isinstance(r[3], list) else json.loads(r[3] or "[]"),
                "createdAt": r[4].isoformat() if r[4] else None,
            } for r in cur.fetchall()]
        return {"success": True, "data": data}
    finally:
        _state["release_db"](conn)


@router.get("/memory-cards")
def get_deck(request: Request) -> dict[str, Any]:
    email = _user(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT cards, updated_at FROM memory_decks WHERE email=%s", (email,))
            row = cur.fetchone()
        cards = (row[0] if isinstance(row[0], list) else json.loads(row[0] or "[]")) if row else []
        return {"success": True, "data": {"cards": cards, "updatedAt": row[1].isoformat() if row and row[1] else None}}
    finally:
        _state["release_db"](conn)


@router.put("/memory-cards")
async def put_deck(request: Request) -> dict[str, Any]:
    email = _user(request)
    body = await request.json()
    cards = body.get("cards")
    if not isinstance(cards, list) or len(cards) > 500:
        raise HTTPException(status_code=400, detail="cards 需为数组且 ≤500")
    payload = json.dumps(cards, ensure_ascii=False)[:400000]
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO memory_decks (email, cards, updated_at) VALUES (%s,%s,now()) "
                "ON CONFLICT (email) DO UPDATE SET cards=EXCLUDED.cards, updated_at=now()",
                (email, payload))
        conn.commit()
        return {"success": True}
    finally:
        _state["release_db"](conn)
