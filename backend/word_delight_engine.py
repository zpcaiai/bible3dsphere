"""
word_delight_engine.py — 爱慕神的话 / 诗篇119（对治「读经像任务」）

系统有读经/背经/麦琴/lectio 等**操练页**，但缺「爱慕圣言」的**塑造**——把「该读经」重构为
「以神的话为甜、为宝、为灯、为自由」。以诗篇119（全本圣经最长、专讲爱慕神话语的诗篇）为骨架。

诗119 给神的话的一串意象：**灯与光**（指引，105）、**甜（比蜜更甜）**（喜乐，103）、
**财宝（胜过金银）**（价值，72）、**自由（宽阔之地）**（14,45）、**藏在心里（防罪）**（11）、
**苏醒安慰（患难中）**（50,92）。对治「读经像任务」的，不是更用力，而是重见它的甜与宝。

纯函数；确定性优先；内置危机词检测；AI 仅作可选增强。不制造「你读经不够」的重担，
只帮助人从「义务」转向「爱慕」，给一个小而可尝到甜的读经操练。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

BLOCKS: List[Dict[str, Any]] = [
    {"key": "duty", "name": "读经像例行任务 / 打卡、没味道",
     "kw": ["任务", "打卡", "例行", "没味道", "应付", "读不进", "干巴", "义务", "枯燥", "走过场"],
     "image": "甜（比蜜更甜）", "note": "读经变苦差，往往因为把它当成『交作业』，而不是『来吃甜的』。",
     "way": "把『读完多少』换成『尝到一句』。今天只读一小段，找出一句触动你的话，慢慢咀嚼、当作神对你说的，"
            "宁可少而甜，不要多而干。神的话本是比蜜更甜的。",
     "ref": "诗119:103", "text": "你的言语在我上膛何等甘美，在我口中比蜜更甜！",
     "practice": "只取一句：读一小段，挑一句最触动你的，反复默想、当作神今天对你说的话，尝它的甜。"},
    {"key": "lost", "name": "读了不知道有什么用 / 跟生活接不上",
     "kw": ["没用", "接不上", "不知道用", "跟生活", "记不住", "读了就忘", "抽象", "离生活远", "读了白读"],
     "image": "灯与光（指引）", "note": "神的话是脚前的灯、路上的光——它未必一次照亮全程，但够照亮你的下一步。",
     "way": "读的时候带一个问题：『这段话，对我今天的一个具体处境说了什么？』让它作你下一步的灯，"
            "而不是一堆存起来的信息。哪怕只领受一个可行的亮光，就够了。",
     "ref": "诗119:105", "text": "你的话是我脚前的灯，是我路上的光。",
     "practice": "带一个处境来读：读前想一件今天的难处，读时问『这里有什么亮光照到它』，领受一步就好。"},
    {"key": "guilt", "name": "因为读得少而愧疚 / 断断续续",
     "kw": ["愧疚", "读得少", "断断续续", "坚持不了", "总是停", "做不到每天", "内疚", "又没读", "半途"],
     "image": "自由（宽阔之地）", "note": "神的话本要带来自由，不该变成新的重担。愧疚不会让你更爱它。",
     "way": "别在愧疚里给自己加码。神的话是恩典不是律法——从『我必须每天读多少』的重担里出来，"
            "改成『我可以随时来喝一口』。今天不追赶进度，只是回来，尝一小口就好。",
     "ref": "诗119:45", "text": "我要自由而行，因我素来考究你的训词。",
     "practice": "轻装回来：不补进度、不愧疚，今天只读一节，谢谢神你可以随时回到祂的话语这口井。"},
    {"key": "hard", "name": "在患难中，想从神的话得安慰",
     "kw": ["患难", "安慰", "难处", "痛", "熬", "苦", "撑", "低谷", "眼泪", "受苦"],
     "image": "苏醒与安慰（患难中）", "note": "诗人说：这话是他患难中的安慰，使他苏醒——神的话在低谷里最显它的分量。",
     "way": "难处里，不必读很多，读能『扶住你』的。去诗篇找一篇与你此刻共鸣的，把它当作神此刻的搀扶；"
            "让一句应许成为你今天抓住的绳子。",
     "ref": "诗119:50", "text": "这话将我救活了；我在患难中，因此得安慰。",
     "practice": "找一句扶住你的：到诗篇挑一句此刻能抓住的应许，抄下来，今天反复对自己读。"},
    {"key": "grow", "name": "想更爱慕神的话 / 想读得更有生命",
     "kw": ["爱慕", "更爱神的话", "有生命", "渴慕", "更深", "喜爱", "宝贝", "亲近神的话", "扎根"],
     "image": "财宝（胜过金银）+ 藏在心里", "note": "诗人视神的话胜过千万金银，又把它藏在心里以免得罪神。",
     "way": "从『读』进到『藏』：选一节你珍爱的经文背下来、藏在心里——被藏起来的话，会在你需要时"
            "自己浮上来，成为随身的财宝。爱慕是一次次尝到它的宝贵而长出来的。",
     "ref": "诗119:11", "text": "我将你的话藏在心里，免得我得罪你。",
     "practice": "藏一节在心里：选一节你珍爱的经文，今天背下来，让它成为随身的财宝。"},
]

CRISIS_WORDS = ["自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死",
                "死了算了", "伤害自己", "撑不下去了", "没有意义活着", "想消失"]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = ("我听见你正承受很重的痛。如果你有伤害自己的念头，请现在就联系你信任的人或当地心理危机热线。"
               "神的话说『这话将我救活了』——你也值得有人此刻真实地陪着你。（本功能不替代专业帮助。）")


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best, best_hits = None, 0
    for d in BLOCKS:
        hits = sum(1 for k in d["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, d
    return best or BLOCKS[0]


def meta() -> Dict[str, Any]:
    return {
        "title": "爱慕神的话 · 诗篇119",
        "source": "诗篇119（全本圣经最长、专讲爱慕神话语的诗篇）",
        "core": "把『该读经』重构为『以神的话为甜、为宝、为灯、为自由』——对治读经像任务，不靠更用力，而靠重见它的甜与宝。",
        "images": ["灯与光(指引)", "比蜜更甜(喜乐)", "胜过金银(财宝)", "宽阔之地(自由)", "藏在心里(防罪)", "患难中苏醒(安慰)"],
        "blocks": [{"key": d["key"], "name": d["name"]} for d in BLOCKS],
        "verse": "诗119:103",
        "principle": "「你的言语在我上膛何等甘美，在我口中比蜜更甜！」——爱慕不是靠意志，是靠尝到它的甜。",
    }


def analyze(text: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    text = (text or "").strip()
    crisis = _detect_crisis(text)
    picked = _pick(text)
    result: Dict[str, Any] = {
        "crisis": crisis, "crisis_note": CRISIS_NOTE if crisis else "",
        "block": {"key": picked["key"], "name": picked["name"]},
        "image": picked["image"],
        "diagnosis": picked["note"],
        "way_forward": picked["way"],
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "word_practice": picked["practice"],
        "prayer": ("主啊，饶恕我常把你的话当成任务、当成负担，忘了它本是比蜜更甜、胜过金银的。"
                   "求你开我的眼，叫我重新尝到你话语的甜；开我的心，叫我爱慕它、藏它在心里。"
                   "叫你的话作我脚前的灯、患难中的安慰、宽阔之地里的自由。我不求读得多，只求读得甜、活得出。"),
        "practices": [
            picked["practice"],
            "读后回应一句：读完对神说一句话回应祂（谢谢/求/降服），把读经从『输入』变成『相会』。",
        ],
        "summary": ("爱慕神的话不靠更用力，而靠重见它的甜与宝：它是灯、是蜜、是财宝、是自由、是患难中的安慰。"
                    "宁可少而甜地尝一句，胜过多而干地读一堆。"),
        "closing": "「你的言语……在我口中比蜜更甜！」（诗119:103）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return ("你是一位温柔、以福音为中心的属灵陪伴者，熟悉诗篇119对神话语的爱慕。核心：把『该读经』重构为"
            "『以神的话为甜/宝/灯/自由』——对治读经像任务，不靠更用力，而靠重见它的甜；诗119意象：灯光、比蜜甜、"
            "胜金银、宽阔之地、藏在心里、患难中苏醒。请针对用户处境，温柔诊断其卡点，给一个小而可尝到甜的读经操练、"
            "经文与祷告。中文，绝不制造『你读经不够』的愧疚。\n"
            f"用户处境：{text}\n"
            "请输出 JSON：{\"diagnosis\":\"...\",\"word_practice\":\"...\",\"prayer\":\"一段可照着祷告的话\",\"summary\":\"...\",\"closing\":\"一句经文\"}。")


def _ai_enhance(text, base, settings):
    raw = _call_ai(build_prompt(text, base), settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        return {k: str(data[k]) for k in ("diagnosis", "word_practice", "prayer", "summary", "closing") if data.get(k)} or None
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
        return (["word", "delight", "growth"], False, True, 2.0)
    return (["word", "delight", "growth"], True, True, 4.0)
