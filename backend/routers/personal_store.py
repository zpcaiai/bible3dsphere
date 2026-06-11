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


# ── 个人数据全局搜索 ──────────────────────────────────────────────────────────
# 一个关键词横跨：灵修日记 / 主日笔记 / 我的祷告 / 聚会纪要 / 背经卡。
# 仅搜本人数据（email 隔离），ILIKE 模糊匹配，按组返回带摘要片段。

def _snippet(text: str, q: str, width: int = 60) -> str:
    """命中词上下文摘要：定位首个命中，前后各取一段。"""
    if not text:
        return ""
    low, ql = text.lower(), q.lower()
    pos = low.find(ql)
    if pos < 0:
        return text[:width] + ("…" if len(text) > width else "")
    start = max(0, pos - width // 3)
    end = min(len(text), pos + len(q) + width)
    return ("…" if start > 0 else "") + text[start:end] + ("…" if end < len(text) else "")


@router.get("/personal-search")
def personal_search(
    request: Request,
    q: str = Query(min_length=1, max_length=80),
    limit: int = Query(default=8, ge=1, le=20),
) -> dict:
    email = _user(request)
    q = q.strip()
    if not q:
        raise HTTPException(status_code=422, detail="empty query")
    like = f"%{q}%"
    groups = []
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            # 1) 灵修日记
            cur.execute(
                "SELECT id, journal_date, title, scripture_text, observation, reflection, application, prayer "
                "FROM devotion_journals WHERE email=%s AND deleted_at IS NULL AND ("
                "title ILIKE %s OR scripture_text ILIKE %s OR observation ILIKE %s OR "
                "reflection ILIKE %s OR application ILIKE %s OR prayer ILIKE %s) "
                "ORDER BY journal_date DESC LIMIT %s",
                (email, like, like, like, like, like, like, limit),
            )
            items = []
            for r in cur.fetchall():
                body = next((v for v in r[3:] if v and q.lower() in v.lower()), r[5] or r[3] or "")
                items.append({
                    "id": r[0],
                    "date": str(r[1] or ""),
                    "title": r[2] or "灵修日记",
                    "snippet": _snippet(body or "", q),
                })
            if items:
                groups.append({"type": "devotion", "label": "灵修日记", "items": items})

            # 2) 主日笔记
            cur.execute(
                "SELECT id, sermon_date, title, preacher, scripture, summary, reflection, lesson "
                "FROM sermon_journals WHERE email=%s AND deleted_at IS NULL AND ("
                "title ILIKE %s OR preacher ILIKE %s OR scripture ILIKE %s OR "
                "summary ILIKE %s OR reflection ILIKE %s OR lesson ILIKE %s) "
                "ORDER BY created_at DESC LIMIT %s",
                (email, like, like, like, like, like, like, limit),
            )
            items = []
            for r in cur.fetchall():
                body = next((v for v in r[3:] if v and q.lower() in v.lower()), r[5] or "")
                items.append({
                    "id": r[0],
                    "date": str(r[1] or ""),
                    "title": r[2] or "主日笔记",
                    "snippet": _snippet(body or "", q),
                })
            if items:
                groups.append({"type": "sermon", "label": "主日笔记", "items": items})

            # 3) 我的祷告
            cur.execute(
                "SELECT id, content, status, created_at FROM prayers "
                "WHERE email=%s AND deleted_at IS NULL AND content ILIKE %s "
                "ORDER BY created_at DESC LIMIT %s",
                (email, like, limit),
            )
            items = [{
                "id": r[0],
                "date": str(r[3])[:10] if r[3] else "",
                "title": "已蒙应允 ✨" if r[2] == "answered" else "代祷中",
                "snippet": _snippet(r[1] or "", q),
            } for r in cur.fetchall()]
            if items:
                groups.append({"type": "prayer", "label": "我的祷告", "items": items})

            # 4) 聚会纪要
            cur.execute(
                "SELECT id, title, summary, created_at FROM call_minutes_history "
                "WHERE email=%s AND (title ILIKE %s OR summary ILIKE %s) "
                "ORDER BY created_at DESC LIMIT %s",
                (email, like, like, limit),
            )
            items = [{
                "id": r[0],
                "date": str(r[3])[:10] if r[3] else "",
                "title": r[1] or "聚会纪要",
                "snippet": _snippet(r[2] or "", q),
            } for r in cur.fetchall()]
            if items:
                groups.append({"type": "minutes", "label": "聚会纪要", "items": items})

            # 5) 背经卡（JSONB 在 Python 侧过滤）
            cur.execute("SELECT cards FROM memory_decks WHERE email=%s", (email,))
            row = cur.fetchone()
            if row and row[0]:
                cards = row[0] if isinstance(row[0], list) else json.loads(row[0])
                ql = q.lower()
                def _card_text(c):
                    return str(c.get("textCuv") or c.get("textEsv") or c.get("text") or "")
                hits = [c for c in cards if ql in str(c.get("ref", "")).lower() or ql in _card_text(c).lower()][:limit]
                items = [{
                    "id": c.get("ref", ""),
                    "date": "",
                    "title": c.get("ref", "背经卡"),
                    "snippet": _snippet(_card_text(c), q),
                } for c in hits]
                if items:
                    groups.append({"type": "memory", "label": "背经卡", "items": items})
        return {"ok": True, "q": q, "groups": groups, "total": sum(len(g["items"]) for g in groups)}
    finally:
        _state["release_db"](conn)
