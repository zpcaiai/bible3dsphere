#!/usr/bin/env python3
"""
Fix short_en labels in emotion_sphere_layout.json.
Restores from backup, then rewrites ONLY short_en using zh_label + explanation as context.
Also fixes zh_label for nodes where it is too generic (感知/情感/体验 etc.)
"""
import json
import time
from pathlib import Path
import requests

LAYOUT_FILE = Path(__file__).parent / "emotion_sphere_layout.json"
BACKUP_FILE = Path(__file__).parent / "emotion_sphere_layout.backup.json"

SILICONFLOW_API_KEY = "sk-dibqkgftealwtpzskkhhovdscfkzmerzxiewpyssnbdcxdeg"
SILICONFLOW_CHAT_URL = "https://api.siliconflow.cn/v1/chat/completions"
SILICONFLOW_CHAT_MODEL = "Qwen/Qwen2.5-72B-Instruct"

# These zh_label values are considered too generic and need replacement
GENERIC_ZH = {
    "感知", "情感", "体验", "感觉", "心绪", "感受", "情感体验", "心象",
    "心境", "感悟", "感触", "情感描述", "情感经历", "情感词汇", "情感回应",
    "情感流露", "情感反应", "情感态度", "情感状态", "情感共鸣", "个人感受",
    "主观感受", "情感表露", "个人情感", "重要情感表达", "体验感", "文本情感",
    "对象情感", "集体情感", "负面情感", "个人意见", "情感情绪",
}

GENERIC_EN = {
    "feeling", "emotion", "mood", "expressions", "sentiments", "sentiment",
    "experiences", "states", "expression", "reactions", "attitudes",
    "emotion expression", "emotion description", "emotion word",
    "subjective feeling", "personal feeling", "complex emotion",
    "emotion experience",
}

SYSTEM_PROMPT = """You are an expert in emotion psychology, counseling, and biblical studies.
Given a Chinese emotion label and its English description, provide:
1. A precise English emotion word (short_en): 1-2 words, must be a specific emotion noun. 
   FORBIDDEN words: feeling, emotion, mood, sentiment, expression, experience, state, sensation
   GOOD examples: grief, awe, longing, shame, compassion, despair, hope, guilt, joy, fear, 
   rage, jealousy, wonder, solitude, nostalgia, yearning, relief, serenity, dread, elation,
   melancholy, gratitude, remorse, tenderness, anxiety, reverence, bitterness, desolation

2. A refined Chinese label (zh_label): 2-4 characters, poetic and specific.
   Only change zh_label if the current one is generic (感知/情感/体验/感受/心绪 etc.)
   GOOD examples: 悲怆 哀恸 释然 敬畏 温柔 盼望 羞愧 嫉妒 怜悯 惊惶 凄凉 哀恸 恸哭 悔恨 惆怅

Respond ONLY with valid JSON: {"zh_label": "...", "short_en": "..."}"""


def headers():
    return {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json",
    }


def needs_fix(item: dict) -> bool:
    return (
        item.get("short_en", "").strip().lower() in GENERIC_EN
        or item.get("zh_label", "").strip() in GENERIC_ZH
    )


def call_llm(zh_label: str, explanation: str, retries: int = 3) -> dict | None:
    user_msg = (
        f"Current zh_label: {zh_label}\n"
        f"Feature description: {explanation.strip()}\n\n"
        f"Provide precise labels."
    )
    for attempt in range(retries):
        try:
            resp = requests.post(
                SILICONFLOW_CHAT_URL,
                headers=headers(),
                json={
                    "model": SILICONFLOW_CHAT_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 60,
                },
                timeout=30,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
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
    # Always restore from backup first
    if not BACKUP_FILE.exists():
        print("ERROR: backup file not found. Cannot proceed safely.", flush=True)
        return

    data = json.loads(BACKUP_FILE.read_text(encoding="utf-8"))
    print(f"Restored {len(data)} nodes from backup.", flush=True)

    to_fix = [(i, item) for i, item in enumerate(data) if needs_fix(item)]
    print(f"Nodes needing fix: {len(to_fix)}", flush=True)
    print(flush=True)

    fixed = 0
    failed = []

    for seq, (i, item) in enumerate(to_fix):
        fkey = item.get("feature_key", f"idx-{i}")
        old_zh = item.get("zh_label", "")
        old_en = item.get("short_en", "")
        explanation = item.get("explanation", "")

        print(f"[{seq+1:3d}/{len(to_fix)}] {fkey}", flush=True)
        print(f"  old: ({old_zh} / {old_en})", flush=True)
        print(f"  exp: {explanation[:70]}", flush=True)

        result = call_llm(old_zh, explanation)
        if result:
            new_zh = result["zh_label"].strip()
            new_en = result["short_en"].strip()
            # Only update zh_label if it was generic
            if old_zh in GENERIC_ZH:
                item["zh_label"] = new_zh
            item["short_en"] = new_en
            fixed += 1
            print(f"  new: ({item['zh_label']} / {new_en})", flush=True)
        else:
            failed.append(fkey)
            print("  FAILED (keeping original)", flush=True)

        # Save every 15 items
        if (seq + 1) % 15 == 0:
            LAYOUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  [checkpoint saved at {seq+1}]", flush=True)

        time.sleep(0.25)

    # Final save
    LAYOUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDone. {fixed}/{len(to_fix)} fixed. {len(failed)} failed.", flush=True)
    if failed:
        print("Failed:", failed, flush=True)


if __name__ == "__main__":
    main()
