#!/usr/bin/env python3
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

QDRANT_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwic3ViamVjdCI6ImFwaS1rZXk6MTkzZjM0OGYtNDY3Zi00NmY3LTliODctNTIxOTZkMzg5NTljIn0.jCb9HCRwG3R9xgSS5cCXr-lPZmw-QrrIFQa2XuI5t-s"
QDRANT_URL = "https://40d5f2bb-1da4-44b5-9510-d73b62caab61.us-west-1-0.aws.cloud.qdrant.io"
QDRANT_COLLECTION = "bible_bilingual"

REQUEST_TIMEOUT = 60
MAX_RETRIES = 5
RETRY_BACKOFF = 2.0
UPSERT_BATCH_SIZE = 128


def qdrant_headers() -> dict:
    return {
        "api-key": QDRANT_API_KEY,
        "Content-Type": "application/json",
    }


def request_with_retry(method: str, url: str, payload: dict | None = None) -> dict:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.request(method=method, url=url, json=payload, headers=qdrant_headers(), timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json() if response.text else {}
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status in (409, 429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF ** attempt
                print(f"    ↻ Qdrant HTTP {status}, retry {attempt}/{MAX_RETRIES - 1}, wait {wait:.1f}s")
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
                print(f"    ↻ Qdrant connection retry {attempt}/{MAX_RETRIES - 1}, wait {wait:.1f}s")
                time.sleep(wait)
                continue
            raise


def ensure_collection(collection_name: str, vector_size: int) -> None:
    url = f"{QDRANT_URL}/collections/{collection_name}"
    payload = {
        "vectors": {
            "vector_cuv": {"size": vector_size, "distance": "Cosine"},
            "vector_esv": {"size": vector_size, "distance": "Cosine"},
        }
    }
    request_with_retry("PUT", url, payload)


def chunked(points: list[dict], batch_size: int):
    for i in range(0, len(points), batch_size):
        yield points[i:i + batch_size]


def build_points(metadata: pd.DataFrame, cuv_vectors: np.ndarray, esv_vectors: np.ndarray) -> list[dict]:
    points = []
    for idx, row in metadata.iterrows():
        payload = {
            "pk_id": row["pk_id"],
            "book_name_zh": row["book_name_zh"],
            "book_name_en": row["book_name_en"],
            "chapter": int(row["chapter"]),
            "verse": int(row["verse"]),
            "chapter_verse": int(row["chapter_verse"]),
            "raw_text_cuv": row["raw_text_cuv"],
            "raw_text_esv": row["raw_text_esv"],
            "context_weight": float(row["context_weight"]),
        }
        points.append(
            {
                "id": int(idx),
                "vector": {
                    "vector_cuv": cuv_vectors[idx].tolist(),
                    "vector_esv": esv_vectors[idx].tolist(),
                },
                "payload": payload,
            }
        )
    return points


def upsert_points(collection_name: str, points: list[dict]) -> None:
    url = f"{QDRANT_URL}/collections/{collection_name}/points"
    total_batches = (len(points) + UPSERT_BATCH_SIZE - 1) // UPSERT_BATCH_SIZE
    for batch_number, batch in enumerate(chunked(points, UPSERT_BATCH_SIZE), start=1):
        request_with_retry("PUT", url, {"points": batch})
        print(f"已写入 batch {batch_number}/{total_batches}")


def upload_bilingual_vectors(
    config_path: str = "bible_bilingual_config.json",
    collection_name: str = QDRANT_COLLECTION,
) -> None:
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"config 文件不存在: {config_file}")
    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)

    metadata = pd.read_pickle(config["metadata_file"])
    cuv_vectors = np.load(config["vectors"]["vector_cuv"]).astype(np.float32)
    esv_vectors = np.load(config["vectors"]["vector_esv"]).astype(np.float32)

    if not (len(metadata) == len(cuv_vectors) == len(esv_vectors)):
        raise ValueError("metadata 与双向量数量不一致")

    ensure_collection(collection_name, int(config["vector_dimension"]))
    points = build_points(metadata, cuv_vectors, esv_vectors)
    upsert_points(collection_name, points)
    print(f"完成: {len(points)} 条双语经文已写入 `{collection_name}`")


if __name__ == "__main__":
    upload_bilingual_vectors()
