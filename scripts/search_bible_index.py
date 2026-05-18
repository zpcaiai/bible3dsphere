#!/usr/bin/env python3
import json
import time
from pathlib import Path

import faiss
import numpy as np
import pandas as pd
import requests

QDRANT_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwic3ViamVjdCI6ImFwaS1rZXk6MTkzZjM0OGYtNDY3Zi00NmY3LTliODctNTIxOTZkMzg5NTljIn0.jCb9HCRwG3R9xgSS5cCXr-lPZmw-QrrIFQa2XuI5t-s"
QDRANT_URL = "https://40d5f2bb-1da4-44b5-9510-d73b62caab61.us-west-1-0.aws.cloud.qdrant.io"
QDRANT_COLLECTION = "bible_cuv"
SILICONFLOW_API_KEY = "sk-dibqkgftealwtpzskkhhovdscfkzmerzxiewpyssnbdcxdeg"
SILICONFLOW_EMBEDDING_URL = "https://api.siliconflow.cn/v1/embeddings"
SILICONFLOW_EMBEDDING_MODEL = "BAAI/bge-m3"

REQUEST_TIMEOUT = 60
MAX_RETRIES = 5
RETRY_BACKOFF = 2.0
DEFAULT_INDEX_PATH = "bible_cuv.index"
DEFAULT_METADATA_PATH = "bible_cuv_metadata.pkl"
DEFAULT_CONFIG_PATH = "bible_cuv_config.json"
DEFAULT_CANDIDATE_POOL = 50
DEFAULT_DENSE_WEIGHT = 0.85
DEFAULT_LEXICAL_WEIGHT = 0.15
DEFAULT_LEXICAL_TERMS = {
    "中保": 1.3,
    "挽回祭": 1.5,
    "赎罪": 1.4,
    "救赎": 1.3,
    "恩慈": 1.2,
    "怜悯": 1.2,
    "恩典": 1.1,
    "悔改": 1.1,
    "公义": 1.1,
    "圣洁": 1.1,
}


def siliconflow_headers() -> dict:
    return {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json",
    }


def qdrant_headers() -> dict:
    return {
        "api-key": QDRANT_API_KEY,
        "Content-Type": "application/json",
    }


def post_with_retry(url: str, payload: dict, headers: dict) -> dict:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF ** attempt
                print(f"↻ HTTP {status}, retry {attempt}/{MAX_RETRIES - 1}, wait {wait:.1f}s")
                time.sleep(wait)
                continue
            raise
        except (
            requests.exceptions.Timeout,
            requests.exceptions.SSLError,
            requests.exceptions.ConnectionError,
        ):
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF ** attempt
                print(f"↻ connection retry {attempt}/{MAX_RETRIES - 1}, wait {wait:.1f}s")
                time.sleep(wait)
                continue
            raise


def get_embedding(text: str) -> np.ndarray:
    payload = {
        "model": SILICONFLOW_EMBEDDING_MODEL,
        "input": text,
        "encoding_format": "float",
    }
    data = post_with_retry(
        SILICONFLOW_EMBEDDING_URL,
        payload,
        siliconflow_headers(),
    )
    embedding = np.asarray([data["data"][0]["embedding"]], dtype=np.float32)
    faiss.normalize_L2(embedding)
    return embedding


