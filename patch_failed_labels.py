#!/usr/bin/env python3
"""Static patch for the 26 failed nodes - maps zh_label to precise short_en."""
import json
from pathlib import Path

LAYOUT_FILE = Path(__file__).parent / "emotion_sphere_layout.json"

# feature_key -> (zh_label override if needed, short_en)
# zh_label kept as-is unless noted; short_en chosen from zh_label meaning
PATCHES = {
    "5-llamascope-res-32k:22687":   (None,       "longing"),       # 思念
    "28-llamascope-res-32k:32431":  (None,       "nostalgia"),     # 怀旧
    "22-llamascope-res-32k:32342":  (None,       "remembrance"),   # 缅怀
    "14-llamascope-res-32k:30673":  (None,       "aspiration"),    # 憧憬
    "0-llamascope-res-32k:18908":   (None,       "reverie"),       # 意境
    "17-llamascope-res-32k:10844":  ("情感流露",  "outpouring"),    # 情感表露 -> 情感流露
    "18-llamascope-res-32k:25961":  (None,       "yearning"),      # 渴盼
    "19-llamascope-res-32k:8917":   (None,       "lingering"),     # 流连
    "30-llamascope-res-32k:27930":  (None,       "touch"),         # 触感
    "23-llamascope-res-32k:17869":  (None,       "sorrow"),        # 悲恸
    "2-llamascope-res-32k:3693":    (None,       "melancholy"),    # 凄婉
    "8-llamascope-res-32k:10541":   (None,       "dread"),         # 惶恐
    "9-llamascope-res-32k:23257":   (None,       "indignation"),   # 嗔怒
    "31-llamascope-res-32k:2954":   (None,       "expression"),    # 表情
    "21-llamascope-res-32k:4662":   ("情感表达",  "articulation"),  # 感受表达
    "20-llamascope-res-32k:28937":  (None,       "remorse"),       # 惭愧
    "14-llamascope-res-32k:22972":  (None,       "elation"),       # 欢畅
    "24-llamascope-res-32k:18720":  (None,       "complexity"),    # 复杂
    "7-llamascope-res-32k:21634":   ("情感",      "affect"),        # 情感
    "31-llamascope-res-32k:12799":  (None,       "context"),       # 情境
    "29-llamascope-res-32k:10690":  (None,       "atmosphere"),    # 情景
    "19-llamascope-res-32k:17599":  (None,       "exhilaration"),  # 振奋
    "18-llamascope-res-32k:1107":   ("文字情感",  "textual affect"),# 文本情感
    "11-llamascope-res-32k:8733":   (None,       "desolation"),    # 凄凉
    "5-llamascope-res-32k:20343":   (None,       "bitterness"),    # 辛酸
    "18-llamascope-res-32k:4631":   (None,       "alarm"),         # 惊惶
}

data = json.loads(LAYOUT_FILE.read_text(encoding="utf-8"))

patched = 0
for item in data:
    fkey = item.get("feature_key")
    if fkey in PATCHES:
        zh_override, short_en = PATCHES[fkey]
        old_en = item.get("short_en", "")
        if zh_override:
            item["zh_label"] = zh_override
        item["short_en"] = short_en
        patched += 1
        print(f"  {fkey}: ({item['zh_label']} / {old_en}) -> ({item['zh_label']} / {short_en})")

LAYOUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nPatched {patched} nodes. Saved.")
