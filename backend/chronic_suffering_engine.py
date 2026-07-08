"""
chronic_suffering_engine.py — 慢性 / 长期受苦 · 与疾病残疾同行
（Vaneetha Rendall Risner《The Scars That Have Shaped Me》；Joni Eareckson Tada）

suffering 引擎偏「急性/一次性」的诊断；本引擎补一个**完全缺失**的领域——**长期、慢性、
不会消失的苦**：慢性病、残疾、长期照护、看不到尽头的痛。这类苦最磨人的，不是一次剧痛，
而是日复一日、没有终点、且常无人真正理解。

要点：(1)不给廉价安慰（不说『会好的』『祷告就好了』）；(2)承认这是长途，不是短跑；
(3)「与刺同行」——保罗的刺没有挪去，神却说「我的恩典够你用」（林后12），恩典不是移除痛，
而是在痛中够用的同在与力量；(4)日复一日的小恩典（怜悯每早晨都是新的，哀3:22-23）；
(5)盼望：这苦不是永远的，复活的身体正在路上（可温柔连到『复活盼望』）。

纯函数；确定性；内置危机词检测（慢性痛↔绝望/求死相邻，格外谨慎，导向真人/专业帮助）；AI 可选增强。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

STATES: List[Dict[str, Any]] = [
    {"key": "endless", "name": "看不到尽头 / 日复一日、太久了",
     "kw": ["看不到尽头", "太久", "日复一日", "没有终点", "一直这样", "熬不到头", "多少年", "遥遥无期", "没完没了"],
     "diag": "长期受苦最磨人的，不是一次剧痛，而是『没有尽头』。你不是矫情——这是一条真实又漫长的路。",
     "way": "神的怜悯是『每早晨都是新的』（哀3:23）——不是一次给足够走完全程的力，而是每一天给够那一天的。"
            "别逼自己一次扛完整条路，只求今天够用的恩典、走好今天这一步。一天，一次呼吸，一份新的怜悯。",
     "ref": "哀3:22-23", "text": "我们不致消灭，是出于耶和华诸般的慈爱；是因他的怜悯不致断绝。每早晨，这都是新的。"},
    {"key": "thorn", "name": "求了很多次医治却没有挪去 / 与刺同行",
     "kw": ["没有医治", "求医治", "没挪去", "刺", "还是这样", "祷告没好", "神没医", "带着病", "没得医治"],
     "diag": "你求过神挪去这刺，它却还在。保罗也三次求主叫刺离开他，主的回答不是移除，而是『我的恩典够你用』。",
     "way": "神有时不挪去刺，却给出够用的恩典——在软弱里显得完全的能力。这不是祂不爱你，"
            "也不是你信心不够；这是另一种更深的同在：祂选择在你的软弱里，把祂的力量显给你和世界看。"
            "你可以继续求医治，同时也支取这份『够用的恩典』走过今天。",
     "ref": "林后12:9", "text": "我的恩典够你用的，因为我的能力是在人的软弱上显得完全。"},
    {"key": "misunderstood", "name": "没有人真正理解 / 孤单地扛",
     "kw": ["没人理解", "孤单", "没人懂这种", "别人以为", "装作没事", "被误解", "解释不清", "独自扛", "隐形的病"],
     "diag": "长期的苦常是『隐形』的——别人看不见，久了也不再问。这份不被理解的孤单，是慢性受苦里额外的重担。",
     "way": "有一位完全明白的——那位道成肉身、亲身受过苦的主，祂懂你说不出口的痛（来4:15）。"
            "在人的不理解里，先被祂的理解托住。也求神给你一两个『长期陪跑』的人（哪怕只有一个）；"
            "你不必让所有人懂，只需有一两个能与你同在的。",
     "ref": "赛53:3-4", "text": "他被藐视，被人厌弃，多受痛苦，常经忧患……他诚然担当我们的忧患，背负我们的痛苦。"},
    {"key": "caregiver", "name": "长期照顾病人/家人 / 照护者的疲惫",
     "kw": ["照顾", "照护", "长期护理", "陪护", "家人生病", "累", "喘不过气", "看护", "照顾病人", "撑着照顾"],
     "diag": "长期照护是一种少有人看见的受苦——你把自己耗在爱里，却常无人照顾你。这份疲惫是真实的、被神看见的。",
     "way": "照护者也需要被照护。允许自己接受帮助、划出喘息的界限，别把自己耗到枯竭（你空了就无法再爱）。"
            "把你所爱的病人交托给那位真正托住他的神——你尽你的一份忠心，其余交给祂。神也顾念你，"
            "祂看见你在暗处的每一次搀扶。",
     "ref": "赛40:11", "text": "他必像牧人牧养自己的羊群……轻轻引导那乳养小羊的。"},
    {"key": "meaning", "name": "想在长期的苦里找到意义/盼望",
     "kw": ["意义", "盼望", "为什么", "有价值吗", "白受苦", "撑下去", "怎么活", "长期病里", "找到盼望"],
     "diag": "在漫长的苦里问『这有意义吗』，是人性的呼求。圣经不给廉价的答案，却给一个确据：这苦不是永远的、也不是白白的。",
     "way": "两个锚：① 这苦是暂时的——复活的身体正在路上，那日再没有疼痛（可到『复活盼望』页）；"
            "② 这苦不是白白的——神能叫它结出你此刻还看不见的果子，也在其中把你炼得更像基督。"
            "你不必现在就看懂全部意义，只需信托住你的那双手，并盼望那必来的更新。",
     "ref": "林后4:16-17", "text": "外体虽然毁坏，内心却一天新似一天……这至暂至轻的苦楚，要为我们成就极重无比、永远的荣耀。"},
]

CRISIS_WORDS = ["自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死",
                "死了算了", "伤害自己", "撑不下去了", "没有意义活着", "想消失", "求解脱", "不想拖累", "求死"]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = ("我听见你已经痛了很久、累到很深的地方了。如果你有伤害自己或求解脱的念头，请现在就联系你信任的人"
               "或当地心理危机热线——长期的痛会让人想放弃，但你的生命是宝贵的，你不该独自扛，也值得有人此刻真实地陪着你。"
               "（本功能不替代专业帮助。）")


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best, best_hits = None, 0
    for d in STATES:
        hits = sum(1 for k in d["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, d
    return best or STATES[0]


def meta() -> Dict[str, Any]:
    return {
        "title": "慢性 / 长期受苦 · 与疾病残疾同行",
        "source": "Vaneetha Risner《The Scars That Have Shaped Me》；Joni Eareckson Tada",
        "core": "长期的苦是长途非短跑；不给廉价安慰。与刺同行——恩典不是移除痛，而是在痛中够用的同在；怜悯每早晨都是新的；盼望复活。",
        "states": [{"key": d["key"], "name": d["name"]} for d in STATES],
        "verse": "林后12:9",
        "principle": "神有时不挪去刺，却给出够用的恩典——在软弱里显得完全的能力。一天，一份新的怜悯。",
    }


def analyze(text: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    text = (text or "").strip()
    crisis = _detect_crisis(text)
    picked = _pick(text)
    result: Dict[str, Any] = {
        "crisis": crisis, "crisis_note": CRISIS_NOTE if crisis else "",
        "state": {"key": picked["key"], "name": picked["name"]},
        "diagnosis": picked["diag"],
        "way_forward": picked["way"],
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "hope_link": "这苦不是永远的——复活的身体正在路上；累的时候，可到『复活盼望』页举目望那日。",
        "prayer": ("主啊，这条路太长了，我看不到尽头，也常常没有人真正懂。谢谢你没有责备我的疲惫。"
                   "我求过你挪去这刺，你却对我说『我的恩典够你用』——那么，今天求你给我够用的恩典，够走今天这一步就好。"
                   "你的怜悯每早晨都是新的；求你新的怜悯此刻临到我。也求你差人来陪我这一段，并叫我举目望见那必来的更新——"
                   "那日，再没有疼痛与眼泪。"),
        "practices": [
            "只求今天够用的：不逼自己扛完整条路，只为『今天这一步的恩典』祷告，一天一次。",
            "找一个长期陪跑的人：向一位可信的人说出你真实的处境，不必让所有人懂，只需一两个能同在。",
        ],
        "summary": ("长期的苦是长途，不是短跑，也常无人理解。神有时不挪去刺，却给够用的恩典——一天一份新的怜悯。"
                    "你不必现在看懂全部意义，只需支取今天够用的同在，并盼望那必来的复活与更新。"),
        "closing": "「他的怜悯不致断绝，每早晨这都是新的。」（哀3:22-23）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return ("你是一位温柔、以福音为中心、有安宁疗护般敏感度的属灵陪伴者，熟悉 Vaneetha Risner 与 Joni Tada 关于慢性/"
            "长期受苦的见证。核心：长期的苦是长途非短跑；绝不给廉价安慰(不说『会好的/祷告就好』)；与刺同行——恩典不是"
            "移除痛而是在痛中够用的同在(林后12:9)；怜悯每早晨都是新的(哀3:23)；盼望复活。慢性痛与绝望相邻，格外温柔，"
            "有求死念头导向专业帮助。请针对用户处境温柔陪伴，给经文、祷告与操练。中文，绝不轻看其痛。\n"
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
        return (["endurance", "grace", "hope"], False, True, 2.0)
    return (["endurance", "grace", "hope"], True, True, 4.5)
