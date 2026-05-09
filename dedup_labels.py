#!/usr/bin/env python3
"""Deduplicate zh_label and short_en in emotion_sphere_layout.json."""
import json
from pathlib import Path

LAYOUT_FILE = Path(__file__).parent / "emotion_sphere_layout.json"

# (feature_key) -> (new_zh_label, new_short_en)
PATCHES = {
    # ---- zh_label: 心绪 x5 -> differentiate ----
    "30-llamascope-res-32k:11280":  ("情感体验", "affective experience"),
    "14-llamascope-res-32k:15994":  ("情绪流动", "emotional flux"),
    "21-llamascope-res-32k:14049":  ("心绪涌动", "emotional stirring"),
    "13-llamascope-res-32k:26998":  ("体验感",   "experiential"),
    "27-llamascope-res-32k:5822":   ("主观感",   "subjectivity"),

    # ---- zh_label: 情绪 x2 ----
    "26-llamascope-res-32k:16773":  ("情绪状态", "emotional state"),

    # ---- zh_label: 心境 x2 ----
    "31-llamascope-res-32k:1174":   ("内心境界", "inner landscape"),

    # ---- zh_label: 心声 x2 ----
    "13-llamascope-res-32k:15210":  ("肺腑之言", "heartfelt"),

    # ---- zh_label: 感悟 x2 ----
    "2-llamascope-res-32k:28049":   ("心有所感", "realization"),

    # ---- zh_label: 情愫 x2 ----
    "21-llamascope-res-32k:29846":  ("情感态度", "emotional attitude"),

    # ---- zh_label: 哀伤 x2 ----
    "17-llamascope-res-32k:1731":   ("悲戚",     "sorrow"),

    # ---- short_en: affection x8 -> keep 情愫/affection, fix others ----
    "3-llamascope-res-32k:16151":   ("衷情",     "devotion"),
    "2-llamascope-res-32k:30286":   ("情致",     "ardor"),
    "31-llamascope-res-32k:19458":  ("私情",     "intimacy"),
    "16-llamascope-res-32k:4839":   ("对象情怀", "attachment"),
    "16-llamascope-res-32k:17953":  ("情谊",     "camaraderie"),
    "13-llamascope-res-32k:9449":   ("情意",     "tenderness"),

    # ---- short_en: longing x7 -> keep 渴慕/思念/眷恋/依恋, fix rest ----
    "0-llamascope-res-32k:16278":   ("牵挂",     "concern"),
    "13-llamascope-res-32k:20703":  ("情牵",     "attachment"),
    "23-llamascope-res-32k:10370":  ("依依",     "reluctance"),

    # ---- short_en: melancholy x6 -> keep 凄婉/melancholy, fix rest ----
    "14-llamascope-res-32k:27960":  ("格调",     "poignancy"),
    "26-llamascope-res-32k:13363":  ("情调",     "wistfulness"),
    "29-llamascope-res-32k:14094":  ("五味",     "bittersweet"),

    # ---- short_en: nostalgia x6 -> keep 追忆/怀旧, fix rest ----
    "4-llamascope-res-32k:14252":   ("情怀",     "reminiscence"),
    "24-llamascope-res-32k:28483":  ("情思",     "reverie"),
    "1-llamascope-res-32k:23915":   ("追思",     "remembrance"),
    "3-llamascope-res-32k:11974":   ("感怀",     "retrospection"),

    # ---- short_en: affect x3 -> keep 情感/affect, fix others ----
    "28-llamascope-res-32k:25898":  ("情表",     "outward affect"),
    "18-llamascope-res-32k:22429":  ("情态",     "demeanor"),

    # ---- short_en: hope x3 -> differentiate ----
    "26-llamascope-res-32k:26763":  ("希望感",   "anticipation"),
    "9-llamascope-res-32k:5090":    ("翘望",     "aspiration"),
    "1-llamascope-res-32k:12368":   ("希望",     "hope"),

    # ---- short_en: aspiration conflict (憧憬 also had aspiration) ----
    "14-llamascope-res-32k:30673":  ("憧憬",     "idealism"),

    # ---- short_en: satisfaction x3 ----
    "19-llamascope-res-32k:3349":   ("充实",     "fulfillment"),
    "12-llamascope-res-32k:25947":  ("满意度",   "contentment"),

    # ---- short_en: joy x3 ----
    "10-llamascope-res-32k:21957":  ("愉悦感",   "delight"),
    "3-llamascope-res-32k:9751":    ("感慨",     "elation"),

    # ---- short_en: positive x3 ----
    "1-llamascope-res-32k:31512":   ("喜悦",     "gladness"),
    "2-llamascope-res-32k:15629":   ("积极",     "positivity"),

    # ---- short_en: approval x3 ----
    "18-llamascope-res-32k:18988":  ("称颂",     "praise"),
    "9-llamascope-res-32k:26548":   ("褒扬",     "commendation"),

    # ---- short_en: happiness x3 -> keep 愉快/happiness, fix others ----
    "2-llamascope-res-32k:10257":   ("欣幸",     "fortune"),
    "4-llamascope-res-32k:26215":   ("悠然",     "serenity"),

    # ---- short_en: uncertainty x3 ----
    "20-llamascope-res-32k:19623":  ("混合情感", "ambivalence"),
    "11-llamascope-res-32k:6107":   ("忐忑",     "trepidation"),

    # ---- short_en: loneliness x3 ----
    "19-llamascope-res-32k:29168":  ("孤寂",     "solitude"),
    "23-llamascope-res-32k:31269":  ("孤独感",   "isolation"),

    # ---- short_en: grief x3 ----
    "0-llamascope-res-32k:16010":   ("怆然",     "anguish"),
    # 哀伤 keeps grief; 悲戚 gets sorrow (already patched above)

    # ---- short_en: insight x3 ----
    "20-llamascope-res-32k:1510":   ("体悟",     "epiphany"),

    # ---- short_en: anxiety x3 -> keep 不安/anxiety, fix others ----
    "4-llamascope-res-32k:10516":   ("心境",     "unease"),

    # ---- short_en: articulation x2 ----
    "22-llamascope-res-32k:21930":  ("情绪表达", "vocal expression"),

    # ---- short_en: compassion x2 ----
    "9-llamascope-res-32k:1069":    ("慈悲",     "compassion"),
    "6-llamascope-res-32k:16443":   ("悲悯",     "empathy"),

    # ---- short_en: elation x2 (欢畅 and 感慨 both got elation) ----
    "14-llamascope-res-32k:22972":  ("欢畅",     "exuberance"),

    # ---- short_en: bitterness x2 ----
    "5-llamascope-res-32k:20343":   ("辛酸",     "anguish"),   # conflict with 怆然/anguish -> fix
}

# Fix anguish conflict: 怆然 and 辛酸 can't both be anguish
# 怆然 = grief/anguish (deep grief), 辛酸 = bitterness/pain
# Override: keep 怆然/anguish, change 辛酸 to pathos
PATCHES["5-llamascope-res-32k:20343"] = ("辛酸", "pathos")


data = json.loads(LAYOUT_FILE.read_text(encoding="utf-8"))

changed = 0
for item in data:
    p = PATCHES.get(item["feature_key"])
    if p:
        old = (item["zh_label"], item["short_en"])
        item["zh_label"], item["short_en"] = p
        print(f"  {item['feature_key']}")
        print(f"    old: {old}")
        print(f"    new: {p}")
        changed += 1

LAYOUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nChanged {changed} nodes. Saved.")
