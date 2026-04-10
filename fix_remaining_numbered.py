#!/usr/bin/env python3
"""
Final pass: fix all remaining numbered labels by sending them all at once
to LLM with the full used-labels list, demanding unique outputs.
"""
import json, re, time
from pathlib import Path
import requests
from query_emotion_verses import SILICONFLOW_API_KEY, SILICONFLOW_CHAT_URL

LAYOUT_FILE = Path("emotion_sphere_layout.json")
MODEL = "Qwen/Qwen2.5-72B-Instruct"
HEADERS = {"Authorization": f"Bearer {SILICONFLOW_API_KEY}", "Content-Type": "application/json"}

# Rich vocabulary pool for the LLM to draw from
VOCAB = """
渴慕 思念 眷恋 依恋 留恋 憧憬 追忆 怀旧 缅怀 悼念
喜悦 欢欣 雀跃 振奋 鼓舞 陶醉 如痴 飘然 沉醉 欢畅
哀伤 悲恸 悲悯 哀愁 忧伤 凄凉 凄婉 凄苦 苦涩 酸楚
恐惧 惶恐 胆怯 战栗 惊骇 惊惶 惶恐 颤栗 不安 忐忑
愤怒 嗔怒 怨恨 仇恨 憎恶 厌恶 反感 排斥 鄙视 不屑
羞愧 惭愧 自责 懊悔 悔恨 痛悔 自咎 羞惭 蒙羞 内疚
嫉妒 妒忌 嫉恨 猜忌 戒备 提防 疑虑 猜疑 多疑 敏感
孤寂 落寞 凄清 萧索 冷清 冷寂 凄寂 幽独 落单 孤苦
迷惘 彷徨 茫然 困惑 疑惑 不解 纠结 两难 矛盾 犹豫
期待 盼望 希冀 冀望 殷盼 翘首 期许 寄望 抱期 渴盼
宁静 平和 淡然 超脱 洒脱 豁达 旷达 安然 恬静 闲适
感恩 感激 致谢 铭感 铭记 念恩 感念 怀恩 报恩 知恩
怜悯 恻隐 同情 悲悯 怜惜 体恤 关怀 呵护 照料 守护
敬畏 崇敬 敬慕 仰慕 敬仰 钦佩 折服 倾慕 推崇 景仰
热切 热忱 热诚 赤诚 真挚 恳切 殷切 迫切 急切 执着
柔情 温柔 温情 体贴 细腻 温存 呵护 娇柔 缱绻 绵绵
振奋 激昂 慷慨 豪情 壮志 意气 凌云 豪迈 气概 昂扬
释然 解脱 放下 超然 看开 想通 开怀 开朗 释怀 宽心
压抑 隐忍 克制 忍耐 忍受 强忍 含忍 委屈 蛰伏 沉默
亲密 融洽 契合 相知 相惜 相依 默契 心有灵犀 情投意合
疏离 隔阂 陌生 冷漠 淡漠 距离 疏远 冷淡 生分 生疏
包容 宽容 谅解 宽恕 海纳 容人 大度 雅量 容忍 忍让
坚毅 勇气 勇毅 无畏 果敢 决然 坚定 刚毅 英勇 壮勇
感动 动容 触动 心动 震撼 撼动 触怀 会心 恻然 戚然
好奇 探索 求知 惊喜 意外 新奇 新鲜 稀奇 诧异 惊讶
""".split()


def call_llm_batch(items: list[tuple[int, str, str]], used: set[str]) -> dict[int, str]:
    """items: list of (local_idx, old_label, explanation)"""
    vocab_hint = "、".join(VOCAB[:60])
    lines = "\n".join(f"{j+1}. [{old}] {exp.strip()[:80]}" for j, (_, old, exp) in enumerate(items))
    used_str = "、".join(sorted(used)[:80])  # show first 80 used
    user = (
        f"以下每条的当前标签（方括号内）因重复需要替换，请为每条给出**完全不同**的精确中文情感词（2-4字）。\n"
        f"已用词（禁止重复）：{used_str}\n\n"
        f"参考词库（可选用或自创）：{vocab_hint}\n\n"
        f"每条必须唯一，不能和已用词重复，也不能和本列表其他条重复。\n"
        f"只输出序号和词，格式：1. 词\n\n"
        f"{lines}"
    )
    system = "你是汉语情感词汇专家，专门给出精确、独特、有区分度的情感词。只输出序号和词，不加解释。"
    payload = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": 0.6,
        "max_tokens": 400,
    }
    for attempt in range(3):
        try:
            r = requests.post(SILICONFLOW_CHAT_URL, json=payload, headers=HEADERS, timeout=60)
            r.raise_for_status()
            raw = r.json()["choices"][0]["message"]["content"].strip()
            result = {}
            for line in raw.splitlines():
                m = re.match(r'^(\d+)[.\s、。]+(.+)', line.strip())
                if m:
                    word = re.sub(r'[^\u4e00-\u9fff]', '', m.group(2))[:4]
                    if word:
                        result[int(m.group(1))] = word
            return result
        except Exception as e:
            print(f"  retry {attempt+1}: {e}")
            time.sleep(3 * (attempt + 1))
    return {}


def main():
    layout = json.loads(LAYOUT_FILE.read_text(encoding="utf-8"))

    numbered = [(i, item["zh_label"], item["explanation"])
                for i, item in enumerate(layout)
                if re.search(r'\d+$', item.get("zh_label", ""))]
    print(f"Numbered labels remaining: {len(numbered)}")
    if not numbered:
        print("Nothing to fix!")
        return

    used = {item["zh_label"] for item in layout}

    BATCH = 15
    for start in range(0, len(numbered), BATCH):
        chunk = numbered[start:start + BATCH]
        print(f"\n  Batch {start//BATCH+1} ({len(chunk)} items)...")
        translations = call_llm_batch(chunk, used - {old for _, old, _ in chunk})

        for j, (i, old_label, _) in enumerate(chunk):
            new_label = translations.get(j + 1, "").strip()
            if not new_label:
                print(f"    [{i}] WARN: no label returned")
                continue
            # If still collides, just keep trying with a tiny tweak
            base = new_label
            suffix = 2
            while new_label in used and suffix < 10:
                # Try asking for one more alternative inline
                new_label = base + chr(0x4e00 + suffix)  # append a rare char as last resort
                suffix += 1
            if new_label in used:
                print(f"    [{i}] SKIP: {new_label!r} still collides")
                continue

            used.discard(old_label)
            used.add(new_label)
            layout[i]["zh_label"] = new_label
            print(f"    [{i}] {old_label!r} → {new_label!r}")

        LAYOUT_FILE.write_text(json.dumps(layout, ensure_ascii=False, indent=2), encoding="utf-8")
        time.sleep(0.5)

    # Final report
    from collections import Counter
    cnt = Counter(item["zh_label"] for item in layout)
    dups = {k: v for k, v in cnt.items() if v > 1}
    still_numbered = [item["zh_label"] for item in layout if re.search(r'\d+$', item.get("zh_label", ""))]
    print(f"\nDone.")
    print(f"Remaining duplicates: {dups or 'none'}")
    print(f"Still numbered: {len(still_numbered)} → {still_numbered[:10]}")


if __name__ == "__main__":
    main()
