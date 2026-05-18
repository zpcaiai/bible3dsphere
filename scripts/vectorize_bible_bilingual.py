#!/usr/bin/env python3
import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from tqdm import tqdm

from bible_book_mappings import build_bbb_ccc_vvv, normalize_book_name

try:
    import faiss
except ImportError:
    faiss = None

SILICONFLOW_API_KEY = "sk-dibqkgftealwtpzskkhhovdscfkzmerzxiewpyssnbdcxdeg"
SILICONFLOW_EMBEDDING_URL = "https://api.siliconflow.cn/v1/embeddings"
SILICONFLOW_EMBEDDING_MODEL = "BAAI/bge-m3"

REQUEST_TIMEOUT = 60
REQUEST_DELAY = 1.0
MAX_RETRIES = 5
RETRY_BACKOFF = 2.0
BATCH_SIZE = 32
MAX_LENGTH_TOKENS = 512

REQUIRED_COLUMNS = ["book_name", "chapter", "verse", "content"]
CANONICAL_COLUMN_CANDIDATES = {
    "book_name": ["book_name", "Book", "title", "Title", "book"],
    "chapter": ["chapter", "Chapter"],
    "verse": ["verse", "Verse"],
    "content": ["content", "Content", "text", "Text"],
}


def siliconflow_headers() -> dict:
    return {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json",
    }


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


def validate_dataframe(df: pd.DataFrame, label: str) -> None:
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"{label} CSV 缺少必要列: {missing}")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    for canonical, candidates in CANONICAL_COLUMN_CANDIDATES.items():
        if canonical in normalized.columns:
            continue
        for candidate in candidates:
            if candidate in normalized.columns:
                normalized[canonical] = normalized[candidate]
                break
    return normalized


