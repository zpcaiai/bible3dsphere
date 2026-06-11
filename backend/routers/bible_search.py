"""
经文语义搜索 API —— 复用仓库根目录的双语 bge-m3 向量资产。
"找那节讲压伤的芦苇的经文" → 语义检索；无 embedding key/熔断时回退关键词检索。

资产（仓库根目录，main.py 启动时已校验存在）：
  bible_bilingual_metadata.pkl        31101 节 DataFrame（pk_id/书卷/章节/中英文文本）
  bible_bilingual_vector_cuv.npy      31101×1024 float（和合本向量，已归一化，内积即余弦）
  bible_bilingual_vector_esv.npy      31101×1024 float（ESV 向量）

向量矩阵用 numpy mmap 加载：不占常驻内存，单次查询 31k×1024 内积毫秒级。
"""
from __future__ import annotations

import logging
import os
import re
import threading
from typing import Any, Optional

from fastapi import APIRouter, Query

from core.ratelimit import limiter
from fastapi import Request

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/bible", tags=["bible-search"])

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo 根 = backend 上一级
_REPO = os.path.dirname(_ROOT) if os.path.basename(_ROOT) == "backend" else _ROOT

_lock = threading.Lock()
_meta = None          # pandas DataFrame
_vectors: dict = {}   # lang -> np.memmap

# OSIS 三字码 → 中文书名（metadata 的 book_name_zh 实为英文全名，这里补真正的中文）
BOOK_ZH = {
    "GEN": "创世记", "EXO": "出埃及记", "LEV": "利未记", "NUM": "民数记", "DEU": "申命记",
    "JOS": "约书亚记", "JDG": "士师记", "RUT": "路得记", "1SA": "撒母耳记上", "2SA": "撒母耳记下",
    "1KI": "列王纪上", "2KI": "列王纪下", "1CH": "历代志上", "2CH": "历代志下", "EZR": "以斯拉记",
    "NEH": "尼希米记", "EST": "以斯帖记", "JOB": "约伯记", "PSA": "诗篇", "PRO": "箴言",
    "ECC": "传道书", "SNG": "雅歌", "ISA": "以赛亚书", "JER": "耶利米书", "LAM": "耶利米哀歌",
    "EZK": "以西结书", "DAN": "但以理书", "HOS": "何西阿书", "JOL": "约珥书", "AMO": "阿摩司书",
    "OBA": "俄巴底亚书", "JON": "约拿书", "MIC": "弥迦书", "NAM": "那鸿书", "HAB": "哈巴谷书",
    "ZEP": "西番雅书", "HAG": "哈该书", "ZEC": "撒迦利亚书", "MAL": "玛拉基书",
    "MAT": "马太福音", "MRK": "马可福音", "LUK": "路加福音", "JHN": "约翰福音", "ACT": "使徒行传",
    "ROM": "罗马书", "1CO": "哥林多前书", "2CO": "哥林多后书", "GAL": "加拉太书", "EPH": "以弗所书",
    "PHP": "腓立比书", "COL": "歌罗西书", "1TH": "帖撒罗尼迦前书", "2TH": "帖撒罗尼迦后书",
    "1TI": "提摩太前书", "2TI": "提摩太后书", "TIT": "提多书", "PHM": "腓利门书", "HEB": "希伯来书",
    "JAS": "雅各书", "1PE": "彼得前书", "2PE": "彼得后书", "1JN": "约翰一书", "2JN": "约翰二书",
    "3JN": "约翰三书", "JUD": "犹大书", "REV": "启示录",
}


def _load_meta():
    global _meta
    if _meta is not None:
        return _meta
    with _lock:
        if _meta is None:
            import pickle
            with open(os.path.join(_REPO, "bible_bilingual_metadata.pkl"), "rb") as f:
                _meta = pickle.load(f)
    return _meta


def _load_vectors(lang: str):
    if lang in _vectors:
        return _vectors[lang]
    with _lock:
        if lang not in _vectors:
            import numpy as np
            path = os.path.join(_REPO, f"bible_bilingual_vector_{lang}.npy")
            _vectors[lang] = np.load(path, mmap_mode="r")
    return _vectors[lang]


def _dto(row, score: float) -> dict[str, Any]:
    code = str(row["book_name_en"])
    return {
        "pkId": row["pk_id"],
        "bookCode": code,
        "bookZh": BOOK_ZH.get(code, str(row["book_name_zh"])),
        "bookEn": str(row["book_name_zh"]),  # metadata 此列实为英文全名
        "chapter": int(row["chapter"]),
        "verse": int(row["verse"]),
        "textCuv": re.sub(r"\s+", "", str(row["raw_text_cuv"])).replace("，", "，"),
        "textEsv": str(row["raw_text_esv"]),
        "score": round(float(score), 4),
    }


def _semantic_search(q: str, lang: str, top: int) -> Optional[list[dict[str, Any]]]:
    """语义检索；embedding 不可用（无 key/熔断返回零向量）时返回 None 触发回退。"""
    try:
        import numpy as np
        import sys
        if _REPO not in sys.path:
            sys.path.insert(0, _REPO)
        from query_emotion_verses import get_embeddings
        vec = np.asarray(get_embeddings([q]), dtype="float32")[0]
        norm = float(np.linalg.norm(vec))
        if norm < 1e-6:  # 熔断零向量
            return None
        vec = vec / norm
        V = _load_vectors(lang)
        scores = np.asarray(V @ vec)
        k = min(top, len(scores))
        idx = np.argpartition(-scores, k - 1)[:k]
        idx = idx[np.argsort(-scores[idx])]
        meta = _load_meta()
        return [_dto(meta.iloc[int(i)], scores[int(i)]) for i in idx]
    except Exception as e:
        logger.warning("bible-search semantic: %s", e)
        return None


def _keyword_search(q: str, top: int) -> list[dict[str, Any]]:
    """回退：关键词检索（中英文都扫，按命中词数排序）。"""
    meta = _load_meta()
    terms = [w for w in re.split(r"[\s,，。、；;]+", q.strip()) if w]
    if not terms:
        return []
    results: list[tuple[float, int]] = []
    cuv = meta["raw_text_cuv"].astype(str)
    esv = meta["raw_text_esv"].astype(str).str.lower()
    import numpy as np
    score = np.zeros(len(meta))
    for term in terms[:8]:
        zh = term.replace(" ", "")
        if re.search(r"[一-鿿]", zh):
            # 和合本原文含全角空格：去空格后匹配
            hits = cuv.str.replace(r"\s+", "", regex=True).str.contains(re.escape(zh), regex=True)
        else:
            hits = esv.str.contains(re.escape(term.lower()), regex=True)
        score += hits.to_numpy().astype(float)
    order = np.argsort(-score)[:top]
    return [_dto(meta.iloc[int(i)], score[int(i)]) for i in order if score[int(i)] > 0]


@router.get("/search")
@limiter.limit("30/minute")
def search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200),
    lang: str = Query("cuv"),
    top: int = Query(20, ge=1, le=50),
) -> dict[str, Any]:
    q = q.strip()[:200]
    lang = lang if lang in ("cuv", "esv") else "cuv"
    if not q:
        return {"success": False, "error": "empty query"}
    try:
        data = _semantic_search(q, lang, top)
        source = "semantic"
        if data is None:
            data = _keyword_search(q, top)
            source = "keyword"
        return {"success": True, "data": data, "source": source}
    except Exception as e:
        logger.warning("bible-search: %s", e)
        return {"success": False, "error": str(e)}
