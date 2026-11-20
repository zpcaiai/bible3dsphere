"""
个人数据存储 —— 聚会纪要历史 + 背经卡云同步 + 个人全局检索。

  POST /api/minutes              保存一份通话/祷告会纪要
  GET  /api/minutes?limit=30     我的纪要历史（小组中心展示）
  GET  /api/memory-cards         拉取我的背经卡组（换设备恢复）
  PUT  /api/memory-cards         全量上传卡组（last-write-wins，≤500 张）
  GET  /api/personal/search      个人数据全局搜索（6 源 owner 隔离 + 通配符转义 + 分页统计）
  GET  /api/personal-search      个人数据全局搜索（兼容别名）
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

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
# 一个关键词横跨：灵修日记 / 个人笔记 / 主日笔记 / 我的祷告 / 聚会纪要 / 背经卡。
# 仅搜本人数据（email 隔离），ILIKE ESCAPE '\' 严格转义通配符，纯 SQL 侧聚合与分页。

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


_CANONICAL_SEARCH_SOURCES = (
    "devotion",
    "personal_note",
    "sermon",
    "prayer",
    "minutes",
    "memory",
)

_SEARCH_SOURCE_ALIASES = {
    "devotion": "devotion",
    "devotions": "devotion",
    "personal_note": "personal_note",
    "personal_notes": "personal_note",
    "note": "personal_note",
    "notes": "personal_note",
    "sermon": "sermon",
    "sermons": "sermon",
    "prayer": "prayer",
    "prayers": "prayer",
    "minutes": "minutes",
    "memory": "memory",
}

_SEARCH_SOURCE_LABELS = {
    "devotion": "灵修日记",
    "personal_note": "个人笔记",
    "sermon": "主日笔记",
    "prayer": "我的祷告",
    "minutes": "聚会纪要",
    "memory": "背经卡",
}


def _parse_requested_sources(sources: Optional[str]) -> list[str]:
    if sources is None or not sources.strip():
        return list(_CANONICAL_SEARCH_SOURCES)
    selected: list[str] = []
    for raw_part in sources.split(","):
        part = raw_part.strip().lower()
        if not part:
            continue
        mapped = _SEARCH_SOURCE_ALIASES.get(part)
        if not mapped:
            raise HTTPException(status_code=400, detail=f"Unsupported search source: {part}")
        if mapped not in selected:
            selected.append(mapped)
    return selected or list(_CANONICAL_SEARCH_SOURCES)


@router.get("/personal/search")
@router.get("/personal-search")
def personal_search(
    request: Request,
    q: str = Query(default="", max_length=80),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sources: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    email = _user(request)
    selected_sources = _parse_requested_sources(sources)
    q_clean = (q or "").strip()
    counts: dict[str, int] = {src: 0 for src in selected_sources}
    if not q_clean:
        return {
            "success": True,
            "ok": True,
            "query": "",
            "q": "",
            "total": 0,
            "counts": counts,
            "groups": [],
            "results": [],
        }

    escaped = q_clean.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    like = f"%{escaped}%"
    ql = q_clean.lower()

    groups: list[dict[str, Any]] = []
    flat_results: list[dict[str, Any]] = []

    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema = COALESCE(current_schema(), 'public') "
                "AND table_name IN ("
                "'devotion_journals', 'personal_notes', 'sermon_journals', "
                "'prayers', 'call_minutes_history', 'memory_decks'"
                ")"
            )
            schema_cols: dict[str, set[str]] = {}
            for tbl_name, col_name in cur.fetchall():
                schema_cols.setdefault(str(tbl_name), set()).add(str(col_name))

            # 1) devotion (devotion_journals)
            if "devotion" in selected_sources and "devotion_journals" in schema_cols:
                d_cols = schema_cols["devotion_journals"]
                searchable_d = [
                    c for c in (
                        "title", "scripture", "scripture_text", "observation",
                        "reflection", "application", "prayer", "mood", "gratitude", "content"
                    )
                    if c in d_cols
                ]
                if searchable_d:
                    date_expr = "journal_date::text" if "journal_date" in d_cols else ("created_at::text" if "created_at" in d_cols else "''")
                    title_expr = "COALESCE(title, '')" if "title" in d_cols else "''"
                    if "scripture" in d_cols and "scripture_text" in d_cols:
                        scr_expr = "COALESCE(NULLIF(scripture, ''), scripture_text, '')"
                    elif "scripture" in d_cols:
                        scr_expr = "COALESCE(scripture, '')"
                    elif "scripture_text" in d_cols:
                        scr_expr = "COALESCE(scripture_text, '')"
                    else:
                        scr_expr = "''"
                    del_clause = "AND deleted_at IS NULL " if "deleted_at" in d_cols else ""
                    order_expr = "journal_date DESC, id DESC" if "journal_date" in d_cols else "id DESC"
                    or_clauses = " OR ".join(f"COALESCE({c}::text, '') ILIKE %s ESCAPE '\\'" for c in searchable_d)
                    select_body_cols = ", ".join(f"COALESCE({c}::text, '')" for c in searchable_d)
                    where_sql = f"WHERE lower(email) = lower(%s) {del_clause}AND ({or_clauses})"
                    where_params = [email, *([like] * len(searchable_d))]
                    cur.execute(
                        f"SELECT id::text, {date_expr}, {title_expr}, {scr_expr}, COUNT(*) OVER(), {select_body_cols} "
                        f"FROM devotion_journals {where_sql} ORDER BY {order_expr} LIMIT %s OFFSET %s",
                        [*where_params, limit, offset],
                    )
                    rows = cur.fetchall()
                    if rows:
                        counts["devotion"] = int(rows[0][4])
                    elif offset > 0:
                        cur.execute(f"SELECT COUNT(*) FROM devotion_journals {where_sql}", where_params)
                        counts["devotion"] = int(cur.fetchone()[0])
                    items = []
                    for r in rows:
                        cand_texts = [v for v in r[5:] if v]
                        matched_body = next((v for v in cand_texts if ql in v.lower()), cand_texts[0] if cand_texts else "")
                        hit = {
                            "id": str(r[0]),
                            "source": "devotion",
                            "title": r[2] or r[3] or "灵修日记",
                            "date": str(r[1] or "")[:10],
                            "snippet": _snippet(matched_body, q_clean),
                            "scripture": str(r[3] or ""),
                        }
                        items.append(hit)
                        flat_results.append(hit)
                    if items:
                        groups.append({"type": "devotion", "label": _SEARCH_SOURCE_LABELS["devotion"], "count": counts["devotion"], "items": items})

            # 2) personal_note (personal_notes, deleted_at IS NULL AND source_sermon_id IS NULL)
            if "personal_note" in selected_sources and "personal_notes" in schema_cols:
                n_cols = schema_cols["personal_notes"]
                searchable_n = [
                    c for c in ("scripture", "observation", "reflection", "application", "prayer", "mood")
                    if c in n_cols
                ]
                if searchable_n:
                    date_expr = "note_date::text" if "note_date" in n_cols else ("created_at::text" if "created_at" in n_cols else "''")
                    scr_expr = "COALESCE(scripture, '')" if "scripture" in n_cols else "''"
                    extra_filters = []
                    if "deleted_at" in n_cols:
                        extra_filters.append("deleted_at IS NULL")
                    if "source_sermon_id" in n_cols:
                        extra_filters.append("source_sermon_id IS NULL")
                    extra_sql = ("AND " + " AND ".join(extra_filters) + " ") if extra_filters else ""
                    order_expr = "updated_at DESC, id DESC" if "updated_at" in n_cols else "id DESC"
                    or_clauses = " OR ".join(f"COALESCE({c}::text, '') ILIKE %s ESCAPE '\\'" for c in searchable_n)
                    select_body_cols = ", ".join(f"COALESCE({c}::text, '')" for c in searchable_n)
                    where_sql = f"WHERE lower(email) = lower(%s) {extra_sql}AND ({or_clauses})"
                    where_params = [email, *([like] * len(searchable_n))]
                    cur.execute(
                        f"SELECT id::text, {date_expr}, {scr_expr}, COUNT(*) OVER(), {select_body_cols} "
                        f"FROM personal_notes {where_sql} ORDER BY {order_expr} LIMIT %s OFFSET %s",
                        [*where_params, limit, offset],
                    )
                    rows = cur.fetchall()
                    if rows:
                        counts["personal_note"] = int(rows[0][3])
                    elif offset > 0:
                        cur.execute(f"SELECT COUNT(*) FROM personal_notes {where_sql}", where_params)
                        counts["personal_note"] = int(cur.fetchone()[0])
                    items = []
                    for r in rows:
                        cand_texts = [v for v in r[4:] if v]
                        matched_body = next((v for v in cand_texts if ql in v.lower()), cand_texts[0] if cand_texts else "")
                        hit = {
                            "id": str(r[0]),
                            "source": "personal_note",
                            "title": r[2] or "个人笔记",
                            "date": str(r[1] or "")[:10],
                            "snippet": _snippet(matched_body, q_clean),
                            "scripture": str(r[2] or ""),
                        }
                        items.append(hit)
                        flat_results.append(hit)
                    if items:
                        groups.append({"type": "personal_note", "label": _SEARCH_SOURCE_LABELS["personal_note"], "count": counts["personal_note"], "items": items})

            # 3) sermon (sermon_journals)
            if "sermon" in selected_sources and "sermon_journals" in schema_cols:
                s_cols = schema_cols["sermon_journals"]
                s_exprs = []
                for col_name in ("title", "preacher", "scripture", "summary", "bible_study", "reflection", "lesson", "conclusion", "encouragement"):
                    if col_name in s_cols:
                        s_exprs.append(f"COALESCE({col_name}::text, '')")
                for json_col in ("questions", "practices"):
                    if json_col in s_cols:
                        s_exprs.append(f"COALESCE({json_col}::text, '')")
                if s_exprs:
                    del_clause = "AND deleted_at IS NULL " if "deleted_at" in s_cols else ""
                    date_expr = "COALESCE(sermon_date::text, '')" if "sermon_date" in s_cols else "''"
                    title_expr = "COALESCE(title, '')" if "title" in s_cols else "''"
                    scr_expr = "COALESCE(scripture, '')" if "scripture" in s_cols else "''"
                    order_expr = "updated_at DESC, id DESC" if "updated_at" in s_cols else ("created_at DESC, id DESC" if "created_at" in s_cols else "id DESC")
                    or_clauses = " OR ".join(f"{ex} ILIKE %s ESCAPE '\\'" for ex in s_exprs)
                    select_body_cols = ", ".join(s_exprs)
                    where_sql = f"WHERE lower(email) = lower(%s) {del_clause}AND ({or_clauses})"
                    where_params = [email, *([like] * len(s_exprs))]
                    cur.execute(
                        f"SELECT id::text, {date_expr}, {title_expr}, {scr_expr}, COUNT(*) OVER(), {select_body_cols} "
                        f"FROM sermon_journals {where_sql} ORDER BY {order_expr} LIMIT %s OFFSET %s",
                        [*where_params, limit, offset],
                    )
                    rows = cur.fetchall()
                    if rows:
                        counts["sermon"] = int(rows[0][4])
                    elif offset > 0:
                        cur.execute(f"SELECT COUNT(*) FROM sermon_journals {where_sql}", where_params)
                        counts["sermon"] = int(cur.fetchone()[0])
                    items = []
                    for r in rows:
                        cand_texts = [v for v in r[5:] if v]
                        matched_body = next((v for v in cand_texts if ql in v.lower()), cand_texts[0] if cand_texts else "")
                        hit = {
                            "id": str(r[0]),
                            "source": "sermon",
                            "title": r[2] or r[3] or "主日笔记",
                            "date": str(r[1] or ""),
                            "snippet": _snippet(matched_body, q_clean),
                            "scripture": str(r[3] or ""),
                        }
                        items.append(hit)
                        flat_results.append(hit)
                    if items:
                        groups.append({"type": "sermon", "label": _SEARCH_SOURCE_LABELS["sermon"], "count": counts["sermon"], "items": items})

            # 4) prayer (prayers)
            if "prayer" in selected_sources and "prayers" in schema_cols and "content" in schema_cols["prayers"]:
                p_cols = schema_cols["prayers"]
                del_clause = "AND deleted_at IS NULL " if "deleted_at" in p_cols else ""
                status_expr = "COALESCE(status::text, '')" if "status" in p_cols else "''"
                date_expr = "created_at::text" if "created_at" in p_cols else "''"
                order_expr = "created_at DESC, id DESC" if "created_at" in p_cols else "id DESC"
                where_sql = f"WHERE lower(email) = lower(%s) {del_clause}AND COALESCE(content, '') ILIKE %s ESCAPE '\\'"
                where_params = [email, like]
                cur.execute(
                    f"SELECT id::text, COALESCE(content, ''), {status_expr}, {date_expr}, COUNT(*) OVER() "
                    f"FROM prayers {where_sql} ORDER BY {order_expr} LIMIT %s OFFSET %s",
                    [*where_params, limit, offset],
                )
                rows = cur.fetchall()
                if rows:
                    counts["prayer"] = int(rows[0][4])
                elif offset > 0:
                    cur.execute(f"SELECT COUNT(*) FROM prayers {where_sql}", where_params)
                    counts["prayer"] = int(cur.fetchone()[0])
                items = []
                for r in rows:
                    hit = {
                        "id": str(r[0]),
                        "source": "prayer",
                        "title": "已蒙应允 ✨" if r[2] == "answered" else "代祷中",
                        "date": str(r[3] or "")[:10],
                        "snippet": _snippet(r[1] or "", q_clean),
                        "scripture": "",
                    }
                    items.append(hit)
                    flat_results.append(hit)
                if items:
                    groups.append({"type": "prayer", "label": _SEARCH_SOURCE_LABELS["prayer"], "count": counts["prayer"], "items": items})

            # 5) minutes (call_minutes_history)
            if "minutes" in selected_sources and "call_minutes_history" in schema_cols:
                m_cols = schema_cols["call_minutes_history"]
                m_exprs = []
                if "title" in m_cols:
                    m_exprs.append("COALESCE(title, '')")
                if "summary" in m_cols:
                    m_exprs.append("COALESCE(summary, '')")
                if "prayer_items" in m_cols:
                    m_exprs.append("COALESCE(prayer_items::text, '')")
                if m_exprs:
                    title_expr = "COALESCE(title, '')" if "title" in m_cols else "''"
                    summary_expr = "COALESCE(summary, '')" if "summary" in m_cols else "''"
                    pitems_expr = "COALESCE(prayer_items::text, '')" if "prayer_items" in m_cols else "''"
                    date_expr = "created_at::text" if "created_at" in m_cols else "''"
                    order_expr = "created_at DESC, id DESC" if "created_at" in m_cols else "id DESC"
                    or_clauses = " OR ".join(f"{ex} ILIKE %s ESCAPE '\\'" for ex in m_exprs)
                    where_sql = f"WHERE lower(email) = lower(%s) AND ({or_clauses})"
                    where_params = [email, *([like] * len(m_exprs))]
                    cur.execute(
                        f"SELECT id::text, {title_expr}, {summary_expr}, {pitems_expr}, {date_expr}, COUNT(*) OVER() "
                        f"FROM call_minutes_history {where_sql} ORDER BY {order_expr} LIMIT %s OFFSET %s",
                        [*where_params, limit, offset],
                    )
                    rows = cur.fetchall()
                    if rows:
                        counts["minutes"] = int(rows[0][5])
                    elif offset > 0:
                        cur.execute(f"SELECT COUNT(*) FROM call_minutes_history {where_sql}", where_params)
                        counts["minutes"] = int(cur.fetchone()[0])
                    items = []
                    for r in rows:
                        cand_texts = [v for v in (r[2], r[3], r[1]) if v]
                        matched_body = next((v for v in cand_texts if ql in v.lower()), r[2] or r[3] or "")
                        hit = {
                            "id": str(r[0]),
                            "source": "minutes",
                            "title": r[1] or "聚会纪要",
                            "date": str(r[4] or "")[:10],
                            "snippet": _snippet(matched_body, q_clean),
                            "scripture": "",
                        }
                        items.append(hit)
                        flat_results.append(hit)
                    if items:
                        groups.append({"type": "minutes", "label": _SEARCH_SOURCE_LABELS["minutes"], "count": counts["minutes"], "items": items})

            # 6) memory (memory_decks via pure SQL LATERAL jsonb_array_elements)
            if "memory" in selected_sources and "memory_decks" in schema_cols and "cards" in schema_cols["memory_decks"]:
                md_cols = schema_cols["memory_decks"]
                date_expr = "md.updated_at::text" if "updated_at" in md_cols else "''"
                mem_from_where = (
                    "FROM memory_decks md "
                    "CROSS JOIN LATERAL jsonb_array_elements("
                    "CASE WHEN jsonb_typeof(md.cards) = 'array' THEN md.cards ELSE '[]'::jsonb END"
                    ") WITH ORDINALITY AS elem(card, ord) "
                    "WHERE lower(md.email) = lower(%s) AND ("
                    "COALESCE(elem.card->>'ref', '') ILIKE %s ESCAPE '\\' "
                    "OR COALESCE(elem.card->>'textCuv', '') ILIKE %s ESCAPE '\\' "
                    "OR COALESCE(elem.card->>'textEsv', '') ILIKE %s ESCAPE '\\' "
                    "OR COALESCE(elem.card->>'text', '') ILIKE %s ESCAPE '\\'"
                    ")"
                )
                mem_params = [email, like, like, like, like]
                cur.execute(
                    f"SELECT COALESCE(NULLIF(elem.card->>'id', ''), NULLIF(elem.card->>'ref', ''), elem.ord::text), "
                    f"COALESCE(elem.card->>'ref', ''), "
                    f"COALESCE(elem.card->>'textCuv', elem.card->>'textEsv', elem.card->>'text', ''), "
                    f"{date_expr}, COUNT(*) OVER() "
                    f"{mem_from_where} ORDER BY elem.ord ASC LIMIT %s OFFSET %s",
                    [*mem_params, limit, offset],
                )
                rows = cur.fetchall()
                if rows:
                    counts["memory"] = int(rows[0][4])
                elif offset > 0:
                    cur.execute(f"SELECT COUNT(*) {mem_from_where}", mem_params)
                    counts["memory"] = int(cur.fetchone()[0])
                items = []
                for r in rows:
                    ref_str = str(r[1] or "")
                    card_text = str(r[2] or "")
                    snippet_src = card_text if (card_text and ql in card_text.lower()) else (card_text or ref_str)
                    hit = {
                        "id": str(r[0] or ref_str),
                        "source": "memory",
                        "title": ref_str or "背经卡",
                        "date": str(r[3] or "")[:10],
                        "snippet": _snippet(snippet_src, q_clean),
                        "scripture": ref_str,
                    }
                    items.append(hit)
                    flat_results.append(hit)
                if items:
                    groups.append({"type": "memory", "label": _SEARCH_SOURCE_LABELS["memory"], "count": counts["memory"], "items": items})

        total = sum(counts.values())
        return {
            "success": True,
            "ok": True,
            "query": q_clean,
            "q": q_clean,
            "total": total,
            "counts": counts,
            "groups": groups,
            "results": flat_results,
        }
    finally:
        _state["release_db"](conn)
