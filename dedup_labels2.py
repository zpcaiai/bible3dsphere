#!/usr/bin/env python3
"""Second-pass dedup: eliminate all remaining short_en duplicates."""
import json
from pathlib import Path

LAYOUT_FILE = Path(__file__).parent / "emotion_sphere_layout.json"

# For each pair, pick ONE to change. Format: feature_key -> (zh_label, new_short_en)
# zh_label stays same unless noted.
PATCHES = {
    # acceptance x2: 接受(acceptance) vs 爱慕(acceptance→admiration)
    "2-llamascope-res-32k:3071":    ("爱慕",    "admiration"),

    # anxiety x2: 情绪(anxiety→agitation) vs 不安(anxiety)
    "17-llamascope-res-32k:7433":   ("情绪",    "agitation"),

    # attachment x2: 情牵(attachment) vs 对象情怀(attachment→devotion)
    "16-llamascope-res-32k:4839":   ("对象情怀", "devotion"),

    # concern x2: 关心感(concern) vs 牵挂(concern→worry)
    "0-llamascope-res-32k:16278":   ("牵挂",    "worry"),

    # contentment x2: 平和(contentment→equanimity) vs 满意度(contentment)
    "4-llamascope-res-32k:2967":    ("平和",    "equanimity"),

    # elation x2: 感慨(elation→awe) vs 畅快(elation)
    "3-llamascope-res-32k:9751":    ("感慨",    "awe"),

    # empathy x2: 悲悯(empathy→compassion) vs 心有戚戚(empathy)
    "6-llamascope-res-32k:16443":   ("悲悯",    "compassion"),

    # enjoyment x2: 享受感(enjoyment) vs 喜爱(enjoyment→fondness)
    "23-llamascope-res-32k:15359":  ("喜爱",    "fondness"),

    # excitement x2: 热切(excitement→eagerness) vs 欣奋(excitement)
    "21-llamascope-res-32k:5779":   ("热切",    "eagerness"),

    # exhilaration x2: 振奋(exhilaration→invigoration) vs 激动(exhilaration)
    "19-llamascope-res-32k:17599":  ("振奋",    "invigoration"),

    # fulfillment x2: 满足(fulfillment) vs 充实(fulfillment→enrichment)
    "19-llamascope-res-32k:3349":   ("充实",    "enrichment"),

    # gratitude x2: 感激(gratitude) vs 感念(gratitude→thankfulness)
    "0-llamascope-res-32k:30098":   ("感念",    "thankfulness"),

    # intimacy x2: 内情(intimacy→confidentiality) vs 私情(intimacy)
    "18-llamascope-res-32k:8128":   ("内情",    "confidentiality"),

    # longing x4: 渴慕→desire, 思念→longing, 眷恋→attachment, 依恋→yearning
    "25-llamascope-res-32k:16851":  ("渴慕",    "desire"),
    "13-llamascope-res-32k:27562":  ("眷恋",    "attachment"),
    "28-llamascope-res-32k:28642":  ("依恋",    "yearning"),
    # 思念 keeps longing; but yearning is now taken (渴盼/向往), fix:
    # 渴盼→longing, 向往→yearning, 依恋→infatuation
    "28-llamascope-res-32k:28642":  ("依恋",    "infatuation"),

    # nostalgia x2: 追忆(nostalgia) vs 怀旧(nostalgia→reminiscence)
    "28-llamascope-res-32k:32431":  ("怀旧",    "reminiscence"),

    # optimism x2: 乐观情感(optimism) vs 乐观情绪(optimism→hopefulness)
    "29-llamascope-res-32k:26305":  ("乐观情绪", "hopefulness"),

    # positivity x2: 积极(positivity) vs 积极体验(positivity→affirmation)
    "4-llamascope-res-32k:6538":    ("积极体验", "affirmation"),

    # rapture x2: 陶醉(rapture) vs 沉醉(rapture→intoxication)
    "3-llamascope-res-32k:31540":   ("沉醉",    "intoxication"),

    # realization x2: 心有所感(realization) vs 理解感(realization→comprehension)
    "2-llamascope-res-32k:4241":    ("理解感",  "comprehension"),

    # remembrance x2: 缅怀(remembrance) vs 追思(remembrance→commemoration)
    "1-llamascope-res-32k:23915":   ("追思",    "commemoration"),

    # reverie x2: 意境(reverie) vs 情思(reverie→daydream)
    "24-llamascope-res-32k:28483":  ("情思",    "daydream"),

    # serenity x2: 悠然(serenity) vs 宁静(serenity→tranquility)
    "12-llamascope-res-32k:18513":  ("宁静",    "tranquility"),

    # sorrow x2: 悲恸(sorrow→lamentation) vs 悲戚(sorrow)
    "23-llamascope-res-32k:17869":  ("悲恸",    "lamentation"),

    # subjectivity x2: 主观感(subjectivity) vs 主观情感(subjectivity→introspection)
    "21-llamascope-res-32k:22182":  ("主观情感", "introspection"),

    # tenderness x2: 细腻(tenderness→delicacy) vs 情意(tenderness)
    "21-llamascope-res-32k:13782":  ("细腻",    "delicacy"),

    # touch x2: 动容(touch→moved) vs 触感(touch→tactile)
    "9-llamascope-res-32k:28668":   ("动容",    "moved"),
    "30-llamascope-res-32k:27930":  ("触感",    "tactile"),

    # turmoil x2: 百感交集(turmoil→overwhelm) vs 心潮澎湃(turmoil)
    "26-llamascope-res-32k:30221":  ("百感交集", "overwhelm"),

    # warmth x2: 慰藉(warmth→solace) vs 款待(warmth→hospitality)
    "25-llamascope-res-32k:9554":   ("慰藉",    "solace"),
    "1-llamascope-res-32k:19624":   ("款待",    "hospitality"),

    # yearning x2: 渴盼(yearning) vs 向往(yearning→aspiration)
    # Note: aspiration already used by 翘望 — use 'longing' for 向往? No, longing is used.
    # 向往 = "aspire toward" → use "aspire"
    "10-llamascope-res-32k:19244":  ("向往",    "aspire"),

    # nostalgia conflict: 怀旧 was just changed to reminiscence,
    # but 情怀 also has reminiscence -> fix 情怀
    "4-llamascope-res-32k:14252":   ("情怀",    "sentimentality"),

    # remembrance conflict: 缅怀=remembrance, 追思=commemoration (ok), 追忆=nostalgia (ok)
    # attachment conflict: 情牵=attachment, 对象情怀=devotion, 眷恋=attachment -> fix 眷恋
    "13-llamascope-res-32k:27562":  ("眷恋",    "devotedness"),
}

data = json.loads(LAYOUT_FILE.read_text(encoding="utf-8"))

changed = 0
for item in data:
    p = PATCHES.get(item["feature_key"])
    if p:
        old = (item["zh_label"], item["short_en"])
        item["zh_label"], item["short_en"] = p
        print(f"  {item['feature_key']}: {old} -> {p}")
        changed += 1

LAYOUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nChanged {changed} nodes. Saved.")
