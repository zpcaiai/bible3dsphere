#!/usr/bin/env python3
import json
import math
import time
from pathlib import Path

import faiss
import numpy as np
import pandas as pd
import requests
from tqdm import tqdm

SILICONFLOW_API_KEY = "sk-dibqkgftealwtpzskkhhovdscfkzmerzxiewpyssnbdcxdeg"
SILICONFLOW_EMBEDDING_URL = "https://api.siliconflow.cn/v1/embeddings"
SILICONFLOW_EMBEDDING_MODEL = "BAAI/bge-m3"

REQUEST_TIMEOUT = 60
REQUEST_DELAY = 1.0
MAX_RETRIES = 5
RETRY_BACKOFF = 2.0
BATCH_SIZE = 32
MAX_TEXT_LENGTH = 512

REQUIRED_COLUMNS = ["book_name", "chapter", "verse", "content"]
BOOK_ABBREV_FALLBACK = {
    "创世记": "创", "出埃及记": "出", "利未记": "利", "民数记": "民", "申命记": "申",
    "约书亚记": "书", "士师记": "士", "路得记": "得", "撒母耳记上": "撒上", "撒母耳记下": "撒下",
    "列王纪上": "王上", "列王纪下": "王下", "历代志上": "代上", "历代志下": "代下", "以斯拉记": "拉",
    "尼希米记": "尼", "以斯帖记": "斯", "约伯记": "伯", "诗篇": "诗", "箴言": "箴",
    "传道书": "传", "雅歌": "歌", "以赛亚书": "赛", "耶利米书": "耶", "耶利米哀歌": "哀",
    "以西结书": "结", "但以理书": "但", "何西阿书": "何", "约珥书": "珥", "阿摩司书": "摩",
    "俄巴底亚书": "俄", "约拿书": "拿", "弥迦书": "弥", "那鸿书": "鸿", "哈巴谷书": "哈",
    "西番雅书": "番", "哈该书": "该", "撒迦利亚书": "亚", "玛拉基书": "玛", "马太福音": "太",
    "马可福音": "可", "路加福音": "路", "约翰福音": "约", "使徒行传": "徒", "罗马书": "罗",
    "哥林多前书": "林前", "哥林多后书": "林后", "加拉太书": "加", "以弗所书": "弗", "腓立比书": "腓",
    "歌罗西书": "西", "帖撒罗尼迦前书": "帖前", "帖撒罗尼迦后书": "帖后", "提摩太前书": "提前", "提摩太后书": "提后",
    "提多书": "多", "腓利门书": "门", "希伯来书": "来", "雅各书": "雅", "彼得前书": "彼前",
    "彼得后书": "彼后", "约翰一书": "约壹", "约翰二书": "约贰", "约翰三书": "约叁", "犹大书": "犹",
    "启示录": "启"
}


def siliconflow_headers() -> dict:
    return {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
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


def format_verse(row: pd.Series) -> str:
    return f"{row['book_name']} {row['chapter']}:{row['verse']} {row['content']}"


def build_verse_id(row: pd.Series) -> str:
    if "book_abbrev" in row and pd.notna(row["book_abbrev"]):
        book_abbrev = str(row["book_abbrev"]).strip()
    else:
        book_name = str(row["book_name"]).strip()
        book_abbrev = BOOK_ABBREV_FALLBACK.get(book_name, book_name)
    chapter = str(row["chapter"]).strip()
    verse = str(row["verse"]).strip()
    return f"{book_abbrev}{chapter}:{verse}"


def add_context_metadata(df: pd.DataFrame) -> pd.DataFrame:
    metadata = df.copy()
    metadata["chapter"] = metadata["chapter"].astype(str)
    metadata["verse"] = metadata["verse"].astype(str)
    metadata["id"] = metadata.apply(build_verse_id, axis=1)
    metadata["content"] = metadata["content"].astype(str)

    total_per_book = metadata.groupby("book_name")["content"].transform("count")
    order_in_book = metadata.groupby("book_name").cumcount() + 1
    metadata["context_weight"] = np.where(
        total_per_book > 1,
        (order_in_book - 1) / (total_per_book - 1),
        1.0,
    ).astype(float)
    metadata["formatted_text"] = metadata.apply(format_verse, axis=1)
    metadata["row_id"] = np.arange(len(metadata))
    return metadata


def validate_dataframe(df: pd.DataFrame) -> None:
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"CSV 缺少必要列: {missing}")


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
        data = post_with_retry(
            SILICONFLOW_EMBEDDING_URL,
            payload,
            siliconflow_headers(),
        )
        batch_embeddings = [item["embedding"] for item in data["data"]]
        all_embeddings.extend(batch_embeddings)
        time.sleep(REQUEST_DELAY)

    return np.asarray(all_embeddings, dtype=np.float32)


def process_bible_vectorization(csv_path: str, output_prefix: str = "bible_cuv"):
    csv_file = Path(csv_path)
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV 文件不存在: {csv_file}")

    df = pd.read_csv(csv_file)
    validate_dataframe(df)

    metadata = add_context_metadata(df)
    formatted_texts = metadata["formatted_text"].tolist()

    print(f"开始向量化 {len(formatted_texts)} 节经文...")
    embeddings = get_embeddings(formatted_texts)

    if embeddings.size == 0:
        raise ValueError("未生成任何 embedding")

    faiss.normalize_L2(embeddings)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    output_base = Path(output_prefix)
    faiss.write_index(index, str(output_base.with_suffix(".index")))
    np.save(output_base.parent / f"{output_base.name}_embeddings.npy", embeddings)
    metadata.to_pickle(output_base.parent / f"{output_base.name}_metadata.pkl")

    with open(output_base.parent / f"{output_base.name}_config.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "embedding_model": SILICONFLOW_EMBEDDING_MODEL,
                "vector_dimension": int(dimension),
                "vector_count": int(len(metadata)),
                "metric": "cosine_via_inner_product",
                "batch_size": BATCH_SIZE,
                "pooling": "model_default_dense",
                "normalization": "l2",
                "input_template": "[卷名] [章:节] [经文内容]",
                "metadata_fields": ["id", "content", "context_weight", "book_name", "chapter", "verse"],
                "max_length_tokens": MAX_TEXT_LENGTH,
                "embeddings_file": str(output_base.parent / f"{output_base.name}_embeddings.npy"),
                "source_csv": str(csv_file),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"处理完成！索引已保存至 {output_base.with_suffix('.index')}")
    print(f"向量已保存至 {output_base.parent / f'{output_base.name}_embeddings.npy'}")
    print(f"元数据已保存至 {output_base.parent / f'{output_base.name}_metadata.pkl'}")
    print(f"配置已保存至 {output_base.parent / f'{output_base.name}_config.json'}")


if __name__ == "__main__":
    # 示例:
    # process_bible_vectorization("cuv_bible_tw.csv")
    pass
