"""自高之事 知识图谱 + RAG 引擎 / Stronghold Knowledge + RAG engine.

为福音重构、经文推荐、操练、祷告生成提供统一知识上下文。
设计取舍：嵌入以 JSONB 存储、Python 内做 cosine（语料很小，无需 pgvector）；
未配置嵌入 key 时退化为关键词检索（始终可用）。配置 OPENAI_API_KEY 后升级为向量检索。

Conventions follow routers/spiritual_formation.py (psycopg2 sync, email user_id,
init_*_router loads a .sql schema). Pure retrieval fns are module-level + testable.
"""
from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/api/strongholds/rag", tags=["strongholds-rag"])
_state: Dict[str, Any] = {}

EMBED_MODEL = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")

PASTORAL_SAFETY_CONTEXT = {
    "riskRules": [
        "Detect self-harm / abuse / crisis first; do not run normal analysis on crisis input.",
        "Distinguish pain, weakness, temptation, and sin; do not call all suffering sin.",
        "For suffering, prioritize lament and comfort before correction.",
    ],
    "forbiddenClaims": [
        "Do not say 'God told you' or speak for God.",
        "Do not shame the user or use guilt to manipulate.",
        "Do not replace Scripture, the church, pastoral care, or professional help.",
    ],
    "escalationGuidance": [
        "For crisis, urge contacting local emergency services and a trusted person now.",
        "For trauma or recurring bondage, recommend a mature pastor, counselor, or accountability partner.",
    ],
}


# ──────────────────────────────────────────────────────────────────────────
# Pure retrieval (no DB) — testable
# ──────────────────────────────────────────────────────────────────────────
_LATIN = re.compile(r"[a-z0-9]+")
_CJK = re.compile(r"[一-鿿]")


def tokenize(text: str) -> set:
    """Latin words + CJK unigrams + CJK bigrams (cheap bilingual tokenization)."""
    t = str(text or "").lower()
    tokens = set(_LATIN.findall(t))
    cjk = _CJK.findall(t)
    tokens.update(cjk)
    for i in range(len(cjk) - 1):
        tokens.add(cjk[i] + cjk[i + 1])
    return tokens


def keyword_score(query_tokens: set, doc: dict) -> float:
    tags = " ".join(doc.get("tags") or [])
    tag_tokens = tokenize(tags)
    body_tokens = tokenize(f"{doc.get('title','')} {doc.get('content','')}")
    score = 3.0 * len(query_tokens & tag_tokens) + 1.0 * len(query_tokens & body_tokens)
    return score


def cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def retrieve(
    query: str,
    docs: List[dict],
    stronghold_codes: Optional[List[str]] = None,
    doctrine_codes: Optional[List[str]] = None,
    top_k: int = 8,
    query_embedding: Optional[List[float]] = None,
) -> List[dict]:
    """Rank docs by vector similarity (if query_embedding + doc embeddings) else
    keyword overlap, boosted by matching stronghold/doctrine codes. Pure."""
    sh = set(stronghold_codes or [])
    dc = set(doctrine_codes or [])
    qt = tokenize(query)
    scored = []
    for d in docs:
        if query_embedding and d.get("embedding"):
            base = cosine(query_embedding, d["embedding"]) * 100.0
        else:
            base = keyword_score(qt, d)
        boost = 0.0
        if sh & set(d.get("stronghold_codes") or []):
            boost += 6.0
        if dc & set(d.get("doctrine_codes") or []):
            boost += 4.0
        total = base + boost
        if total > 0:
            scored.append({**d, "score": round(total, 3)})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def build_context_bundle(
    query: str,
    retrieved: List[dict],
    stronghold_codes: Optional[List[str]] = None,
    doctrine_codes: Optional[List[str]] = None,
    need_type: Optional[str] = None,
) -> dict:
    stronghold_ctx = [
        {"code": (d.get("stronghold_codes") or [None])[0], "title": d["title"], "content": d["content"]}
        for d in retrieved if d.get("doc_type") == "stronghold_pattern_note"
    ]
    doctrine_ctx = [
        {"code": (d.get("doctrine_codes") or [None])[0], "title": d["title"], "content": d["content"]}
        for d in retrieved if d.get("doc_type") == "doctrine_note"
    ]
    return {
        "query": query,
        "needType": need_type,
        "strongholdContext": stronghold_ctx,
        "doctrineContext": doctrine_ctx,
        "retrievedDocuments": [
            {"id": d["id"], "title": d["title"], "docType": d.get("doc_type"), "score": d.get("score", 0), "content": d["content"]}
            for d in retrieved
        ],
        "pastoralSafetyContext": PASTORAL_SAFETY_CONTEXT,
    }


