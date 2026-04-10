#!/usr/bin/env python3
"""
Neuronpedia Emotion Feature Fetcher
====================================
通过 Neuronpedia API 的 explanation search 端点，
按情绪相关关键词检索 SAE 特征，并输出 JSON 映射表。

重要说明:
- Claude 3 Sonnet (claude-3-sonnet) 目前 **不在** Neuronpedia 可用资源中。
- res-jb SAE set 仅适用于 gpt2-small (12 层: 0-res-jb ~ 11-res-jb)。
- 本脚本默认使用 gpt2-small/res-jb 作为演示；
  若需搜索全平台所有模型，可将 SEARCH_MODE 改为 "all"。
- API 文档: https://www.neuronpedia.org/api-doc

API 端点 (POST):
  /api/explanation/search       — 搜索特定模型 + SAE(s) 内的特征解释
  /api/explanation/search-model — 搜索特定模型内所有 SAE 的特征解释
  /api/explanation/search-all   — 搜索全平台所有特征解释
  每次返回最多 20 条，通过 offset 翻页。
"""

import requests
import json
import time
import sys
from pathlib import Path
from typing import Optional

# ─────────────────────── 配置参数 ───────────────────────

API_BASE = "https://www.neuronpedia.org/api"

# 搜索模式: "sae" | "model" | "all"
#   "sae"   → 搜索特定 model + 指定 SAE layers (最精确)
#   "model" → 搜索特定 model 下所有 SAE
#   "all"   → 搜索 Neuronpedia 全平台
SEARCH_MODE = "sae"

# ── 模型和 SAE 配置 (仅 "sae" / "model" 模式使用) ──
MODEL_ID = "llama3.1-8b"
# llamascope-res-32k 在 llama3.1-8b 有 32 层 (layer 0-31)
SAE_LAYERS = [f"{i}-llamascope-res-32k" for i in range(32)]

# ── API Key (可选，公开搜索通常免费，但有速率限制) ──
API_KEY = "sk-np-tbNBLkZ89zQRzjX0Wak0B8ZCXuDaYXkCmV2Uyagf3qc0"
QDRANT_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIiwic3ViamVjdCI6ImFwaS1rZXk6MTkzZjM0OGYtNDY3Zi00NmY3LTliODctNTIxOTZkMzg5NTljIn0.jCb9HCRwG3R9xgSS5cCXr-lPZmw-QrrIFQa2XuI5t-s"
QDRANT_URL = "https://40d5f2bb-1da4-44b5-9510-d73b62caab61.us-west-1-0.aws.cloud.qdrant.io"
SILICONFLOW_API_KEY = "sk-dibqkgftealwtpzskkhhovdscfkzmerzxiewpyssnbdcxdeg"
SILICONFLOW_EMBEDDING_URL = "https://api.siliconflow.cn/v1/embeddings"
SILICONFLOW_EMBEDDING_MODEL = "BAAI/bge-m3"
GENERATE_EMBEDDINGS = True

# ── 情绪关键词列表 ──
EMOTION_KEYWORDS = [
    # 基础情绪
    "emotion", "feeling", "sentiment",
    # 正面情绪
    "joy", "happiness", "love", "hope", "gratitude", "praise", "worship",
    "delight", "peace", "comfort", "blessing", "grace", "faith",
    # 负面情绪
    "sorrow", "grief", "suffering", "pain", "fear", "anger", "wrath",
    "guilt", "shame", "despair", "lament", "mourning", "anguish",
    # 道德/灵性情绪
    "compassion", "mercy", "forgiveness", "repentance", "humility",
    "righteousness", "sin", "redemption", "sacrifice", "devotion",
]

# 目标特征数量
TARGET_FEATURE_COUNT = 171

# 输出文件
OUTPUT_FILE = "emotion_features_map.json"

# 请求间隔 (秒)，避免触发速率限制
REQUEST_DELAY = 5.0

# 重试配置
MAX_RETRIES = 5
RETRY_BACKOFF = 2.0  # 指数退避基数 (秒)


# ─────────────────────── 核心逻辑 ───────────────────────

def build_headers():
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["x-api-key"] = API_KEY
    return headers


