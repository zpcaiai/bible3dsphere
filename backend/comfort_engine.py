"""
comfort_engine.py — 安慰的服事 · 与哀哭的人同哭（林后1:3-4；卢云《负伤的治疗者》；罗12:15）

系统的 care/suffering 是「受安慰」侧；本引擎补「施安慰」侧——**如何陪伴一个正在受苦的人**。
这也是把系统再次「向外转」：从被牧养，到牧养别人。

林后1:3-4：神是「发慈悲的父，赐各样安慰的神」；祂安慰我们，「叫我们能用……所得的安慰去安慰
那遭各样患难的人」。卢云：真正的安慰者是「负伤的治疗者」——不是站在高处给答案，而是带着自己的
软弱进到对方的痛里。

要点（对治好心却帮倒忙的常见错误）：**同在胜过话语**；先聆听不急着修理；不说「我懂」「都会好的」
「这是神的美意」等轻慢的话；与哀哭的人同哭（罗12:15）；把人指向神，而非替神发言。

纯函数；确定性；内置危机词检测（若陪伴对象在危机中，导向专业帮助）；AI 可选增强。
装备用户去安慰人，不制造「你必须救对方」的重担。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

STATES: List[Dict[str, Any]] = [
    {"key": "dontknow", "name": "不知道说什么 / 怕说错话",
     "kw": ["不知道说什么", "怕说错", "不会安慰", "说什么好", "词穷", "不知怎么", "怕帮倒忙", "开不了口"],
     "diag": "你怕说错话——这份小心是好的。好消息是：安慰最需要的不是『对的话』，而是『在场』。",
     "way": "同在胜过话语。你不必有答案，只要在。可以说少一点：『我在这里』『我很难过你经历这些』"
            "『我不走开』。避免『我懂』『都会好的』这类会显得轻慢的话。有时最好的安慰，是安静地陪坐、递一杯水。",
     "ref": "伯2:13", "text": "他们就同他七天七夜坐在地上，一个人也不向他说句话，因为他们见他极其痛苦。"},
    {"key": "fix", "name": "忍不住想给建议/讲道理 / 想赶紧解决",
     "kw": ["给建议", "讲道理", "解决", "想帮他", "出主意", "分析", "教他", "让他想开", "赶紧好"],
     "diag": "你的关心让你想赶紧『修好』对方的痛——但受苦的人此刻多半不需要方案，需要被听见。急着修理，反而让人更孤单。",
     "way": "先聆听，把『修理』的冲动按下。多问、少答：『能多说说吗？』『那一定很难吧。』"
            "让对方把话说完，别急着接『你应该……』。等他真的觉得被听见了，若他要，才轻轻分享一点。同在先于建议。",
     "ref": "雅1:19", "text": "你们各人要快快地听，慢慢地说。"},
    {"key": "grief", "name": "陪伴丧亲/重大失去的人",
     "kw": ["丧亲", "去世", "失去", "离世", "白发人", "哀伤", "过世", "重大失去", "亲人走了"],
     "diag": "陪伴哀伤的人，最忌『把哀伤讲道理讲掉』。哀伤需要被见证，不需要被解释。",
     "way": "与哀哭的人同哭（罗12:15）——允许他哀伤，不催他『快点好』。不说『他去了更好的地方』『别哭了』。"
            "记住具体的日子（忌日、生日），在那些日子多陪一句。长期的陪伴，胜过一次性的金句。你的『在』本身就是安慰。",
     "ref": "罗12:15", "text": "与喜乐的人要同乐；与哀哭的人要同哭。"},
    {"key": "spiritualize", "name": "怕自己太属灵化 / 想恰当地指向神",
     "kw": ["太属灵", "指向神", "怎么说神", "引用经文", "属灵化", "神的美意", "恰当", "该不该讲道理"],
     "diag": "想把人指向神是对的，但时机与方式很重要。过早地『这是神的美意』会像约伯的朋友，帮倒忙。",
     "way": "先陪伴、后指引；先赢得信任、再轻轻分享盼望。少替神发言（别急着解释『为什么』），多把神的同在带进来："
            "为他祷告、与他一起把痛端到神面前。指向神最有力的方式，往往不是你的话，而是你如基督般的『在场』。",
     "ref": "林后1:4", "text": "我们在一切患难中，他就安慰我们，叫我们能用……所得的安慰去安慰那遭各样患难的人。"},
    {"key": "drained", "name": "陪伴到自己也很累 / 被消耗",
     "kw": ["自己也累", "被消耗", "撑不住", "太沉重", "扛不动", "陪到累", "负能量", "情绪被拖", "耗"],
     "diag": "陪伴受苦的人会消耗你——这是真的。你是『负伤的治疗者』，不是无限的容器；你也需要被喂养、被界限保护。",
     "way": "记住：你是陪伴者，不是救主。你不必也不能背起对方全部的痛。设立健康的界限，也让自己被神与他人喂养。"
            "把对方交托给那位真正的安慰者，你只需忠心地『在』，其余交给神。",
     "ref": "加6:2,5", "text": "你们各人的重担要互相担当……因为各人必担当自己的担子。"},
]

CRISIS_WORDS = ["自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死",
                "死了算了", "伤害自己", "撑不下去了", "没有意义活着", "想消失"]
OBJECT_CRISIS = ["他想自杀", "她想自杀", "想不开", "要轻生", "想自杀", "要自杀", "他想死", "她想死"]


def _detect_crisis(text: str) -> bool:
    t = (text or "")
    return any(w in t for w in CRISIS_WORDS) or any(w in t for w in OBJECT_CRISIS)


CRISIS_NOTE = ("听起来你想陪伴的人（或你自己）可能正处在危机里。如果有人有伤害自己的念头，陪伴很重要，"
               "但请务必同时帮他联系专业帮助或当地心理危机热线——有些重担需要专业与真人一起来托住，不该你一人独扛。"
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
        "title": "安慰的服事 · 与哀哭的人同哭",
        "source": "林后1:3-4；卢云《负伤的治疗者》；罗12:15",
        "core": "神安慰我们，叫我们能去安慰别人；真安慰是『负伤的治疗者』——同在胜过话语，聆听先于修理，与哀哭者同哭。",
        "avoid": ["急着给建议/修理", "说『我懂』『都会好的』『这是神的美意』", "替神发言解释『为什么』", "催对方快点好起来"],
        "states": [{"key": d["key"], "name": d["name"]} for d in STATES],
        "verse": "林后1:4",
        "principle": "「与哀哭的人要同哭。」——你不必有答案，只要真实地在。",
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
        "avoid": ["急着给建议/修理", "说『我懂』『都会好的』『这是神的美意』", "替神发言解释为什么", "催对方快点好"],
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "prayer": ("发慈悲的父，赐各样安慰的神——谢谢你曾这样安慰我。求你叫我能用从你所得的安慰，去安慰这位正在受苦的人。"
                   "给我一颗肯聆听、不急着修理的心；帮我住口不说轻慢的话，只是真实地在。教我像负伤的治疗者，"
                   "带着自己的软弱进到他的痛里，把他轻轻指向你——真正的安慰者。求你亲自安慰他，也保守我有界限、不独扛。"),
        "practices": [
            "同在先于话语：下次陪伴时，先只做三件事——到场、聆听、说『我在这里，我不走开』。",
            "记住具体：记下对方的难处/重要日子，在那天多发一条问候——长期的『在』胜过一次性的金句。",
        ],
        "summary": ("安慰的服事是『负伤的治疗者』：同在胜过话语，聆听先于修理，与哀哭的人同哭。"
                    "别急着给答案或属灵化，先真实地在；把人轻轻指向神，其余交给那位真正的安慰者。"),
        "closing": "「与哀哭的人要同哭。」（罗12:15）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return ("你是一位温柔、以福音为中心的属灵陪伴者，装备用户去安慰受苦的人，熟悉林后1:3-4 与卢云《负伤的治疗者》。"
            "核心：神安慰我们叫我们去安慰人；同在胜过话语、聆听先于修理、与哀哭者同哭(罗12:15)；避免急着给建议、"
            "说『我懂/都会好的/这是神的美意』、替神发言、催对方快好。若陪伴对象在危机中，导向专业帮助。"
            "请针对用户处境给具体的陪伴之道、经文、祷告与操练；不制造『你必须救对方』的重担。中文。\n"
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
        return (["comfort", "love", "presence"], False, True, 2.0)
    return (["comfort", "love", "presence"], True, True, 4.5)
