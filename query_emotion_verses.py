#!/usr/bin/env python3
import argparse
import csv
import json
import os
import time
from typing import Any
from pathlib import Path

import numpy as np
import requests

SILICONFLOW_API_KEY = "sk-dibqkgftealwtpzskkhhovdscfkzmerzxiewpyssnbdcxdeg"
SILICONFLOW_EMBEDDING_URL = "https://api.siliconflow.cn/v1/embeddings"
SILICONFLOW_EMBEDDING_MODEL = "BAAI/bge-m3"

REQUEST_TIMEOUT = 60
MAX_RETRIES = 5
RETRY_BACKOFF = 2.0

FEATURES_FILE = "emotion_features_map.json"
MATCHES_FILE = "emotion_exemplar_verse_matches.json"
EMBEDDING_CACHE_FILE = "emotion_feature_embedding_cache.json"
DEFAULT_TOP_FEATURES = 5
DEFAULT_TOP_VERSES_PER_LANGUAGE = 5
EMBEDDING_BATCH_SIZE = 32
DEFAULT_OUTPUT_DIR = "query_outputs"
DEFAULT_ENABLE_RERANK = False
DEFAULT_RERANK_CANDIDATES = 20
DEFAULT_RERANK_WEIGHT = 0.7
RERANK_MODEL_NAME = os.getenv("RERANK_MODEL_NAME", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")

SILICONFLOW_CHAT_URL = "https://api.siliconflow.cn/v1/chat/completions"
SILICONFLOW_CHAT_MODEL = "Qwen/Qwen2.5-72B-Instruct"

RERANKER = None
RERANKER_LOAD_ERROR = None

PSYCHOLOGICAL_SYSTEM_PROMPT = """你是一位深植于基督教灵修传统的属灵导师，同时具备牧关聆听的温柔。
你的话语应当像一封来自父神心怀的信——有圣经的根基，有圣灵的温度，有盼望的光芒。

请按以下四个维度回应，语言贴近灵修日记与属灵书信的风格，避免临床术语，使用圣经意象、神学词汇（恩典、救赎、蒙爱、圣约、同在、更新、盼望、交托、默想）：

1. **core_emotions**：2-4 个词，用属灵语言命名此刻的心灵处境（如"哀恸"而非"悲伤"，"灵里枯干"而非"疲惫"，"渴慕神同在"而非"孤独"）。

2. **psychological_assessment**：2-3 句，以牧者的眼光温柔地看见这个人——承认他/她的挣扎是真实的，同时将其置于神的救赎叙事中（不要诊断，要见证）。

3. **coping_suggestions**：1-2 条属灵操练的邀请——例如：安静默祷、诵读某类诗篇、向神倾诉痛苦、放下控制权交托给神、在团契中寻求代祷。每条以"你可以……"开头，语气是邀请而非指令。

4. **spiritual_guidance**：1 段深刻的灵性话语（4-6 句），用圣经神学（如神的信实、基督的同受苦难、圣灵的保惠、末世的盼望）来诠释此处境，引用或化用 1 处圣经意象，语气如同一封写给受苦之人的信，有诗意，有重量，有温度。

5. **core_need**：一句话，以"你的灵魂此刻最深的渴望是……"开头，道出这个人在神面前最核心的属灵需要。

回应使用中文，总长度不超过 400 字。
请严格按以下 JSON 格式输出（不要附带 markdown 代码块）：
{
  "core_emotions": ["词1", "词2"],
  "psychological_assessment": "...",
  "coping_suggestions": ["你可以……", "你可以……"],
  "spiritual_guidance": "...",
  "core_need": "你的灵魂此刻最深的渴望是……"
}"""


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


def siliconflow_headers() -> dict:
    return {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json",
    }


def l2_normalize(vectors: np.ndarray) -> np.ndarray:
    if vectors.size == 0:
        return vectors
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return (vectors / norms).astype(np.float32)


def sigmoid(value: float) -> float:
    if value >= 0:
        z = np.exp(-value)
        return float(1.0 / (1.0 + z))
    z = np.exp(value)
    return float(z / (1.0 + z))


def get_reranker() -> Any:
    global RERANKER
    global RERANKER_LOAD_ERROR
    if RERANKER is not None:
        return RERANKER
    if RERANKER_LOAD_ERROR is not None:
        raise RuntimeError(RERANKER_LOAD_ERROR)
    try:
        from sentence_transformers import CrossEncoder
    except ImportError:
        RERANKER_LOAD_ERROR = (
            "Rerank is enabled but sentence-transformers is not installed. "
            "Please install sentence-transformers and torch first."
        )
        raise RuntimeError(RERANKER_LOAD_ERROR)
    try:
        RERANKER = CrossEncoder(RERANK_MODEL_NAME)
        return RERANKER
    except Exception as exc:
        RERANKER_LOAD_ERROR = f"Failed to load rerank model {RERANK_MODEL_NAME}: {exc}"
        raise RuntimeError(RERANKER_LOAD_ERROR) from exc


def get_embeddings(texts: list[str]) -> np.ndarray:
    all_embeddings = []
    for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[start:start + EMBEDDING_BATCH_SIZE]
        payload = {
            "model": SILICONFLOW_EMBEDDING_MODEL,
            "input": batch,
            "encoding_format": "float",
        }
        data = post_with_retry(SILICONFLOW_EMBEDDING_URL, payload, siliconflow_headers())
        all_embeddings.extend(item["embedding"] for item in data["data"])
    embeddings = np.asarray(all_embeddings, dtype=np.float32)
    return l2_normalize(embeddings)


def load_json(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_feature_text(feature: dict) -> str:
    parts = [
        str(feature.get("source_keyword", "")).strip(),
        str(feature.get("explanation", "")).strip(),
        str(feature.get("layer", "")).strip(),
        str(feature.get("feature_id", "")).strip(),
    ]
    return " | ".join(part for part in parts if part)


def feature_key(feature: dict) -> str:
    return f"{feature.get('layer')}:{feature.get('feature_id')}"


def load_or_build_feature_embeddings(
    features: list[dict],
    cache_file: str = EMBEDDING_CACHE_FILE,
) -> tuple[list[dict], np.ndarray]:
    cache_path = Path(cache_file)
    cache = {}
    if cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            cache = json.load(f)

    missing_features = []
    for feature in features:
        key = feature_key(feature)
        if key not in cache:
            missing_features.append(feature)

    if missing_features:
        texts = [build_feature_text(feature) for feature in missing_features]
        embeddings = get_embeddings(texts)
        for feature, embedding in zip(missing_features, embeddings, strict=True):
            cache[feature_key(feature)] = embedding.tolist()
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

    ordered_embeddings = np.asarray([cache[feature_key(feature)] for feature in features], dtype=np.float32)
    ordered_embeddings = l2_normalize(ordered_embeddings)
    return features, ordered_embeddings


def map_matches_by_feature(matches: list[dict]) -> dict[str, dict]:
    return {f"{item.get('layer')}:{item.get('feature_id')}": item for item in matches}


def select_top_features(
    query_text: str,
    features: list[dict],
    feature_embeddings: np.ndarray,
    top_k: int = DEFAULT_TOP_FEATURES,
) -> list[dict]:
    query_vec = get_embeddings([query_text])
    scores = np.dot(feature_embeddings, query_vec[0])
    ranked_indices = np.argsort(scores)[::-1][:top_k]
    selected = []
    for idx in ranked_indices:
        feature = features[idx]
        selected.append(
            {
                "feature_id": feature.get("feature_id"),
                "layer": feature.get("layer"),
                "model_id": feature.get("model_id"),
                "source_keyword": feature.get("source_keyword"),
                "explanation": feature.get("explanation"),
                "similarity": float(scores[idx]),
                "feature_key": feature_key(feature),
            }
        )
    return selected


def aggregate_verses(
    selected_features: list[dict],
    matches_by_feature: dict[str, dict],
    top_verses_per_language: int = DEFAULT_TOP_VERSES_PER_LANGUAGE,
    candidate_pool_per_language: int | None = None,
) -> dict[str, list[dict]]:
    aggregated = {"cuv": {}, "esv": {}}
    for feature in selected_features:
        feature_match = matches_by_feature.get(feature["feature_key"], {})
        for language in ("cuv", "esv"):
            for verse in feature_match.get("matches", {}).get(language, []):
                pk_id = verse.get("pk_id")
                if not pk_id:
                    continue
                verse_score = float(verse.get("score", 0.0))
                combined_score = 0.6 * feature["similarity"] + 0.4 * verse_score
                existing = aggregated[language].get(pk_id)
                feature_hit = {
                    "feature_id": feature.get("feature_id"),
                    "layer": feature.get("layer"),
                    "similarity": feature.get("similarity"),
                    "verse_score": verse_score,
                }
                if existing is None:
                    aggregated[language][pk_id] = {
                        "pk_id": pk_id,
                        "book_name": verse.get("book_name"),
                        "chapter": verse.get("chapter"),
                        "verse": verse.get("verse"),
                        "raw_text": verse.get("raw_text"),
                        "combined_score": combined_score,
                        "final_score": combined_score,
                        "best_feature_similarity": feature.get("similarity"),
                        "best_verse_score": verse_score,
                        "rerank_score": None,
                        "matched_features": [feature_hit],
                    }
                else:
                    existing["combined_score"] = max(existing["combined_score"], combined_score)
                    existing["final_score"] = existing["combined_score"]
                    existing["best_feature_similarity"] = max(existing["best_feature_similarity"], feature.get("similarity"))
                    existing["best_verse_score"] = max(existing["best_verse_score"], verse_score)
                    existing["matched_features"].append(feature_hit)

    final_output = {}
    for language, verses in aggregated.items():
        ranked = sorted(verses.values(), key=lambda item: item["combined_score"], reverse=True)
        limit = candidate_pool_per_language if candidate_pool_per_language is not None else top_verses_per_language
        final_output[language] = ranked[:limit]
    return final_output


def rerank_verses(
    query_text: str,
    verses: list[dict],
    top_n: int,
    rerank_weight: float = DEFAULT_RERANK_WEIGHT,
) -> list[dict]:
    if not verses:
        return []
    reranker = get_reranker()
    clipped_weight = min(max(rerank_weight, 0.0), 1.0)
    sentence_pairs = [(query_text, str(item.get("raw_text", ""))) for item in verses]
    rerank_scores = reranker.predict(sentence_pairs)
    reranked = []
    for verse, raw_score in zip(verses, rerank_scores, strict=True):
        normalized_rerank_score = sigmoid(float(raw_score))
        fused_score = (1.0 - clipped_weight) * float(verse.get("combined_score", 0.0)) + clipped_weight * normalized_rerank_score
        reranked_item = dict(verse)
        reranked_item["rerank_score"] = normalized_rerank_score
        reranked_item["final_score"] = fused_score
        reranked.append(reranked_item)
    reranked.sort(key=lambda item: item["final_score"], reverse=True)
    return reranked[:top_n]


def call_chat(system_prompt: str, user_message: str) -> str:
    payload = {
        "model": SILICONFLOW_CHAT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.7,
        "max_tokens": 800,
    }
    data = post_with_retry(SILICONFLOW_CHAT_URL, payload, siliconflow_headers())
    return data["choices"][0]["message"]["content"].strip()


def assess_psychological_state(query_text: str) -> dict:
    raw = call_chat(PSYCHOLOGICAL_SYSTEM_PROMPT, query_text)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "core_emotions": [],
            "psychological_assessment": raw,
            "coping_suggestions": [],
            "spiritual_guidance": "",
            "core_need": "",
            "parse_error": True,
        }


def query_emotion_verses(
    query_text: str,
    top_features: int = DEFAULT_TOP_FEATURES,
    top_verses_per_language: int = DEFAULT_TOP_VERSES_PER_LANGUAGE,
    features_file: str = FEATURES_FILE,
    matches_file: str = MATCHES_FILE,
    cache_file: str = EMBEDDING_CACHE_FILE,
    include_guidance: bool = False,
    enable_rerank: bool = DEFAULT_ENABLE_RERANK,
    rerank_candidates: int = DEFAULT_RERANK_CANDIDATES,
    rerank_weight: float = DEFAULT_RERANK_WEIGHT,
) -> dict:
    features = load_json(features_file)
    matches = load_json(matches_file)
    features, feature_embeddings = load_or_build_feature_embeddings(features, cache_file)
    matches_by_feature = map_matches_by_feature(matches)
    selected_features = select_top_features(query_text, features, feature_embeddings, top_k=top_features)
    candidate_pool_size = max(top_verses_per_language, rerank_candidates)
    verse_summary = aggregate_verses(
        selected_features,
        matches_by_feature,
        top_verses_per_language=top_verses_per_language,
        candidate_pool_per_language=candidate_pool_size if enable_rerank else None,
    )
    rerank_applied = False
    if enable_rerank:
        verse_summary = {
            language: rerank_verses(
                query_text=query_text,
                verses=verses,
                top_n=top_verses_per_language,
                rerank_weight=rerank_weight,
            )
            for language, verses in verse_summary.items()
        }
        rerank_applied = True
    result = {
        "query_text": query_text,
        "selected_emotions": selected_features,
        "verse_summary": verse_summary,
        "rerank": {
            "enabled": enable_rerank,
            "applied": rerank_applied,
            "model": RERANK_MODEL_NAME if enable_rerank else None,
            "candidate_pool_per_language": candidate_pool_size if enable_rerank else None,
            "weight": rerank_weight if enable_rerank else None,
        },
    }
    if include_guidance:
        result["guidance"] = assess_psychological_state(query_text)
    return result


def result_to_markdown(result: dict) -> str:
    lines = []
    lines.append("# Emotion Query Result")
    lines.append("")
    lines.append(f"**Query**: {result.get('query_text', '')}")
    lines.append("")
    lines.append("## Matched Emotion Features")
    lines.append("")
    for idx, feature in enumerate(result.get("selected_emotions", []), start=1):
        lines.append(
            f"- **{idx}. {feature.get('layer')}:{feature.get('feature_id')}** | "
            f"keyword=`{feature.get('source_keyword')}` | similarity={feature.get('similarity', 0.0):.4f}"
        )
        lines.append(f"  - {feature.get('explanation', '')}")
    for language in ("cuv", "esv"):
        verses = result.get("verse_summary", {}).get(language, [])
        lines.append("")
        lines.append(f"## {language.upper()} Verses")
        lines.append("")
        for idx, verse in enumerate(verses, start=1):
            lines.append(
                f"- **{idx}. {verse.get('pk_id')}** | score={verse.get('combined_score', 0.0):.4f} | "
                f"{verse.get('book_name')} {verse.get('chapter')}:{verse.get('verse')}"
            )
            lines.append(f"  - {verse.get('raw_text', '')}")
    lines.append("")
    return "\n".join(lines)


def result_to_rows(result: dict) -> list[dict]:
    feature_lookup = {
        item["feature_key"]: item for item in result.get("selected_emotions", [])
    }
    rows = []
    for language, verses in result.get("verse_summary", {}).items():
        for rank, verse in enumerate(verses, start=1):
            matched_features = verse.get("matched_features", [])
            matched_feature_keys = []
            matched_feature_explanations = []
            for feature_hit in matched_features:
                feature_key_value = f"{feature_hit.get('layer')}:{feature_hit.get('feature_id')}"
                matched_feature_keys.append(feature_key_value)
                matched_feature_explanations.append(
                    feature_lookup.get(feature_key_value, {}).get("explanation", "")
                )
            rows.append(
                {
                    "query_text": result.get("query_text", ""),
                    "language": language,
                    "rank": rank,
                    "pk_id": verse.get("pk_id"),
                    "book_name": verse.get("book_name"),
                    "chapter": verse.get("chapter"),
                    "verse": verse.get("verse"),
                    "combined_score": verse.get("combined_score"),
                    "final_score": verse.get("final_score"),
                    "rerank_score": verse.get("rerank_score"),
                    "best_feature_similarity": verse.get("best_feature_similarity"),
                    "best_verse_score": verse.get("best_verse_score"),
                    "raw_text": verse.get("raw_text"),
                    "matched_feature_keys": " | ".join(matched_feature_keys),
                    "matched_feature_explanations": " | ".join(matched_feature_explanations),
                }
            )
    return rows


def export_result_files(result: dict, output_dir: str = DEFAULT_OUTPUT_DIR, slug: str | None = None) -> dict:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if slug is None:
        slug = str(int(time.time()))

    json_path = output_path / f"emotion_query_{slug}.json"
    markdown_path = output_path / f"emotion_query_{slug}.md"
    csv_path = output_path / f"emotion_query_{slug}.csv"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    with open(markdown_path, "w", encoding="utf-8") as f:
        f.write(result_to_markdown(result))

    rows = result_to_rows(result)
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [
            "query_text", "language", "rank", "pk_id", "book_name", "chapter", "verse",
            "combined_score", "final_score", "rerank_score", "best_feature_similarity", "best_verse_score", "raw_text",
            "matched_feature_keys", "matched_feature_explanations",
        ])
        writer.writeheader()
        if rows:
            writer.writerows(rows)

    return {
        "json": str(json_path),
        "markdown": str(markdown_path),
        "csv": str(csv_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Natural language -> emotion features -> verse summary")
    parser.add_argument("query", nargs="?", help="自然语言查询文本")
    parser.add_argument("--query-file", help="从文本文件读取查询")
    parser.add_argument("--top-features", type=int, default=DEFAULT_TOP_FEATURES)
    parser.add_argument("--top-verses", type=int, default=DEFAULT_TOP_VERSES_PER_LANGUAGE)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--slug", default=None)
    parser.add_argument("--export", action="store_true", help="导出 JSON/Markdown/CSV")
    parser.add_argument("--markdown", action="store_true", help="在终端输出 Markdown")
    parser.add_argument("--json", action="store_true", help="在终端输出 JSON")
    parser.add_argument("--guidance", action="store_true", help="调用 LLM 生成心理状态评估与灵性指导")
    parser.add_argument("--enable-rerank", action="store_true", help="启用轻量 rerank 精排")
    parser.add_argument("--rerank-candidates", type=int, default=DEFAULT_RERANK_CANDIDATES)
    parser.add_argument("--rerank-weight", type=float, default=DEFAULT_RERANK_WEIGHT)
    return parser.parse_args()


def resolve_query_text(args: argparse.Namespace) -> str:
    if args.query_file:
        return Path(args.query_file).read_text(encoding="utf-8").strip()
    if args.query:
        return args.query.strip()
    raise ValueError("请提供 query 参数或 --query-file")


def main() -> None:
    args = parse_args()
    query = resolve_query_text(args)
    result = query_emotion_verses(
        query_text=query,
        top_features=args.top_features,
        top_verses_per_language=args.top_verses,
        include_guidance=args.guidance,
        enable_rerank=args.enable_rerank,
        rerank_candidates=args.rerank_candidates,
        rerank_weight=args.rerank_weight,
    )

    if args.export:
        paths = export_result_files(result, output_dir=args.output_dir, slug=args.slug)
        print(json.dumps({"exported": paths}, ensure_ascii=False, indent=2))

    if args.markdown:
        print(result_to_markdown(result))
    elif args.json or not args.export:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
