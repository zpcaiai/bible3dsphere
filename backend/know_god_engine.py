"""
know_god_engine.py — 认识神 / Knowing God（Packer《认识神》/ Tozer《认识至圣者》/
Reeves《活在三一神的爱中》）

按「神的属性」系统化编排的默想引擎，回答「神是谁」，并用一个具体的属性去迎见一个具体的
人性需要 / 恐惧。

与 `dew_engine`（每日按主题的灵修默想）刻意区隔：dew 做的是日更式的 TOPICAL 默想；
本引擎以 GOD'S ATTRIBUTES 为索引，答「神是谁」，把人从自我聚焦拉向神聚焦。

神学根基：
  Tozer：「我们思想神时心中所浮现的，是我们身上最重要的事。」
  Packer：认识神（与神相交、被神认识）胜过认识关于神的知识。
  Reeves：神的本体是父、子、灵之间爱的团契。

纯函数；确定性优先；内置危机词检测（need 可为自由文本）；AI 仅作可选增强，失败回退确定性结果。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ── 神的属性（系统化索引）：每个属性迎见一个具体的人性需要/恐惧 ──
ATTRIBUTES: List[Dict[str, str]] = [
    {"key": "holy", "name": "圣洁", "ref": "赛6:3", "text": "圣哉，圣哉，圣哉，万军之耶和华！",
     "meditation": "祂全然分别、纯全无瑕——祂的圣洁不是要压垮我，而是要洁净并抬举我。",
     "meets": "遇见我的随波与妥协",
     "kw": ["妥协", "随波", "随流", "同流", "沾染", "不洁", "污", "堕落", "松懈", "混"]},
    {"key": "sovereign", "name": "掌权", "ref": "但4:35", "text": "祂都凭自己的意旨行事……无人能拦住祂手。",
     "meditation": "祂随己意行，无人能拦阻——我失控的地方，正是祂仍然在掌权的地方。",
     "meets": "遇见我失控的焦虑",
     "kw": ["失控", "掌控", "焦虑", "无力", "混乱", "不确定", "抓不住", "崩", "局面", "无能为力"]},
    {"key": "faithful", "name": "信实", "ref": "哀3:22-23", "text": "祂的怜悯不致断绝……每早晨这都是新的。",
     "meditation": "祂的信实每早晨都是新的——即使我失信，祂仍守约，不会中途放手。",
     "meets": "遇见我被弃的恐惧",
     "kw": ["被弃", "抛弃", "背叛", "失信", "食言", "靠不住", "会不会走", "离开我", "不会长久", "失约"]},
    {"key": "good", "name": "良善", "ref": "诗34:8", "text": "你们要尝尝主恩的滋味，便知道祂是美善。",
     "meditation": "尝尝便知祂是美善——祂待我的心肠，比我以为的更良善。",
     "meets": "遇见我对神的怀疑",
     "kw": ["怀疑", "神真的", "祂真的好吗", "不信", "祂在乎吗", "沉默", "祂公平吗", "质疑", "祂听吗", "祂真的爱"]},
    {"key": "gracious", "name": "有恩典", "ref": "弗2:8", "text": "你们得救是本乎恩，也因着信……不是出于行为。",
     "meditation": "你得救是本乎恩——你不必赚取祂的接纳，那已是白白给你的礼物。",
     "meets": "遇见我赚取式的挣扎",
     "kw": ["赚", "配不配", "做得够", "表现", "达标", "努力换", "值得", "换取", "够好", "白费"]},
    {"key": "immutable", "name": "不改变", "ref": "玛3:6", "text": "因我耶和华是不改变的。",
     "meditation": "祂永不改变——当一切在我脚下摇动时，祂是那不动的磐石。",
     "meets": "遇见我的动荡不安",
     "kw": ["动荡", "变化", "不安", "摇", "无常", "起伏", "变来变去", "站不稳", "飘", "翻天覆地"]},
    {"key": "omnipresent", "name": "无所不在", "ref": "诗139:7-8", "text": "我往哪里去躲避你的灵？我往哪里逃躲避你的面？",
     "meditation": "我无处可躲开祂的同在——最孤独的角落，也已经有祂在等我。",
     "meets": "遇见我的孤独",
     "kw": ["孤独", "孤单", "没人", "一个人", "孤立", "无人", "空荡", "陪", "独自", "没人懂"]},
    {"key": "love", "name": "慈爱", "ref": "约一4:8", "text": "神就是爱。",
     "meditation": "神就是爱——不是祂勉强去爱，而是爱是祂的本体；祂看你，眼里满是爱。",
     "meets": "遇见我的不配感",
     "kw": ["不配", "不值得", "羞", "自卑", "糟糕", "没价值", "厌恶自己", "丑", "差劲", "自我厌弃"]},
    {"key": "patient", "name": "忍耐", "ref": "彼后3:9", "text": "乃是宽容你们，不愿有一人沉沦。",
     "meditation": "祂宽容、忍耐你——祂没有厌烦你，祂给你的时间，是恩典不是催促。",
     "meets": "遇见我的自我定罪",
     "kw": ["定罪", "自责", "又failed", "又跌倒", "老毛病", "反复", "内疚", "羞愧", "对不起神", "又犯"]},
    {"key": "triune_love", "name": "三一之爱", "ref": "约17:24", "text": "因为创立世界以前，你已经爱我了。",
     "meditation": "创世以前你已经爱我——你被卷入的，是父子灵那从永恒就有、要分给你的爱。",
     "meets": "遇见我「不被爱」的谎言",
     "kw": ["不被爱", "没人爱", "没有人爱我", "被讨厌", "多余", "没人要", "被嫌弃", "不重要", "隐形", "没人在乎"]},
]
ATTRIBUTE_INDEX = {a["key"]: a for a in ATTRIBUTES}

TOZER_QUOTE = "我们思想神时心中所浮现的，是我们身上最重要的事。—— A. W. Tozer《认识至圣者》"

CRISIS_WORDS = [
    "自杀", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死", "死了算了",
    "伤害自己", "撑不下去了", "没有意义活着", "想消失",
]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = (
    "我听见你正承受很重的痛。在我们一起仰望神之前，我想先温柔地说：如果你有伤害自己的念头，"
    "请现在就联系你信任的人，或当地的心理危机热线——你值得有人此刻真实地陪着你。神爱你，"
    "你不必独自扛。（本功能不替代专业帮助。）"
)


def _match_attribute(need: str) -> Dict[str, str]:
    """把所感的需要/恐惧，确定性地映射到迎见它的那个属性。"""
    t = need or ""
    best: Optional[Dict[str, str]] = None
    best_hits = 0
    for a in ATTRIBUTES:
        hits = sum(1 for k in a["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, a
    if best is None:
        # 默认引向「神就是爱」——最根本的迎见
        return ATTRIBUTE_INDEX["love"]
    return best


def _package(attr: Dict[str, str]) -> Dict[str, Any]:
    """把一个属性组装成默想包：从自我聚焦拉向神聚焦 + 经文 + 2 分钟定睛仰望操练。"""
    meditation = (
        "把目光从自己身上挪开一会儿，抬起来看神——" + attr["name"] + "的神。"
        + attr["meditation"] + "（" + attr["ref"] + "：" + attr["text"] + "）"
        "你不是先改变自己才够格来看祂；正相反，是仰望祂，才把你渐渐改变。"
    )
    practice = (
        "【2 分钟定睛仰望】"
        "① 静下来，深呼吸三次，把手中所抓的暂放下。"
        "② 慢慢读一遍这句经文：「" + attr["text"] + "」（" + attr["ref"] + "），"
        "读三遍，每一遍都更慢。"
        "③ 不求什么，只说一句：「神啊，你是" + attr["name"] + "的，我此刻单单仰望你。」"
        "让这一个关于神的真理，比你此刻的感受更大。"
    )
    return {
        "attribute": {"key": attr["key"], "name": attr["name"], "meets": attr["meets"]},
        "scripture": {"ref": attr["ref"], "text": attr["text"]},
        "meditation": meditation,
        "practice": practice,
        "closing": "「改变你的，不是更多关于神的信息，而是仰望神自己。」",
    }


def meta() -> Dict[str, Any]:
    """Tozer 引言 + 十个属性 + 核心原则（供前端展示）。"""
    return {
        "tozer_quote": TOZER_QUOTE,
        "attributes": [
            {"key": a["key"], "name": a["name"], "ref": a["ref"], "text": a["text"],
             "meditation": a["meditation"], "meets": a["meets"]}
            for a in ATTRIBUTES
        ],
        "principle": "改变你的，不是更多关于神的信息，而是仰望神自己。",
        "foundation": ("Packer：认识神——与神相交、被神认识——胜过认识关于神的知识；"
                       "Reeves：神的本体是父、子、灵之间爱的团契。"),
    }


def meditate(need: Optional[str] = None, attribute: Optional[str] = None,
             *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    """给定 attribute key 则直接返回该属性的默想包；否则按所感的 need/fear 映射到迎见它的属性。"""
    need = (need or "").strip()
    crisis = _detect_crisis(need)

    if attribute and attribute in ATTRIBUTE_INDEX:
        attr = ATTRIBUTE_INDEX[attribute]
        entry = "chosen"
    else:
        attr = _match_attribute(need)
        entry = "matched" if need else "default"

    pkg = _package(attr)
    result: Dict[str, Any] = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "entry": entry,
        "need": need,
        "tozer_quote": TOZER_QUOTE,
        **pkg,
        "summary": ("你带来的这份需要，神用祂的" + attr["name"] + "来迎见它（" + attr["meets"] + "）。"
                    "默想的方向不是往里看自己，而是往上看祂——祂是谁，决定了我能不能安息。"),
        "ai_used": False,
    }

    if use_ai:
        enhanced = _ai_enhance(need, attr, result, settings)
        if enhanced:
            result.update(enhanced)
            result["ai_used"] = True
    return result


def build_prompt(need: str, attr: Dict[str, str], base: Dict[str, Any]) -> str:
    return (
        "你是一位温柔、以福音为中心的属灵陪伴者，熟悉 J. I. Packer《认识神》、A. W. Tozer"
        "《认识至圣者》与 Michael Reeves《活在三一神的爱中》。你的任务不是给更多关于神的信息，"
        "而是帮助用户仰望神自己，把目光从自我聚焦拉向神聚焦。此刻默想的属性是「"
        + attr["name"] + "」（" + attr["ref"] + "：" + attr["text"] + "），它迎见的是"
        + attr["meets"] + "。请写一段简短、温暖、不说教的默想，中文，绝不定罪、不贴标签，"
        "带人安息在神的性情里。\n"
        f"用户所感的需要 / 恐惧：{need or '（未特别说明）'}\n"
        "请输出 JSON：{\"meditation\":\"一段把人从自我拉向神的默想\",\"summary\":\"...\","
        "\"practice\":\"一个 2 分钟的定睛仰望操练\"}。"
    )


def _ai_enhance(need: str, attr: Dict[str, str], base: Dict[str, Any], settings: Any) -> Optional[Dict[str, Any]]:
    """可选 AI 增强：任何失败都回退（返回 None）。"""
    prompt = build_prompt(need, attr, base)
    raw = _call_ai(prompt, settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        out: Dict[str, Any] = {}
        for k in ("meditation", "summary", "practice"):
            if data.get(k):
                out[k] = str(data[k])
        return out or None
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
    """回流 formation：认识神属于「敬拜 + 盼望 + 成长」。"""
    if result.get("crisis"):
        return (["worship", "hope", "growth"], False, True, 2.0)
    return (["worship", "hope", "growth"], True, True, 5.0)
