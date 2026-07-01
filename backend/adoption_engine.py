"""
adoption_engine.py — 儿子的名分 / 天父的收纳 / Abba（巴刻《认识神》收纳章；
辛克莱·傅格森《成为神的儿女》Children of the Living God）

补「身份层」最温暖的一块。巴刻说：**收纳（adoption）是福音的最高特权**——
高于称义。称义把我从审判台上无罪开释（法庭语言）；收纳把我领进家里、给我父的名、
赐我「儿子的灵」，叫我可以喊「阿爸，父」（罗8:15；加4:4-7）。我不再是孤儿、不再是奴仆、
不再是雇工——我是神所爱的儿女，是后嗣，与基督同作后嗣。

三个转向：孤儿→儿女（不再靠自己）、奴仆→儿子（不再靠表现赚爱）、疏远→亲密（可坦然喊阿爸）。
纯函数；确定性优先；内置危机词检测；AI 仅作可选增强。语气最温暖，只把人从「孤儿/奴仆」的谎言
领回「被父收纳」的怀里。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

STATES: List[Dict[str, Any]] = [
    {"key": "orphan", "name": "觉得孤立无援 / 像个孤儿，什么都得靠自己",
     "kw": ["孤儿", "靠自己", "没人管", "孤立无援", "一个人扛", "没有依靠", "无依无靠", "自生自灭", "没人要"],
     "lie": "我是孤儿，一切都得自己扛。",
     "truth": "你不是孤儿。神藉圣灵把你收纳为儿女，赐你「儿子的灵」——你有一位天父，祂看顾你、供应你、"
              "不撇下你。你可以停止独自硬撑，回到父的看顾里。",
     "ref": "约14:18", "text": "我不撇下你们为孤儿，我必到你们这里来。"},
    {"key": "slave", "name": "总在靠表现赚神的爱 / 像个奴仆",
     "kw": ["赚", "表现", "不够好", "达标", "奴仆", "怕做不好", "换取", "证明自己", "值得被爱", "做得不够"],
     "lie": "我得表现够好，神才会爱我。",
     "truth": "你不是奴仆，是儿子。神差祂儿子的灵进入你心，不是叫你重回「怕」的奴仆之灵，而是叫你喊「阿爸，父」。"
              "父的爱不是赚来的工价，是白白赐给儿女的名分。",
     "ref": "加4:6-7", "text": "神就差他儿子的灵进入你们的心，呼叫：阿爸，父！可见，从此以后，你不是奴仆，乃是儿子了。"},
    {"key": "distant", "name": "觉得神很遥远 / 不敢亲近祂",
     "kw": ["遥远", "不敢亲近", "隔", "疏远", "高高在上", "不敢祷告", "生分", "怕神", "有距离", "冷"],
     "lie": "神太遥远、太威严，我不敢靠近。",
     "truth": "藉着基督，你可以坦然无惧地进到父面前，甚至可以像孩子一样喊「阿爸」（是最亲昵的称呼）。"
              "威严的神，是你的父；施恩宝座是为祂儿女敞开的。",
     "ref": "罗8:15", "text": "你们所受的，不是奴仆的心，仍旧害怕；所受的，乃是儿子的心，因此我们呼叫：阿爸，父。"},
    {"key": "fatherwound", "name": "地上的父带来的伤，让我很难信靠天父",
     "kw": ["父亲", "爸", "原生", "父爱", "被父", "父亲的伤", "重男", "严厉的父", "缺失的父", "被抛弃"],
     "lie": "父亲让我失望/受伤，所以天父大概也一样。",
     "truth": "你地上的父或许软弱、或许缺席、或许伤了你——但天父不是他的放大版。天父是完全的父：祂的爱不改变、"
              "不落空、不离弃。祂正是要医治那道父爱的伤，让你重新学会被一位完全的父所爱。",
     "ref": "诗27:10", "text": "我父母离弃我，耶和华必收留我。"},
    {"key": "seek", "name": "想更深经历天父的爱 / 想学会喊阿爸",
     "kw": ["天父的爱", "阿爸", "被爱", "更深", "儿女", "收纳", "亲密", "父的怀抱", "归属", "被接纳"],
     "lie": "",
     "truth": "收纳是福音的最高特权。你不只被赦免，更被领进家里、给了父的名、赐了儿子的灵。"
              "让这真理沉下去：你是父所爱的孩子，这是比任何成就都深的身份。",
     "ref": "约壹3:1", "text": "你看父赐给我们是何等的慈爱，使我们得称为神的儿女；我们也真是他的儿女。"},
]

CRISIS_WORDS = ["自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死",
                "死了算了", "伤害自己", "撑不下去了", "没有意义活着", "想消失"]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = ("我听见你正承受很重的痛。如果你有伤害自己的念头，请现在就联系你信任的人或当地心理危机热线。"
               "你不是孤儿——有一位天父爱你、不撇下你，也愿有人此刻真实地陪着你。（本功能不替代专业帮助。）")


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best, best_hits = None, 0
    for d in STATES:
        hits = sum(1 for k in d["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, d
    return best or STATES[4]


def meta() -> Dict[str, Any]:
    return {
        "title": "儿子的名分 · 天父的收纳",
        "source": "巴刻《认识神》收纳章；辛克莱·傅格森《成为神的儿女》",
        "core": "收纳是福音的最高特权——不只被无罪开释（称义），更被领进家里、给父的名、赐儿子的灵，可喊阿爸。",
        "states": [{"key": d["key"], "name": d["name"]} for d in STATES],
        "verse": "加4:6-7",
        "principle": "「从此以后，你不是奴仆，乃是儿子了。」——身份的转变：从孤儿/奴仆，到被父收纳的儿女。",
    }


def analyze(text: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    text = (text or "").strip()
    crisis = _detect_crisis(text)
    picked = _pick(text)
    result: Dict[str, Any] = {
        "crisis": crisis, "crisis_note": CRISIS_NOTE if crisis else "",
        "state": {"key": picked["key"], "name": picked["name"]},
        "lie": picked.get("lie", ""),
        "adoption_truth": picked["truth"],
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "prayer": ("阿爸，父——谢谢你，我不只是被你赦免，更是被你收纳。我常常活得像孤儿，靠自己硬撑；"
                   "又常常活得像奴仆，想靠表现赚你的爱。今天求你的灵向我心里印证：我是你所爱的孩子。"
                   "医治我心里父爱的伤，教我坦然地回到你怀里，像孩子一样喊你——阿爸，父。"),
        "practices": [
            "学喊「阿爸」：安静下来，把「阿爸，父」这称呼慢慢对神说几遍，让它从头脑沉到心里。",
            "换掉谎言：把「" + (picked.get("lie") or "我得靠自己") + "」写下，旁边写上「我是父所收纳、所爱的儿女」（" + picked["ref"] + "）。",
        ],
        "summary": ("收纳是福音最高的特权：你不再是孤儿、不再是奴仆，而是被父领进家里、赐了父名与儿子的灵的儿女。"
                    "你可以坦然喊——阿爸，父。"),
        "closing": "「你看父赐给我们是何等的慈爱，使我们得称为神的儿女。」（约壹3:1）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return ("你是一位温柔、以福音为中心的属灵陪伴者，熟悉巴刻《认识神》收纳章与傅格森《成为神的儿女》。"
            "核心：收纳是福音最高特权——不只称义(无罪开释)，更被父领进家里、给父名、赐儿子的灵、可喊阿爸(罗8:15,加4:6-7)；"
            "从孤儿/奴仆到被爱的儿女。请针对用户处境，温柔地把对应的收纳真理说给他，语气最温暖，"
            "给经文、祷告与操练。中文，绝不说教、不定罪。\n"
            f"用户处境：{text}\n"
            "请输出 JSON：{\"adoption_truth\":\"...\",\"prayer\":\"一段可照着祷告的话\",\"summary\":\"...\",\"closing\":\"一句经文\"}。")


def _ai_enhance(text, base, settings):
    raw = _call_ai(build_prompt(text, base), settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        return {k: str(data[k]) for k in ("adoption_truth", "prayer", "summary", "closing") if data.get(k)} or None
    except Exception:
        return None


def _call_ai(prompt, settings):
    for modname, fn in (("waiting_engine", "call_ai_provider"), ("llm_provider", "call_llm")):
        try:
            mod = __import__(modname); f = getattr(mod, fn, None)
            if f:
                out = f(prompt) if settings is None else f(prompt, settings=settings)
                if out:
                    return out if isinstance(out, str) else str(out)
        except Exception:
            continue
    return None


def formation_signal(result):
    if result.get("crisis"):
        return (["identity", "adoption", "love"], False, True, 2.0)
    return (["identity", "adoption", "love"], True, True, 4.5)
