#!/usr/bin/env python3
import json
from pathlib import Path

from search_bible_index import QDRANT_COLLECTION, search_bible_hybrid

FEATURES_FILE = "emotion_features_map.json"
OUTPUT_FILE = "emotion_feature_verse_matches.json"
DEFAULT_TOP_K = 5
DEFAULT_BACKEND = "qdrant"
DEFAULT_COLLECTION = QDRANT_COLLECTION


def load_features(features_path: str = FEATURES_FILE) -> list[dict]:
    path = Path(features_path)
    if not path.exists():
        raise FileNotFoundError(f"feature 文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_emotion_query_text(feature: dict) -> str:
    explanation = str(feature.get("explanation", "")).strip()
    source_keyword = str(feature.get("source_keyword", "")).strip()
    feature_id = str(feature.get("feature_id", "")).strip()
    layer = str(feature.get("layer", "")).strip()

    parts = [
        "请寻找与以下情绪、属灵体验或心理状态最共振的中文和合本经文",
        f"特征说明：{explanation}" if explanation else "",
        f"关键词：{source_keyword}" if source_keyword else "",
        f"特征定位：{layer} / {feature_id}" if layer or feature_id else "",
        "重点关注怜悯、悔改、盼望、痛苦、安慰、救赎、恩典等情绪与神学语义",
    ]
    return "。".join(part for part in parts if part)


def search_for_feature(
    feature: dict,
    top_k: int = DEFAULT_TOP_K,
    backend: str = DEFAULT_BACKEND,
    collection_name: str = DEFAULT_COLLECTION,
) -> dict:
    query_text = build_emotion_query_text(feature)
    results = search_bible_hybrid(
        query_text=query_text,
        top_k=top_k,
        backend=backend,
        collection_name=collection_name,
    )
    return {
        "feature_id": feature.get("feature_id"),
        "model_id": feature.get("model_id"),
        "layer": feature.get("layer"),
        "source_keyword": feature.get("source_keyword"),
        "explanation": feature.get("explanation"),
        "emotion_query_text": query_text,
        "matches": results,
    }


def batch_search_features(
    features_path: str = FEATURES_FILE,
    output_path: str = OUTPUT_FILE,
    top_k: int = DEFAULT_TOP_K,
    backend: str = DEFAULT_BACKEND,
    collection_name: str = DEFAULT_COLLECTION,
) -> list[dict]:
    features = load_features(features_path)
    all_results = []

    print(f"开始批量检索 {len(features)} 个 emotion features，backend={backend}")
    for i, feature in enumerate(features, start=1):
        print(
            f"[{i}/{len(features)}] 搜索 feature {feature.get('layer')}:{feature.get('feature_id')}"
        )
        all_results.append(
            search_for_feature(
                feature=feature,
                top_k=top_k,
                backend=backend,
                collection_name=collection_name,
            )
        )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"完成，结果已保存到: {output_path}")
    return all_results


if __name__ == "__main__":
    batch_search_features()
