"""
loneliness_engine.py — 孤单 · 被看不见的痛（创16 夏甲「你是看顾人的神 El Roi」）

「孤单」在系统里散见 16 个引擎却无专属。它是「被看不见、被不知、无人同行」的痛。
夏甲在旷野走投无路时遇见神，给祂起名「El Roi——你是看顾人的神」（创16:13）：孤单最深处，
有一位看见你、认识你、与你同在的神。

分辨：**独处（solitude）**是好的、可与神同在的；**孤单（loneliness）**是那份未被满足的痛。
两不偏废：既不属灵地跳过（『你只要在神里知足就好』会显得轻慢），也不任其吞没。
真理 + 一步：神看见你（垂直）→ 从这份被看见里，迈一小步向人（水平）。

纯函数；确定性；内置危机词检测（孤单↔绝望相邻，谨慎）；AI 可选增强。不轻看痛，
只把人从「没人看见我」领回「有一位看见你」，并温柔地推一步向连接。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

STATES: List[Dict[str, Any]] = [
    {"key": "unseen", "name": "没人懂我 / 觉得不被看见、不被知道",
     "kw": ["没人懂", "不被看见", "不被理解", "没人知道", "被忽略", "透明人", "存在感", "没人在乎", "被无视"],
     "diag": "你最深的痛，是觉得没有人真正看见、真正认识你。这份痛是真的，也是最人性的。",
     "way": "夏甲在旷野被神看见，就称祂『El Roi——看顾人的神』。在没有人看见你的地方，有一位一直看见你、"
            "完全认识你、并且爱你。先让这真理坐下来：你不是隐形的，神从未错过你。再从这份被看见里，"
            "试着向一个安全的人露出一点真实——被神看见，能给你勇气被人看见。",
     "ref": "创16:13", "text": "夏甲就称那对她说话的耶和华为「看顾人的神」……因为她说：在这里我也看见那看顾我的吗？"},
    {"key": "alone", "name": "身边没有人 / 独居、举目无亲",
     "kw": ["一个人", "独居", "没有人", "举目无亲", "没朋友", "空荡", "回家没人", "孤身", "身边没人", "无人陪"],
     "diag": "你身边确实很空——这不是矫情，是真实的缺乏。神造人本不宜独居，你对同伴的渴望是对的。",
     "way": "神与你同在，这是根基（祂说『我总不撇下你』）；但祂也常藉着『人』来爱你。把『向神支取同在』"
            "与『向人迈一小步』一起做：为神差人到你生命里祷告，同时你也主动迈半步——一句问候、一次赴约、"
            "一个小群体。孤单里最勇敢的一步，往往是主动伸出手。",
     "ref": "诗68:6", "text": "神叫孤独的有家，使被囚的出来享福。"},
    {"key": "crowd", "name": "人群里更孤单 / 热闹却没有归属",
     "kw": ["人群里", "热闹", "没有归属", "格格不入", "融不进", "表面热闹", "散场后", "一群人却", "谁都不亲"],
     "diag": "最深的孤单，有时发生在人多的地方——你在场，却没被真正连接。热闹填不满对被知的渴望。",
     "way": "你缺的不是更多的人，是更深的一两段真实连接。求神给你一两个可以卸下面具的人；也在祂面前先被完全知道——"
            "祂知道你的名、你的每一根头发。从『被祂完全知道』的安稳里，去寻求少而真的连接，而非多而浅的热闹。",
     "ref": "诗139:1-2", "text": "耶和华啊，你已经鉴察我，认识我……我坐下，我起来，你都晓得。"},
    {"key": "loss", "name": "失去后的孤单 / 分离、丧亲、关系断裂后",
     "kw": ["失去", "分离", "丧", "离开我", "分手", "断了", "走了", "空缺", "再也没有", "阴阳两隔"],
     "diag": "你的孤单来自一个真实的失去，留下一个具体的空缺。这样的孤单，需要被哀悼，而不只是被填补。",
     "way": "允许自己哀伤这份失去（可到『哀歌』页）。同时记得：那位『与哀哭的人同哭』的神，此刻与你一同在这空缺旁。"
            "祂不急着叫你『赶紧好起来』，祂先与你同坐。慢慢来，让祂的同在陪你走过这一段。",
     "ref": "诗34:18", "text": "耶和华靠近伤心的人，拯救灵性痛悔的人。"},
    {"key": "seek", "name": "想在孤单中更深经历神的同在",
     "kw": ["经历同在", "与神独处", "孤单中", "更深", "神的陪伴", "安息", "亲近神", "独处", "渴慕同在"],
     "diag": "你愿意让孤单成为遇见神的地方——旷野常是神最亲近人的地方（夏甲、以利亚、旷野四十年）。",
     "way": "把孤单转成与神独处的邀请：安静下来，对祂说『主啊，我很孤单，但我知道你在这里』。"
            "让被祂看见、被祂陪伴充满你；这份饱足，会让你不再『饥饿地』抓人，而能『自由地』去爱人。",
     "ref": "赛41:10", "text": "你不要害怕，因为我与你同在……我必坚固你，我必帮助你。"},
]

CRISIS_WORDS = ["自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死",
                "死了算了", "伤害自己", "撑不下去了", "没有意义活着", "想消失", "没人会想我"]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = ("我听见你的孤单已经很深、很痛了。如果你有伤害自己的念头，或觉得没有人会在意你消失，"
               "请现在就联系你信任的人或当地心理危机热线——你的痛是真的，也一定有人愿意此刻陪着你。"
               "神看见你、从未撇下你。（本功能不替代专业帮助。）")


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
        "title": "孤单 · 被看不见的痛",
        "source": "创16 夏甲「你是看顾人的神 El Roi」；诗篇",
        "core": "孤单是被看不见/不被知/无人同行的痛；真理是神看见你、认识你、与你同在；从被神看见里迈一步向人。",
        "distinction": "独处(solitude)是好的、可与神同在；孤单(loneliness)是未被满足的痛——两不偏废：不属灵地跳过，也不任其吞没。",
        "states": [{"key": d["key"], "name": d["name"]} for d in STATES],
        "verse": "创16:13",
        "principle": "「你是看顾人的神。」——孤单最深处，有一位看见你、认识你、爱你的神。",
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
        "two_moves": "两个方向一起做：**垂直**——让『神看见你』的真理坐实；**水平**——从这份被看见里，向一个人迈一小步。",
        "prayer": ("主啊，我很孤单，觉得没有人真正看见我、懂我。谢谢你——你是看顾人的神，在没有人看见我的地方，"
                   "你一直看见我、完全认识我、并且爱我。求你用这份被你看见的确据充满我，叫我不再那样孤单；"
                   "也求你差人到我生命里，并给我勇气，向一个安全的人迈出一小步。你从未撇下我。"),
        "practices": [
            "坐实真理：安静一分钟，把『你是看顾我的神，你此刻看见我』对神说几遍，让它沉到心里。",
            "迈半步向人：今天主动向一个人伸出一点手——一句问候、一次约、加入一个小群体。孤单里最勇敢的是主动。",
        ],
        "summary": ("孤单是真实的痛，不必被属灵地跳过。真理是：有一位看见你、认识你、与你同在的神(El Roi)。"
                    "从这份被看见里，向一个人迈一小步——垂直的饱足，给你水平的勇气。"),
        "closing": "「神叫孤独的有家。」（诗68:6）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return ("你是一位温柔、以福音为中心的属灵陪伴者，熟悉创16 夏甲『你是看顾人的神 El Roi』。核心：孤单是被看不见/"
            "不被知的痛；真理是神看见你、认识你、与你同在；分辨独处(好)与孤单(痛)——不属灵地跳过、也不任其吞没；"
            "两个方向一起：垂直(神看见你)+水平(向人迈一步)。请针对用户处境温柔诊断，给经文、祷告与一个向连接的小步。"
            "中文，不轻看其痛，孤单与绝望相邻时格外温柔。\n"
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
        return (["loneliness", "presence", "connection"], False, True, 2.0)
    return (["loneliness", "presence", "connection"], True, True, 4.5)
