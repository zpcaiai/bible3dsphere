#!/usr/bin/env python3
"""
Extract a 1-3 word English emotion label from each feature's explanation,
save as `short_en` in emotion_sphere_layout.json.  Resumable.
"""
import json, time
from pathlib import Path
import requests
from query_emotion_verses import SILICONFLOW_API_KEY, SILICONFLOW_CHAT_URL

LAYOUT_FILE = Path("emotion_sphere_layout.json")
MODEL = "Qwen/Qwen2.5-7B-Instruct"
HEADERS = {"Authorization": f"Bearer {SILICONFLOW_API_KEY}", "Content-Type": "application/json"}
BATCH = 25

SYSTEM = (
    "You are a concise emotion labeler. "
    "I will give you numbered English emotion feature descriptions. "
    "For each, output a 1-3 word English emotion label (noun or adjective phrase, no punctuation). "
    "Strict format — one line per item:\n"
    "1. loneliness\n2. joy\n3. guilt\n..."
)

def call_batch(batch):
    lines = "\n".join(f"{j+1}. {exp}" for j, (_, exp) in enumerate(batch))
    payload = {"model": MODEL,
               "messages": [{"role":"system","content":SYSTEM},
                             {"role":"user","content":lines}],
               "temperature": 0.1, "max_tokens": 250}
    for attempt in range(3):
        try:
            r = requests.post(SILICONFLOW_CHAT_URL, json=payload, headers=HEADERS, timeout=30)
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"].strip()
            out = {}
            for line in raw.splitlines():
                parts = line.strip().split(".", 1)
                if len(parts) == 2:
                    try: out[int(parts[0].strip())] = parts[1].strip()
                    except ValueError: pass
            return out
        except Exception as e:
            print(f"  retry {attempt+1}: {e}"); time.sleep(2*(attempt+1))
    return {}

def main():
    layout = json.loads(LAYOUT_FILE.read_text())
    pending = [(i, item["explanation"]) for i, item in enumerate(layout) if not item.get("short_en")]
    print(f"Pending: {len(pending)}/171")
    if not pending: return

    done = 0
    for start in range(0, len(pending), BATCH):
        chunk = pending[start:start+BATCH]
        print(f"  batch {start//BATCH+1} ({len(chunk)} items)...", end=" ", flush=True)
        tr = call_batch(chunk)
        for j, (i, _) in enumerate(chunk):
            lbl = tr.get(j+1)
            if lbl:
                layout[i]["short_en"] = lbl; done += 1
            else:
                print(f"\n  WARN: no label for item {i}")
        print(f"got {len(tr)}")
        LAYOUT_FILE.write_text(json.dumps(layout, ensure_ascii=False, indent=2))
        time.sleep(0.3)

    print(f"Done. {done} labelled.")

if __name__ == "__main__":
    main()
