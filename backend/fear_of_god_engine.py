"""
fear_of_god_engine.py — 敬畏神 / The Fear of the Lord（Michael Reeves《欢喜而战兢》Rejoice and Tremble）

给 know_god（神的属性·慈爱一面）配一条平衡轴：**敬畏**。里夫斯的核心洞见——
圣经所说「敬畏神」，绝大多数不是「怕神、躲着神」的**奴仆式惊惧**，而是儿女在所爱的父面前
**又惊叹又喜乐的战兢**——是爱到深处的敬畏，越爱越深、越亲越敬。

关键分辨：
  · **罪疚/奴仆式的怕**（sinful/servile fear）：把神当仇敌、怕祂的刑罚、想躲开祂。
    ——解药是福音：完全的爱把这种惧怕除去（约壹4:18），神在基督里不再定你的罪。
  · **儿女式/正确的敬畏**（filial fear）：在神的圣洁、荣美、伟大面前俯伏惊叹，却因祂的爱而喜乐亲近。
    ——这种敬畏不减损喜乐，反而是喜乐的高峰；越认识祂的爱，越深地敬畏祂。

两个失衡：
  (A) 只有「怕」没有「乐」→ 需要福音，认识神不是要压垮你的仇敌；
  (B) 只有「亲」没有「敬」→ 需要神圣洁荣美的异象，免得把神看小、看轻。

纯函数；确定性优先；内置危机词检测；AI 仅作可选增强。不定罪、不贴标签，
只把人领进「欢喜而战兢」——在被爱的确据里，重得对神的惊叹。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ── 与神关系的失衡状态 → 诊断 + 出路 + 经文 ──
STATES: List[Dict[str, Any]] = [
    {"key": "servile", "name": "怕神 / 觉得神随时要惩罚我",
     "kw": ["怕神", "惩罚", "神生气", "躲", "怕祂", "刑罚", "报复", "随时", "害怕神", "战战兢兢地怕"],
     "type": "servile",
     "diag": "你心里的「怕」是奴仆式的——把神当成随时要降罚的仇敌，于是只想躲开祂。里夫斯说：这不是圣经要的敬畏。",
     "way": "先听福音：在基督里，神不再是你的审判官，而是你的父。完全的爱把这种惧怕除去。神的圣洁不是要压垮你，"
            "而是把你从罪里洁净、抬举到祂面前。可以不再躲——被爱的儿女才能真正地敬畏。",
     "ref": "约壹4:18", "text": "爱里没有惧怕；爱既完全，就把惧怕除去。"},
    {"key": "casual", "name": "把神看得太随便 / 失去了敬畏与惊叹",
     "kw": ["随便", "无所谓", "麻木", "不当回事", "看小", "没有敬畏", "轻慢", "习以为常", "无感", "把神当哥们"],
     "type": "casual",
     "diag": "你与神很「熟」，却把祂看小了——亲近有余，敬畏不足。当神变得「理所当然」，惊叹就消失了。",
     "way": "你需要重见神的圣洁与荣美。默想祂的伟大：创造、圣洁、公义、那不可测度的荣耀——不是要吓你，"
            "而是要唤回那份「祂竟是这样一位神，而祂爱我」的战兢与惊叹。真亲密里一定有敬畏。",
     "ref": "赛6:3", "text": "圣哉，圣哉，圣哉，万军之耶和华！他的荣光充满全地。"},
    {"key": "anxious", "name": "怕自己不够好、怕达不到神的标准",
     "kw": ["不够好", "达不到", "标准", "怕做错", "怕失败", "完美", "怕让神失望", "永远不够", "苛求自己"],
     "type": "servile",
     "diag": "你的「敬畏」被扭成了一种表现焦虑——怕达不到、怕让神失望。这仍是奴仆式的怕，不是儿女的敬畏。",
     "way": "敬畏神不是「怕考砸」。你在基督里的地位不靠你的成绩。把这份怕换成惊叹：一位如此圣洁伟大的神，"
            "竟俯就、悦纳你这样的人——从这惊叹里生出的敬畏，是喜乐的，不是焦虑的。",
     "ref": "诗130:4", "text": "但在你有赦免之恩，要叫人敬畏你。"},
    {"key": "awe_seek", "name": "想更深地敬畏神 / 找回惊叹",
     "kw": ["更敬畏", "惊叹", "渴慕", "找回", "敬拜", "俯伏", "深经历", "看见神", "敬畏他", "更深"],
     "type": "healthy",
     "diag": "你渴望的正是圣经所说那「欢喜而战兢」的敬畏——这渴望本身就是恩典在动工。",
     "way": "去默想神的双重之美：祂的圣洁伟大（叫你俯伏），与祂在基督里的慈爱（叫你亲近）。让这两者一起烧——"
            "越认识祂的爱，越深地敬畏祂；越敬畏祂，喜乐越深。这不是矛盾，是敬拜的高峰。",
     "ref": "诗2:11", "text": "当存畏惧事奉耶和华，又当存战兢而快乐。"},
]

CRISIS_WORDS = [
    "自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死", "死了算了",
    "伤害自己", "撑不下去了", "没有意义活着", "想消失",
]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = (
    "我听见你正承受很重的痛。谈敬畏神之前，我想先温柔地说：如果你有伤害自己的念头，"
    "请现在就联系你信任的人或当地心理危机热线。神在基督里对你的心意不是刑罚，而是慈爱——你不必独自扛。"
    "（本功能不替代专业帮助。）"
)


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best: Optional[Dict[str, Any]] = None
    best_hits = 0
    for s in STATES:
        hits = sum(1 for k in s["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, s
    return best or (STATES[3] if len(STATES) > 3 else STATES[0])  # 默认落到「想更深敬畏」


def meta() -> Dict[str, Any]:
    return {
        "title": "敬畏神",
        "source": "Michael Reeves《欢喜而战兢》(Rejoice and Tremble)",
        "thesis": ("圣经的『敬畏神』不是奴仆怕主人的惊惧，而是儿女在所爱之父面前又惊叹又喜乐的战兢——"
                   "越认识祂的爱，越深地敬畏祂。"),
        "two_fears": [
            {"kind": "奴仆式的怕（要除去）", "note": "把神当仇敌、怕刑罚、想躲开——完全的爱把它除去（约壹4:18）。"},
            {"kind": "儿女式的敬畏（要长进）", "note": "在神的圣洁荣美前俯伏惊叹，却因祂的爱喜乐亲近（诗2:11）。"},
        ],
        "verse": "诗2:11",
        "principle": "「当存畏惧事奉耶和华，又当存战兢而快乐。」——敬畏与喜乐，本是一件事。",
    }


def analyze(state_text: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    state_text = (state_text or "").strip()
    crisis = _detect_crisis(state_text)
    picked = _pick(state_text)
    ftype = picked["type"]

    balance = {
        "servile": "你偏向「只有怕、没有乐」——需要的是福音：神在基督里不再定你的罪，你可以不再躲。",
        "casual": "你偏向「只有亲、没有敬」——需要的是神圣洁荣美的异象，免得把神看小。",
        "anxious": "你把敬畏错当成了表现焦虑——真敬畏生自「祂竟悦纳我」的惊叹，不是「怕考砸」。",
        "healthy": "你正走在「欢喜而战兢」的正路上——让敬畏与喜乐一起加深。",
    }.get(ftype, "")

    result: Dict[str, Any] = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "state": {"key": picked["key"], "name": picked["name"], "type": ftype},
        "diagnosis": picked["diag"],
        "balance_note": balance,
        "way_forward": picked["way"],
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "prayer": ("父啊，求你叫我认识你是谁——你的圣洁伟大叫我俯伏，你在基督里的慈爱叫我亲近。"
                   "除去我里面奴仆式的怕，也除去我对你的随便与麻木；求你把那『欢喜而战兢』的敬畏赐给我，"
                   "叫我越深地被你爱，就越深地敬畏你，越敬畏你，喜乐越满。"),
        "practices": [
            "默想神的双重之美：花几分钟，一面默想祂的圣洁伟大（赛6:3），一面默想祂在基督里的慈爱（罗8:15），"
            "让「俯伏」与「亲近」一起发生。",
            "把一次「怕」换成一次「惊叹」：当那份不安浮现，就改口说「这位如此伟大的神，竟然爱我、悦纳我」。",
        ],
        "summary": ("敬畏神不是躲着神发抖，而是在所爱之父面前又惊叹又喜乐的战兢。"
                    "越认识祂的爱，越深地敬畏祂——这是敬拜的高峰，不是喜乐的对立面。"),
        "closing": "「当存畏惧事奉耶和华，又当存战兢而快乐。」（诗2:11）",
        "ai_used": False,
    }

    if use_ai:
        enhanced = _ai_enhance(state_text, result, settings)
        if enhanced:
            result.update(enhanced)
            result["ai_used"] = True
    return result


def build_prompt(state_text: str, base: Dict[str, Any]) -> str:
    return (
        "你是一位温柔、以福音为中心的属灵陪伴者，熟悉 Michael Reeves《欢喜而战兢》(Rejoice and Tremble)。"
        "核心：圣经的敬畏神不是奴仆怕主人的惊惧，而是儿女在所爱之父前又惊叹又喜乐的战兢；"
        "奴仆式的怕要被福音除去（约壹4:18），儿女式的敬畏要因认识神的圣洁与慈爱而加深（诗2:11）。"
        "请针对用户与神关系的状态，分辨他偏向『只有怕』还是『只有亲』，把他领进『欢喜而战兢』，"
        "给经文、祷告与操练。中文，温暖不说教，绝不用刑罚恐吓，也不把神看小。\n"
        f"用户处境：{state_text}\n"
        "请输出 JSON：{\"diagnosis\":\"...\",\"way_forward\":\"...\",\"prayer\":\"一段可照着祷告的话\","
        "\"summary\":\"...\",\"closing\":\"一句经文\"}。"
    )


def _ai_enhance(state_text: str, base: Dict[str, Any], settings: Any) -> Optional[Dict[str, Any]]:
    prompt = build_prompt(state_text, base)
    raw = _call_ai(prompt, settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        out: Dict[str, Any] = {}
        for k in ("diagnosis", "way_forward", "prayer", "summary", "closing"):
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
    """敬畏神属于「敬拜 + 认识神 + 喜乐」。"""
    if result.get("crisis"):
        return (["worship", "know_god", "joy"], False, True, 2.0)
    return (["worship", "know_god", "joy"], True, True, 4.0)
