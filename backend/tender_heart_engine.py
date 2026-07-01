"""
tender_heart_engine.py — 温柔谦卑 / Gentle and Lowly（Dane Ortlund《Gentle and Lowly》）

针对「羞愧/自我定罪」的谎言，宣告基督内心最深处对着软弱、失败、羞愧之人的姿态。
本引擎的独一件事：接住一句「我搞砸了 / 我离神太远 / 我这样祂不会要我」，
温柔地把说话者从谎言里领回到基督的心那里。

Ortlund（承 Thomas Goodwin、Richard Sibbes；本于太11:29「我心里柔和谦卑」）：
基督对着软弱、羞愧、失败的人，不是勉强的容忍，更不是嫌弃与疏远，
而是被吸引、动了慈心。祂「不折断压伤的芦苇，不吹灭将残的灯火」。
罪与苦难不会把祂推开，反而正是祂怜悯所朝向的。

纯函数；确定性优先；内置危机词检测；AI 仅作可选增强，失败回退确定性结果。
不定罪、不贴标签，只把人领回基督张开的手。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ── 羞愧的谎言 → 基督之心的真理 + 经文 ──
LIES_TO_TRUTH: List[Dict[str, Any]] = [
    {"key": "disappointed",
     "lie": "我搞砸了，神对我失望透了",
     "kw": ["搞砸", "失望", "让神失望", "让祂失望", "又失败", "糟透", "毁了", "闯祸", "又跌倒"],
     "truth": "基督向悔改的人涌流的是怜悯，不是嫌弃。你还在远处，父已经动了慈心跑向你。",
     "ref": "路15:20", "text": "相离还远，他父亲看见，就动了慈心，跑去抱着他的颈项，连连与他亲嘴。"},
    {"key": "weak",
     "lie": "我这么软弱，祂一定厌烦我",
     "kw": ["软弱", "厌烦", "嫌弃", "没用", "废", "撑不住", "又犯", "反复", "老毛病", "改不掉"],
     "truth": "祂不折断压伤的芦苇，不吹灭将残的灯火。你的软弱不是祂转身的理由，正是祂扶持的地方。",
     "ref": "赛42:3", "text": "压伤的芦苇，他不折断；将残的灯火，他不吹灭。"},
    {"key": "far",
     "lie": "我离神太远了",
     "kw": ["离神太远", "离神很远", "回不去", "太远", "回不来", "断了", "冷淡太久", "很久没", "浪子"],
     "truth": "你以为的「太远」，正是祂来寻找的地方。祂来，本是为寻找、拯救失丧的人。",
     "ref": "路19:10", "text": "人子来，为要寻找、拯救失丧的人。"},
    {"key": "unworthy",
     "lie": "我不配被爱",
     "kw": ["不配", "不值得", "配不上", "没资格", "凭什么爱我", "肮脏", "污秽", "恶心", "羞耻"],
     "truth": "祂爱你，不是因为你配，而是因为祂本是爱。当你还是罪人时，基督的爱已经证明在你身上。",
     "ref": "罗5:8", "text": "惟有基督在我们还作罪人的时候为我们死，神的爱就在此向我们显明了。"},
    {"key": "fix_first",
     "lie": "我必须先变好祂才接纳我",
     "kw": ["先变好", "先改好", "配得上", "够好", "先干净", "达标", "先悔改够", "先做到", "先够格"],
     "truth": "你不必先修好自己再来。正当我们还软弱、还无力的时候，基督就为我们死了——恩典在前，改变在后。",
     "ref": "罗5:6", "text": "因我们还软弱的时候，基督就按所定的日期为罪人死。"},
]
LIE_INDEX = {d["key"]: d for d in LIES_TO_TRUTH}

CRISIS_WORDS = [
    "自杀", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死", "死了算了",
    "伤害自己", "撑不下去了", "没有意义活着", "想消失",
]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = (
    "我听见你正承受很重的痛。在我们一起向神倾诉之前，我想先温柔地说：如果你有伤害自己的念头，"
    "请现在就联系你信任的人，或当地的心理危机热线——你值得有人此刻真实地陪着你。神爱你，"
    "你不必独自扛。（本功能不替代专业帮助。）"
)


def _pick_lie(text: str) -> Dict[str, Any]:
    """确定性关键词匹配，选出最贴近这个人处境的谎言；无匹配则回退到最普遍的一条。"""
    t = text or ""
    best: Optional[Dict[str, Any]] = None
    best_hits = 0
    for d in LIES_TO_TRUTH:
        hits = sum(1 for k in d["kw"] if k in t)
        if hits > best_hits:
            best_hits = hits
            best = d
    if best is None:
        best = LIE_INDEX["unworthy"]  # 最普遍的羞愧根：不配被爱
    return best


def meta() -> Dict[str, Any]:
    """基督的心 + 谎言→真理对照表 + 邀请（供前端展示）。"""
    return {
        "heart_of_christ": "祂心里柔和谦卑（太11:29）——祂对你的默认姿态不是皱眉，是张开的手。",
        "lies_to_truth": [
            {"key": d["key"], "lie": d["lie"], "truth": d["truth"],
             "scripture": {"ref": d["ref"], "text": d["text"]}}
            for d in LIES_TO_TRUTH
        ],
        "invitation": "太11:28 凡劳苦担重担的，可以到我这里来。",
        "principle": "基督最深的心，是对着软弱、羞愧、失败之人的怜悯——罪与苦难不把祂推开，"
                     "反倒是祂慈心所朝向的。",
    }


def comfort(text: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    """接住一句羞愧/自我定罪的话，把说话者温柔地领回基督的心（确定性；可选 AI 增强）。"""
    text = (text or "").strip()
    crisis = _detect_crisis(text)
    chosen = _pick_lie(text)

    # 确定性地反映基督对着「这个人」的温柔姿态
    posture = (
        "我听见你心里那句「" + chosen["lie"] + "」。我想轻轻告诉你：那不是基督看你的眼光。"
        "祂心里柔和谦卑，此刻朝着你的，不是皱眉，不是叹气，而是动了慈心、张开的手。"
    )
    assurance = "你现在不需要先够好、先站稳——只要把自己交给祂张开的手，让祂接住你。"

    parts: List[str] = []
    if crisis:
        parts.append(CRISIS_NOTE)
    parts.append(posture)
    parts.append(chosen["truth"] + "（" + chosen["ref"] + "：" + chosen["text"] + "）")
    parts.append(assurance)

    result: Dict[str, Any] = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "lie": chosen["lie"],
        "truth": chosen["truth"],
        "scripture": {"ref": chosen["ref"], "text": chosen["text"]},
        "posture": posture,
        "assurance": assurance,
        "message": "\n\n".join(parts),
        "invitation": "凡劳苦担重担的，可以到我这里来，我就使你们得安息。（太11:28）",
        "ai_used": False,
    }

    if use_ai:
        enhanced = _ai_enhance(text, result, settings)
        if enhanced:
            result.update(enhanced)
            result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return (
        "你是一位温柔、以福音为中心的属灵陪伴者，熟悉 Dane Ortlund《Gentle and Lowly 温柔谦卑》"
        "所讲的基督之心（本于太11:29「我心里柔和谦卑」，承 Thomas Goodwin、Richard Sibbes）："
        "基督对着软弱、羞愧、失败的人，不是勉强的容忍，更不是嫌弃疏远，而是被吸引、动了慈心；"
        "祂不折断压伤的芦苇，不吹灭将残的灯火。请接住用户那句羞愧/自我定罪的话，"
        "温柔地把他领回基督的心那里，中文，温暖不说教，绝不定罪、不贴标签、"
        "不说『你信心不够/你要更努力』之类的话。\n"
        f"用户所信的谎言（系统判断）：{base.get('lie', '')}\n用户倾诉：{text}\n"
        "请输出 JSON：{\"posture\":\"反映基督此刻朝向他的温柔姿态\","
        "\"truth\":\"以基督的心对治那谎言的真理\",\"assurance\":\"一句领受的邀请\"}。"
    )


def _ai_enhance(text: str, base: Dict[str, Any], settings: Any) -> Optional[Dict[str, Any]]:
    """可选 AI 增强：任何失败都回退（返回 None）。"""
    prompt = build_prompt(text, base)
    raw = _call_ai(prompt, settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        out: Dict[str, Any] = {}
        posture = str(data["posture"]) if data.get("posture") else base["posture"]
        truth = str(data["truth"]) if data.get("truth") else base["truth"]
        assurance = str(data["assurance"]) if data.get("assurance") else base["assurance"]
        out["posture"] = posture
        out["truth"] = truth
        out["assurance"] = assurance
        parts: List[str] = []
        if base.get("crisis"):
            parts.append(CRISIS_NOTE)
        parts.append(posture)
        parts.append(truth + "（" + base["scripture"]["ref"] + "：" + base["scripture"]["text"] + "）")
        parts.append(assurance)
        out["message"] = "\n\n".join(parts)
        return out
    except Exception:
        return None


def _call_ai(prompt: str, settings: Any) -> Optional[str]:
    """尽力调用既有 provider；不可用则返回 None（引擎保持零硬依赖）。"""
    for modname, fn in (("waiting_engine", "call_ai_provider"), ("llm_provider", "call_llm")):
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
    """回流 formation：温柔谦卑对治羞愧谎言，重塑身份与盼望。"""
    if result.get("crisis"):
        return (["identity", "hope", "growth"], False, True, 2.0)
    return (["identity", "hope", "growth"], True, True, 5.0)
