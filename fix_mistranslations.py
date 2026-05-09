#!/usr/bin/env python3
"""Fix inaccurate zh/en label pairs."""
import json
from pathlib import Path

LAYOUT_FILE = Path(__file__).parent / "emotion_sphere_layout.json"

# feature_key -> (new_zh_label, new_short_en)
# Only fix genuinely wrong pairs; zh_label updated where needed too
PATCHES = {
    # 情语/eloquence -> eloquence是雄辩，情语是"情感言语" -> utterance
    "3-llamascope-res-32k:23361":   ("情语",    "utterance"),

    # 内情/confidentiality -> 内情是内心情感 -> inner feeling
    "18-llamascope-res-32k:8128":   ("内情",    "inner feeling"),

    # 丰富/variegated -> 丰富情感 -> richness
    "21-llamascope-res-32k:13867":  ("丰富",    "richness"),

    # 追念/emotional states -> 追念是追忆怀念 -> commemoration (追思已占) -> veneration
    "2-llamascope-res-32k:22916":   ("心意",    "intent"),

    # 共鸣/connections -> 共鸣是resonance
    "12-llamascope-res-32k:17366":  ("共鸣",    "resonance"),

    # 意识/sense of -> 意识是consciousness/awareness (觉知已占awareness) -> consciousness
    "21-llamascope-res-32k:14049":  ("意识感",  "consciousness"),

    # 渴望/descriptors -> 渴望是craving/longing (longing占用) -> craving
    "25-llamascope-res-32k:14428":  ("渴望",    "craving"),

    # 悔恨/situations -> 悔恨是remorse (remorse已占by惭愧) -> regret
    "20-llamascope-res-32k:21752":  ("悔恨",    "regret"),

    # 特殊享受/enjoyable -> enjoyable是形容词 -> indulgence
    "14-llamascope-res-32k:4049":   ("特殊享受", "indulgence"),

    # 音乐情感/music -> 音乐情感 -> musical feeling
    "8-llamascope-res-32k:14898":   ("音乐情感", "musical feeling"),

    # 影响感受/influenced -> influenced不准 -> susceptibility
    "28-llamascope-res-32k:11049":  ("影响感受", "susceptibility"),

    # 评价感受/evaluations -> appraisal更准
    "12-llamascope-res-32k:30673":  ("评价感受", "appraisal"),

    # 热忱/markers -> markers完全错 -> fervor
    "9-llamascope-res-32k:14728":   ("热忱",    "fervor"),

    # 情感重音/emphasis -> emphasis不是情绪 -> intensity
    "14-llamascope-res-32k:12717":  ("情感强度", "intensity"),

    # 炽烈/charged -> intense更准
    "9-llamascope-res-32k:23913":   ("炽烈",    "intense"),

    # 深情/depth -> depth太泛 -> deep love
    "7-llamascope-res-32k:20082":   ("深情",    "deep love"),

    # 卸责/accountability -> 卸责是卸下负担/推卸责任 -> absolution
    "21-llamascope-res-32k:7985":   ("卸责",    "absolution"),

    # 幸福/fortunate -> fortunate是幸运 幸福是bliss
    "18-llamascope-res-32k:10564":  ("幸福",    "bliss"),

    # 心境描绘/description -> description太泛 -> portrayal
    "20-llamascope-res-32k:23205":  ("心境描绘", "portrayal"),

    # 个人观点/opinion -> 个人观点不算情绪 -> personal stance
    "15-llamascope-res-32k:26865":  ("个人观点", "personal stance"),

    # 凉爽/cool -> 凉爽在情绪语境 -> refreshing
    "5-llamascope-res-32k:29441":   ("凉爽",    "refreshing"),

    # 追念(心意)/intent -> 心意=intent ✓ (已在上面修正追念节点)
    # 体感/somatic -> somatic可接受（身体感受的学术词）保留

    # 情绪词汇/emotional terms -> 改为更精准的 lexicon
    "23-llamascope-res-32k:15355":  ("情绪词汇", "lexicon"),

    # 感知/perception ✓ 保留
    # 情感体验/affective experience ✓ 保留
}

data = json.loads(LAYOUT_FILE.read_text(encoding="utf-8"))

# Build feature_key lookup
key_map = {item["feature_key"]: item for item in data}

# Also fix by matching zh_label for nodes where we don't know the exact key
ZH_PATCHES = {
    # zh_label -> (new_zh_label, new_short_en)
    "追念":    ("追念",    "veneration"),
    "凉爽":    ("凉爽",    "refreshing"),
    "特殊享受": ("特殊享受", "indulgence"),
    "音乐情感": ("音乐情感", "musical feeling"),
    "影响感受": ("影响感受", "susceptibility"),
    "评价感受": ("评价感受", "appraisal"),
    "热忱":    ("热忱",    "fervor"),
    "情感重音": ("情感强度", "intensity"),
    "炽烈":    ("炽烈",    "intense"),
    "深情":    ("深情",    "deep love"),
    "卸责":    ("卸责",    "absolution"),
    "幸福":    ("幸福",    "bliss"),
    "心境描绘": ("心境描绘", "portrayal"),
    "个人观点": ("个人观点", "personal stance"),
    "共鸣":    ("共鸣",    "resonance"),
    "内情":    ("内情",    "inner feeling"),
    "丰富":    ("丰富",    "richness"),
    "情语":    ("情语",    "utterance"),
    "意识":    ("意识感",  "consciousness"),
    "渴望":    ("渴望",    "craving"),
    "悔恨":    ("悔恨",    "regret"),
    "情绪词汇": ("情绪词汇", "lexicon"),
}

changed = 0
for item in data:
    zh = item["zh_label"]
    if zh in ZH_PATCHES:
        new_zh, new_en = ZH_PATCHES[zh]
        old = (item["zh_label"], item["short_en"])
        item["zh_label"] = new_zh
        item["short_en"] = new_en
        print(f"  [{item['feature_key']}] {old} -> ({new_zh}, {new_en})")
        changed += 1

LAYOUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nChanged {changed} nodes. Saved.")
