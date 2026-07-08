"""
conscience_engine.py — 良心（Naselli & Crowley《Conscience》；罗14；提前1:5）

散见 5 引擎却无专属。良心是神放在人里面、就着「对错」发出的内在见证。它不是绝对可靠的
（可被亏损、可被过度捆绑、也可被烙惯麻木），需要**按圣经不断校准**。

三种失调：
  · **弱的良心**（罗14）：为圣经未禁止的事定罪自己（过度敏感、被规条捆绑）；
  · **迟钝/麻木的良心**（提前4:2 被热铁烙惯）：对真罪失去知觉；
  · **被亏损/污秽的良心**（多1:15）：带着未处理的罪，良心持续控告。
目标：**清洁/无亏的良心**（提前1:5 爱是从清洁的心、无亏的良心生出来的）——藉认罪领受赦免而洁净，
藉圣经校准而准确；也学习尊重别人不同强弱的良心（罗14 不论断、不绊倒）。

纯函数；确定性；内置危机词检测 + 强迫性内疚（弱/被捆绑的良心滑向自我定罪时先托住恩典）；AI 可选增强。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

STATES: List[Dict[str, Any]] = [
    {"key": "weak", "name": "为圣经没禁止的事一直定罪自己 / 良心过度敏感",
     "kw": ["定罪自己", "过度敏感", "一点小事就内疚", "是不是罪", "良心不安", "太多规条", "总觉得有罪", "怕犯罪", "钻牛角尖"],
     "diag": "你的良心可能偏『弱/过度敏感』——为圣经并未禁止的事持续定罪自己（罗14 讲这种情形）。敏感是好的，但被捆绑不是神的心意。",
     "way": "用圣经校准良心：分辨『这真是神所禁止的，还是我加上去的规条/别人的标准？』良心要顺服圣经，"
            "不顺服模糊的内疚感。同时对自己温柔——神要你有的是『无亏的良心』，不是『永不安宁的良心』。"
            "对确实是罪的，认罪领受赦免；对并非罪的，学着在自由里安心。",
     "ref": "罗14:5", "text": "只是各人心里要意见坚定……",
     },
    {"key": "dull", "name": "对某些罪越来越无所谓 / 良心麻木了",
     "kw": ["无所谓", "麻木", "不当回事", "习惯了", "良心麻木", "不觉得有错", "钝了", "没感觉", "合理化"],
     "diag": "你对某些罪渐渐『没感觉』了——这可能是良心被『烙惯』而迟钝（提前4:2）。合理化久了，警报会失灵。",
     "way": "求圣灵重新敏化你的良心，也用圣经的光照它（而非用自己的钝感当标准）。别让『大家都这样』"
            "或『我已经习惯了』替神发言。回到圣经问：神怎么看这件事？在小事上重新学习顺从良心的提醒，"
            "免得它越来越钝。",
     "ref": "提前4:2", "text": "……良心如同被热铁烙惯了一般。",
     },
    {"key": "guilty", "name": "带着未处理的罪 / 良心一直控告我",
     "kw": ["未处理", "控告", "过不去", "一直内疚", "藏着罪", "良心谴责", "睡不安", "亏欠", "洗不掉"],
     "diag": "你的良心在持续控告——若底下是一件真实、未处理的罪，良心是对的，它在催你去解决，而非碾压你。",
     "way": "别再压着或绕开：把那件具体的罪拿到神面前认了（约壹1:9），必要时向人认罪、赔偿、修复。"
            "基督的血能洁净被亏损的良心（来9:14）。认了、领受了赦免、做了该做的修复，就让良心随神的赦免一同安息，"
            "不要在神已赦免之处继续自我定罪。",
     "ref": "来9:14", "text": "何况基督……用永远的灵，将自己无瑕无疵献给神，他的血岂不更能洗净你们的心，除去你们的死行？"},
    {"key": "others", "name": "为『可不可以做某事』与人有分歧 / 论断或被论断",
     "kw": ["可不可以", "分歧", "论断", "看不惯别人", "被别人说", "灰色地带", "自由", "绊倒", "别人的标准", "该不该"],
     "diag": "你在为『圣经没有明说』的事与人有张力——罗14 正讲这个：信心/良心有强有弱，不可彼此论断、也不可绊倒人。",
     "way": "两条原则：① 强的不轻看弱的、弱的不论断强的——各人在自己的良心里向主负责；② 有爱心地行，"
            "不为自己的自由绊倒良心软弱的弟兄。你的良心是给你自己的准绳，不是审判别人的法官。",
     "ref": "罗14:12-13", "text": "这样看来，我们各人必要将自己的事在神面前说明。所以，我们不可再彼此论断。"},
    {"key": "calibrate", "name": "想让良心更准 / 学习清洁无亏的良心",
     "kw": ["校准", "更准", "清洁", "无亏", "调整良心", "更敏锐", "学习", "对齐圣经", "良心健康"],
     "diag": "愿意校准良心，是成熟的记号。目标是『清洁/无亏的良心』——准确（对齐圣经）又安宁（藉赦免而洁净）。",
     "way": "两件事一起做：① 校准准确度——持续用圣经调整良心，既不加规条、也不减真理；② 保守它无亏——"
            "随时认罪、领受赦免，不让罪积压。清洁的良心是爱的源头之一（提前1:5），也让你能坦然来到神面前。",
     "ref": "提前1:5", "text": "但命令的总归就是爱；这爱是从清洁的心和无亏的良心，无伪的信心生出来的。"},
]

SCRUPLE = ["我不可饶恕", "永远洗不掉", "神不会原谅", "我太脏", "没救了", "该下地狱"]


def _detect_scruple(text: str) -> bool:
    return any(w in (text or "") for w in SCRUPLE)


CRISIS_WORDS = ["自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死",
                "死了算了", "伤害自己", "撑不下去了", "没有意义活着", "想消失"]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = ("我听见你正承受很重的痛。如果你有伤害自己的念头，请现在就联系你信任的人或当地心理危机热线。"
               "基督的血能洁净被亏损的良心，神的赦免比你最深的罪更深——你也值得有人此刻真实地陪着你。（本功能不替代专业帮助。）")


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    if _detect_scruple(t):
        return next(d for d in STATES if d["key"] == "guilty")
    best, best_hits = None, 0
    for d in STATES:
        hits = sum(1 for k in d["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, d
    return best or (STATES[4] if len(STATES) > 4 else STATES[0])


def meta() -> Dict[str, Any]:
    return {
        "title": "良心",
        "source": "Naselli & Crowley《Conscience》；罗14；提前1:5",
        "core": "良心是神放在人里的对错见证，非绝对可靠，需按圣经校准；目标是清洁无亏的良心，并尊重别人强弱不同的良心。",
        "disorders": [
            {"name": "弱的良心", "note": "为圣经未禁止的事定罪自己（罗14）"},
            {"name": "迟钝的良心", "note": "对真罪失去知觉（提前4:2 被烙惯）"},
            {"name": "被亏损的良心", "note": "带着未处理的罪持续控告（多1:15）"},
        ],
        "states": [{"key": d["key"], "name": d["name"]} for d in STATES],
        "verse": "提前1:5",
        "principle": "良心要顺服圣经，不顺服模糊的内疚；藉认罪领受赦免而洁净，藉圣经校准而准确。",
    }


def analyze(text: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    text = (text or "").strip()
    crisis = _detect_crisis(text)
    scruple = _detect_scruple(text)
    picked = _pick(text)
    result: Dict[str, Any] = {
        "crisis": crisis, "crisis_note": CRISIS_NOTE if crisis else "",
        "scruple_flag": scruple,
        "state": {"key": picked["key"], "name": picked["name"]},
        "diagnosis": picked["diag"],
        "way_forward": picked["way"],
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "calibrate_note": "良心要顺服圣经、不顺服模糊的内疚：既不加规条(免得像弱的良心)、也不减真理(免得钝掉)；藉认罪领受赦免而洁净。",
        "prayer": ("主啊，谢谢你把良心放在我里面。但我知道它不是绝对可靠的——求你用你的话校准它：不叫我为你没有定罪的事"
                   "自我捆绑，也不叫我对真的罪渐渐麻木。若我带着未处理的罪，求你的血洁净我被亏损的良心；"
                   "叫我有一颗清洁、无亏、又准确的良心，能坦然来到你面前，也能有爱心地尊重别人不同的良心。"),
        "practices": [
            "对齐圣经：就眼下这件让你不安的事，问『这真是神所禁止的，还是我加的规条/别人的标准？』据圣经调整。",
            "洁净良心：若底下是真实的罪，今天就具体认罪、领受赦免、做该做的修复，然后让良心随神的赦免安息。",
        ],
        "summary": ("良心是神放在你里的见证，却非绝对可靠，要按圣经校准：不加规条、不减真理。"
                    "清洁无亏的良心，来自认罪领受赦免 + 持续对齐圣经；也要尊重别人强弱不同的良心。"),
        "closing": "「爱是从清洁的心和无亏的良心……生出来的。」（提前1:5）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return ("你是一位温柔、以福音为中心的属灵陪伴者，熟悉 Naselli & Crowley《Conscience》与罗14。核心：良心是神放在人里的"
            "对错见证、非绝对可靠、需按圣经校准；三种失调=弱(为未禁止事定罪自己)/迟钝(对真罪麻木)/被亏损(带罪控告)；"
            "目标是清洁无亏的良心(提前1:5)，并尊重别人强弱不同的良心(不论断、不绊倒)。若滑向强迫性自我定罪先托住恩典。"
            "请针对用户处境温柔诊断，给经文、祷告与操练。中文。\n"
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
    if result.get("crisis") or result.get("scruple_flag"):
        return (["conscience", "grace", "truth"], False, True, 2.0)
    return (["conscience", "grace", "truth"], True, True, 4.0)
