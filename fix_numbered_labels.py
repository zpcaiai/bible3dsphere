#!/usr/bin/env python3
"""
Fix labels that ended up with numeric suffixes (情愫2, 感慨3, etc.)
by asking LLM for a truly distinct Chinese emotion word, avoiding all already-used labels.
"""
import json, re, time
from pathlib import Path
import requests
from query_emotion_verses import SILICONFLOW_API_KEY, SILICONFLOW_CHAT_URL

LAYOUT_FILE = Path("emotion_sphere_layout.json")
MODEL = "Qwen/Qwen2.5-72B-Instruct"
HEADERS = {"Authorization": f"Bearer {SILICONFLOW_API_KEY}", "Content-Type": "application/json"}

SYSTEM = """你是汉语情感词汇专家。

我会给你一条英文情感特征描述，以及一组**已被占用、不能再用**的中文词列表。
请给出一个**全新的、精确的、2-4个汉字**的中文情感词，必须不在已用列表中。

优先从以下词库中选择（如不适用可自行创造）：
渴慕 思念 喜悦 安慰 盼望 感恩 怜悯 敬畏 哀恸 悔恨 羞愧 嫉妒 愤恨 忧郁 迷惘
彷徨 期待 失落 沮丧 抑郁 焦虑 恐惧 惊慌 厌倦 冷漠 淡然 宁静 平和 欢欣 雀跃
振奋 鼓舞 感动 动容 怀念 眷恋 依恋 留恋 憧憬 向往 渴望 追求 执着 坚毅 勇气
柔情 温存 体贴 关怀 呵护 珍惜 守护 承担 包容 谅解 宽恕 和解 释怀 超脱 升华
心疼 酸楚 委屈 隐忍 压抑 克制 挣扎 纠结 两难 矛盾 复杂 微妙 细腻 丰富 深沉
热忱 赤诚 真挚 坦诚 信任 依赖 归属 认同 共鸣 契合 融洽 亲密 疏离 隔阂 陌生

只输出那一个中文词，不要任何解释或标点。"""


def call_llm(exp: str, used: list[str]) -> str:
    user = f"英文描述：{exp.strip()}\n\n已占用词（不能用）：{', '.join(sorted(used))}"
    payload = {
        "model": MODEL,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": user}],
        "temperature": 0.5,
        "max_tokens": 20,
    }
    for attempt in range(3):
        try:
            r = requests.post(SILICONFLOW_CHAT_URL, json=payload, headers=HEADERS, timeout=30)
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"].strip()
            # Take first word/line only, strip punctuation
            raw = re.sub(r'[^\u4e00-\u9fff]', '', raw.split('\n')[0])
            return raw[:4] if raw else ""
        except Exception as e:
            print(f"  retry {attempt+1}: {e}")
            time.sleep(3 * (attempt + 1))
    return ""


def main():
    layout = json.loads(LAYOUT_FILE.read_text(encoding="utf-8"))

    # Find items with numeric suffixes
    numbered = [(i, item) for i, item in enumerate(layout)
                if re.search(r'\d+$', item.get("zh_label", ""))]
    print(f"Items with numeric suffix: {len(numbered)}")

    used_labels = {item["zh_label"] for item in layout}

    for i, item in numbered:
        exp = item["explanation"]
        old_label = item["zh_label"]
        used_now = sorted(used_labels - {old_label})

        print(f"  [{i}] {old_label!r} → ?  ({exp[:60]})")
        new_label = call_llm(exp, used_now)

        if not new_label or new_label in used_labels:
            print(f"    WARN: got {new_label!r}, skipping")
            continue

        used_labels.discard(old_label)
        used_labels.add(new_label)
        layout[i]["zh_label"] = new_label
        print(f"    ✓ {old_label!r} → {new_label!r}")
        time.sleep(0.3)

    LAYOUT_FILE.write_text(json.dumps(layout, ensure_ascii=False, indent=2), encoding="utf-8")

    # Final check
    from collections import Counter
    cnt = Counter(item["zh_label"] for item in layout)
    dups = {k: v for k, v in cnt.items() if v > 1}
    numbered_remain = [(i, item["zh_label"]) for i, item in enumerate(layout)
                       if re.search(r'\d+$', item.get("zh_label", ""))]
    print(f"\nDone. Remaining duplicates: {dups}")
    print(f"Remaining numbered: {len(numbered_remain)}")
    if numbered_remain:
        for i, lbl in numbered_remain[:10]:
            print(f"  [{i}] {lbl!r}")


if __name__ == "__main__":
    main()
