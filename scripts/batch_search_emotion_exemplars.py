#!/usr/bin/env python3
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

NEURONPEDIA_API_KEY = "sk-np-tbNBLkZ89zQRzjX0Wak0B8ZCXuDaYXkCmV2Uyagf3qc0"
NEURONPEDIA_API_BASE = "https://www.neuronpedia.org/api"
SILICONFLOW_API_KEY = "sk-dibqkgftealwtpzskkhhovdscfkzmerzxiewpyssnbdcxdeg"
SILICONFLOW_EMBEDDING_URL = "https://api.siliconflow.cn/v1/embeddings"
SILICONFLOW_EMBEDDING_MODEL = "BAAI/bge-m3"
QDRANT_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwic3ViamVjdCI6ImFwaS1rZXk6MTkzZjM0OGYtNDY3Zi00NmY3LTliODctNTIxOTZkMzg5NTljIn0.jCb9HCRwG3R9xgSS5cCXr-lPZmw-QrrIFQa2XuI5t-s"
QDRANT_URL = "https://40d5f2bb-1da4-44b5-9510-d73b62caab61.us-west-1-0.aws.cloud.qdrant.io"
QDRANT_COLLECTION = "bible_bilingual"

REQUEST_TIMEOUT = 60
MAX_RETRIES = 5
RETRY_BACKOFF = 2.0
TOP_K = 5
DEFAULT_FEATURES_FILE = "emotion_features_map.json"
DEFAULT_BIBLE_CONFIG = "bible_bilingual_config.json"
DEFAULT_OUTPUT_FILE = "emotion_exemplar_verse_matches.json"


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


def get_with_retry(url: str, headers: dict) -> dict:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
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


def neuronpedia_headers() -> dict:
    return {"x-api-key": NEURONPEDIA_API_KEY} if NEURONPEDIA_API_KEY else {}


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


def get_embeddings(texts: list[str]) -> np.ndarray:
    if not texts:
        raise ValueError("缺少 exemplar texts")
    payload = {
        "model": SILICONFLOW_EMBEDDING_MODEL,
        "input": texts,
        "encoding_format": "float",
    }
    data = post_with_retry(SILICONFLOW_EMBEDDING_URL, payload, siliconflow_headers())
    embeddings = np.asarray([item["embedding"] for item in data["data"]], dtype=np.float32)
    return l2_normalize(embeddings)


def l2_normalize(vectors: np.ndarray) -> np.ndarray:
    if vectors.size == 0:
        return vectors
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return (vectors / norms).astype(np.float32)


def mean_emotion_vector(texts: list[str]) -> np.ndarray:
    embeddings = get_embeddings(texts)
    mean_vec = np.mean(embeddings, axis=0, keepdims=True).astype(np.float32)
    return l2_normalize(mean_vec)


def fetch_feature_detail(feature: dict) -> dict:
    url = f"{NEURONPEDIA_API_BASE}/feature/{feature['model_id']}/{feature['layer']}/{feature['feature_id']}"
    return get_with_retry(url, neuronpedia_headers())


def token_to_text(token: dict | str) -> str:
    if isinstance(token, str):
        return token
    if isinstance(token, dict):
        return str(token.get("token") or token.get("text") or token.get("valueString") or "")
    return ""


def build_exemplar_texts(feature: dict, detail: dict, max_samples: int = 8) -> list[str]:
    texts = []
    for act in detail.get("activations", [])[:max_samples]:
        tokens = act.get("tokens", [])
        text = "".join(token_to_text(tok) for tok in tokens).strip()
        if text:
            texts.append(text)
    if not texts:
        explanation = str(feature.get("explanation", "")).strip()
        if explanation:
            texts.append(explanation)
    if not texts:
        texts.append(str(feature.get("source_keyword", "emotion")))
    return texts


def qdrant_search_named_vector(query_vec: np.ndarray, vector_name: str, limit: int) -> list[dict]:
    url = f"{QDRANT_URL}/collections/{QDRANT_COLLECTION}/points/search"
    payload = {
        "vector": {"name": vector_name, "vector": query_vec[0].tolist()},
        "limit": limit,
        "with_payload": True,
        "with_vector": False,
    }
    data = post_with_retry(url, payload, qdrant_headers())
    return data.get("result", [])


def search_bilingual_emotion_vector(query_vec: np.ndarray, top_k: int = TOP_K) -> dict:
    cuv_points = qdrant_search_named_vector(query_vec, "vector_cuv", top_k)
    esv_points = qdrant_search_named_vector(query_vec, "vector_esv", top_k)
    return {
        "cuv": [
            {
                "pk_id": p.get("payload", {}).get("pk_id"),
                "book_name": p.get("payload", {}).get("book_name_zh"),
                "chapter": p.get("payload", {}).get("chapter"),
                "verse": p.get("payload", {}).get("verse"),
                "raw_text": p.get("payload", {}).get("raw_text_cuv"),
                "score": float(p.get("score", 0.0)),
            }
            for p in cuv_points
        ],
        "esv": [
            {
                "pk_id": p.get("payload", {}).get("pk_id"),
                "book_name": p.get("payload", {}).get("book_name_en"),
                "chapter": p.get("payload", {}).get("chapter"),
                "verse": p.get("payload", {}).get("verse"),
                "raw_text": p.get("payload", {}).get("raw_text_esv"),
                "score": float(p.get("score", 0.0)),
            }
            for p in esv_points
        ],
    }


def load_features(features_path: str) -> list[dict]:
    with open(features_path, "r", encoding="utf-8") as f:
        return json.load(f)


def batch_search_emotion_exemplars(
    features_path: str = DEFAULT_FEATURES_FILE,
    output_path: str = DEFAULT_OUTPUT_FILE,
    top_k: int = TOP_K,
) -> list[dict]:
    features = load_features(features_path)
    results = []
    print(f"开始按 exemplars/activations 批量检索 {len(features)} 个 features")
    for i, feature in enumerate(features, start=1):
        print(f"[{i}/{len(features)}] {feature.get('layer')}:{feature.get('feature_id')}")
        detail = fetch_feature_detail(feature)
        exemplar_texts = build_exemplar_texts(feature, detail)
        emotion_vec = mean_emotion_vector(exemplar_texts)
        matches = search_bilingual_emotion_vector(emotion_vec, top_k=top_k)
        results.append(
            {
                "feature_id": feature.get("feature_id"),
                "model_id": feature.get("model_id"),
                "layer": feature.get("layer"),
                "source_keyword": feature.get("source_keyword"),
                "explanation": feature.get("explanation"),
                "exemplar_texts": exemplar_texts,
                "matches": matches,
            }
        )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"完成，结果已保存到: {output_path}")
    return results


if __name__ == "__main__":
    batch_search_emotion_exemplars()
