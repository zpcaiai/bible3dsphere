"""
prodigal_engine.py — 为浪子 / 未信至亲祷告（路15；奥古斯丁之母莫妮加；恒切代求）

系统的 intercession 是通用代祷；本引擎专补一个巨大的现实之痛——**为一个远离神/未信的至亲揪心**
（孩子、配偶、父母、挚友）。莫妮加为浪荡的奥古斯丁流泪祷告了近二十年，主教对她说：
「流这许多眼泪的儿子，断不至灭亡。」后来奥古斯丁归主，成了教会伟大的教父。

要点：(1)你的揪心，神比你更深地爱那人；(2)恒切代求、不灰心（路18 寡妇）；(3)交托——你不能替他信，
不能强扭他的心，只能把他交在那位追寻浪子的父手里；(4)守住关系的门（浪子的父天天望路口）；
(5)照顾好自己的心，别在等待中被苦毒或自责吞没（他的选择不由你负全责）。

纯函数；确定性；内置危机词检测；AI 可选增强。不给「保证他一定会信」的空头支票，
只把揪心的父母/亲人领向恒切的代求、交托与不灭的盼望。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

STATES: List[Dict[str, Any]] = [
    {"key": "child", "name": "为远离神的孩子揪心",
     "kw": ["孩子", "儿子", "女儿", "孩子不信", "孩子离开神", "叛逆", "孩子走偏", "娃", "下一代"],
     "diag": "为孩子的灵魂揪心，是父母心里最深的痛之一。你不孤单——莫妮加为奥古斯丁流泪祷告了近二十年。",
     "way": "记住那位主教对莫妮加说的：『流这许多眼泪的儿子，断不至灭亡。』你的眼泪神都收在祂的皮袋里。"
            "恒切为孩子代求、不灰心；同时守住关系的门（像浪子的父天天望路口），让家里始终有一条回来的路。"
            "你不能替他信，但你能不停地把他举到父面前。",
     "ref": "路15:20", "text": "相离还远，他父亲看见，就动了慈心，跑去抱着他的颈项，连连与他亲嘴。"},
    {"key": "spouse", "name": "为未信的配偶祷告",
     "kw": ["配偶", "另一半", "老公", "妻子", "丈夫", "未信的家人", "伴侣不信", "夫妻信仰"],
     "diag": "与最亲近的人在信仰上不同步，是一种日日相伴的孤单与负担。神看见这份张力，也看见你的盼望。",
     "way": "圣经说不信的丈夫因妻子成了圣洁（林前7:14）——你的同在不是徒然。彼前3 说，或许不靠言语，"
            "而靠你温柔安静、有盼望的生命把他赢得。为他恒切祷告、以爱相待、不唠叨也不放弃；把改变他心的工，"
            "交给唯一能改变人心的圣灵。",
     "ref": "彼前3:1-2", "text": "……也可以不用言语，被妻子的品行感化过来；这正是因看见你们有贞洁的品行和敬畏的心。"},
    {"key": "parent", "name": "为年迈/未信的父母祷告",
     "kw": ["父母", "爸妈", "老人", "长辈", "父母未信", "爸不信", "妈不信", "为父母"],
     "diag": "为把你养大、却还不认识主的父母祷告，带着一种紧迫的爱——尤其当他们年岁渐长。",
     "way": "把这份紧迫交给神的时间，而非你的焦虑。恒切为他们的心祷告，用他们能感受到的方式去爱与孝敬；"
            "在合适的时候温柔分享，不合适时就用生命见证。救恩在乎神的怜悯——祂能在最后一刻寻回一个人（十架的强盗）。"
            "你负责忠心地爱与祷告，结果交给神。",
     "ref": "徒16:31", "text": "当信主耶稣，你和你一家都必得救。"},
    {"key": "weary", "name": "祷告很久了却看不到改变 / 快灰心",
     "kw": ["祷告很久", "看不到改变", "灰心", "没用", "多少年", "还是不信", "累了", "快放弃", "石沉大海"],
     "diag": "你已经为这人祷告了很久，久到快灰心。耶稣正是为这种时刻讲了那个『不可灰心』的寡妇的比喻。",
     "way": "神的『还没有』不是『不』。莫妮加祷告了近二十年才看见答案。恒切不是操纵神，而是持守盼望、"
            "把这人一次次重新交托。若你累了，容许自己也被神安慰——你不是独自扛起他得救的责任，那是神的工。"
            "继续祷告，但从『我必须促成』的重担里松手。",
     "ref": "路18:1", "text": "耶稣设一个比喻，是要人常常祷告，不可灰心。"},
    {"key": "guilt", "name": "自责 / 觉得是我没做好他才这样",
     "kw": ["自责", "怪自己", "我没做好", "都怪我", "是不是我", "没教好", "我的错", "愧疚", "没带好"],
     "diag": "你把他的偏离全揽到自己身上——这份自责可以理解，但它既不准确、也压垮你。",
     "way": "你有你的责任，但每个人在神面前也为自己负责；你不能替他做选择，也不必替他的选择背全责。"
            "把自责交给神，求祂赦免你确实的亏欠、也除去那些不属于你的重担。你现在能做的，不是无尽自责，"
            "而是继续祷告、继续以爱守住门。神能修复你以为毁了的。",
     "ref": "结18:20", "text": "惟有犯罪的，他必死亡。儿子必不担当父亲的罪孽，父亲也不担当儿子的罪孽。"},
    {"key": "how", "name": "想学习怎样为他恒切代求",
     "kw": ["怎么祷告", "怎样代求", "恒切", "为他祷告", "代祷", "学习", "该求什么", "怎么交托"],
     "diag": "愿意学着为所爱的人恒切代求，本身就是爱与信心。",
     "way": "为他这样求：求圣灵在他心里作工（唯有圣灵能重生人）、求神安排环境与人触动他、求神保守他的路、"
            "求给你智慧与恰当的时机去爱与见证。定一个恒常的节奏（每天为他名字祷告一次），把他放进你的『代祷名单』。"
            "祷告 + 以爱守门 + 交托结果——这是浪子之父的姿态。",
     "ref": "帖后3:5", "text": "愿主引导你们的心，叫你们爱神，并学基督的忍耐。"},
]

CRISIS_WORDS = ["自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死",
                "死了算了", "伤害自己", "撑不下去了", "没有意义活着", "想消失"]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = ("我听见你正承受很重的痛。如果你有伤害自己的念头，请现在就联系你信任的人或当地心理危机热线。"
               "你为所爱之人的揪心，神都看见；你也值得有人此刻真实地陪着你。（本功能不替代专业帮助。）")


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
        "title": "为浪子 / 未信至亲祷告",
        "source": "路15；奥古斯丁之母莫妮加；路18 恒切祷告",
        "core": "神比你更深爱那人；恒切代求不灰心，把他交在追寻浪子的父手里，守住关系的门，照顾好自己的心。",
        "posture": ["恒切代求（不灰心）", "交托（不能替他信）", "守门（天天望路口）", "自我看顾（不被自责/苦毒吞没）"],
        "states": [{"key": d["key"], "name": d["name"]} for d in STATES],
        "verse": "路15:20",
        "principle": "「流这许多眼泪的儿子，断不至灭亡。」（主教对莫妮加语）——你的眼泪，神都收在皮袋里。",
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
        "posture": ["恒切代求（不灰心）", "交托（你不能替他信）", "守门（像浪子的父天天望路口）", "自我看顾（别被自责/苦毒吞没）"],
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "prayer": ("追寻浪子的父啊，你比我更爱这个人。我把他/她的名字再一次举到你面前——求你的灵在他心里动工，"
                   "唯有你能重生一个人的心。求你安排环境与人触动他，保守他的脚步，也给我智慧、忍耐与恰当的时机去爱、去见证。"
                   "当我灰心时，提醒我你的『还没有』不是『不』；当我自责时，除去那些不属于我的重担。我把他交在你手里，"
                   "像浪子的父，天天望着路口，存着不灭的盼望。"),
        "practices": [
            "定一个恒切的节奏：把他的名字放进你的『代祷名单』，每天为他祷告一次，不灰心。",
            "守住门：本周用他能感受到的方式，向他表达一次无条件的爱（不说教、不唠叨），让家里始终有回来的路。",
        ],
        "summary": ("神比你更深爱那人。你的姿态是浪子之父的姿态：恒切代求、把他交给唯一能改变人心的神、"
                    "守住关系的门、也照顾好自己的心。神的『还没有』不是『不』——继续流泪祷告，存着不灭的盼望。"),
        "closing": "「相离还远，他父亲看见，就动了慈心，跑去……」（路15:20）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return ("你是一位温柔、以福音为中心的属灵陪伴者，熟悉路15浪子与莫妮加为奥古斯丁的代求。核心：神比你更深爱那人；"
            "恒切代求不灰心(路18)、交托(你不能替他信)、守住关系的门(浪子的父天天望路口)、照顾好自己的心(别被自责/苦毒吞没)。"
            "请针对用户为浪子/未信至亲的处境温柔陪伴，给经文、祷告与操练；不给『保证他一定会信』的空头支票，"
            "但给不灭的盼望。中文。\n"
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
    if result.get("crisis"):
        return (["intercession", "hope", "trust"], False, True, 2.0)
    return (["intercession", "hope", "trust"], True, True, 4.0)
