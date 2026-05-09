#!/usr/bin/env python3
import json
import time

import faiss
import numpy as np
import requests

SILICONFLOW_API_KEY = "sk-dibqkgftealwtpzskkhhovdscfkzmerzxiewpyssnbdcxdeg"
SILICONFLOW_EMBEDDING_URL = "https://api.siliconflow.cn/v1/embeddings"
SILICONFLOW_EMBEDDING_MODEL = "BAAI/bge-m3"
QDRANT_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwic3ViamVjdCI6ImFwaS1rZXk6MTkzZjM0OGYtNDY3Zi00NmY3LTliODctNTIxOTZkMzg5NTljIn0.jCb9HCRwG3R9xgSS5cCXr-lPZmw-QrrIFQa2XuI5t-s"
QDRANT_URL = "https://40d5f2bb-1da4-44b5-9510-d73b62caab61.us-west-1-0.aws.cloud.qdrant.io"
QDRANT_COLLECTION = "bible_bilingual"

REQUEST_TIMEOUT = 60
MAX_RETRIES = 5
RETRY_BACKOFF = 2.0
DEFAULT_TOP_K = 5
DEFAULT_LANGUAGE = "cuv"


def post_with_retry(url: str, payload: dict, headers: dict) -> dict:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF ** attempt
                print(f"    ↻ HTTP {status}, retry {attempt}/{MAX_RETRIES - 1}, wait {wait:.1f}s")
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
                print(f"    ↻ connection retry {attempt}/{MAX_RETRIES - 1}, wait {wait:.1f}s")
                time.sleep(wait)
                continue
            raise


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


def get_embedding(text: str) -> np.ndarray:
    payload = {
        "model": SILICONFLOW_EMBEDDING_MODEL,
        "input": text,
        "encoding_format": "float",
    }
    data = post_with_retry(SILICONFLOW_EMBEDDING_URL, payload, siliconflow_headers())
    embedding = np.asarray([data["data"][0]["embedding"]], dtype=np.float32)
    faiss.normalize_L2(embedding)
    return embedding


def qdrant_search(query_vec: np.ndarray, vector_name: str, top_k: int) -> list[dict]:
    url = f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}/points/search"
    payload = {
        "vector": {"name": vector_name, "vector": query_vec[0].tolist()},
        "limit": top_k,
        "with_payload": True,
        "with_vector": False,
    }
    data = post_with_retry(url, payload, qdrant_headers())
    return data.get("result", [])


def search_bilingual(query_text: str, top_k: int = DEFAULT_TOP_K, language: str = DEFAULT_LANGUAGE) -> list[dict]:
    vector_name = "vector_cuv" if language == "cuv" else "vector_esv"
    query_vec = get_embedding(query_text)
    points = qdrant_search(query_vec, vector_name, top_k)
    results = []
    for point in points:
        payload = point.get("payload", {})
        results.append(
            {
                "pk_id": payload.get("pk_id"),
                "book_name_zh": payload.get("book_name_zh"),
                "book_name_en": payload.get("book_name_en"),
                "chapter": payload.get("chapter"),
                "verse": payload.get("verse"),
                "raw_text_cuv": payload.get("raw_text_cuv"),
                "raw_text_esv": payload.get("raw_text_esv"),
                "score": float(point.get("score", 0.0)),
                "vector_name": vector_name,
            }
        )
    return results


if __name__ == "__main__":
    query = "mercy and redemption in suffering"
    print(json.dumps(search_bilingual(query, top_k=5, language="esv"), ensure_ascii=False, indent=2))
