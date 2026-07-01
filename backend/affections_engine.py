"""
affections_engine.py — 宗教情感真伪辨（Jonathan Edwards《Religious Affections》）

补足 gap 分析所缺的「情感辨识」框架。爱德华兹的核心命题：**真恩典的凭据，不在于宗教
情感有多强、多热烈、多频繁，而在于它的「本质」——它从哪里来、往哪里去、结什么果。**
强烈的情感既非有恩典的证据，也非没有恩典的证据；真正可靠的记号，是情感的性质与果子。

与 `checkup`／`confession` 等「诊断/认罪」引擎互补而不重叠：本引擎只做一件事——
拿爱德华兹归纳的「不可靠的迹象」与「可靠的记号」当一面温柔的镜子，帮用户看见自己的
属灵情感扎根在哪里；**不是给属灵状态打分，也不下判断**。

纯函数；确定性优先；自评为主（可选自由文本时才做轻量危机词检测）；AI 仅作可选增强，
失败回退确定性结果。不定罪、不贴标签，只帮助人把情感重新对准基督、导向信靠。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ── 「既非证据、也非反证」的迹象（NO_SIGNS）──
# 爱德华兹提醒：以下这些都**不能**用来判断一个人有没有真恩典——请用户不要拿它们
# 给自己定案（有，不代表得救；没有，也不代表失丧）。
NO_SIGNS: List[str] = [
    "情感来得很强烈、很激动",
    "能滔滔不绝地谈论属灵的事",
    "有大量的宗教活动，外表很热心",
    "常有经文自动浮现在心头",
    "情感来得很突然，或次序分明、条理清楚",
    "会开口赞美神、口里显得火热",
    "别人都觉得你很属灵、很敬虔",
]

# ── 爱德华兹的「可靠记号」（TRUE_SIGNS）——指向恩典，作温柔的镜子，非判决 ──
# 每一条给一个 key（供 ratings 自评键），一句简述，一处经文。
TRUE_SIGNS: List[Dict[str, Any]] = [
    {"key": "beauty",   "name": "因神本身的荣美而爱慕祂",
     "desc": "不只因祂对我有用、能给我好处，而是因祂本身的圣洁与荣美就值得爱。",
     "ref": "约一4:19", "text": "我们爱，因为神先爱我们。"},
    {"key": "humility", "name": "福音性的谦卑",
     "desc": "越靠近神，越看见自己的小与不配——不是自我厌恶，是在恩典里的诚实。",
     "ref": "赛6:5", "text": "祸哉！我灭亡了！因为我是嘴唇不洁的人……又因我眼见大君王万军之耶和华。"},
    {"key": "renewal",  "name": "心性的更新改变",
     "desc": "不只是一时的情绪，而是整个人被更新——成为新造的人，方向变了。",
     "ref": "林后5:17", "text": "若有人在基督里，他就是新造的人，旧事已过，都变成新的了。"},
    {"key": "christlike", "name": "基督的性情",
     "desc": "生出温柔、怜悯、饶恕——像基督那样待人，而非只在情绪上被感动。",
     "ref": "加5:22-23", "text": "圣灵所结的果子，就是仁爱、喜乐、和平、忍耐、恩慈、良善、信实、温柔、节制。"},
    {"key": "hunger",   "name": "越发恨恶罪、饥渴慕义",
     "desc": "对罪越来越敏感、越发想远离，同时越发渴慕神与祂的义。",
     "ref": "太5:6", "text": "饥渴慕义的人有福了！因为他们必得饱足。"},
    {"key": "fruit",    "name": "结在生活里的果子",
     "desc": "真情感落地成实践——在日常的选择与行为里结果子，不只停在感动。",
     "ref": "约15:8", "text": "你们多结果子，我父就因此得荣耀，你们也就是我的门徒了。"},
]
TRUE_SIGN_INDEX = {s["key"]: s for s in TRUE_SIGNS}

# ── 危机词（自 lament_engine 复制；仅当用户填了自由文本 text 时轻量检测）──
CRISIS_WORDS = [
    "自杀", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死", "死了算了",
    "伤害自己", "撑不下去了", "没有意义活着", "想消失",
]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = (
    "我听见你正承受很重的痛。在我们一起看这些属灵的记号之前，我想先温柔地说：如果你有伤害自己的念头，"
    "请现在就联系你信任的人，或当地的心理危机热线——你值得有人此刻真实地陪着你。神爱你，"
    "你不必独自扛。（本功能不替代专业帮助。）"
)


def meta() -> Dict[str, Any]:
    """不可靠迹象 + 可靠记号 + 总纲原则（供前端展示）。"""
    return {
        "no_signs": NO_SIGNS,
        "true_signs": TRUE_SIGNS,
        "principle": "衡量属灵情感的，不是它有多强，而是它从哪里来、往哪里去、结什么果。",
    }


def _bucket(v: float) -> str:
    """把 0..1 自评分档：strong / growing / seed。"""
    if v >= 0.66:
        return "strong"
    if v >= 0.34:
        return "growing"
    return "seed"


def assess(ratings: Dict[str, float], text: Optional[str] = None,
           *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    """
    拿爱德华兹的六个可靠记号当一面温柔的镜子（确定性；可选 AI 增强）。
    ratings：以 true_sign 的 key 为键、0..1 的自评分。**不是打分或判断**，
    只帮用户看见自己的属灵情感目前扎根在哪、可以求神在哪里加深。
    """
    ratings = ratings or {}
    text = (text or "").strip()
    crisis = _detect_crisis(text) if text else False

    # 归一化 + 分档
    marks: List[Dict[str, Any]] = []
    for s in TRUE_SIGNS:
        raw = ratings.get(s["key"], None)
        try:
            v = float(raw) if raw is not None else 0.0
        except Exception:
            v = 0.0
        v = max(0.0, min(1.0, v))
        marks.append({
            "key": s["key"], "name": s["name"], "value": round(v, 3),
            "bucket": _bucket(v), "rated": raw is not None,
            "scripture": {"ref": s["ref"], "text": s["text"]},
        })

    strong = [m for m in marks if m["bucket"] == "strong"]
    growing = [m for m in marks if m["bucket"] == "growing"]

    # 取自评最低的 1-2 项，作为「可以求神加深的方向」（配经文）
    rated = [m for m in marks if m["rated"]] or marks
    lowest = sorted(rated, key=lambda m: m["value"])[:2]
    deepen = [{
        "key": m["key"], "name": m["name"],
        "invitation": "可以在祷告里，求神在「" + m["name"] + "」上加深你——不是为了达标，而是想更认识祂。",
        "scripture": m["scripture"],
    } for m in lowest]

    # 温柔的镜子式反馈（明确声明：不是打分、不下判断）
    if strong:
        mirror = ("你在「" + "、".join(m["name"] for m in strong[:3]) +
                  "」上似乎感到较扎实——这不是给你打分，只是帮你看见：你的情感正朝着基督的方向长。")
    elif growing:
        mirror = ("你在「" + "、".join(m["name"] for m in growing[:3]) +
                  "」上正在生长中——记号不必满分才算真，方向对了就是恩典在动工。")
    else:
        mirror = ("此刻你或许觉得这些记号都还很微小——没关系，这不是判决。"
                  "连一点想更爱神的心，本身就是圣灵在你里面动工的迹象。")

    encouragement = (
        "请记得爱德华兹的提醒：真情感的凭据不在乎它有多强，而在乎它往哪里去、结什么果。"
        "你不必靠情绪的高低来确认神爱你——祂的爱在基督里已经稳稳定住了。"
    )

    result: Dict[str, Any] = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "disclaimer": "这不是给你的属灵状态打分或下判断，只帮助你看见你的情感扎根在哪里、可以往哪里更深。",
        "principle": "衡量属灵情感的，不是它有多强，而是它从哪里来、往哪里去、结什么果。",
        "marks": marks,
        "strong": [m["name"] for m in strong],
        "growing": [m["name"] for m in growing],
        "mirror": mirror,
        "deepen": deepen,
        "no_signs_reassurance": {
            "note": "以下这些既不是有恩典的证据，也不是没有恩典的证据——请不要拿它们给自己定案：",
            "items": NO_SIGNS,
        },
        "encouragement": encouragement,
        "closing": "「我们爱，因为神先爱我们。」（约一4:19）",
        "ai_used": False,
    }

    if use_ai:
        enhanced = _ai_enhance(ratings, text, result, settings)
        if enhanced:
            result.update(enhanced)
            result["ai_used"] = True
    return result


def build_prompt(ratings: Dict[str, float], text: Optional[str], base: Dict[str, Any]) -> str:
    marks_desc = "；".join(
        m["name"] + "=" + m["bucket"] for m in base.get("marks", [])
    )
    return (
        "你是一位温柔、以福音为中心的属灵陪伴者，熟悉 Jonathan Edwards《Religious Affections》"
        "所讲的辨识：真恩典的凭据不在乎情感多强，而在乎其本质与果子。请用这六个可靠记号"
        "（因神荣美而爱、福音性谦卑、心性更新、基督性情、恨恶罪饥渴慕义、结出果子）作一面"
        "温柔的镜子，中文，温暖不说教，**不定罪、不贴标签、不给属灵状态打分或下判断**，"
        "不说『你信心不够』之类的话。也要提醒用户：情感强烈、能言善道、宗教热心等，既非证据、"
        "也非反证，不要拿来给自己定案。\n"
        f"用户各记号自评分档：{marks_desc}\n用户补充：{text or '（未特别说明）'}\n"
        "请输出 JSON：{\"mirror\":\"温柔的镜子式反馈\",\"deepen\":[{\"key\":\"...\",\"invitation\":\"...\"}],"
        "\"encouragement\":\"一句鼓励\",\"closing\":\"一句经文\"}。语气要像朋友，不像考官。"
    )


def _ai_enhance(ratings: Dict[str, float], text: Optional[str], base: Dict[str, Any], settings: Any) -> Optional[Dict[str, Any]]:
    """可选 AI 增强：任何失败都回退（返回 None）。"""
    prompt = build_prompt(ratings, text, base)
    raw = _call_ai(prompt, settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        out: Dict[str, Any] = {}
        if data.get("mirror"):
            out["mirror"] = str(data["mirror"])
        if data.get("encouragement"):
            out["encouragement"] = str(data["encouragement"])
        if data.get("closing"):
            out["closing"] = str(data["closing"])
        inv = {d.get("key"): d.get("invitation") for d in data.get("deepen", []) if isinstance(d, dict)}
        if inv:
            deepen = []
            for d in base.get("deepen", []):
                nd = dict(d)
                if inv.get(d["key"]):
                    nd["invitation"] = str(inv[d["key"]])
                deepen.append(nd)
            out["deepen"] = deepen
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
    """回流 formation：情感辨识属于「爱慕神+渴望成长」，标注爱/成长维度。"""
    if result.get("crisis"):
        return (["love", "growth"], False, True, 2.0)
    return (["love", "growth"], True, True, 5.0)
