"""
envy_engine.py — 嫉妒 / 羡慕（雅3-4；该隐；扫罗）

散见却无专属。嫉妒是「因别人的好而痛，想要他所有的，有时甚至想他没有」。它躲在暗处、
乔装成「上进」或「不服」。雅各说嫉妒里有「扰乱和各样的坏事」（雅3:16）。

分辨：**嫉妒**（resent 别人的好）vs **正当的效法**（aspire，被激励向上而不贬损他人）。
根：与人比较、对神的分配不满、把自我价值押在「胜过别人」。解药：(1)拿到光下命名（它最怕被看见）；
(2)与喜乐的人同乐（罗12:15 是嫉妒的正相反）；(3)在基督里知足、数算神给我的那一份；(4)为那人祝福。

纯函数；确定性；内置危机词检测；AI 可选增强。不定罪（嫉妒人人都有），
只帮人把嫉妒拿到光下，重排为知足、同乐与祝福。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

STATES: List[Dict[str, Any]] = [
    {"key": "success", "name": "见不得别人成功 / 别人得意我就难受",
     "kw": ["别人成功", "见不得", "难受", "凭什么他", "不服", "别人得意", "眼红", "别人升", "他凭什么"],
     "diag": "别人的好，成了你的痛——这是嫉妒。它常乔装成『不服』或『上进』，其实底下是『他不该比我好』。",
     "way": "先在神面前诚实命名它（嫉妒最怕被看见）。然后做它的正相反——罗12:15『与喜乐的人要同乐』："
            "试着为那个人真心高兴、甚至道一句恭喜。同乐是嫉妒的解药，因为它把你从比较的牢里放出来。",
     "ref": "雅3:16", "text": "在何处有嫉妒、纷争，就在何处有扰乱和各样的坏事。"},
    {"key": "compare", "name": "刷到别人就自惭 / 社交媒体比较",
     "kw": ["刷到", "社交媒体", "朋友圈", "别人的生活", "自惭", "比下去", "看别人光鲜", "羡慕别人", "对比"],
     "diag": "你在拿自己的『幕后』比别人的『精修封面』——比较的赛道上，永远有人在前面，嫉妒就永无止境。",
     "way": "从这条赛道上退出来。你看到的是别人的高光，不是全部；而神量给你的那一份，够用且合宜。"
            "少看几眼别人的封面，多数一数神给你的恩典。知足不靠得到更多，靠不再把眼睛盯在别人碗里。",
     "ref": "加6:4", "text": "各人应当察验自己的行为；这样，他所夸的就专在自己，不在别人了。"},
    {"key": "passed", "name": "被比下去 / 被忽略、别人被选中",
     "kw": ["被比下去", "被忽略", "别人被选", "落选", "被超过", "轮不到我", "被冷落", "别人被看重", "不被青睐"],
     "diag": "像扫罗听见『扫罗杀千千，大卫杀万万』——被比下去的刺痛，很容易长成嫉妒甚至苦毒。",
     "way": "你的价值不由『排在第几』决定，而由神对你的爱定案。把这刺痛带到神面前，别让它像扫罗那样长成苦毒。"
            "求神医治你被比较刺伤的地方，叫你能在自己蒙的恩里知足，不必靠盖过别人来站立。",
     "ref": "撒上18:8-9", "text": "扫罗甚发怒……从这日起，扫罗就怒视大卫。",
     },
    {"key": "atgod", "name": "不满神的分配 / 觉得神偏待、给他不给我",
     "kw": ["神偏心", "给他不给我", "不公平", "凭什么他有", "神偏待", "为什么他", "神对我不公", "分配不公"],
     "diag": "嫉妒的最深处，常是对神的不满——像葡萄园里的工人，嫉妒主人对别人的慷慨。问题从『他』转到了『神』。",
     "way": "把账算到正确的地方：你嫉妒的，其实是神的慷慨与主权。祂有权照祂的美意分配，且祂待你从未亏负。"
            "回到『祂给我的那一份』——你在基督里已经拥有了最好的。求祂医治你嫉妒的眼，看见祂对你的良善。",
     "ref": "太20:15", "text": "我的东西难道不可随我的意思用吗？因为我作好人，你就红了眼吗？"},
    {"key": "free", "name": "想从嫉妒里得自由 / 学会为人祝福",
     "kw": ["得自由", "为人祝福", "不再嫉妒", "同乐", "知足", "祝福别人", "对付嫉妒", "释放", "为他高兴"],
     "diag": "愿意对付嫉妒，是恩典在动工。嫉妒是可以被『知足 + 同乐 + 祝福』一点点松开的。",
     "way": "为你所嫉妒的那个人，具体地祝福一次——为他的好祷告、甚至当面道贺。这在一开始会别扭，"
            "但『为他祝福』会一点点把嫉妒从你心里挤出去，代之以自由与喜乐。",
     "ref": "罗12:15", "text": "与喜乐的人要同乐；与哀哭的人要同哭。"},
]

CRISIS_WORDS = ["自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死",
                "死了算了", "伤害自己", "撑不下去了", "没有意义活着", "想消失"]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = ("我听见你正承受很重的痛。如果你有伤害自己的念头，请现在就联系你信任的人或当地心理危机热线。"
               "神量给你的那一份够用且合宜，你在祂眼中是宝贵的——你也值得有人此刻真实地陪着你。（本功能不替代专业帮助。）")


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best, best_hits = None, 0
    for d in STATES:
        hits = sum(1 for k in d["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, d
    return best or STATES[4]


def meta() -> Dict[str, Any]:
    return {
        "title": "嫉妒 / 羡慕",
        "source": "雅3-4；该隐；扫罗；葡萄园的工人",
        "core": "嫉妒是因别人的好而痛，躲在暗处乔装成『上进/不服』；解药是拿到光下命名 + 与喜乐者同乐 + 在基督里知足 + 为人祝福。",
        "distinction": "嫉妒(resent 别人的好) vs 正当的效法(aspire，被激励向上而不贬损他人)。",
        "states": [{"key": d["key"], "name": d["name"]} for d in STATES],
        "verse": "罗12:15",
        "principle": "「与喜乐的人要同乐。」——同乐是嫉妒的正相反，也是从比较之牢里出来的钥匙。",
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
        "antidote": "三味解药：拿到光下命名它 → 与喜乐的人同乐（罗12:15）→ 在基督里数算神给我的那一份，并为那人祝福。",
        "prayer": ("主啊，我承认我心里有嫉妒——别人的好让我难受，我甚至不愿承认。谢谢你不定我的罪，"
                   "而是把它接到光下来医治。求你叫我能为那个人真心高兴，能数算你量给我的那一份并知足；"
                   "医治我被比较刺伤的地方，把嫉妒从我心里挤出去，代之以自由、知足与祝福人的喜乐。"),
        "practices": [
            "拿到光下：向神诚实说出你在嫉妒谁、嫉妒什么——命名，是松开它的第一步。",
            "为他祝福一次：为你所嫉妒的人具体祝福/道贺一次（哪怕别扭），练习用『同乐』挤走嫉妒。",
        ],
        "summary": ("嫉妒躲在暗处、乔装成上进。把它拿到光下命名，做它的正相反——与喜乐的人同乐、"
                    "在基督里数算你自己的那一份、为那人祝福。你不必靠盖过别人来站立。"),
        "closing": "「与喜乐的人要同乐。」（罗12:15）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return ("你是一位温柔、以福音为中心的属灵陪伴者，处理嫉妒。核心：嫉妒是因别人的好而痛、躲在暗处乔装成上进/不服"
            "(雅3:16)；分辨嫉妒(resent 别人的好)与正当效法(aspire)；解药是拿到光下命名+与喜乐者同乐(罗12:15)+在基督里知足+"
            "为人祝福。请针对用户处境温柔诊断(不定罪，嫉妒人人都有)，给经文、祷告与操练。中文。\n"
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
        return (["contentment", "joy", "blessing"], False, True, 2.0)
    return (["contentment", "joy", "blessing"], True, True, 4.0)
