#!/usr/bin/env python3
"""
Relabel emotion sphere nodes with precise zh_label and short_en using LLM.
Reads emotion_sphere_layout.json, rewrites zh_label + short_en, saves back.
"""
import json
import time
import sys
from pathlib import Path
import requests

LAYOUT_FILE = Path(__file__).parent / "emotion_sphere_layout.json"
BACKUP_FILE = Path(__file__).parent / "emotion_sphere_layout.backup.json"

SILICONFLOW_API_KEY = "sk-dibqkgftealwtpzskkhhovdscfkzmerzxiewpyssnbdcxdeg"
SILICONFLOW_CHAT_URL = "https://api.siliconflow.cn/v1/chat/completions"
SILICONFLOW_CHAT_MODEL = "Qwen/Qwen2.5-72B-Instruct"

SYSTEM_PROMPT = """You are an expert in emotion psychology and biblical studies.
Given a cluster of emotion-related neural network features, produce precise labels.

Rules:
- zh_label: 2-4 Chinese characters, a poetic yet precise emotion word. Must be SPECIFIC (not generic like 感觉/情感/体验). Examples of good labels: 悲怆、释然、惶惑、敬畏、温柔、哀恸、盼望、羞耻、嫉妒、怜悯.
- short_en: 1-2 English words, precise emotion noun/adjective. Must be SPECIFIC (not generic like "feeling"/"emotion"/"mood"). Examples: "grief", "awe", "longing", "shame", "compassion", "despair", "hope", "guilt".

Respond ONLY with valid JSON: {"zh_label": "...", "short_en": "..."}
No explanation, no markdown, just the JSON object."""


def headers():
    return {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json",
    }


def get_neighbor_keywords(item: dict, all_items: list[dict]) -> list[str]:
    """Extract explanation snippets from nearest neighbors for context."""
    key_map = {x["feature_key"]: x for x in all_items}
    keywords = []
    for nk in item.get("nearest_neighbors", [])[:4]:
        neighbor = key_map.get(nk)
        if neighbor:
            exp = neighbor.get("explanation", "").strip().lstrip()
            if exp:
                keywords.append(exp)
    return keywords


def build_prompt(item: dict, all_items: list[dict]) -> str:
    explanation = item.get("explanation", "").strip().lstrip()
    source_kw = item.get("source_keyword", "")
    neighbor_exps = get_neighbor_keywords(item, all_items)

    lines = [
        f"Source keyword: {source_kw}",
        f"Feature explanation: {explanation}",
    ]
    if neighbor_exps:
        lines.append("Nearby related features:")
        for exp in neighbor_exps:
            lines.append(f"  - {exp}")
    lines.append(f"\nCurrent labels (may be inaccurate): zh_label='{item.get('zh_label','')}', short_en='{item.get('short_en','')}'")
    lines.append("\nProvide precise replacement labels.")
    return "\n".join(lines)


def call_llm(prompt: str, retries: int = 3) -> dict | None:
    for attempt in range(retries):
        try:
            resp = requests.post(
                SILICONFLOW_CHAT_URL,
                headers=headers(),
                json={
                    "model": SILICONFLOW_CHAT_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 60,
                },
                timeout=30,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            # Strip markdown code fences if present
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            result = json.loads(content)
            if "zh_label" in result and "short_en" in result:
                return result
        except Exception as e:
            print(f"  [attempt {attempt+1}] error: {e}", flush=True)
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    return None


def main():
    # Backup original
    data = json.loads(LAYOUT_FILE.read_text(encoding="utf-8"))
    if not BACKUP_FILE.exists():
        BACKUP_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Backup saved to {BACKUP_FILE.name}", flush=True)

    total = len(data)
    updated = 0
    failed = []

    for i, item in enumerate(data):
        fkey = item.get("feature_key", f"idx-{i}")
        old_zh = item.get("zh_label", "")
        old_en = item.get("short_en", "")

        prompt = build_prompt(item, data)
        print(f"[{i+1:3d}/{total}] {fkey}  old=({old_zh} / {old_en})", end="  ", flush=True)

        result = call_llm(prompt)
        if result:
            new_zh = result["zh_label"].strip()
            new_en = result["short_en"].strip()
            item["zh_label"] = new_zh
            item["short_en"] = new_en
            updated += 1
            print(f"-> ({new_zh} / {new_en})", flush=True)
        else:
            failed.append(fkey)
            print("FAILED (keeping original)", flush=True)

        # Save progress every 20 items
        if (i + 1) % 20 == 0:
            LAYOUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  [checkpoint saved at {i+1}]", flush=True)

        # Rate limit
        time.sleep(0.3)

    # Final save
    LAYOUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDone. {updated}/{total} updated. {len(failed)} failed.", flush=True)
    if failed:
        print("Failed keys:", failed, flush=True)


if __name__ == "__main__":
    main()