def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> dict:
    path = Path(config_path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def qdrant_search(
    query_vec: np.ndarray,
    limit: int,
    collection_name: str = QDRANT_COLLECTION,
) -> list[dict]:
    url = f"{QDRANT_URL}/collections/{collection_name}/points/search"
    payload = {
        "vector": query_vec[0].tolist(),
        "limit": limit,
        "with_payload": True,
        "with_vector": False,
    }
    data = post_with_retry(url, payload, qdrant_headers())
    return data.get("result", [])


def extract_query_terms(query_text: str, lexical_terms: dict[str, float]) -> dict[str, float]:
    return {
        term: weight for term, weight in lexical_terms.items() if term in query_text
    }


def compute_lexical_score(content: str, matched_terms: dict[str, float]) -> float:
    if not matched_terms:
        return 0.0
    score = 0.0
    for term, weight in matched_terms.items():
        if term in content:
            score += weight
    max_possible = sum(matched_terms.values())
    if max_possible <= 0:
        return 0.0
    return score / max_possible


def search_bible_hybrid(
    query_text: str,
    top_k: int = 5,
    index_path: str = DEFAULT_INDEX_PATH,
    metadata_path: str = DEFAULT_METADATA_PATH,
    config_path: str = DEFAULT_CONFIG_PATH,
    candidate_pool: int = DEFAULT_CANDIDATE_POOL,
    dense_weight: float = DEFAULT_DENSE_WEIGHT,
    lexical_weight: float = DEFAULT_LEXICAL_WEIGHT,
    lexical_terms: dict[str, float] | None = None,
    backend: str = "faiss",
    collection_name: str = QDRANT_COLLECTION,
) -> list[dict]:
    config = load_config(config_path)
    query_vec = get_embedding(query_text)

    terms = extract_query_terms(query_text, lexical_terms or DEFAULT_LEXICAL_TERMS)
    results = []

    if backend == "faiss":
        index = faiss.read_index(index_path)
        df = pd.read_pickle(metadata_path)

        if index.d != query_vec.shape[1]:
            raise ValueError(
                f"查询向量维度 {query_vec.shape[1]} 与索引维度 {index.d} 不一致"
            )

        pool_size = min(max(top_k, candidate_pool), len(df))
        distances, indices = index.search(query_vec.astype("float32"), pool_size)

        for i, idx in enumerate(indices[0]):
            row = df.iloc[idx]
            dense_score = float(distances[0][i])
            lexical_score = compute_lexical_score(str(row["content"]), terms)
            hybrid_score = dense_weight * dense_score + lexical_weight * lexical_score
            results.append(
                {
                    "id": row.get("id", f"{row['book_name']}{row['chapter']}:{row['verse']}"),
                    "verse": f"{row['book_name']} {row['chapter']}:{row['verse']}",
                    "content": row["content"],
                    "context_weight": row.get("context_weight", None),
                    "score": hybrid_score,
                    "dense_score": dense_score,
                    "lexical_score": lexical_score,
                    "matched_terms": list(terms.keys()),
                    "embedding_model": config.get("embedding_model", SILICONFLOW_EMBEDDING_MODEL),
                    "backend": "faiss",
                }
            )
    elif backend == "qdrant":
        pool_size = max(top_k, candidate_pool)
        points = qdrant_search(query_vec.astype("float32"), pool_size, collection_name)
        for point in points:
            payload = point.get("payload", {})
            content = str(payload.get("content", ""))
            dense_score = float(point.get("score", 0.0))
            lexical_score = compute_lexical_score(content, terms)
            hybrid_score = dense_weight * dense_score + lexical_weight * lexical_score
            results.append(
                {
                    "id": payload.get("id"),
                    "verse": f"{payload.get('book_name')} {payload.get('chapter')}:{payload.get('verse')}",
                    "content": content,
                    "context_weight": payload.get("context_weight", None),
                    "score": hybrid_score,
                    "dense_score": dense_score,
                    "lexical_score": lexical_score,
                    "matched_terms": list(terms.keys()),
                    "embedding_model": config.get("embedding_model", SILICONFLOW_EMBEDDING_MODEL),
                    "backend": "qdrant",
                }
            )
    else:
        raise ValueError(f"Unknown backend: {backend}")

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]


def search_bible(
    query_text: str,
    top_k: int = 5,
    index_path: str = DEFAULT_INDEX_PATH,
    metadata_path: str = DEFAULT_METADATA_PATH,
    config_path: str = DEFAULT_CONFIG_PATH,
    backend: str = "faiss",
    collection_name: str = QDRANT_COLLECTION,
) -> list[dict]:
    return search_bible_hybrid(
        query_text=query_text,
        top_k=top_k,
        index_path=index_path,
        metadata_path=metadata_path,
        config_path=config_path,
        backend=backend,
        collection_name=collection_name,
    )


if __name__ == "__main__":
    query = "一种看到他人受苦而产生的极度同情与救赎冲动"
    results = search_bible(query, top_k=5)
    print(json.dumps(results, ensure_ascii=False, indent=2))