def get_embedding(text: str) -> list[float]:
    payload = {
        "model": SILICONFLOW_EMBEDDING_MODEL,
        "input": text,
        "encoding_format": "float",
    }
    headers = {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json",
    }
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(
                SILICONFLOW_EMBEDDING_URL,
                json=payload,
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["data"][0]["embedding"]
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status in (429, 500, 502, 503, 504) and attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF ** attempt
                print(f"    ↻ SiliconFlow 服务器 {status}, 第 {attempt} 次重试, 等待 {wait:.1f}s...")
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
                print(f"    ↻ SiliconFlow 连接异常, 第 {attempt} 次重试, 等待 {wait:.1f}s...")
                time.sleep(wait)
                continue
            raise


def _post_with_retry(url: str, payload: dict) -> dict:
    """带指数退避重试的 POST 请求"""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(
                url, json=payload, headers=build_headers(), timeout=30
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status in (500, 502, 503, 504) and attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF ** attempt
                print(f"    ↻ 服务器 {status}, 第 {attempt} 次重试, 等待 {wait:.1f}s...")
                time.sleep(wait)
                continue
            raise
        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF ** attempt
                print(f"    ↻ 超时, 第 {attempt} 次重试, 等待 {wait:.1f}s...")
                time.sleep(wait)
                continue
            raise
        except requests.exceptions.SSLError:
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF ** attempt
                print(f"    ↻ SSL 错误, 第 {attempt} 次重试, 等待 {wait:.1f}s...")
                time.sleep(wait)
                continue
            raise
        except requests.exceptions.ConnectionError:
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF ** attempt
                print(f"    ↻ 连接错误, 第 {attempt} 次重试, 等待 {wait:.1f}s...")
                time.sleep(wait)
                continue
            raise


def search_by_sae(query: str, offset: int = 0) -> dict:
    """POST /api/explanation/search — 搜索特定 SAE layers"""
    url = f"{API_BASE}/explanation/search"
    payload = {
        "modelId": MODEL_ID,
        "layers": SAE_LAYERS,
        "query": query,
        "offset": offset,
    }
    return _post_with_retry(url, payload)


def search_by_model(query: str, offset: int = 0) -> dict:
    """POST /api/explanation/search-model — 搜索特定 model"""
    url = f"{API_BASE}/explanation/search-model"
    payload = {
        "modelId": MODEL_ID,
        "query": query,
        "offset": offset,
    }
    return _post_with_retry(url, payload)


def search_all(query: str, offset: int = 0) -> dict:
    """POST /api/explanation/search-all — 搜索全平台"""
    url = f"{API_BASE}/explanation/search-all"
    payload = {
        "query": query,
        "offset": offset,
    }
    return _post_with_retry(url, payload)


def get_search_fn():
    """根据 SEARCH_MODE 返回对应的搜索函数"""
    if SEARCH_MODE == "sae":
        return search_by_sae
    elif SEARCH_MODE == "model":
        return search_by_model
    elif SEARCH_MODE == "all":
        return search_all
    else:
        raise ValueError(f"Unknown SEARCH_MODE: {SEARCH_MODE}")


def extract_features_from_results(results: list, keyword: str) -> list:
    """
    从搜索结果中提取 feature 信息。
    Neuronpedia 的 explanation/search 返回格式:
    {
      "results": [
        {
          "modelId": "...",
          "layer": "6-res-jb",
          "index": "14057",
          "description": "references to emotion or feeling",
          ...
        }, ...
      ],
      "hasMore": true/false,
      "nextOffset": 20
    }
    """
    features = []
    for item in results:
        model_id = item.get("modelId", MODEL_ID)
        layer = item.get("layer", "")
        index = item.get("index", "")
        description = item.get("description", "") or ""

        # 构建唯一标识
        feature_key = f"{model_id}/{layer}/{index}"

        features.append({
            "feature_key": feature_key,
            "feature_id": index,
            "model_id": model_id,
            "layer": layer,
            "explanation": description,
            "source_keyword": keyword,
        })
    return features


def fetch_feature_detail(model_id: str, layer: str, index: str) -> Optional[dict]:
    """
    GET /api/feature/{modelId}/{layer}/{index}
    获取单个特征的完整信息 (含 activations, explanations 等)。
    """
    url = f"{API_BASE}/feature/{model_id}/{layer}/{index}"
    try:
        resp = requests.get(url, headers=build_headers(), timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  ⚠ 获取特征详情失败 {model_id}/{layer}/{index}: {e}")
        return None


def collect_emotion_features():
    """主流程: 按关键词批量搜索，收集去重后的特征列表"""
    search_fn = get_search_fn()
    # 用 feature_key 去重
    unique_features: dict[str, dict] = {}

    print(f"搜索模式: {SEARCH_MODE}")
    if SEARCH_MODE in ("sae", "model"):
        print(f"目标模型: {MODEL_ID}")
    if SEARCH_MODE == "sae":
        print(f"SAE layers: {SAE_LAYERS[0]} ~ {SAE_LAYERS[-1]} ({len(SAE_LAYERS)} 层)")
    print(f"关键词数: {len(EMOTION_KEYWORDS)}")
    print(f"目标特征数: {TARGET_FEATURE_COUNT}")
    print("=" * 60)

    for kw in EMOTION_KEYWORDS:
        if len(unique_features) >= TARGET_FEATURE_COUNT:
            break

        offset = 0
        page = 1
        total_for_kw = 0

        while True:
            try:
                data = search_fn(kw, offset=offset)
            except requests.exceptions.HTTPError as e:
                print(f"  ✗ [{kw}] 请求失败 (offset={offset}): {e}")
                break
            except Exception as e:
                print(f"  ✗ [{kw}] 异常: {e}")
                break

            results = data.get("results", [])
            if not results:
                break

            new_features = extract_features_from_results(results, kw)
            added = 0
            for feat in new_features:
                key = feat["feature_key"]
                if key not in unique_features:
                    unique_features[key] = feat
                    added += 1

            total_for_kw += len(results)
            print(
                f"  [{kw}] page {page}: "
                f"返回 {len(results)} 条, 新增 {added} 条, "
                f"累计唯一 {len(unique_features)} 条"
            )

            # 检查是否还有更多结果
            has_more = data.get("hasMore", False)
            next_offset = data.get("nextOffset")

            if not has_more or len(unique_features) >= TARGET_FEATURE_COUNT:
                break

            offset = next_offset if next_offset is not None else offset + 20
            page += 1
            time.sleep(REQUEST_DELAY)

        time.sleep(REQUEST_DELAY)

    # 截取到目标数量
    feature_list = list(unique_features.values())[:TARGET_FEATURE_COUNT]
    print("=" * 60)
    print(f"共收集到 {len(feature_list)} 个唯一特征")
    return feature_list


def enrich_with_details(features: list, max_detail_fetches: int = 0) -> list:
    """
    可选: 为每个特征获取完整详情 (含 activation_max 等)。
    设置 max_detail_fetches > 0 启用，默认关闭以节省请求量。
    """
    if max_detail_fetches <= 0:
        return features

    print(f"\n获取前 {max_detail_fetches} 个特征的详细信息...")
    for i, feat in enumerate(features[:max_detail_fetches]):
        detail = fetch_feature_detail(
            feat["model_id"], feat["layer"], feat["feature_id"]
        )
        if detail:
            # 从详情中提取额外信息
            # activations 中可能包含 max activation
            acts = detail.get("activations", [])
            max_act = 0.0
            for act_record in acts:
                tokens = act_record.get("tokens", [])
                for tok in tokens:
                    val = tok.get("value", 0) if isinstance(tok, dict) else 0
                    max_act = max(max_act, val)

            # 从 explanations 中获取最佳解释
            explanations = detail.get("explanations", [])
            if explanations:
                best = explanations[0]
                feat["explanation"] = best.get("description", feat["explanation"])

            feat["activation_max"] = max_act

        if (i + 1) % 10 == 0:
            print(f"  已处理 {i + 1}/{max_detail_fetches}")
        time.sleep(REQUEST_DELAY)

    return features


def build_output(features: list) -> list:
    """构建最终输出格式"""
    output = []
    for feat in features:
        embedding = None
        if GENERATE_EMBEDDINGS:
            embedding_text = " | ".join([
                feat.get("model_id", ""),
                feat.get("layer", ""),
                feat.get("feature_id", ""),
                feat.get("explanation", ""),
            ])
            try:
                embedding = get_embedding(embedding_text)
            except Exception as e:
                print(
                    f"  ⚠ SiliconFlow embedding 失败 {feat.get('layer')}:{feat.get('feature_id')}: {e}"
                )
        entry = {
            "feature_id": feat.get("feature_id"),
            "model_id": feat.get("model_id"),
            "layer": feat.get("layer"),
            "explanation": feat.get("explanation", ""),
            "activation_max": feat.get("activation_max", None),
            "source_keyword": feat.get("source_keyword", ""),
        }
        if embedding is not None:
            entry["embedding"] = embedding
        output.append(entry)
    return output


def main():
    print("Neuronpedia Emotion Feature Fetcher")
    print("=" * 60)

    # Step 1: 收集特征
    features = collect_emotion_features()

    if not features:
        print("未找到任何特征，请检查网络连接和 API Key 设置。")
        sys.exit(1)

    # Step 2 (可选): 获取详细信息
    # 取消注释下行以获取 activation 详情 (会增加大量 API 请求)
    # features = enrich_with_details(features, max_detail_fetches=len(features))

    # Step 3: 构建并保存 JSON
    output = build_output(features)
    output_path = Path(__file__).parent / OUTPUT_FILE
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 已保存 {len(output)} 个特征到: {output_path}")
    print(f"\n前 3 条预览:")
    for entry in output[:3]:
        print(json.dumps(entry, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
