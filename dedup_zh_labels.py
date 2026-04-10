#!/usr/bin/env python3
"""
Re-label duplicate zh_label entries with unique, precise Chinese emotion words.
For each group of duplicates, sends all their explanations to LLM together,
asking for distinct labels that differentiate the subtle nuances.
"""
import json, time
from collections import defaultdict
from pathlib import Path
import requests
from query_emotion_verses import SILICONFLOW_API_KEY, SILICONFLOW_CHAT_URL

LAYOUT_FILE = Path("emotion_sphere_layout.json")
MODEL = "Qwen/Qwen2.5-72B-Instruct"   # use the big model for nuance
HEADERS = {"Authorization": f"Bearer {SILICONFLOW_API_KEY}", "Content-Type": "application/json"}

SYSTEM = """你是情感词典专家，精通汉语情感词汇的细微区分。

我会给你一组英文情感特征描述，它们目前都被翻译成了同一个中文词（因为太泛化）。
请仔细阅读每条描述的细微差别，为每条给出一个**独特、精确、2-4个汉字**的中文情感词。

要求：
- 每条必须不同，不能重复
- 优先用具体情感词（如：渴慕、释怀、惆怅、慰藉、欣喜、忐忑、感恩、敬畏、哀恸、怜悯、热切、淡然）
- 避免泛化词（情感、感受、表达、情绪）
- 如果描述涉及特定场景，词语可以带场景感（如：如释重负、念念不忘、百感交集）
- 严格按序号输出，格式：序号. 中文词（不要加任何解释）

示例输出格式：
1. 惆怅
2. 欣喜
3. 忐忑"""


def call_llm(system: str, user: str) -> str:
    payload = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": 0.3,
        "max_tokens": 600,
    }
    for attempt in range(3):
        try:
            r = requests.post(SILICONFLOW_CHAT_URL, json=payload, headers=HEADERS, timeout=45)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"  retry {attempt+1}: {e}")
            time.sleep(3 * (attempt + 1))
    return ""


def parse_numbered(raw: str) -> dict[int, str]:
    result = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(".", 1)
        if len(parts) == 2:
            try:
                result[int(parts[0].strip())] = parts[1].strip()
            except ValueError:
                pass
    return result


def main():
    layout = json.loads(LAYOUT_FILE.read_text(encoding="utf-8"))

    # Build groups of duplicates
    groups: dict[str, list[int]] = defaultdict(list)
    for i, item in enumerate(layout):
        groups[item["zh_label"]].append(i)

    dup_groups = {zh: idxs for zh, idxs in groups.items() if len(idxs) > 1}
    print(f"Duplicate groups: {len(dup_groups)}, total items to re-label: {sum(len(v) for v in dup_groups.values())}")

    # Track all labels already used (start with unique ones)
    used_labels: set[str] = {item["zh_label"] for item in layout
                              if groups[item["zh_label"]] and len(groups[item["zh_label"]]) == 1}

    total_fixed = 0
    for zh, idxs in sorted(dup_groups.items(), key=lambda x: -len(x[1])):
        entries = [(j + 1, layout[i]["explanation"]) for j, i in enumerate(idxs)]
        user_msg = (
            f'当前这些描述都被翻译成了"{zh}"，请为每条给出不同的精确中文情感词：\n\n'
            + "\n".join(f"{seq}. {exp.strip()}" for seq, exp in entries)
        )
        print(f"\n  [{zh}] × {len(idxs)} items → re-labeling...", flush=True)
        raw = call_llm(SYSTEM, user_msg)
        translations = parse_numbered(raw)

        for j, i in enumerate(idxs):
            new_label = translations.get(j + 1, "").strip()
            if not new_label:
                print(f"    WARNING: no label for item {i} (seq {j+1})")
                continue
            # Ensure uniqueness: if collision, append a suffix
            original = new_label
            suffix = 2
            while new_label in used_labels:
                new_label = f"{original}{suffix}"
                suffix += 1
            used_labels.add(new_label)
            old = layout[i]["zh_label"]
            layout[i]["zh_label"] = new_label
            print(f"    [{i}] {old!r} → {new_label!r}  ({layout[i]['explanation'][:50]})")
            total_fixed += 1

        # Save incrementally
        LAYOUT_FILE.write_text(json.dumps(layout, ensure_ascii=False, indent=2), encoding="utf-8")
        time.sleep(0.5)

    print(f"\nDone. Re-labeled {total_fixed} items.")

    # Final duplicate check
    from collections import Counter
    final_labels = [item["zh_label"] for item in layout]
    cnt = Counter(final_labels)
    remaining = {k: v for k, v in cnt.items() if v > 1}
    if remaining:
        print(f"Still duplicated: {remaining}")
    else:
        print("✓ All zh_labels are now unique!")


if __name__ == "__main__":
    main()
