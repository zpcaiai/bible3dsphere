"""
repentance_engine.py — 悔改的解剖 / The Doctrine of Repentance（汤姆·华森 Thomas Watson）

confession 引擎是「认罪的流程」；本引擎补悔改的**神学解剖**：真悔改是什么、不是什么。
华森《悔改的教义》归纳真悔改的**六要素**：
  1. 看见罪（对罪有省悟）；2. 为罪忧伤（依着神的忧愁，非世俗的忧愁）；
  3. 认罪；4. 为罪羞愧；5. 恨恶罪；6. 转离罪（转向神）。
关键分辨（林后7:10）：**依着神的忧愁**生出没有后悔的懊悔，以致得救；**世俗的忧愁**（只是怕后果、
怕丢脸、懊恼自己），是叫人死的。真悔改不是情绪的自责，而是**心与行的转向**——恨恶并离弃罪，转向神。

纯函数；确定性优先；内置危机词检测 + **强迫性自责/属灵虐待式内疚**的分辨（命中则先托住恩典，
不加重自我定罪）；AI 仅作可选增强。不定罪、不催逼，只把「懊恼」引向「依神的忧愁 → 转向」。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# 真悔改的六要素（华森）
SIX = [
    {"key": "sight", "name": "看见罪", "note": "先如实看见——不是笼统地『我很糟』，而是具体地看见这件事错在哪。"},
    {"key": "sorrow", "name": "为罪忧伤", "note": "依着神的忧愁：为得罪了神而痛，而非只为后果而懊恼。"},
    {"key": "confess", "name": "认罪", "note": "向神（必要时向人）说出来，不遮掩、不找借口。"},
    {"key": "shame", "name": "为罪羞愧", "note": "健康的羞愧是『在恩典里的』——不是自我定罪，而是诚实面对。"},
    {"key": "hate", "name": "恨恶罪", "note": "不只是怕它的后果，而是开始厌恶罪本身。"},
    {"key": "turn", "name": "转离罪·转向神", "note": "悔改的核心动作——转身，离开罪，走向神。"},
]

STATES: List[Dict[str, Any]] = [
    {"key": "worldly", "name": "只是懊恼后果 / 怕被发现、怕丢脸",
     "kw": ["被发现", "丢脸", "后果", "怕被抓", "懊恼", "倒霉", "怎么这么蠢", "怕别人知道", "怕受罚"],
     "diagnosis": "这更像华森说的『世俗的忧愁』——为后果、为面子而懊恼，而非为得罪了神而忧伤。",
     "way": "世俗的忧愁盯着『我损失了什么』，依神的忧愁盯着『我伤了神的心』。求神把你的懊恼，"
            "转成依着祂的忧愁——从『我真倒霉』转向『我得罪了那爱我的主』，再从那里转身归向祂。",
     "ref": "林后7:10", "text": "因为依着神的意思忧愁，就生出没有后悔的懊悔来，以致得救；但世俗的忧愁是叫人死。"},
    {"key": "stuck", "name": "一直自责却没有改变 / 走不出来",
     "kw": ["自责", "走不出", "循环", "又犯", "没改变", "反复", "陷在", "过不去", "老是想", "内疚循环"],
     "diagnosis": "你困在『懊悔的情绪』里，却还没走到悔改的核心——转身。自责本身不是悔改，转向才是。",
     "way": "别再绕着自责打转。真悔改的第六要素是『转离罪、转向神』——把注意力从『我又搞砸了』，"
            "移到『我现在往哪个方向迈一步』。认了，就靠恩典转身；跌倒了，就再回来，而不是躺在自责里。",
     "ref": "赛55:7", "text": "恶人当离弃自己的道路……归向耶和华，耶和华就必怜恤他……我们的神，因为他必广行赦免。"},
    {"key": "genuine", "name": "想真正地悔改 / 认真面对一个罪",
     "kw": ["悔改", "认真面对", "真正", "对付罪", "回转", "归向神", "想改", "对付", "彻底"],
     "diagnosis": "愿意认真悔改，本身就是恩典在动工。华森会帮你走全六要素，而不停在半路。",
     "way": "走一遍六要素：看见→依神忧伤→认罪→羞愧→恨恶→转向。重点在最后一步——具体地转身："
            "定一个离开罪、走向神的实际行动。悔改不是一次情绪，是持续的转向。",
     "ref": "徒3:19", "text": "所以，你们当悔改归正，使你们的罪得以涂抹。"},
    {"key": "condemn", "name": "陷在强迫性的自我定罪里 / 觉得神不会原谅",
     "kw": ["不会原谅", "不可饶恕", "定罪", "没救了", "太脏", "神恨我", "永远不配", "罪太大", "无法赦免"],
     "diagnosis": "这已经不是悔改，而是滑进了强迫性的自我定罪——那不是圣灵的责备，倒像控告者的声音。",
     "way": "真悔改带来的是『依神的忧愁』+『转向的盼望』，不是无止境的自我碾压。若你已经认了罪，"
            "神的赦免就已经临到——不是因你够痛，而是因基督的血够全。请从定罪里出来，接受赦免，然后转身。",
     "ref": "约壹1:9", "text": "我们若认自己的罪，神是信实的，是公义的，必要赦免我们的罪，洗净我们一切的不义。"},
]

# 强迫性内疚/属灵虐待式自责
SCRUPLE_WORDS = ["不可饶恕", "永远不配", "神恨我", "没救了", "太脏了", "无法赦免", "该下地狱", "配不上活"]


def _detect_scruple(text: str) -> bool:
    return any(w in (text or "") for w in SCRUPLE_WORDS)


CRISIS_WORDS = ["自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死",
                "死了算了", "伤害自己", "撑不下去了", "没有意义活着", "想消失"]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = ("我听见你正承受很重的痛。如果你有伤害自己的念头，请现在就联系你信任的人或当地心理危机热线。"
               "神的赦免比你最深的罪更深；你也值得有人此刻真实地陪着你。（本功能不替代专业帮助。）")


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    if _detect_scruple(t):
        return next(d for d in STATES if d["key"] == "condemn")
    best, best_hits = None, 0
    for d in STATES:
        hits = sum(1 for k in d["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, d
    return best or (STATES[2] if len(STATES) > 2 else STATES[0])


def meta() -> Dict[str, Any]:
    return {
        "title": "悔改的解剖",
        "source": "汤姆·华森《悔改的教义》(The Doctrine of Repentance)",
        "core": "真悔改的六要素：看见罪、为罪忧伤、认罪、为罪羞愧、恨恶罪、转离罪转向神；关键是依神的忧愁(而非世俗的忧愁)。",
        "six_elements": SIX,
        "key_distinction": "依着神的忧愁生出以致得救的悔改；世俗的忧愁（只怕后果/丢脸）是叫人死的（林后7:10）。",
        "verse": "徒3:19",
        "principle": "悔改不是情绪的自责，而是心与行的转向——恨恶并离弃罪，转向神。",
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
        "diagnosis": picked["diagnosis"],
        "way_forward": picked["way"],
        "six_elements": SIX,
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "prayer": ("父啊，我不要停在只为后果懊恼的『世俗忧愁』里，也不要陷进无止境的自我定罪。"
                   "求你赐我依着你的忧愁——为得罪了你而真心痛悔，然后靠着你的恩典转身，离开这罪、归向你。"
                   "谢谢你，我若认罪，你必赦免、必洗净。求你不但赦免我，也改变我的心，叫我渐渐恨恶罪、爱慕你。"),
        "practices": [
            "走到第六步：不停在自责——写下一个『转离罪、转向神』的具体行动，今天就迈出。",
            "分辨忧愁：问自己『我是为得罪了神而痛，还是只为后果而懊恼？』求神把后者转成前者。",
        ],
        "summary": ("真悔改不是情绪的自责，而是依着神的忧愁 + 实际的转向。别停在懊悔里，"
                    "认了罪就靠恩典转身；神的赦免够全，因基督的血够全。"),
        "closing": "「你们当悔改归正，使你们的罪得以涂抹。」（徒3:19）",
        "ai_used": False,
    }
    if scruple:
        result["practices"] = [
            "先领受赦免：若你已认罪，神的赦免已经临到（约壹1:9）——大声读一遍，接受它，不再自我碾压。",
            "分辨声音：圣灵的责备带来盼望与转向；控告者的声音只带来绝望。跟随前者，拒绝后者。",
        ]
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return ("你是一位温柔、以福音为中心的属灵陪伴者，熟悉华森《悔改的教义》。核心：真悔改六要素"
            "(看见罪/为罪忧伤/认罪/羞愧/恨恶罪/转离罪转向神)，关键分辨依神的忧愁 vs 世俗的忧愁(林后7:10)；"
            "悔改不是情绪自责，而是心与行的转向。若用户陷入强迫性自我定罪，先托住恩典、不加重定罪。"
            "请针对用户处境，温柔诊断，引向『依神的忧愁 + 转向』，给经文、祷告与操练。中文，绝不催逼、不定罪。\n"
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
        return (["repentance", "grace", "turning"], False, True, 2.0)
    return (["repentance", "grace", "turning"], True, True, 4.0)
