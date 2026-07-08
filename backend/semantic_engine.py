"""
semantic_engine.py — 语义检索引擎（embedding + 余弦排序）

纯逻辑 + 一个 embed 入口：
  embed(text)            -> list[float]    复用 llm_provider.embed_text（真实/mock 自动切换）
  cosine(a, b)           -> float
  rank(query_vec, rows)  -> list[dict]     按余弦相似度降序（仅比较同维向量）

不访问数据库；不做跨用户逻辑（隔离由路由层 WHERE email=%s 保证）。
"""
from __future__ import annotations

import hashlib
import logging
import math
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MOCK_DIM = 16


def _mock_embed(text: str, dim: int = MOCK_DIM) -> List[float]:
    """16 维确定性伪嵌入（offline 安全；与 llm_provider Mock 同思路）。"""
    h = hashlib.sha256((text or "").encode("utf-8")).hexdigest()
    return [((int(h[i % len(h)], 16) / 15.0) * 2 - 1) for i in range(dim)]


def _real_embed_configured() -> bool:
    """True when a real embedding provider is configured (i.e. not Mock)."""
    for mod in ("llm_provider", "backend.llm_provider"):
        try:
            return bool(__import__(mod, fromlist=["_real_configured"])._real_configured())
        except Exception:
            continue
    return False


def embed(text: str) -> Optional[List[float]]:
    """优先复用项目的 embed_text（OpenAI 兼容）。
    当配置了真实 provider 但其嵌入不可用（embed_text 返回 None）时，返回 None 表示
    『嵌入不可用』，而不是回退到维度不同的 16 维 mock —— 否则会与已存的高维向量维度不符，
    让相似度检索被静默清空。仅在离线/Mock 模式下才回退本地一致的 16 维 mock。"""
    txt = (text or "").strip()
    if not txt:
        return _mock_embed("")
    got_none = False
    for mod in ("llm_provider", "backend.llm_provider"):
        try:
            embed_text = __import__(mod, fromlist=["embed_text"]).embed_text
        except Exception:
            continue
        try:
            vec = embed_text(txt)
        except Exception:
            vec = None
        if isinstance(vec, list) and vec:
            return [float(x) for x in vec]
        got_none = True
        break
    if got_none and _real_embed_configured():
        logger.warning("[semantic_engine] real embedding unavailable; "
                       "degrading to unranked (no mismatched-dim mock)")
        return None
    return _mock_embed(txt)


def cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _unranked(rows: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    return [{k: v for k, v in r.items() if k != "embedding"} for r in (rows or [])][:limit]


def rank(query_vec: Optional[List[float]], rows: List[Dict[str, Any]], limit: int = 5,
         min_similarity: float = 0.0) -> List[Dict[str, Any]]:
    """rows: [{..., 'embedding': list[float]}]。仅比较与 query 同维的向量。
    当 query_vec 不可用（None/空），或所有行的维度都与 query 不符（例如嵌入源漂移：
    query 为 mock 维、存储为真实维），降级为『不排序直通』返回，而非静默清空结果。"""
    rows = rows or []
    if not query_vec:
        return _unranked(rows, limit)
    qdim = len(query_vec)
    same_dim = [r for r in rows
                if isinstance(r.get("embedding"), list) and len(r["embedding"]) == qdim]
    if rows and not same_dim:
        return _unranked(rows, limit)
    scored: List[Dict[str, Any]] = []
    for r in same_dim:
        sim = cosine(query_vec, r["embedding"])
        if sim >= min_similarity:
            item = {k: v for k, v in r.items() if k != "embedding"}
            item["similarity"] = round(sim, 4)
            scored.append(item)
    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:limit]


def content_id_for(content: str) -> str:
    """缺省 source_id：内容哈希，便于 upsert 去重。"""
    return hashlib.sha256((content or "").encode("utf-8")).hexdigest()[:32]


def meta() -> Dict[str, Any]:
    return {"mock_dim": MOCK_DIM, "embed_entry": "llm_provider.embed_text",
            "note": "embedding stored as JSONB; cosine computed in Python; user-scoped only"}
