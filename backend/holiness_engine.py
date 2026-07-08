"""
holiness_engine.py — 成圣与圣洁 / Sanctification（莱尔 J.C. Ryle《圣洁》Holiness；
Walter Marshall《成圣的福音奥秘》The Gospel Mystery of Sanctification）

给系统补上「治死」之外的正面一半。欧文《治死身体的恶行》已在语料里（负面 mortification，除罪）；
本引擎补上**正面的更新（vivification，穿上基督）**，并锁定「成圣的福音次序」——这正是马歇尔的核心：

  · **成圣的福音奥秘（Marshall）**：我们不是「靠成圣去换取神的接纳」，而是**从已经在基督里被接纳、
    与祂联合的地位，出于信心去追求圣洁**。次序是「先有身份，后有行为」——你不是为了被爱而圣洁，
    而是因为已被爱而圣洁。倒过来，就落回律法主义。
  · **莱尔《圣洁》**：成圣是真实的、需要努力的（striving）、却是圣灵所赐能力的。圣洁是与神同心、
    恨恶罪、渴慕像基督；它是称义的果子与凭据，却与称义分别——不可混为一谈，也不可彼此拆开。
  · **治死 + 更新（put off / put on）**：不只是「停止做某罪」，更是「穿上基督相反的美德」——
    以正面的爱取代负面的空缺（弗4:22-24）。

与 union（身份脊椎）、gospel（福音诊断）、affections 协同：本引擎只做一件事——
接住一个「想胜过的罪 / 想长进的方向」，先校正福音次序，再给一对「治死—穿上」的具体操练。
纯函数；确定性优先；内置危机词检测；AI 仅作可选增强。不定罪、不把人定义为罪、导向恩典中的努力。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ── 常见「缠累的罪 / 想长进处」→ 治死什么 + 穿上什么（put off / put on）+ 经文 ──
STRUGGLES: List[Dict[str, Any]] = [
    {"key": "anger", "name": "易怒 / 苦毒 / 口舌伤人",
     "kw": ["怒", "苦毒", "生气", "脾气", "恨", "报复", "口舌", "骂", "暴躁", "怨"],
     "put_off": "以牙还牙的怒气与苦毒", "put_on": "以恩慈、怜悯、饶恕待人（基督怎样饶恕了你）",
     "ref": "弗4:31-32", "text": "一切苦毒、恼恨、忿怒……都当从你们中间除掉；并要以恩慈相待，存怜悯的心，彼此饶恕。"},
    {"key": "lust", "name": "情欲 / 私密的挣扎",
     "kw": ["情欲", "色情", "淫", "私密", "肉体", "欲望", "手淫", "不洁", "眼目", "沉溺"],
     "put_off": "暗中喂养的情欲与遮掩", "put_on": "在光中的圣洁、坦诚（向可信的人）、把身体献给神为圣洁的器皿",
     "ref": "罗13:14", "text": "总要披戴主耶稣基督，不要为肉体安排，去放纵私欲。"},
    {"key": "pride", "name": "骄傲 / 自义 / 爱比较",
     "kw": ["骄傲", "自义", "比较", "面子", "自大", "看不起", "争强", "虚荣", "高傲", "论断"],
     "put_off": "自高与看别人不如自己", "put_on": "存心谦卑，看别人比自己强，效法基督的虚己",
     "ref": "腓2:3-5", "text": "只要存心谦卑，各人看别人比自己强……你们当以基督耶稣的心为心。"},
    {"key": "greed", "name": "贪爱钱财 / 抓紧不放",
     "kw": ["贪", "钱", "物质", "抓紧", "舍不得", "囤", "占有", "吝啬", "贪婪", "放不下"],
     "put_off": "贪婪与倚靠钱财的安全感", "put_on": "知足、慷慨施予、把财宝积在天上",
     "ref": "来13:5", "text": "你们存心不可贪爱钱财，要以自己所有的为足；因为主曾说：我总不撇下你，也不丢弃你。"},
    {"key": "lie", "name": "说谎 / 虚假 / 戴面具",
     "kw": ["说谎", "虚假", "面具", "装", "隐瞒", "夸大", "欺骗", "两面", "假", "伪"],
     "put_off": "谎言与虚假的自我保护", "put_on": "凭爱心说诚实话，在光中行、活得真实",
     "ref": "弗4:25", "text": "所以你们要弃绝谎言，各人与邻舍说实话，因为我们是互相为肢体。"},
    {"key": "sloth", "name": "懒散 / 拖延 / 属灵懈怠",
     "kw": ["懒", "拖延", "懈怠", "颓", "混日子", "无力", "提不起", "松懈", "怠惰", "逃避"],
     "put_off": "属灵的懈怠与自我放纵", "put_on": "殷勤、忠心地服事，像是给主做的，在小事上忠心",
     "ref": "西3:23", "text": "无论做什么，都要从心里做，像是给主做的，不是给人做的。"},
    {"key": "general", "name": "说不清的挣扎 / 只是想更像基督",
     "kw": [],
     "put_off": "旧人的行为", "put_on": "那照着神形像造的新人，穿上基督",
     "ref": "弗4:22-24", "text": "脱去……旧人，将你们的心志改换一新，并且穿上新人，这新人是照着神的形像造的。"},
]

CRISIS_WORDS = [
    "自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死", "死了算了",
    "伤害自己", "撑不下去了", "没有意义活着", "想消失",
]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = (
    "我听见你正承受很重的痛。谈成圣长进之前，我想先温柔地说：如果你有伤害自己的念头，"
    "请现在就联系你信任的人或当地心理危机热线。你在基督里的地位，不因你的挣扎而动摇——你不必独自扛。"
    "（本功能不替代专业帮助。）"
)


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best: Optional[Dict[str, Any]] = None
    best_hits = 0
    for s in STRUGGLES:
        if s["key"] == "general":
            continue
        hits = sum(1 for k in s["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, s
    return best or next(s for s in STRUGGLES if s["key"] == "general")


def meta() -> Dict[str, Any]:
    return {
        "title": "成圣与圣洁",
        "source": "J.C. Ryle《圣洁》；Walter Marshall《成圣的福音奥秘》",
        "gospel_order": ("成圣的福音次序：不是靠圣洁去换取神的接纳，而是从已在基督里被接纳、与祂联合的地位，"
                         "出于信心去追求圣洁——先有身份，后有行为。倒过来就是律法主义。"),
        "put_off_put_on": "治死（put off 旧人的罪）+ 更新（put on 穿上基督的美德）——除罪之外，更要以正面的美德填满。",
        "verse": "弗4:22-24",
        "principle": "成圣是真实的、需努力的，却是圣灵所赐能力的；它是称义的果子与凭据，与称义分别却不可拆开（来12:14）。",
    }


def analyze(struggle: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    struggle = (struggle or "").strip()
    crisis = _detect_crisis(struggle)
    picked = _pick(struggle)

    # 侦测「为得接纳而努力」的律法主义口吻，好校正福音次序
    legalism_kw = ["才配", "才能被爱", "神才会", "换取", "达标", "够好", "赚", "证明自己", "才算", "值得被爱"]
    legalist_lean = any(k in struggle for k in legalism_kw)
    order_note = (
        ("我留意到一个口吻：你像是想「靠胜过这罪来换取神的悦纳」。Marshall 会温柔地把次序倒过来——"
         "你不是为了被接纳才圣洁，而是**因为已在基督里被接纳**，才从这份安稳里去追求圣洁。先领受，再流出。")
        if legalist_lean else
        ("先站稳福音次序：你追求圣洁，不是为了赚取神的爱，而是因为你已在基督里被爱、与祂联合——"
         "从这个已经稳妥的身份出发，去长进。")
    )

    result: Dict[str, Any] = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "focus": {"key": picked["key"], "name": picked["name"]},
        "gospel_order_note": order_note,
        "legalist_lean": legalist_lean,
        "mortify": {"put_off": picked["put_off"], "label": "治死（put off）"},
        "vivify": {"put_on": picked["put_on"], "label": "更新（put on）"},
        "pair_line": ("治死—更新是一对：不只是「别再" + picked["put_off"] + "」，更是主动「穿上"
                      + picked["put_on"] + "」——用正面的美德填满除去罪后留下的空。"),
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "spirit_note": ("这不是靠意志硬扛：真正的能力来自圣灵，与你在基督里的联合。"
                        "你尽力，但倚靠的是祂在你里面动的工（腓2:12-13）。"),
        "prayer": ("父啊，谢谢你，我在基督里已经被你完全接纳——我追求圣洁不是要赚你的爱，而是因为已被你爱。"
                   "求圣灵在我里面动工，帮助我治死「" + picked["put_off"] + "」，也穿上「" + picked["put_on"]
                   + "」。我尽力，但我倚靠的是你的能力，不是我的意志。愿我一天比一天更像基督。"),
        "practices": [
            "写下这一对：今天我要治死「" + picked["put_off"] + "」，穿上「" + picked["put_on"] + "」。贴在看得见处。",
            "求圣灵、定一个具体动作：为「穿上」那一面想一个今天就能做的小行动（一次饶恕、一句实话、一次谦让）。",
        ],
        "summary": ("成圣是真实、需努力、却靠圣灵的长进。站稳福音次序（因被爱而圣洁，非为被爱而圣洁），"
                    "并把「治死罪」与「穿上基督」当作一对来操练。"),
        "closing": "「非圣洁没有人能见主。」（来12:14）——但那圣洁，是恩典在你里面结出的果子。",
        "ai_used": False,
    }

    if use_ai:
        enhanced = _ai_enhance(struggle, result, settings)
        if enhanced:
            result.update(enhanced)
            result["ai_used"] = True
    return result


def build_prompt(struggle: str, base: Dict[str, Any]) -> str:
    return (
        "你是一位温柔、以福音为中心的属灵陪伴者，熟悉 J.C. Ryle《圣洁》与 Walter Marshall《成圣的福音奥秘》。"
        "核心：成圣的福音次序是『因已在基督里被接纳而追求圣洁』，不是靠圣洁换取接纳（否则落回律法主义）；"
        "成圣是真实、需努力、却靠圣灵的；要『治死罪(put off)』并『穿上基督的美德(put on)』成对操练。"
        "请针对用户想胜过的罪或想长进处，先校正福音次序，再给一对治死—穿上的具体操练、经文与祷告。"
        "中文，温暖不说教，绝不把人定义为罪、不制造『你不够努力』的重担，导向恩典中的努力。\n"
        f"用户处境：{struggle}\n"
        "请输出 JSON：{\"gospel_order_note\":\"...\",\"pair_line\":\"...\",\"prayer\":\"一段可照着祷告的话\","
        "\"summary\":\"...\",\"closing\":\"一句经文\"}。"
    )


def _ai_enhance(struggle: str, base: Dict[str, Any], settings: Any) -> Optional[Dict[str, Any]]:
    prompt = build_prompt(struggle, base)
    raw = _call_ai(prompt, settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        out: Dict[str, Any] = {}
        for k in ("gospel_order_note", "pair_line", "prayer", "summary", "closing"):
            if data.get(k):
                out[k] = str(data[k])
        return out or None
    except Exception:
        return None


def _call_ai(prompt: str, settings: Any) -> Optional[str]:
    for modname, fn in (("engine_ai", "call_ai"),):
        try:
            mod = __import__(modname)
            f = getattr(mod, fn, None)
            if f:
                out = f(prompt) if settings is None else f(prompt, settings=settings)
                if out:
                    return out if isinstance(out, str) else str(out)
        except Exception:
            continue
    return None


def formation_signal(result: Dict[str, Any]):
    """成圣属于「品格 + 身份 + 顺服」。"""
    if result.get("crisis"):
        return (["character", "identity", "obedience"], False, True, 2.0)
    return (["character", "identity", "obedience"], True, True, 4.0)
