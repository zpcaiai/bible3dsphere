#!/usr/bin/env python3
"""
Translate each emotion feature's English explanation into a concise 2-4 char
Chinese emotional label and write it back to emotion_sphere_layout.json as
the `zh_label` field.  Already-labelled items are skipped (resumable).
"""
import json
import time
from pathlib import Path

import requests
from query_emotion_verses import SILICONFLOW_API_KEY, SILICONFLOW_CHAT_URL

LAYOUT_FILE = Path("emotion_sphere_layout.json")
API_URL = SILICONFLOW_CHAT_URL
MODEL = "Qwen/Qwen2.5-7B-Instruct"
API_KEY = SILICONFLOW_API_KEY

BATCH_SIZE = 20   # items per LLM call
RETRY = 3
BACKOFF = 2.0

SYSTEM = (
    "你是情感词典翻译专家。"
    "我会给你一批英文情感描述（每行一条，格式为 序号. 描述），"
    "请将每条翻译为 2-4 个汉字的中文情感词（可以是词组），"
    "只输出对应序号和中文词，格式严格如下（不要多余内容）：\n"
    "1. 感受\n2. 孤独\n..."
)


HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def call_batch(batch: list[tuple[int, str]]) -> dict[int, str]:
    lines = "\n".join(f"{idx}. {exp}" for idx, exp in batch)
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": lines},
        ],
        "temperature": 0.2,
        "max_tokens": 300,
    }
    for attempt in range(1, RETRY + 1):
        try:
            r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=30)
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"].strip()
            result = {}
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split(".", 1)
                if len(parts) == 2:
                    try:
                        seq = int(parts[0].strip())
                        label = parts[1].strip()
                        result[seq] = label
                    except ValueError:
                        pass
            return result
        except Exception as e:
            print(f"  attempt {attempt} failed: {e}")
            if attempt < RETRY:
                time.sleep(BACKOFF * attempt)
    return {}


def main():
    layout = json.loads(LAYOUT_FILE.read_text(encoding="utf-8"))

    # Find items that still need translation
    pending = [(i, item) for i, item in enumerate(layout) if not item.get("zh_label")]
    print(f"Total items: {len(layout)}, pending translation: {len(pending)}")

    if not pending:
        print("All items already have zh_label, nothing to do.")
        return

    done = 0
    for start in range(0, len(pending), BATCH_SIZE):
        chunk = pending[start: start + BATCH_SIZE]
        batch_input = [(j + 1, layout[i]["explanation"]) for j, (i, _) in enumerate(chunk)]

        print(f"  Translating batch {start // BATCH_SIZE + 1} ({len(chunk)} items)...", end=" ", flush=True)
        translations = call_batch(batch_input)

        for j, (i, _) in enumerate(chunk):
            label = translations.get(j + 1)
            if label:
                layout[i]["zh_label"] = label
                done += 1
            else:
                print(f"\n  WARNING: no translation for item {i} ({layout[i]['explanation'][:50]})")

        print(f"got {len(translations)} labels")
        LAYOUT_FILE.write_text(json.dumps(layout, ensure_ascii=False, indent=2), encoding="utf-8")
        time.sleep(0.3)  # rate limit courtesy

    print(f"\nDone. Labelled {done}/{len(pending)} items. Saved to {LAYOUT_FILE}")


if __name__ == "__main__":
    main()
