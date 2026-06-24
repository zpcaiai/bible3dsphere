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
import math
from typing import Any, Dict, List, Optional

MOCK_DIM = 16


def _mock_embed(text: str, dim: int = MOCK_DIM) -> List[float]:
    """16 维确定性伪嵌入（offline 安全；与 llm_provider Mock 同思路）。"""
    h = hashlib.sha256((text or "").encode("utf-8")).hexdigest()
    return [((int(h[i % len(h)], 16) / 15.0) * 2 - 1) for i in range(dim)]


def embed(text: str) -> List[float]:
    """优先复用项目的 embed_text（OpenAI 兼容，未配置则其内部回退 mock）；
    任何导入/调用失败再回退本地 mock，保证 index 与 query 走同一路径。"""
    txt = (text or "").strip()
    if not txt:
        return _mock_embed("")
    try:
        from llm_provider import embed_text  # type: ignore
        vec = embed_text(txt)
        if isinstance(vec, list) and vec:
            return [float(x) for x in vec]
    except Exception:
        pass
    try:
        from backend.llm_provider import embed_text  # type: ignore
        vec = embed_text(txt)
        if isinstance(vec, list) and vec:
            return [float(x) for x in vec]
    except Exception:
        pass
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


def rank(query_vec: List[float], rows: List[Dict[str, Any]], limit: int = 5,
         min_similarity: float = 0.0) -> List[Dict[str, Any]]:
    """rows: [{..., 'embedding': list[float]}]。仅比较与 query 同维的向量。"""
    qdim = len(query_vec or [])
    scored: List[Dict[str, Any]] = []
    for r in rows or []:
        emb = r.get("embedding")
        if not isinstance(emb, list) or len(emb) != qdim:
            continue
        sim = cosine(query_vec, emb)
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
