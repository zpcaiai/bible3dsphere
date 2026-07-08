"""
generosity_engine.py — 慷慨 / 管家 / 金钱的救赎（Randy Alcorn《财宝在天》The Treasure Principle）

idolatry/contentment 处理金钱的**偶像面**（贪爱、掌控、不安）；本引擎补**建设性**的一面：
把钱财从「主人」降回「工具」，藉着给予得自由，把财宝积在天上。

Alcorn 的「财宝原则」：**你不能把财富带到天上，但可以提前把它送到天上去。**
要点：(1)我不是拥有者，是**管家**——一切都是神的，我只是受托管理；(2)给予不是失去，是**投资于永恒**；
(3)心与财宝同在（太6:21）——想改变心的方向，就改变财宝的方向；(4)给予是脱离玛门辖制、得自由的操练。

纯函数；确定性优先；内置危机词检测；AI 仅作可选增强。不制造愧疚式奉献、不谈具体金额，
只把人从「金钱的辖制」领向「管家的自由与永恒的投资」。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

STATES: List[Dict[str, Any]] = [
    {"key": "grip", "name": "钱抓得很紧 / 不安、总怕不够",
     "kw": ["抓紧", "舍不得", "怕不够", "不安", "囤", "紧张", "存钱焦虑", "怕穷", "放不下钱", "缺乏感"],
     "truth": "越攥紧越不安，因为把安全感放在了会朽坏的东西上。给予恰恰是松开手的操练——它宣告"
             "『我的安全在神，不在存款』。奇妙的是，松开的手，比攥紧的手更自由、更满足。",
     "ref": "太6:21", "text": "因为你的财宝在哪里，你的心也在那里。"},
    {"key": "owner", "name": "把钱当成自己的 / 我的努力我的钱",
     "kw": ["我的钱", "我挣的", "凭什么给", "我的努力", "自己赚", "拥有", "支配", "我说了算", "血汗钱"],
     "truth": "财宝原则的起点：你不是拥有者，是管家。一切（连你赚钱的能力）都是神给的，你只是受托管理一段时间。"
             "这不减损你，反而释放你——当它是神的，你就不必替它焦虑，只需忠心地管好、慷慨地用好。",
     "ref": "代上29:14", "text": "我算什么，我的民算什么……因为万物都从你而来，我们把从你而得的献给你。"},
    {"key": "hoard", "name": "只为今生积攒 / 想更会花钱、更有意义地用钱",
     "kw": ["积攒", "为今生", "怎么花", "有意义", "投资", "理财", "花在哪", "值不值", "用钱", "更会用"],
     "truth": "你不能把财富带到天上，但可以提前把它送到天上去——藉着给予，投资于永恒。今生的积攒会留下，"
             "但为神国的给予会存到永远。问的不再是『怎么积得更多』，而是『怎么把一部分投到不会朽坏的地方』。",
     "ref": "太6:20", "text": "只要积攒财宝在天上……因为你的财宝在哪里，你的心也在那里。"},
    {"key": "free", "name": "想脱离金钱的辖制 / 想学慷慨",
     "kw": ["辖制", "慷慨", "施予", "自由", "学给予", "奉献", "松手", "脱离玛门", "乐捐", "给出去"],
     "truth": "慷慨是脱离玛门辖制、得自由的操练。给予不是失去，是把心从『地上的库房』搬向『天上的库房』；"
             "而且神爱乐意给的人，给予里有一种攥紧永远尝不到的喜乐。从一次具体、乐意的给予开始。",
     "ref": "林后9:7", "text": "各人要随本心所酌定的，不要作难，不要勉强，因为捐得乐意的人是神所喜爱的。"},
    {"key": "trust", "name": "想给却怕自己不够用 / 信心与钱财",
     "kw": ["怕不够用", "想给又怕", "先顾自己", "没安全感给", "信心不足", "怕吃亏", "给了怎么办", "供应"],
     "truth": "给予是信心的操练：它把『我的供应者是神，不是我的余额』这句话活出来。神不是要榨干你，"
             "而是要你在给予里经历祂的看顾——祂能叫你在凡事上常常充足，能多行各样善事。先小小地、凭信心迈一步。",
     "ref": "林后9:8", "text": "神能将各样的恩惠多多地加给你们，使你们凡事常常充足，能多行各样善事。"},
]

CRISIS_WORDS = ["自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死",
                "死了算了", "伤害自己", "撑不下去了", "没有意义活着", "想消失"]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = ("我听见你正承受很重的痛。如果你有伤害自己的念头，请现在就联系你信任的人或当地心理危机热线。"
               "你的价值远超任何账户数字——你也值得有人此刻真实地陪着你。（本功能不替代专业帮助。）")


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best, best_hits = None, 0
    for d in STATES:
        hits = sum(1 for k in d["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, d
    return best or (STATES[3] if len(STATES) > 3 else STATES[0])


def meta() -> Dict[str, Any]:
    return {
        "title": "慷慨 · 管家 · 财宝在天",
        "source": "Randy Alcorn《财宝在天》(The Treasure Principle)",
        "core": "你不能把财富带到天上，但可以提前把它送到天上去；你不是拥有者而是管家，给予是脱离玛门、投资永恒、得自由的操练。",
        "states": [{"key": d["key"], "name": d["name"]} for d in STATES],
        "verse": "太6:21",
        "principle": "「你的财宝在哪里，你的心也在那里。」——想改变心的方向，就改变财宝的方向。",
        "note": "本模块不谈具体金额、不制造愧疚式奉献，只帮助把金钱从『主人』降回『工具』。",
    }


def analyze(text: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    text = (text or "").strip()
    crisis = _detect_crisis(text)
    picked = _pick(text)
    result: Dict[str, Any] = {
        "crisis": crisis, "crisis_note": CRISIS_NOTE if crisis else "",
        "state": {"key": picked["key"], "name": picked["name"]},
        "truth": picked["truth"],
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "steward_reminder": "起点是身份的转换：你不是拥有者，是管家——一切都是神的，你受托管理一段时间。",
        "prayer": ("主啊，我承认我常常把钱财当成主人，替它焦虑、被它抓住。谢谢你提醒我：我不是拥有者，是管家；"
                   "万物都从你而来。求你松开我攥紧的手，叫我在给予里经历自由与你的看顾。"
                   "帮助我把财宝、也把心，一点点地投向你的国——因为财宝在哪里，我的心也在那里。"),
        "practices": [
            "一次乐意的给予：本周凭信心、乐意地给出一笔（不必大），作为『松手』与『投资永恒』的操练。",
            "换个问题：把『我怎么积得更多』换成『我能把一部分投到哪个不会朽坏的地方』，想一个具体去处。",
        ],
        "summary": ("金钱不必是主人，可以只是工具。你是管家不是拥有者；给予不是失去，是脱离辖制、"
                    "投资永恒的操练——因为财宝在哪里，心也在那里。"),
        "closing": "「施比受更为有福。」（徒20:35）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return ("你是一位温柔、以福音为中心的属灵陪伴者，熟悉 Randy Alcorn《财宝在天》。核心：你不能把财富带到天上，"
            "但可提前送去；你是管家非拥有者；给予是脱离玛门、投资永恒、得自由的操练(太6:21)。请针对用户与金钱的处境，"
            "温柔地把管家身份与财宝原则说给他，给经文、祷告与一个操练。不谈具体金额、绝不制造愧疚式奉献。中文，温暖不说教。\n"
            f"用户处境：{text}\n"
            "请输出 JSON：{\"truth\":\"...\",\"prayer\":\"一段可照着祷告的话\",\"summary\":\"...\",\"closing\":\"一句经文\"}。")


def _ai_enhance(text, base, settings):
    raw = _call_ai(build_prompt(text, base), settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        return {k: str(data[k]) for k in ("truth", "prayer", "summary", "closing") if data.get(k)} or None
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
        return (["generosity", "stewardship", "freedom"], False, True, 2.0)
    return (["generosity", "stewardship", "freedom"], True, True, 4.0)