def sanitize_rows(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    if "book_name" in frame.columns:
        frame = frame[frame["book_name"].astype(str).str.strip().str.lower() != "book_name"]
    if "chapter" in frame.columns:
        frame["chapter"] = pd.to_numeric(frame["chapter"], errors="coerce")
    if "verse" in frame.columns:
        frame["verse"] = pd.to_numeric(frame["verse"], errors="coerce")
    frame = frame.dropna(subset=["book_name", "chapter", "verse", "content"])
    return frame.reset_index(drop=True)


def format_verse_text(book_name: str, chapter, verse, content: str) -> str:
    return f"{book_name} {chapter}:{verse} {content}"


def enrich_frame(df: pd.DataFrame, lang: str) -> pd.DataFrame:
    frame = df.copy()
    frame["book_name"] = frame["book_name"].astype(str).str.strip()
    frame["chapter"] = frame["chapter"].astype(int)
    frame["verse"] = frame["verse"].astype(int)
    frame["content"] = frame["content"].astype(str)
    frame["pk_id"] = frame.apply(lambda row: build_bbb_ccc_vvv(row["book_name"], row["chapter"], row["verse"]), axis=1)
    frame["book_meta"] = frame["book_name"].map(normalize_book_name)
    if frame["book_meta"].isna().any():
        bad = frame.loc[frame["book_meta"].isna(), "book_name"].unique().tolist()
        raise ValueError(f"{lang} 存在无法识别的书卷名: {bad}")
    frame[f"raw_text_{lang}"] = frame["content"]
    frame[f"formatted_text_{lang}"] = frame.apply(
        lambda row: format_verse_text(row["book_name"], row["chapter"], row["verse"], row["content"]),
        axis=1,
    )
    return frame


def chunked(items: list[str], batch_size: int):
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


def get_embeddings(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.empty((0, 0), dtype=np.float32)
    all_embeddings: list[list[float]] = []
    total_batches = math.ceil(len(texts) / BATCH_SIZE)
    for batch in tqdm(chunked(texts, BATCH_SIZE), total=total_batches, desc="Embedding"):
        payload = {
            "model": SILICONFLOW_EMBEDDING_MODEL,
            "input": batch,
            "encoding_format": "float",
        }
        data = post_with_retry(SILICONFLOW_EMBEDDING_URL, payload, siliconflow_headers())
        all_embeddings.extend(item["embedding"] for item in data["data"])
        time.sleep(REQUEST_DELAY)
    return np.asarray(all_embeddings, dtype=np.float32)


def l2_normalize(embeddings: np.ndarray) -> np.ndarray:
    if embeddings.size == 0:
        return embeddings
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return (embeddings / norms).astype(np.float32)


def align_bibles(cuv_csv_path: str, esv_csv_path: str) -> pd.DataFrame:
    cuv = sanitize_rows(normalize_columns(pd.read_csv(cuv_csv_path)))
    esv = sanitize_rows(normalize_columns(pd.read_csv(esv_csv_path)))
    validate_dataframe(cuv, "CUV")
    validate_dataframe(esv, "ESV")

    cuv_frame = enrich_frame(cuv, "cuv")
    esv_frame = enrich_frame(esv, "esv")

    aligned = cuv_frame.merge(
        esv_frame[["pk_id", "book_name", "chapter", "verse", "raw_text_esv", "formatted_text_esv"]],
        on="pk_id",
        suffixes=("_cuv", "_esvmeta"),
        how="inner",
    )
    aligned = aligned.rename(
        columns={
            "book_name_cuv": "book_name_zh",
            "chapter_cuv": "chapter",
            "verse_cuv": "verse",
            "raw_text_cuv": "raw_text_cuv",
        }
    )
    aligned["book_name_en"] = aligned["pk_id"].map(lambda pk: pk.split("-")[0])
    aligned["chapter_verse"] = aligned.apply(lambda row: int(row["chapter"]) * 1000 + int(row["verse"]), axis=1)
    aligned["context_weight"] = (
        aligned.groupby(aligned["pk_id"].str[:3]).cumcount() /
        aligned.groupby(aligned["pk_id"].str[:3])["pk_id"].transform("count").sub(1).replace(0, 1)
    ).astype(float)
    aligned = aligned.sort_values("pk_id").reset_index(drop=True)
    return aligned


def build_faiss_index(embeddings: np.ndarray):
    if faiss is None:
        return None
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings.astype(np.float32))
    return index


def process_bilingual_vectorization(
    cuv_csv_path: str,
    esv_csv_path: str,
    output_prefix: str = "bible_bilingual",
) -> None:
    aligned = align_bibles(cuv_csv_path, esv_csv_path)
    if aligned.empty:
        raise ValueError("CUV / ESV 对齐结果为空")

    print(f"开始对齐并向量化 {len(aligned)} 节双语经文...")
    cuv_embeddings = get_embeddings(aligned["formatted_text_cuv"].tolist())
    esv_embeddings = get_embeddings(aligned["formatted_text_esv"].tolist())

    if cuv_embeddings.size == 0 or esv_embeddings.size == 0:
        raise ValueError("未生成双语 embeddings")

    cuv_embeddings = l2_normalize(cuv_embeddings)
    esv_embeddings = l2_normalize(esv_embeddings)

    cuv_index = build_faiss_index(cuv_embeddings)
    esv_index = build_faiss_index(esv_embeddings)

    output_base = Path(output_prefix)
    if cuv_index is not None and esv_index is not None:
        faiss.write_index(cuv_index, str(output_base.parent / f"{output_base.name}_cuv.index"))
        faiss.write_index(esv_index, str(output_base.parent / f"{output_base.name}_esv.index"))
    np.save(output_base.parent / f"{output_base.name}_vector_cuv.npy", cuv_embeddings)
    np.save(output_base.parent / f"{output_base.name}_vector_esv.npy", esv_embeddings)

    metadata = aligned[[
        "pk_id",
        "book_name_zh",
        "book_name_en",
        "chapter",
        "verse",
        "chapter_verse",
        "raw_text_cuv",
        "raw_text_esv",
        "formatted_text_cuv",
        "formatted_text_esv",
        "context_weight",
    ]].copy()
    metadata.to_pickle(output_base.parent / f"{output_base.name}_metadata.pkl")

    with open(output_base.parent / f"{output_base.name}_config.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "embedding_model": SILICONFLOW_EMBEDDING_MODEL,
                "vector_dimension": int(cuv_embeddings.shape[1]),
                "vector_count": int(len(metadata)),
                "metric": "cosine_via_inner_product",
                "max_length_tokens": MAX_LENGTH_TOKENS,
                "pk_format": "BBB-CCC-VVV",
                "faiss_available": faiss is not None,
                "vectors": {
                    "vector_cuv": str(output_base.parent / f"{output_base.name}_vector_cuv.npy"),
                    "vector_esv": str(output_base.parent / f"{output_base.name}_vector_esv.npy"),
                },
                "indexes": {
                    "cuv": str(output_base.parent / f"{output_base.name}_cuv.index"),
                    "esv": str(output_base.parent / f"{output_base.name}_esv.index"),
                },
                "metadata_file": str(output_base.parent / f"{output_base.name}_metadata.pkl"),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"完成: 已输出双语索引与 metadata，prefix={output_base}")


if __name__ == "__main__":
    pass
