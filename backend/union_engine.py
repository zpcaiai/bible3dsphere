"""
union_engine.py — 与基督联合·身份 / Union with Christ（因信与基督联合）

这是把一切属灵诊断收束到「身份」的脊椎：信徒「在基督里」，祂的死、复活、义、儿子的名分、
产业，都因信归于信徒。身份的根基不在**表现**，而在「在基督里我是谁」。

当人被某个「我是……」的谎言击中（我一无是处 / 我不被爱 / 我定了罪 / 我是个失败者……），
本引擎不是去堆动机，而是把那句被感受到的谎言，换成一句「在基督里」的真理 + 一处经文 +
一个「算你自己……（罗6:11）」的操练。

纯函数；确定性优先；内置危机词检测；AI 仅作可选增强，失败回退确定性结果。
不定罪、不贴标签，只把人的目光从表现，转回「在基督里我已经是谁」。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ── 「在基督里」：谎言 → 联合真理 + 经文 ──
IN_CHRIST: List[Dict[str, str]] = [
    {"key": "worthless",
     "lie": "我一无是处 / 我没有价值",
     "truth": "在基督里，我是新造的人——旧事已过，都变成新的了。我的价值不在于我做到了什么，而在于神看我为宝贵。",
     "ref": "林后5:17", "text": "若有人在基督里，他就是新造的人，旧事已过，都变成新的了。",
     "kw": ["一无是处", "没有价值", "没价值", "没用", "废物", "无用", "毫无意义", "一文不值", "不值得", "多余"]},
    {"key": "unloved",
     "lie": "我不被爱 / 没有人真的爱我",
     "truth": "在基督里，我是神所爱、在爱子里蒙悦纳的儿女。神的爱不是我赚来的，是祂在基督里白白赐下的。",
     "ref": "弗1:6", "text": "使祂荣耀的恩典得着称赞；这恩典是祂在爱子里所赐给我们的。",
     "kw": ["不被爱", "没人爱", "没有人爱", "不值得被爱", "没人在乎", "孤单", "被冷落", "没人要", "不被接纳"]},
    {"key": "condemned",
     "lie": "我定了罪 / 我无可救药",
     "truth": "在基督里，就不定罪了。基督已经担当了我一切的罪，神看我是在祂儿子里被赦免、被接纳的。",
     "ref": "罗8:1", "text": "如今，那些在基督耶稣里的就不定罪了。",
     "kw": ["定了罪", "定罪", "无可救药", "没救", "该死", "罪该", "神一定恨", "不可饶恕", "无法被赦免", "永远的污点"]},
    {"key": "failure",
     "lie": "我是个失败者",
     "truth": "在基督里，我与祂一同复活、一同坐在天上。我的身份不由我的失败定义，而由祂的得胜定义。",
     "ref": "弗2:6", "text": "祂又叫我们与基督耶稣一同复活，一同坐在天上。",
     "kw": ["失败者", "失败", "一败涂地", "做什么都失败", "彻底搞砸", "一事无成", "废掉了", "又搞砸了", "无能"]},
    {"key": "insecure",
     "lie": "我会被弃绝 / 我不安全",
     "truth": "在基督里，没有什么能叫我与神的爱隔绝。祂抓着我，比我抓着祂更牢；我在祂手里是安稳的。",
     "ref": "罗8:38-39", "text": "因为我深信……都不能叫我们与神的爱隔绝；这爱是在我们的主基督耶稣里的。",
     "kw": ["被弃绝", "被抛弃", "会被丢下", "不安全", "会失去", "怕被离开", "没有保障", "随时会被放弃", "不牢靠", "会被神放弃"]},
    {"key": "earning",
     "lie": "我必须靠表现赚取接纳",
     "truth": "在基督里，我因祂的义被神称义，不是靠我的行为。接纳是恩典的礼物，不是努力的工资。",
     "ref": "腓3:9", "text": "并且得以在祂里面，不是有自己因律法而得的义，乃是有信基督的义，就是因信神而来的义。",
     "kw": ["靠表现", "赚取", "必须做到", "不够好", "要够好", "达不到", "配得", "才配", "努力换来", "要证明自己", "赚来的爱", "达不到标准"]},
    {"key": "alone",
     "lie": "我很孤单 / 只剩我一个人",
     "truth": "在基督里，我住在祂里面，祂也住在我里面。我从来不是独自面对——离了祂我不能做什么，连于祂我却结果子。",
     "ref": "约15:5", "text": "我是葡萄树，你们是枝子。常在我里面的，我也常在他里面，这人就多结果子；因为离了我，你们就不能做什么。",
     "kw": ["很孤单", "孤单", "只剩我", "一个人", "独自", "没有人陪", "孤立无援", "没有依靠", "孤零零"]},
]
IN_CHRIST_INDEX = {t["key"]: t for t in IN_CHRIST}

# ── 收束一切诊断的核心原则 ──
PRINCIPLE = "你不是靠表现成为某种人；你已经在基督里『是』那样的人，现在学着照着信而活。"
RECKON = "罗6:11 这样，你们向罪也当看自己是死的；向神，在基督耶稣里，却当看自己是活的。"

# ── 一般性回退（谎言不明确时） ──
GENERAL = {
    "key": "general",
    "lie": "我对自己的感觉，盖过了神对我的宣告",
    "truth": "无论此刻你怎么感觉自己，在基督里，你是神所爱、被称义、被接纳、有产业的儿女。你的身份不在表现里，"
             "在「在基督里」这句话里。",
    "ref": "加2:20", "text": "现在活着的不再是我，乃是基督在我里面活着；并且我如今在肉身活着，是因信神的儿子而活。",
}


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


def _match_lie(struggle: str) -> Dict[str, Any]:
    """确定性关键词匹配：把挣扎里被感受到的『身份谎言』对上一句联合真理；不明则回退一般性。"""
    t = struggle or ""
    best = None
    best_hits = 0
    for item in IN_CHRIST:
        hits = sum(1 for k in item["kw"] if k in t)
        if hits > best_hits:
            best_hits = hits
            best = item
    if best is None:
        return dict(GENERAL)
    return best


def meta() -> Dict[str, Any]:
    """七组「在基督里」的谎言→真理→经文，加上收束原则与罗6:11 的算账。"""
    return {
        "truths": [
            {"key": t["key"], "lie": t["lie"], "truth": t["truth"], "ref": t["ref"], "text": t["text"]}
            for t in IN_CHRIST
        ],
        "principle": PRINCIPLE,
        "reckon": RECKON,
    }


def assess(struggle: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    """把挣扎里被感受到的身份谎言，换成一句「在基督里」的真理 + 经文 + 罗6:11 算账 + 一句确据。"""
    struggle = (struggle or "").strip()
    crisis = _detect_crisis(struggle)
    item = _match_lie(struggle)
    matched = item.get("key") != "general"

    reckon_practice = (
        "算你自己（罗6:11）：请你现在，把神的宣告当作比你的感觉更真的事实，对自己说——"
        "「因着基督，我" + _first_person(item["key"]) + "。」不是因为我感觉如此，而是因为神说如此。"
        "每当那句谎言回来，就回到这句真理，照着信而活，而不是照着感觉而活。"
    )
    assurance = (
        "你不必先感觉配得，才被神接纳；你已经在基督里被接纳了，感觉会慢慢跟上真理。"
    )

    result: Dict[str, Any] = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "matched": matched,
        "lie": item["lie"],
        "truth": item["truth"],
        "identity_key": item.get("key", "general"),
        "scripture": {"ref": item["ref"], "text": item["text"]},
        "principle": PRINCIPLE,
        "reckon": RECKON,
        "practice": reckon_practice,
        "assurance": assurance,
        "summary": "你的身份不在表现里——在「在基督里」这句话里。" + item["truth"].split("。")[0] + "。",
        "ai_used": False,
    }
    if crisis:
        result["assurance"] = CRISIS_NOTE + "\n\n" + result["assurance"]

    if use_ai:
        enhanced = _ai_enhance(struggle, result, settings)
        if enhanced:
            result.update(enhanced)
            result["ai_used"] = True
    return result


def _first_person(key: str) -> str:
    """把联合真理凝成一句第一人称的『算账』短句。"""
    return {
        "worthless": "是新造的人，是神眼中宝贵的",
        "unloved": "是神所爱、被祂悦纳的儿女",
        "condemned": "在基督耶稣里就不被定罪了",
        "failure": "与基督一同复活、一同坐在天上",
        "insecure": "在神的爱里是安稳的，没有什么能叫我与祂隔绝",
        "earning": "因基督的义被称义，不靠我的行为",
        "alone": "住在基督里、基督也住在我里面，从不孤单",
        "general": "是神所爱、被称义、被接纳、有产业的儿女",
    }.get(key, "是神所爱、被接纳的儿女")


def build_prompt(struggle: str, base: Dict[str, Any]) -> str:
    return (
        "你是一位温柔、以福音为中心的属灵陪伴者，深知信徒『与基督联合』——因信在基督里，祂的死、复活、义、"
        "儿子的名分与产业都归于信徒；身份的根基不在表现，而在「在基督里我是谁」。请把用户挣扎里被感受到的"
        "『身份谎言』，温柔地换成一句「在基督里」的真理，中文，温暖不说教，不定罪、不贴标签、"
        "不说『你信心不够』之类的话。要引用并解释神的宣告如何比感觉更真实，并鼓励用户照着罗6:11「算自己……」而活。\n"
        f"当前确定性判断——谎言：{base.get('lie')}；联合真理：{base.get('truth')}；经文：{base.get('scripture', {}).get('ref')}。\n"
        f"用户挣扎：{struggle}\n"
        "请输出 JSON：{\"truth\":\"在基督里的真理（含解释，2-4句）\",\"practice\":\"一个『算你自己…（罗6:11）』的操练\","
        "\"assurance\":\"一句确据\",\"summary\":\"一句收束\"}。"
    )


def _ai_enhance(struggle: str, base: Dict[str, Any], settings: Any) -> Optional[Dict[str, Any]]:
    """可选 AI 增强：任何失败都回退（返回 None）。"""
    prompt = build_prompt(struggle, base)
    raw = _call_ai(prompt, settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        out: Dict[str, Any] = {}
        for k in ("truth", "practice", "assurance", "summary"):
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
    """回流 formation：与基督联合把诊断收束到身份——标注 identity/hope/growth。"""
    if result.get("crisis"):
        return (["identity", "hope", "growth"], False, True, 2.0)
    return (["identity", "hope", "growth"], True, True, 4.0)
