#!/usr/bin/env python3
"""
Offline fix: replace the 19 zh_labels that ended up with invalid suffix chars
(丂 / 七) with handcrafted, unique Chinese emotion words. No LLM calls needed.
"""
import json, re
from collections import Counter
from pathlib import Path

LAYOUT = Path("emotion_sphere_layout.json")

# 19 unique replacements, chosen to NOT conflict with any currently-used label.
# Verified against the full label set before writing this file.
REPLACEMENTS = {
    2:   "如梦",   # feel-like / perceptual states
    16:  "五味",   # mixed emotional states
    37:  "格调",   # general emotional tone
    41:  "意境",   # emotional atmosphere / words for emotion
    43:  "内情",   # inner feelings
    45:  "衷情",   # deep feelings / heartfelt emotion
    46:  "渴盼",   # earnest longing  (渴慕/渴望 taken)
    47:  "流连",   # lingering attachment
    49:  "追念",   # reminiscence / looking back
    89:  "慈悲",   # compassion / mercy  (悲悯 taken)
    121: "牵挂",   # worried concern / missing someone
    136: "情牵",   # emotionally attached
    137: "翘望",   # eager anticipation  (憧憬/向往 taken)
    147: "依依",   # reluctant parting feelings
    150: "追思",   # cherished memory  (缅怀 taken)
    153: "沉醉",   # deeply immersed / intoxicated  (陶醉 taken)
    160: "畅快",   # feeling of free joy  (欢畅 taken)
    164: "辛酸",   # bitter sorrow  (苦涩 taken)
    166: "惊惶",   # panic / alarmed  (惶恐 taken)
}


def main():
    layout = json.loads(LAYOUT.read_text(encoding="utf-8"))

    bad_indices = set(REPLACEMENTS.keys())
    used = {item["zh_label"] for i, item in enumerate(layout) if i not in bad_indices}

    # Pre-flight checks
    new_vals = list(REPLACEMENTS.values())
    conflicts = [v for v in new_vals if v in used]
    dupes = [v for v in new_vals if new_vals.count(v) > 1]
    if conflicts:
        print(f"ERROR – conflicts with existing labels: {conflicts}")
        return
    if dupes:
        print(f"ERROR – duplicates in replacement list: {set(dupes)}")
        return

    # Apply
    for idx, new_lbl in sorted(REPLACEMENTS.items()):
        old = layout[idx]["zh_label"]
        layout[idx]["zh_label"] = new_lbl
        print(f"  [{idx:3d}] {old!r:12} → {new_lbl!r}")

    LAYOUT.write_text(json.dumps(layout, ensure_ascii=False, indent=2), encoding="utf-8")

    # Final verification
    cnt = Counter(item["zh_label"] for item in layout)
    remaining_dups = {k: v for k, v in cnt.items() if v > 1}
    still_bad = [item["zh_label"] for item in layout
                 if re.search(r'[丂七\d]', item.get("zh_label", ""))]
    print(f"\n✓  Total:{len(layout)}  Unique:{len(cnt)}"
          f"  Dups:{remaining_dups or 'none'}  Bad-suffix:{still_bad or 'none'}")


if __name__ == "__main__":
    main()
