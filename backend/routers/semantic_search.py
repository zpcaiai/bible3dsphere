"""
Semantic Search router — 语义检索 (/api/semantic)

  GET  /api/semantic/meta              引擎信息
  POST /api/semantic/index             把一段用户文本写入语义索引（embed + upsert）
  GET  /api/semantic/search?q=...      在本人历史文本中做语义检索（按 email 隔离）

附加能力：不改既有写路径。其它路由可 import index_content() 在用户写反思/记忆时best-effort建索引。
embedding 存 JSONB，余弦在 Python 计算；未配置嵌入服务时走 mock，offline 可用。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

try:
    from backend import semantic_engine as engine
except Exception:  # pragma: no cover
    import semantic_engine as engine  # type: ignore

router = APIRouter(prefix="/api/semantic", tags=["semantic"])
_state: Dict[str, Any] = {}

_ALLOWED_SOURCES = {"reflection", "formation_memory", "examen", "journal",
                    "checkin", "prayer", "diagnostic", "generic"}


def init_semantic_search_router(*, get_db, release_db, get_session_user, to_shanghai_iso) -> None:
    _state.update(locals())


def _require_user(request: Request) -> dict:
    user = _state["get_session_user"](request)
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _Json(obj):
    try:
        from psycopg2.extras import Json
        return Json(obj)
    except Exception:
        import json as _json
        return _json.dumps(obj)


def index_content(email: str, source_type: str, content: str,
                  source_id: Optional[str] = None) -> Dict[str, Any]:
    """embed + upsert 一条语义索引。可被其它路由复用（需先 init 注入 get_db）。"""
    get_db = _state.get("get_db")
    release_db = _state.get("release_db")
    content = (content or "").strip()
    if not content:
        return {"ok": False, "reason": "empty"}
    source_id = source_id or engine.content_id_for(content)
    vec = engine.embed(content)
    dim = len(vec)

    if get_db is None:
        return {"ok": True, "persisted": False, "dim": dim, "source_id": source_id}

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO semantic_index "
                "(email, source_type, source_id, content, embedding, model, dim) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (email, source_type, source_id) DO UPDATE SET "
                " content=EXCLUDED.content, embedding=EXCLUDED.embedding, "
                " model=EXCLUDED.model, dim=EXCLUDED.dim, updated_at=now() "
                "RETURNING id",
                (email, source_type, source_id, content[:8000], _Json(vec), "embed_text", dim),
            )
            new_id = cur.fetchone()[0]
            conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        return {"ok": False, "persisted": False, "error": str(exc)}
    finally:
        release_db(conn)
    return {"ok": True, "persisted": True, "id": new_id, "dim": dim, "source_id": source_id}


class IndexBody(BaseModel):
    source_type: str = Field(default="reflection", max_length=40)
    source_id: Optional[str] = Field(default=None, max_length=120)
    content: str = Field(..., min_length=1, max_length=8000)


@router.get("/meta")
def get_meta() -> dict:
    return {"ok": True, "allowed_sources": sorted(_ALLOWED_SOURCES), **engine.meta()}


@router.post("/index")
def index(request: Request, body: IndexBody) -> dict:
    user = _require_user(request)
    st = body.source_type if body.source_type in _ALLOWED_SOURCES else "generic"
    res = index_content(email=user["email"], source_type=st,
                        content=body.content, source_id=body.source_id)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res.get("error") or res.get("reason") or "index failed")
    return res


@router.get("/search")
def search(request: Request, q: str = Query(..., min_length=1, max_length=2000),
           source_type: Optional[str] = Query(default=None),
           limit: int = Query(default=5, ge=1, le=25)) -> dict:
    user = _require_user(request)
    qvec = engine.embed(q)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            if source_type:
                cur.execute(
                    "SELECT source_type, source_id, content, embedding, created_at "
                    "FROM semantic_index WHERE email=%s AND source_type=%s "
                    "AND embedding IS NOT NULL ORDER BY created_at DESC LIMIT 2000",
                    (user["email"], source_type),
                )
            else:
                cur.execute(
                    "SELECT source_type, source_id, content, embedding, created_at "
                    "FROM semantic_index WHERE email=%s AND embedding IS NOT NULL "
                    "ORDER BY created_at DESC LIMIT 2000",
                    (user["email"],),
                )
            rows = cur.fetchall()
    finally:
        _state["release_db"](conn)

    to_iso = _state["to_shanghai_iso"]
    candidates = [{
        "source_type": r[0], "source_id": r[1], "content": r[2],
        "embedding": r[3], "created_at": to_iso(r[4]),
    } for r in rows]
    ranked = engine.rank(qvec, candidates, limit=limit)
    for item in ranked:  # 截断内容用于展示
        item["snippet"] = (item.get("content") or "")[:240]
        item.pop("content", None)
    return {"ok": True, "query": q, "count": len(ranked), "items": ranked}