# ──────────────────────────────────────────────────────────────────────────
# Embedding client (env-gated; None => keyword mode)
# ──────────────────────────────────────────────────────────────────────────
def embeddings_enabled() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def embed_texts(texts: List[str]) -> Optional[List[List[float]]]:
    """Return embeddings via OpenAI REST if OPENAI_API_KEY is set, else None.
    Network/errors are tolerated (returns None) so the system never hard-fails."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key or not texts:
        return None
    try:
        import urllib.request

        body = json.dumps({"model": EMBED_MODEL, "input": texts}).encode("utf-8")
        req = urllib.request.Request(
            os.environ.get("OPENAI_EMBED_URL", "https://api.openai.com/v1/embeddings"),
            data=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return [row["embedding"] for row in data["data"]]
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────
# Wiring + DB
# ──────────────────────────────────────────────────────────────────────────
def init_stronghold_rag_router(*, get_db, release_db, get_session_user, root_dir=None, **_ignore) -> None:
    _state.update(get_db=get_db, release_db=release_db, get_session_user=get_session_user, root_dir=root_dir)
    if get_db and release_db:
        _init_tables(get_db, release_db, root_dir)


def _init_tables(get_db, release_db, root_dir=None) -> None:
    schema_path = Path(root_dir or Path(__file__).resolve().parents[2]) / "backend" / "stronghold_rag_schema.sql"
    sql = schema_path.read_text(encoding="utf-8")
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        release_db(conn)


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
        return obj


def _load_docs() -> List[dict]:
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, doc_type, title, content, lang, tags, stronghold_codes, doctrine_codes, embedding "
                "FROM stronghold_rag_documents"
            )
            rows = cur.fetchall()
        return [
            {
                "id": r[0], "doc_type": r[1], "title": r[2], "content": r[3], "lang": r[4],
                "tags": r[5] or [], "stronghold_codes": r[6] or [], "doctrine_codes": r[7] or [],
                "embedding": r[8],
            }
            for r in rows
        ]
    finally:
        _state["release_db"](conn)


def _mode(docs: List[dict]) -> str:
    if not docs:
        return "empty"
    if embeddings_enabled() and any(d.get("embedding") for d in docs):
        return "vector"
    return "keyword"


# ──────────────────────────────────────────────────────────────────────────
# Models + endpoints
# ──────────────────────────────────────────────────────────────────────────
class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class SearchIn(CamelModel):
    query: str = Field(default="", max_length=4000)
    stronghold_codes: List[str] = Field(default_factory=list, alias="strongholdCodes", max_length=30)
    doctrine_codes: List[str] = Field(default_factory=list, alias="doctrineCodes", max_length=30)
    top_k: int = Field(default=8, alias="topK", ge=1, le=30)


class ContextIn(SearchIn):
    need_type: Optional[str] = Field(default=None, alias="needType", max_length=40)


@router.get("/status")
def rag_status(request: Request):
    _require_user(request)
    docs = _load_docs()
    return {"documents": len(docs), "mode": _mode(docs), "embedModel": EMBED_MODEL if embeddings_enabled() else None}


@router.post("/ingest")
def rag_ingest(request: Request):
    """Idempotently seed the knowledge corpus. Computes embeddings if a key is set."""
    _require_user(request)
    try:
        from stronghold_knowledge import corpus_documents
    except ImportError:  # pragma: no cover
        from backend.stronghold_knowledge import corpus_documents

    docs = corpus_documents()
    vectors = embed_texts([d["content"] for d in docs]) if embeddings_enabled() else None

    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            for i, d in enumerate(docs):
                emb = vectors[i] if vectors else None
                cur.execute(
                    """
                    INSERT INTO stronghold_rag_documents
                      (id, doc_type, title, content, lang, tags, stronghold_codes, doctrine_codes, embedding, embed_model)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (id) DO UPDATE SET
                      doc_type=EXCLUDED.doc_type, title=EXCLUDED.title, content=EXCLUDED.content,
                      lang=EXCLUDED.lang, tags=EXCLUDED.tags, stronghold_codes=EXCLUDED.stronghold_codes,
                      doctrine_codes=EXCLUDED.doctrine_codes, embedding=EXCLUDED.embedding,
                      embed_model=EXCLUDED.embed_model, updated_at=NOW()
                    """,
                    (
                        d["id"], d["doc_type"], d["title"], d["content"], d.get("lang", "zh"),
                        d.get("tags", []), d.get("stronghold_codes", []), d.get("doctrine_codes", []),
                        _Json(emb) if emb is not None else None, EMBED_MODEL if emb is not None else None,
                    ),
                )
        conn.commit()
    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Ingest failed: {exc}")
    finally:
        _state["release_db"](conn)

    return {"ingested": len(docs), "mode": "vector" if vectors else "keyword", "embeddings": bool(vectors)}


@router.post("/search")
def rag_search(payload: SearchIn, request: Request):
    _require_user(request)
    docs = _load_docs()
    if not docs:
        return {"mode": "empty", "results": [], "hint": "POST /api/strongholds/rag/ingest to seed the corpus."}
    qvec = embed_texts([payload.query])[0] if (embeddings_enabled() and payload.query) else None
    results = retrieve(payload.query, docs, payload.stronghold_codes, payload.doctrine_codes, payload.top_k, qvec)
    return {
        "mode": _mode(docs),
        "results": [{"id": r["id"], "title": r["title"], "docType": r["doc_type"], "score": r["score"], "content": r["content"]} for r in results],
    }


@router.post("/context")
def rag_context(payload: ContextIn, request: Request):
    _require_user(request)
    docs = _load_docs()
    if not docs:
        return {"mode": "empty", "context": None, "hint": "POST /api/strongholds/rag/ingest to seed the corpus."}
    qvec = embed_texts([payload.query])[0] if (embeddings_enabled() and payload.query) else None
    results = retrieve(payload.query, docs, payload.stronghold_codes, payload.doctrine_codes, payload.top_k, qvec)
    bundle = build_context_bundle(payload.query, results, payload.stronghold_codes, payload.doctrine_codes, payload.need_type)
    return {"mode": _mode(docs), "context": bundle}
