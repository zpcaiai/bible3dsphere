"""
humility_engine.py — 谦卑（慕安得烈 Andrew Murray《谦卑》Humility）

virtues/tender_heart/fellowship 触及谦卑，但无专属。慕安得烈的核心：
**谦卑不是自我贬低，而是自我遗忘**——不再执着于自己（无论抬高还是踩低），
把目光从『我』移向神与他人。基督是谦卑的范本：祂虚己、取奴仆的形象、存心顺服（腓2）。
谦卑是「让神作神、让自己回到受造者的正位」，是一切恩典的根，也是接受更多恩典的器皿
（神阻挡骄傲的人，赐恩给谦卑的人，雅4:6）。

分辨：真谦卑 ≠ 自我贬低（那仍是聚焦自己）；真谦卑是从『我』里被释放出来，能安然地做仆人。
纯函数；确定性优先；内置危机词检测（自我贬低若滑向自我定罪，先托住恩典）；AI 仅作可选增强。
不定罪、不催人『更谦卑』（那会制造新的属灵表现），只把人从对自我的执着里领向神。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

STATES: List[Dict[str, Any]] = [
    {"key": "pride", "name": "骄傲 / 自以为是、爱表现",
     "kw": ["骄傲", "自以为是", "爱表现", "想被看见", "自大", "居功", "看不起", "争强", "显摆", "自负"],
     "diagnosis": "骄傲的核心是『把自己放中间』。慕安得烈说，解药不是打压自己，而是被神的伟大与恩典吸引到"
                  "祂的中心去——当神变大，我自然回到该在的位置。",
     "way": "谦卑不是想着『我要更卑微』，而是更少想到自己。今天刻意把一次『显出自己』的机会，换成"
            "『托举别人』——在暗中做一件不会被看见的好事，练习从舞台上下来。",
     "ref": "腓2:5-7", "text": "你们当以基督耶稣的心为心……反倒虚己，取了奴仆的形象。"},
    {"key": "selfdeprecate", "name": "老是贬低自己 / 觉得自己很差",
     "kw": ["贬低自己", "很差", "没用", "不如人", "自卑", "配不上", "我不行", "看轻自己", "低到尘埃"],
     "diagnosis": "这其实不是谦卑——自我贬低仍然是『盯着自己看』，只是从抬高换成了踩低。真谦卑是自我遗忘，"
                  "不是自我否定。",
     "way": "把目光从『我够不够好』移开，安息在『我是神所造、所爱、在基督里被悦纳的』这件事上。"
            "你不必贬低自己来讨神喜悦；你只需不再执着于自己（无论好坏），转向神与他人。",
     "ref": "诗139:14", "text": "我要称谢你，因我受造，奇妙可畏……",
     },
    {"key": "compare", "name": "总在跟人比较 / 在意排名高低",
     "kw": ["比较", "排名", "谁更", "赢过", "输给", "高低", "地位", "被超过", "攀比", "谁厉害"],
     "diagnosis": "比较是骄傲和自卑共同的温床——都要靠『我比别人如何』来定位自己。慕安得烈会说："
                  "从这场比赛里下来吧。",
     "way": "谦卑让你从与人比较的赛道上退场：你的价值不在排名里，而在神里。今天试着为一个『赢过你』的人"
            "真心祝福、甚至喝彩——这是从『我』里被释放的操练。",
     "ref": "加5:26", "text": "不要贪图虚名，彼此惹气，互相嫉妒。"},
    {"key": "serve", "name": "想学习像基督那样谦卑服事",
     "kw": ["服事", "谦卑", "像基督", "虚己", "作仆人", "低下来", "洗脚", "舍己", "顺服", "更谦卑"],
     "diagnosis": "愿意学谦卑，本身已是恩典。基督是范本：祂虚己、取奴仆形象、存心顺服至死——真谦卑能"
                  "安然地做仆人，不觉委屈。",
     "way": "效法基督『取奴仆的形象』：今天选一件低微的、无人称赞的服事去做，把它当作跟随那位为门徒"
            "洗脚之主的操练。谦卑不是想法，是弯下腰的动作。",
     "ref": "约13:14-15", "text": "我是你们的主，你们的夫子，尚且洗你们的脚，你们也当彼此洗脚……我给你们作了榜样。"},
]

SELF_CONDEMN = ["没救了", "该死", "配不上活", "我最差", "恨自己", "废物"]


def _detect_self_condemn(text: str) -> bool:
    return any(w in (text or "") for w in SELF_CONDEMN)


CRISIS_WORDS = ["自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死",
                "死了算了", "伤害自己", "撑不下去了", "没有意义活着", "想消失"]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = ("我听见你正承受很重的痛。如果你有伤害自己的念头，请现在就联系你信任的人或当地心理危机热线。"
               "在神眼中你受造奇妙可畏、是被爱的——你也值得有人此刻真实地陪着你。（本功能不替代专业帮助。）")


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    if _detect_self_condemn(t):
        return next(d for d in STATES if d["key"] == "selfdeprecate")
    best, best_hits = None, 0
    for d in STATES:
        hits = sum(1 for k in d["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, d
    return best or (STATES[3] if len(STATES) > 3 else STATES[0])


def meta() -> Dict[str, Any]:
    return {
        "title": "谦卑",
        "source": "Andrew Murray《谦卑》(Humility)",
        "core": "谦卑不是自我贬低，而是自我遗忘——从对自我的执着里被释放，让神作神、能安然作仆人；基督是范本(腓2)。",
        "states": [{"key": d["key"], "name": d["name"]} for d in STATES],
        "verse": "雅4:6",
        "principle": "「神阻挡骄傲的人，赐恩给谦卑的人。」——谦卑是接受更多恩典的器皿。",
    }


def analyze(text: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    text = (text or "").strip()
    crisis = _detect_crisis(text)
    picked = _pick(text)
    result: Dict[str, Any] = {
        "crisis": crisis, "crisis_note": CRISIS_NOTE if crisis else "",
        "state": {"key": picked["key"], "name": picked["name"]},
        "diagnosis": picked["diagnosis"],
        "way_forward": picked["way"],
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "key_distinction": "真谦卑 ≠ 自我贬低——后者仍在盯着自己看。谦卑是自我遗忘：更少想到自己，更多转向神与他人。",
        "prayer": ("主耶稣，你本有神的形像，却虚己、取了奴仆的形象，存心顺服。求你把这样的心赐给我。"
                   "叫我不再执着于自己——无论是抬高还是踩低；帮助我更少想到自己，把目光转向你和身边的人。"
                   "你阻挡骄傲的、赐恩给谦卑的；求你叫我谦卑下来，好承受你更多的恩典。"),
        "practices": [
            "一次暗中的服事：今天做一件不会被看见、不会被称赞的好事，练习从舞台上下来。",
            "为『赢过你的人』祝福：想一个让你羡慕/比下去的人，真心为他祝福一次——从比较里退场。",
        ],
        "summary": ("谦卑不是打压自己或自我贬低（那仍是盯着自己），而是自我遗忘：让神作神，"
                    "从对自我的执着里被释放出来，能安然地弯下腰服事。"),
        "closing": "「神阻挡骄傲的人，赐恩给谦卑的人。」（雅4:6）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return ("你是一位温柔、以福音为中心的属灵陪伴者，熟悉慕安得烈《谦卑》。核心：谦卑不是自我贬低，而是自我遗忘"
            "——从对自我的执着里被释放，让神作神、能安然作仆人；基督是范本(腓2虚己取奴仆形象)；真谦卑≠自我否定。"
            "请针对用户处境，温柔诊断(区分骄傲/自我贬低/比较)，给出路、经文、祷告与操练；若滑向自我定罪先托住恩典。"
            "中文，绝不催『你要更谦卑』式的重担。\n"
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
        return (["humility", "character", "grace"], False, True, 2.0)
    return (["humility", "character", "grace"], True, True, 4.0)
