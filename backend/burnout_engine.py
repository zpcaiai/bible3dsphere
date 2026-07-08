"""
burnout_engine.py — 耗竭 / 服事倦怠（王上19 以利亚；安息神学）

rule_of_life 治「匆忙」，本引擎治「已经烧干」的耗竭——尤其服事者与照顾者。
以利亚刚打完大胜仗，却在罗腾树下求死；神的回应不是责备，而是：让他睡、给他吃、
温柔地问「你在这里做什么」、更新他的呼召、给他同伴（以利沙）。神医治耗竭的次序：
**先身体（睡与吃）→ 后心灵（倾听、遇见神的微声）→ 再使命（重派、给同伴）**。

分辨：耗竭不是不属灵，是身心灵的油烧干了；它常伴随愤世、麻木、想逃、觉得自己没用。
对治不是「更努力」，而是「先被喂养，再喂养」——领受安息、卸下弥赛亚情结（救主只有一位，不是你）。

纯函数；确定性；内置危机词检测（以利亚求死，耗竭↔绝望相邻，谨慎）；AI 可选增强。
不催「你要更委身」，只温柔地把烧干的人先领去被神喂养与安息。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

STATES: List[Dict[str, Any]] = [
    {"key": "empty", "name": "身心俱疲 / 油烧干了、什么都给不出",
     "kw": ["耗竭", "烧干", "给不出", "疲惫", "累垮", "透支", "油尽", "身心俱疲", "空了", "掏空"],
     "diag": "你不是不属灵，是油烧干了。以利亚打完大胜仗也曾累到求死——耗竭是真实的、身心灵的枯竭。",
     "way": "看神怎样待以利亚：祂没有责备，先让他睡、给他吃。你此刻最属灵的事，可能就是好好睡一觉、吃顿饭、"
            "停下来。先照顾身体，让神从最基本处开始修复你。先被喂养，才谈得上再喂养。",
     "ref": "王上19:5-7", "text": "他就躺在罗腾树下睡着了。有一个天使拍他，说：起来吃吧……因为你当走的路甚远。"},
    {"key": "numb", "name": "麻木愤世 / 对以前热爱的事再无感觉",
     "kw": ["麻木", "愤世", "无感", "冷掉", "没热情", "机械", "厌倦", "提不起劲", "行尸走肉", "心死"],
     "diag": "麻木与愤世，是耗竭的典型信号——不是你变坏了，是你烧得太久没有补给。心的火需要被重新点燃，而非被逼着烧。",
     "way": "神在何烈山问以利亚『你在这里做什么』，让他把苦水倒出来。你也需要一个地方，诚实说出你的疲惫与失望。"
            "别急着找回热情，先允许自己承认『我累了、我冷了』——被听见，是重新点火的开始。",
     "ref": "王上19:9-10", "text": "耶和华的话临到他说：以利亚啊，你在这里做什么？"},
    {"key": "caregiver", "name": "照顾别人到自己空了 / 弥赛亚情结",
     "kw": ["照顾", "付出", "别人依赖", "扛所有", "没人管我", "牺牲自己", "谁来管我", "撑着大家", "责任全在我"],
     "diag": "你一直在托住别人，直到自己空了。也许你不自觉地背上了『救主』的担子——但救主只有一位，不是你。",
     "way": "卸下弥赛亚情结：你被呼召去服事，不是去做别人的救主。神并不要你耗尽自己来证明爱。"
            "学会接受别人的服事、划出界限、把人交回给那位真正托住他们的神。你也需要被喂养，这不是自私，是必需。",
     "ref": "太11:28-30", "text": "凡劳苦担重担的人，可以到我这里来，我就使你们得安息……因为我的轭是容易的，我的担子是轻省的。"},
    {"key": "quit", "name": "想逃 / 想放弃服事、撂挑子",
     "kw": ["想逃", "想放弃", "撂挑子", "不想干了", "退出", "逃避", "坚持不下去", "想消失一阵", "不想服事"],
     "diag": "想逃，未必是没有信心，常常只是烧干了的身体在喊停。以利亚也逃到了旷野——神没有骂他懦弱。",
     "way": "在做重大决定（如彻底退出）之前，先让自己被喂养、被安息、被恢复——不要在耗竭中改弦更张。"
            "神对以利亚的更新里，也重新指派了使命、并给了同伴（以利沙）。也许你需要的不是『放弃』，"
            "而是『重整节奏 + 找到同伴 + 被恢复』。先歇够，再决定。",
     "ref": "王上19:15-16", "text": "耶和华对他说：你回去……你要膏……以利沙作先知接续你。"},
    {"key": "restore", "name": "想被恢复 / 学习可持续地服事",
     "kw": ["恢复", "可持续", "重新得力", "补给", "重整", "长久服事", "被更新", "回血", "重新出发"],
     "diag": "愿意学可持续地服事，是智慧。神对以利亚的医治是有次序的：先身体，后心灵，再使命。",
     "way": "照这次序恢复自己：① 身体——睡够、吃好、停下来；② 心灵——把疲惫倒给神，安静听祂的微声；"
            "③ 使命——重整节奏、找到同伴、重新领受呼召。服事的力量之源是神，不是你的意志；先回到源头补给。",
     "ref": "赛40:31", "text": "但那等候耶和华的必从新得力……行走却不困倦。"},
]

CRISIS_WORDS = ["自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死",
                "死了算了", "伤害自己", "撑不下去了", "没有意义活着", "想消失", "求死"]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = ("我听见你已经累到很深、甚至撑不住的地方了。如果你有伤害自己或求死的念头，请现在就联系你信任的人"
               "或当地心理危机热线。像以利亚一样，此刻你最需要的也许是先被好好照顾——你不必独自硬撑。"
               "（本功能不替代专业帮助。）")


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best, best_hits = None, 0
    for d in STATES:
        hits = sum(1 for k in d["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, d
    return best or (STATES[4] if len(STATES) > 4 else STATES[0])


def meta() -> Dict[str, Any]:
    return {
        "title": "耗竭 · 服事倦怠",
        "source": "王上19 以利亚；安息神学",
        "core": "耗竭是身心灵的油烧干，不是不属灵；神医治的次序是先身体(睡与吃)→后心灵(倾听微声)→再使命(重派+同伴)。",
        "order": ["身体：睡够、吃好、停下来", "心灵：把疲惫倒给神、听祂微声", "使命：重整节奏、找到同伴、重领呼召"],
        "states": [{"key": d["key"], "name": d["name"]} for d in STATES],
        "verse": "太11:28",
        "principle": "对治耗竭不是『更努力』，而是『先被喂养，再喂养』——卸下弥赛亚情结，救主只有一位。",
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
        "restore_order": ["身体：睡够、吃好、停下来", "心灵：把疲惫倒给神、听祂的微声", "使命：重整节奏、找到同伴、重领呼召"],
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "prayer": ("主啊，我烧干了。谢谢你没有责备以利亚，而是先让他睡、给他吃——求你也这样温柔地待我。"
                   "帮助我卸下那个『我必须撑住一切』的重担——我不是救主，你才是。教我先回到你这里被喂养、被安息，"
                   "再谈服事；求你从新得力给我，让我学会可持续地爱、可持续地服事，力量从你而来，不从我的意志。"),
        "practices": [
            "先顾身体：这两天刻意补一次觉、好好吃一顿、停一件可以停的事——把这当作属灵的操练。",
            "卸下救主担子：写下一件你一直硬扛、其实可以交托或交给别人的事，把它交回给神。",
        ],
        "summary": ("耗竭不是不属灵，是油烧干了。照神医治以利亚的次序恢复：先身体、后心灵、再使命。"
                    "先被喂养，再喂养；卸下弥赛亚情结——救主只有一位，不是你。"),
        "closing": "「那等候耶和华的必从新得力。」（赛40:31）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return ("你是一位温柔、以福音为中心的属灵陪伴者，熟悉王上19 以利亚的耗竭与安息神学。核心：耗竭是身心灵油烧干、"
            "非不属灵；神医治次序=先身体(睡与吃)→后心灵(倾听微声)→再使命(重派+同伴)；对治不是更努力而是先被喂养再喂养，"
            "卸下弥赛亚情结(救主只有一位)。若有求死/自伤念头先导向真人帮助。请针对用户处境温柔诊断，给经文、祷告与操练；"
            "绝不催『你要更委身』。中文。\n"
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
        return (["rest", "restoration", "trust"], False, True, 2.0)
    return (["rest", "restoration", "trust"], True, True, 4.0)
