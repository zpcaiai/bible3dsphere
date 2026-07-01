"""
anger_engine.py — 忿怒 · 在神面前处理愤怒（David Powlison《Good and Angry》；弗4:26；哀怨诗篇）

补情绪层最后一味（已有哀歌/惧怕/羞愧/知足，独缺愤怒）。Powlison 的核心：愤怒本身不都是罪
——它是「对我所认为的错的回应」。问题不在于「有没有怒」，而在于「怒得对不对、如何处理」。
弗4:26「生气却不要犯罪」：不压抑、不爆发，而是带到神面前处理。

分辨：**义怒**（为真实的不义/邪恶、以神为中心、盼望公义与挽回）vs **私怒**（为受伤的自尊、
被拦阻的欲望、我要作神来审判）。多数日常的怒混着两者。
建设性的四步：(1)诚实命名（哀怨诗篇允许把生的怒摆在神前）；(2)察看底下（伤？惧？被拦阻的偶像？）；
(3)分辨这是神的事还是我的国；(4)把伸冤交给神（罗12:19），转向忍耐、饶恕或公义的行动。

纯函数；确定性；内置危机词检测 + 「伤人/暴力」倾向检测（命中则先导向安全与自控）；AI 可选增强。
不定罪、不压抑，只把怒从「爆发或压抑」引向「在神面前被听见、被炼净」。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

STATES: List[Dict[str, Any]] = [
    {"key": "explode", "name": "一点就炸 / 容易爆发、事后后悔",
     "kw": ["爆发", "一点就炸", "忍不住", "发脾气", "吼", "摔", "冲动", "失控", "后悔", "脾气上来"],
     "diag": "你的怒来得快、冲出去也快——问题多半不在有怒，而在它没被处理就先爆了出来。",
     "way": "弗4:26 说『生气却不要犯罪』。练习在怒与行动之间插一个『停顿』：先离开现场几分钟，"
            "把生的怒对神说出来（祂承受得住），再问『这底下是什么』，等能自控了再回应人。",
     "ref": "雅1:19-20", "text": "你们各人要快快地听，慢慢地说，慢慢地动怒，因为人的怒气并不成就神的义。"},
    {"key": "simmer", "name": "闷着的怒 / 记恨、生闷气、放不下",
     "kw": ["记恨", "生闷气", "放不下", "怨", "憋", "耿耿于怀", "冷战", "积怨", "咽不下", "越想越气"],
     "diag": "你把怒压了下去，它却在里面发酵成苦毒。压抑不是处理，只是把火埋进灰里。",
     "way": "别再假装没事，也别任它烧。把它端到神面前诚实说出来，然后走饶恕的路——不是说对方没错，"
            "而是把讨债权交给神（罗12:19）。闷着的怒最需要的，是被说出来、被交出去。",
     "ref": "弗4:26-27", "text": "不可含怒到日落，也不可给魔鬼留地步。"},
    {"key": "atgod", "name": "对神生气 / 觉得祂不公、祂让这事发生",
     "kw": ["对神生气", "神不公", "怪神", "为什么让", "神不管", "恨神", "凭什么", "神狠心", "怨神"],
     "diag": "你在对神生气——这不必藏着。诗篇里满了把不解与怒直接向神哭诉的祷告；祂宁可你带着怒来，也不愿你转身走开。",
     "way": "把对神的怒像哀怨诗篇那样如实倾诉（可到『哀歌』页）。神能承受你的质问。倾诉到底，"
            "常会在尽头遇见：祂并没有错待你，十字架证明了祂的爱——即使这一刻还想不通。",
     "ref": "诗13:1-2", "text": "耶和华啊，你忘记我要到几时呢？……我心里筹算，终日愁苦，要到几时呢？"},
    {"key": "injustice", "name": "为不义/邪恶而怒 / 义愤",
     "kw": ["不义", "邪恶", "不公", "看不下去", "义愤", "被欺压", "受害", "冤", "作恶", "欺负弱小"],
     "diag": "你为真实的不义而怒——这更接近『义怒』，是神自己也有的怒。关键是别让它变质成个人的报复。",
     "way": "义怒的出路不是私自报复，而是：为受害者代求、为公义行动、把最终的伸冤交给那位公义的审判者。"
            "『有火，但归给神的祭坛』——让怒推动你去爱、去护卫，而不是去毁灭。",
     "ref": "罗12:19", "text": "亲爱的弟兄，不要自己伸冤……主说：伸冤在我，我必报应。"},
    {"key": "atself", "name": "对自己生气 / 气自己没用、又搞砸",
     "kw": ["气自己", "对自己", "恨自己", "怎么又", "没用", "自责成怒", "跟自己过不去", "我怎么这样"],
     "diag": "你把怒转向了自己。适度的懊悔可以促人回转，但『对自己发怒到碾压』就滑向了自我定罪。",
     "way": "把对自己的怒，交给那位向软弱者柔和谦卑的基督。你不必用自我攻击来赎罪——基督已经赎了。"
            "承认、领受赦免、转身，然后温柔地待自己，像神温柔地待你一样。",
     "ref": "诗103:13-14", "text": "父亲怎样怜恤他的儿女，耶和华也怎样怜恤敬畏他的人，因为他知道我们的本体，思念我们不过是尘土。"},
    {"key": "process", "name": "想学习在神面前健康地处理愤怒",
     "kw": ["处理愤怒", "学习", "健康", "怎么办", "管理情绪", "对付怒", "不想再", "疏导"],
     "diag": "愿意学着处理怒，本身是成熟的记号。愤怒是可以被神炼净、甚至被祂使用的。",
     "way": "走四步：诚实命名 → 察看底下（伤/惧/被拦阻的偶像）→ 分辨『这是神的事还是我的国』→ 把伸冤交神，"
            "转向忍耐、饶恕或公义的行动。愤怒不必压抑，也不必爆发；它可以被带到神面前，炼成爱与勇气。",
     "ref": "弗4:26", "text": "生气却不要犯罪；不可含怒到日落。"},
]

VIOLENCE_WORDS = ["想打", "想揍", "弄死他", "报复他", "伤害他", "打死", "同归于尽", "让他好看", "动手"]


def _detect_violence(text: str) -> bool:
    return any(w in (text or "") for w in VIOLENCE_WORDS)


CRISIS_WORDS = ["自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死",
                "死了算了", "伤害自己", "撑不下去了", "没有意义活着", "想消失"]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = ("我听见你正承受很重的痛。如果你有伤害自己的念头，请现在就联系你信任的人或当地心理危机热线。"
               "你的怒也可以带到神面前——你不必独自扛。（本功能不替代专业帮助。）")
VIOLENCE_NOTE = ("我听见你的怒很强烈，甚至想伤害某人。这里要温柔而清楚地说：请先让自己离开会失控的处境，"
                 "在动手之前停下来。你的怒可以带到神面前处理，但绝不要让它变成伤害人的行动。"
                 "如果你觉得可能失控，请立刻联系你信任的人或专业帮助。")


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best, best_hits = None, 0
    for d in STATES:
        hits = sum(1 for k in d["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, d
    return best or STATES[5]


def meta() -> Dict[str, Any]:
    return {
        "title": "忿怒 · 在神面前处理愤怒",
        "source": "David Powlison《Good and Angry》；弗4:26；哀怨诗篇",
        "core": "愤怒是对所认为的错的回应；问题不在有没有怒，而在怒得对不对、如何处理。分辨义怒与私怒，带到神前而非压抑或爆发。",
        "four_steps": ["诚实命名", "察看底下（伤/惧/被拦阻的偶像）", "分辨这是神的事还是我的国", "把伸冤交给神，转向忍耐/饶恕/公义行动"],
        "states": [{"key": d["key"], "name": d["name"]} for d in STATES],
        "verse": "弗4:26",
        "principle": "「生气却不要犯罪；不可含怒到日落。」——愤怒可以被带到神面前炼净，成为爱与勇气。",
    }


def analyze(text: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    text = (text or "").strip()
    crisis = _detect_crisis(text)
    violence = _detect_violence(text)
    picked = _pick(text)
    result: Dict[str, Any] = {
        "crisis": crisis, "crisis_note": CRISIS_NOTE if crisis else "",
        "violence_flag": violence, "violence_note": VIOLENCE_NOTE if violence else "",
        "state": {"key": picked["key"], "name": picked["name"]},
        "diagnosis": picked["diag"],
        "way_forward": picked["way"],
        "four_steps": ["诚实命名", "察看底下", "分辨这是神的事还是我的国", "把伸冤交给神，转向忍耐/饶恕/公义"],
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "prayer": ("主啊，你知道我心里的怒有多真。我不把它藏起来，也不愿让它伤人——我把它带到你面前。"
                   "求你帮我看清：这怒底下是什么？是受了伤、是怕、还是我想作神来审判？教我分辨哪些是为你的义，"
                   "哪些只是为我的国。我把伸冤交给你，求你炼净我的怒，叫它化作忍耐、饶恕，或为公义而有的勇气。"),
        "practices": [
            "插一个停顿：怒上来时先离开现场，把生的怒对神说出来，等能自控了再回应人。",
            "察看底下：写下这次的怒底下藏着什么（哪个伤口、哪个被拦阻的期待），把它交给神。",
        ],
        "summary": ("愤怒不必压抑、也不必爆发。带它到神面前：诚实命名 → 察看底下 → 分辨是神的事还是我的国 → "
                    "把伸冤交给神。让怒被炼成爱与勇气，而非苦毒或伤害。"),
        "closing": "「快快地听，慢慢地说，慢慢地动怒。」（雅1:19）",
        "ai_used": False,
    }
    if violence:
        result["practices"] = [
            "先安全：立刻离开会失控的处境，在动手前停下来；必要时联系你信任的人或专业帮助。",
            "再处理：等平静后，把这股怒带到神面前，走四步慢慢梳理——但绝不让它变成伤害人的行动。",
        ]
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return ("你是一位温柔、以福音为中心的属灵陪伴者，熟悉 David Powlison《Good and Angry》。核心：愤怒是对所认为的错的"
            "回应，问题不在有没有怒而在如何处理(弗4:26 生气却不要犯罪)；分辨义怒(为真实不义、以神为中心)与私怒"
            "(受伤自尊/被拦阻欲望/想作神)；四步：诚实命名→察看底下→分辨是神的事还是我的国→把伸冤交神转向忍耐/饶恕/公义。"
            "若有伤人倾向先导向安全与自控。请针对用户处境温柔诊断，给经文、祷告与操练。中文，不压抑、不定罪。\n"
            f"用户处境：{text}\n"
            "请输出 JSON：{\"diagnosis\":\"...\",\"way_forward\":\"...\",\"prayer\":\"一段可照着祷告的话\",\"summary\":\"...\",\"closing\":\"一句经文\"}。")


def _ai_enhance(text, base, settings):
    raw = _call_ai(build_prompt(text, base), settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        return {k: str(data[k]) for k in ("diagnosis", "way_forward", "prayer", "summary", "closing") if data.get(k)} or None
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
    if result.get("crisis") or result.get("violence_flag"):
        return (["anger", "self_control", "grace"], False, True, 2.0)
    return (["anger", "self_control", "grace"], True, True, 4.5)
