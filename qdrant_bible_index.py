#!/usr/bin/env python3
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

QDRANT_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwic3ViamVjdCI6ImFwaS1rZXk6MTkzZjM0OGYtNDY3Zi00NmY3LTliODctNTIxOTZkMzg5NTljIn0.jCb9HCRwG3R9xgSS5cCXr-lPZmw-QrrIFQa2XuI5t-s"
QDRANT_URL = "https://40d5f2bb-1da4-44b5-9510-d73b62caab61.us-west-1-0.aws.cloud.qdrant.io"
QDRANT_COLLECTION = "bible_cuv"

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
            response = requests.request(
                method=method,
                url=url,
                json=payload,
                headers=qdrant_headers(),
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            if response.text:
                return response.json()
            return {}
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
            "size": vector_size,
            "distance": "Cosine",
        },
        "optimizers_config": {
            "default_segment_number": 2,
        },
    }
    request_with_retry("PUT", url, payload)


def chunked_points(points: list[dict], batch_size: int):
    for i in range(0, len(points), batch_size):
        yield points[i:i + batch_size]


def build_points(metadata: pd.DataFrame, embeddings: np.ndarray) -> list[dict]:
    points = []
    for idx, row in metadata.iterrows():
        payload = {
            "id": row.get("id"),
            "content": row.get("content"),
            "context_weight": float(row.get("context_weight", 0.0)),
            "book_name": row.get("book_name"),
            "chapter": str(row.get("chapter")),
            "verse": str(row.get("verse")),
            "formatted_text": row.get("formatted_text"),
            "row_id": int(row.get("row_id", idx)),
        }
        points.append(
            {
                "id": int(idx),
                "vector": embeddings[idx].tolist(),
                "payload": payload,
            }
        )
    return points


def upsert_points(collection_name: str, points: list[dict]) -> None:
    url = f"{QDRANT_URL}/collections/{collection_name}/points"
    total_batches = (len(points) + UPSERT_BATCH_SIZE - 1) // UPSERT_BATCH_SIZE
    for batch_number, batch in enumerate(chunked_points(points, UPSERT_BATCH_SIZE), start=1):
        request_with_retry("PUT", url, {"points": batch})
        print(f"已写入 batch {batch_number}/{total_batches}")


def upload_bible_vectors(
    embeddings_path: str = "bible_cuv_embeddings.npy",
    metadata_path: str = "bible_cuv_metadata.pkl",
    collection_name: str = QDRANT_COLLECTION,
) -> None:
    embeddings_file = Path(embeddings_path)
    metadata_file = Path(metadata_path)
    if not embeddings_file.exists():
        raise FileNotFoundError(f"embeddings 文件不存在: {embeddings_file}")
    if not metadata_file.exists():
        raise FileNotFoundError(f"metadata 文件不存在: {metadata_file}")

    embeddings = np.load(embeddings_file).astype(np.float32)
    metadata = pd.read_pickle(metadata_file)

    if len(metadata) != len(embeddings):
        raise ValueError("metadata 与 embeddings 数量不一致")

    ensure_collection(collection_name, embeddings.shape[1])
    points = build_points(metadata, embeddings)
    upsert_points(collection_name, points)

    print(f"完成: {len(points)} 条经文已写入 Qdrant collection `{collection_name}`")


if __name__ == "__main__":
    upload_bible_vectors()
