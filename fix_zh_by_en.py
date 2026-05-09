#!/usr/bin/env python3
"""Fix zh_label to accurately match short_en (English is the authoritative source)."""
import json
from pathlib import Path

LAYOUT_FILE = Path(__file__).parent / "emotion_sphere_layout.json"

# short_en -> correct zh_label
EN_TO_ZH = {
    "fortune":        "幸运感",    # fortune = luck/good fortune, not 欣幸
    "unease":         "不安感",    # unease = discomfort/anxiety, not 心境(mindset)
    "confession":     "告白",      # confession = revealing inner truth, not just 心声
    "poignancy":      "触动",      # poignancy = moving/piercing feeling, not 格调(style/tone)
    "infatuation":    "痴迷",      # infatuation = obsessive attraction, not 依恋(attachment)
    "idealism":       "理想",      # idealism = belief in ideals, not 憧憬(longing)
    "absolution":     "赦免",      # absolution = forgiveness/pardon, not 卸责(shirk responsibility)
    "awe":            "敬畏",      # awe = wonder+reverence, not 感慨(sigh/lament)
    "guilt":          "罪咎",      # guilt = moral culpability, not 道德感(moral sense)
    "self-reflection":"自我反思",   # self-reflection = introspection of self, not 主观情感
    "idealization":   "理想化",    # idealization = seeing as perfect, not 向往(aspire toward)
    "demeanor":       "神态",      # demeanor = outward manner/bearing, not 情态
    "pathos":         "悲情",      # pathos = evoking pity/sadness, not 辛酸(bitterness/hardship)
    "devotedness":    "忠诚",      # devotedness = loyal dedication, not 眷恋(clinging fondness)
    "introspection":  "内省",      # introspection = examining own mind (反省 is closer to repentance)
}

data = json.loads(LAYOUT_FILE.read_text(encoding="utf-8"))

changed = 0
for item in data:
    en = item["short_en"]
    if en in EN_TO_ZH:
        old_zh = item["zh_label"]
        new_zh = EN_TO_ZH[en]
        item["zh_label"] = new_zh
        print(f"  [{en:25s}] zh: {old_zh} -> {new_zh}")
        changed += 1

LAYOUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nChanged {changed} nodes. Saved.")
