"""
fear_of_man_engine.py — 怕人 → 敬畏神 / The Fear of Man（Ed Welch
《当人变得渺小·当神变得伟大》When People Are Big and God Is Small）

极高频的现实捆绑，此前只在别的引擎里零散出现。与已建的 fear_of_god 天然一体两面：
怕人使人变小、神变小；敬畏神使神变大、人回到正位。

Welch 的核心：**怕人**——被别人的看法、认可、拒绝所辖制——是「网罗」（箴29:25）。
它的根有几种：怕**被拒绝**（要人的爱）、怕**被看穿/羞辱**（要人的看重）、怕**被伤害/被控制**（要人的保护）。
共同点是把人「放大」到了神的位置。**解药不是不在乎人，而是把神放大**：
敬畏神过于怕人；从基督支取被接纳的身份，好叫你能**去爱人**，而不是**需要人**。
Welch 的反转公式：不再「怕人、利用神」，而是「敬畏神、爱人」。

纯函数；确定性优先；内置危机词检测；AI 仅作可选增强。不定罪、不贴「你太软弱」，
只把人从「怕人的网罗」领回「敬畏神、被神接纳、去爱人」。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

FORMS: List[Dict[str, Any]] = [
    {"key": "please", "name": "讨好 / 不会拒绝 / 怕让人失望",
     "kw": ["讨好", "不会拒绝", "不敢说不", "怕让人失望", "老好人", "答应", "迎合", "委屈自己", "怕得罪"],
     "root": "你把「别人的满意」放大成了必需——怕拒绝就失去他们的接纳。",
     "cure": "你在基督里已被完全接纳，不必再用讨好去赚。因为不缺爱，你才能自由地去爱、也能诚实地说「不」。"
             "敬畏神过于怕人：先问「神要我怎么行」，而不是「他们会怎么想」。",
     "ref": "加1:10", "text": "我现在是要得人的心呢？还是要得神的心呢？……我就不是基督的仆人了。"},
    {"key": "criticism", "name": "被批评就崩 / 太在意别人评价",
     "kw": ["批评", "评价", "在意别人", "被说", "别人怎么看", "否定", "指责就崩", "玻璃心", "被看轻"],
     "root": "你把「别人的评价」放大成了你的法官——他们的一句话能定你的价值。",
     "cure": "你的价值不由人的评价裁定，而由神的评价定案：在基督里你已蒙悦纳。人的批评可以听、可以学，"
             "但不再是审判你的法官。神对你的定论，才是终审。",
     "ref": "林前4:3-4", "text": "我被你们论断，或被别人论断，我都以为极小的事……判断我的乃是主。"},
    {"key": "rejection", "name": "怕被拒绝 / 怕被抛弃、被排挤",
     "kw": ["怕被拒绝", "被抛弃", "被排挤", "怕孤立", "融不进", "没人要", "被冷落", "怕被讨厌", "落单"],
     "root": "你把「被人接纳」放大成了安全感的地基——被拒绝就像失去一切。",
     "cure": "有一位永不离弃你的，已经把你接纳到底。当地基是「神绝不撇下我」，人的接纳与否就不再能摧毁你。"
             "你可以带着这份稳妥去靠近人——即使被拒，你仍是被神接纳的。",
     "ref": "来13:5", "text": "因为主曾说：我总不撇下你，也不丢弃你。"},
    {"key": "shame", "name": "怕被看穿 / 怕出丑、被羞辱",
     "kw": ["被看穿", "出丑", "羞辱", "怕丢脸", "怕暴露", "社恐", "怕表现不好", "尴尬", "怕被笑"],
     "root": "你把「在人前的体面」放大成了必须守住的东西——怕被看穿真实的自己。",
     "cure": "神已经看穿了你的全部，却仍在基督里完全接纳你——「被完全看见、仍被完全爱」。既然最深的暴露"
             "在神面前已经安全，人前的出丑就不再是灭顶之灾。你可以卸下表演，活得真实。",
     "ref": "诗34:5", "text": "凡仰望他的，便有光荣；他们的脸必不蒙羞。"},
    {"key": "pressure", "name": "同侪压力 / 随波逐流、不敢与众不同",
     "kw": ["同侪", "压力", "随波", "不敢不同", "从众", "怕另类", "跟风", "不敢坚持", "怕被孤立才做"],
     "root": "你把「合群、被这群人认可」放大成了不能失去的——于是随了不该随的流。",
     "cure": "讨神喜悦比讨人喜悦更值得。敬畏神给你勇气与众不同——不是标新立异，而是当众人向左，你能因神向右。"
             "你只有一位真正要交账的对象。",
     "ref": "箴29:25", "text": "惧怕人的，陷入网罗；惟有倚靠耶和华的，必得安稳。"},
    {"key": "witness", "name": "怕别人眼光，不敢表明信仰",
     "kw": ["不敢传", "怕别人知道", "不敢表明", "信仰", "怕被笑信教", "见证", "不敢承认", "怕异样眼光"],
     "root": "你把「在人前的形象」放大到了盖过「认主」——怕别人的眼光过于在乎主的心。",
     "cure": "敬畏神会松开怕人的舌头。你不必辩赢谁、也不必完美，只需不再把人的眼光放在主之上。"
             "从一句诚实、自然的分享开始——主与你同在。",
     "ref": "太10:28", "text": "那杀身体不能杀灵魂的，不要怕他们……惟有能把身体和灵魂都灭在地狱里的，正要怕他。"},
]

CRISIS_WORDS = ["自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死",
                "死了算了", "伤害自己", "撑不下去了", "没有意义活着", "想消失"]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = ("我听见你正承受很重的痛。如果你有伤害自己的念头，请现在就联系你信任的人或当地心理危机热线。"
               "在神眼中你是宝贵的，不由任何人的眼光定夺——你也值得有人此刻真实地陪着你。（本功能不替代专业帮助。）")


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best, best_hits = None, 0
    for d in FORMS:
        hits = sum(1 for k in d["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, d
    return best or FORMS[0]


def meta() -> Dict[str, Any]:
    return {
        "title": "怕人 → 敬畏神",
        "source": "Ed Welch《当人变得渺小·当神变得伟大》",
        "core": "怕人（被他人看法/认可/拒绝辖制）是网罗；解药不是不在乎人，而是把神放大——敬畏神、从基督支取接纳，好去爱人而非需要人。",
        "forms": [{"key": d["key"], "name": d["name"]} for d in FORMS],
        "reversal": "反转公式：不再『怕人、利用神』，而是『敬畏神、爱人』。",
        "verse": "箴29:25",
        "principle": "「惧怕人的，陷入网罗；惟有倚靠耶和华的，必得安稳。」",
    }


def analyze(text: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    text = (text or "").strip()
    crisis = _detect_crisis(text)
    picked = _pick(text)
    result: Dict[str, Any] = {
        "crisis": crisis, "crisis_note": CRISIS_NOTE if crisis else "",
        "form": {"key": picked["key"], "name": picked["name"]},
        "root": picked["root"],
        "cure": picked["cure"],
        "reversal": "把公式倒过来：不再『怕人、利用神』，而是『敬畏神、爱人』——因不缺接纳，才能自由地爱。",
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "prayer": ("主啊，我承认我把人放大了，大到盖过了你——我太在意他们的看法、认可与接纳，就被捆住了。"
                   "求你在我眼中变得伟大，叫我敬畏你过于怕人。谢谢你在基督里已经完全接纳我；"
                   "因为我不缺你的爱，求你叫我能自由地去爱人，而不是被『需要人』辖制。让我今天先讨你的喜悦。"),
        "practices": [
            "一个小小的不讨好：本周做一件「讨神喜悦但可能让某人不满意」的对的事，练习敬畏神过于怕人。",
            "换地基：当那份在意涌上来，默想「在基督里我已被完全接纳」（" + picked["ref"] + "），从这里再面对那个人。",
        ],
        "summary": ("怕人是网罗，因为把人放大到了神的位置。解药不是变冷漠，而是把神放大：敬畏神、"
                    "从基督支取被接纳的身份，好叫你能去爱人，而不是被需要人辖制。"),
        "closing": "「惧怕人的，陷入网罗；惟有倚靠耶和华的，必得安稳。」（箴29:25）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return ("你是一位温柔、以福音为中心的属灵陪伴者，熟悉 Ed Welch《当人变得渺小·当神变得伟大》。"
            "核心：怕人(被他人看法/认可/拒绝辖制)是网罗(箴29:25)，根在把人放大到神的位置；解药是把神放大——"
            "敬畏神、从基督支取被接纳的身份，好去『爱人』而非『需要人』(反转:不再怕人利用神,而是敬畏神爱人)。"
            "请针对用户处境，温柔指出怕人的形态与根，给出反转、经文、祷告与一个小操练。中文，绝不贴『你太软弱』的标签。\n"
            f"用户处境：{text}\n"
            "请输出 JSON：{\"root\":\"...\",\"cure\":\"...\",\"prayer\":\"一段可照着祷告的话\",\"summary\":\"...\",\"closing\":\"一句经文\"}。")


def _ai_enhance(text, base, settings):
    raw = _call_ai(build_prompt(text, base), settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        return {k: str(data[k]) for k in ("root", "cure", "prayer", "summary", "closing") if data.get(k)} or None
    except Exception:
        return None


def _call_ai(prompt, settings):
    for modname, fn in (("engine_ai", "call_ai"),):
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
        return (["fear_of_god", "identity", "freedom"], False, True, 2.0)
    return (["fear_of_god", "identity", "freedom"], True, True, 4.5)
