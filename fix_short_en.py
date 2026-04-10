#!/usr/bin/env python3
"""
For items where short_en is still generic (feeling/sentiment/emotion),
derive short_en by translating zh_label to English instead.
"""
import json, time
from pathlib import Path
import requests
from query_emotion_verses import SILICONFLOW_API_KEY, SILICONFLOW_CHAT_URL

LAYOUT_FILE = Path("emotion_sphere_layout.json")
MODEL = "Qwen/Qwen2.5-7B-Instruct"
HEADERS = {"Authorization": f"Bearer {SILICONFLOW_API_KEY}", "Content-Type": "application/json"}
GENERIC = {'feeling', 'sentiment', 'emotion', 'feelings', 'emotions', 'sense'}
BATCH = 30

SYSTEM = (
    "Translate each numbered Chinese emotion word into a concise 1-3 word English emotion label. "
    "Output one line per item in strict format:\n"
    "1. loneliness\n2. joyfulness\n3. inner peace\n..."
)

def call_batch(batch):
    lines = "\n".join(f"{j+1}. {zh}" for j, (_, zh) in enumerate(batch))
    payload = {"model": MODEL,
               "messages": [{"role":"system","content":SYSTEM},
                             {"role":"user","content":lines}],
               "temperature": 0.1, "max_tokens": 200}
    for attempt in range(3):
        try:
            r = requests.post(SILICONFLOW_CHAT_URL, json=payload, headers=HEADERS, timeout=30)
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"].strip()
            out = {}
            for line in raw.splitlines():
                parts = line.strip().split(".", 1)
                if len(parts) == 2:
                    try: out[int(parts[0].strip())] = parts[1].strip().lower()
                    except ValueError: pass
            return out
        except Exception as e:
            print(f"  retry {attempt+1}: {e}"); time.sleep(2*(attempt+1))
    return {}

def main():
    layout = json.loads(LAYOUT_FILE.read_text())
    pending = [(i, item["zh_label"]) for i, item in enumerate(layout)
               if item.get("short_en", "").lower() in GENERIC or not item.get("short_en")]
    print(f"Fixing {len(pending)} generic labels...")

    done = 0
    for start in range(0, len(pending), BATCH):
        chunk = pending[start:start+BATCH]
        print(f"  batch {start//BATCH+1} ({len(chunk)})...", end=" ", flush=True)
        tr = call_batch(chunk)
        for j, (i, _) in enumerate(chunk):
            lbl = tr.get(j+1)
            if lbl:
                layout[i]["short_en"] = lbl; done += 1
        print(f"got {len(tr)}")
        LAYOUT_FILE.write_text(json.dumps(layout, ensure_ascii=False, indent=2))
        time.sleep(0.3)

    print(f"Done. Fixed {done}/{len(pending)}.")

if __name__ == "__main__":
    main()
