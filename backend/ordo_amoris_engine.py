"""
ordo_amoris_engine.py — 失序之爱 → 重排（奥古斯丁 ordo amoris）

补足 gap 分析所缺的「爱的次序」框架。奥古斯丁在《忏悔录》《上帝之城》里讲：
  · 罪 = **失序的爱**——把次好的当作至好，爱受造之物过于爱造物主；
  · 德性 = **ordo amoris**，按正确的次序与分量去爱：一切之爱都在「爱神」之下、
    并且因着神而爱它。名言意译：「我的心不得安息，直到安息在你里面。」

与「偶像监测」类引擎互补而不重叠：偶像监测重在「指认」失序的爱；本引擎是它建设性的
另一面——不只命名那份失序的爱，更把它**重新排回神以下、因神而爱之**（re-ordering）。

纯函数；确定性优先；仅当用户填了自由文本 text 时才做轻量危机词检测；AI 仅作可选增强，
失败回退确定性结果。不定罪、不贴标签，只帮助人把爱重新对准神、导向安息与信靠。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ── 正确的爱的次序（三层阶梯）──
LADDER: List[Dict[str, str]] = [
    {"rank": "1", "name": "爱神", "en": "Love God",
     "note": "至高、无条件的爱——祂是终极，是一切之爱的源头与归宿。"},
    {"rank": "2", "name": "爱人（自己与邻舍，在神里）", "en": "Love self and neighbor in God",
     "note": "因祂的形像而爱自己与他人；这份爱从「爱神」里流出，也归回神。"},
    {"rank": "3", "name": "爱受造之物（为神的恩赐，不为终极）", "en": "Love created things as gifts",
     "note": "工作、成就、关系、享受都是好的——当作神所赐的礼物来领受、来爱，而非当作神。"},
]

# ── 把用户所爱之物粗略归类 → 温柔的「可能失序」提示 + 重排经文 ──
# kw 命中即倾向判为「容易被当成终极」的次好之爱（仅提示，非定罪）。
LOVE_KINDS: List[Dict[str, Any]] = [
    {"key": "approval", "name": "他人的认可 / 名声", "kw": ["认可", "肯定", "面子", "名声", "别人怎么看", "评价", "点赞", "称赞", "被看见"],
     "hint": "渴望被爱、被看见是好的，但当「别人的目光」成了心的定盘星，它就悄悄坐上了只有神能坐的位置。"},
    {"key": "success", "name": "成就 / 事业", "kw": ["成功", "事业", "工作", "业绩", "升职", "赚钱", "成就", "表现", "效率", "赢"],
     "hint": "工作是神所赐的呼召，值得尽心；但当「成就」成了你价值的根基，它就从恩赐变成了偶像。"},
    {"key": "control", "name": "掌控 / 安全感", "kw": ["掌控", "控制", "安全感", "确定", "计划", "稳定", "保障", "把握"],
     "hint": "想要安稳是人之常情；但把「掌控」当作终极的倚靠，会让人错过在神里那种更深的安息。"},
    {"key": "relationship", "name": "某段关系 / 某个人", "kw": ["他", "她", "感情", "恋", "婚", "家人", "孩子", "伴侣", "朋友", "关系"],
     "hint": "爱人是神的心意；但当一个人成了你全部的意义，这份爱反倒承受不起——因为只有神能做终极。"},
    {"key": "comfort", "name": "享受 / 舒适", "kw": ["享受", "舒适", "快乐", "放松", "娱乐", "美食", "旅行", "安逸", "刺激"],
     "hint": "享受是神慷慨的礼物；只是当追逐舒适成了心之所向，它就从礼物悄悄变成了主人。"},
    {"key": "self",  "name": "自我 / 自我实现", "kw": ["自我", "自由", "理想", "梦想", "实现自己", "做自己", "价值"],
     "hint": "成为神所造的你是美的；但「自我实现」若成了终极，就会把本该归神的中心让给了自己。"},
]

REORDER_VERSES: List[Dict[str, str]] = [
    {"ref": "太22:37-39", "text": "你要尽心、尽性、尽意爱主你的神……其次也相仿，就是要爱人如己。"},
    {"ref": "诗73:25-26", "text": "除你以外，在天上我有谁呢？除你以外，在地上我也没有所爱慕的。……但神是我心里的力量，又是我的福分，直到永远。"},
]

AUGUSTINE_QUOTE = "「你为自己造了我们，我们的心不得安息，直到安息在你里面。」——奥古斯丁《忏悔录》"

# ── 危机词（自 lament_engine 复制；仅当用户填了自由文本 text 时轻量检测）──
CRISIS_WORDS = [
    "自杀", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死", "死了算了",
    "伤害自己", "撑不下去了", "没有意义活着", "想消失",
]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = (
    "我听见你正承受很重的痛。在我们一起看爱的次序之前，我想先温柔地说：如果你有伤害自己的念头，"
    "请现在就联系你信任的人，或当地的心理危机热线——你值得有人此刻真实地陪着你。神爱你，"
    "你不必独自扛。（本功能不替代专业帮助。）"
)


def meta() -> Dict[str, Any]:
    """定义 + 爱的阶梯 + 重排步骤 + 奥古斯丁名言（供前端展示）。"""
    return {
        "definition": "罪是失序的爱（爱受造多于爱造物主）；德性是 ordo amoris——按正确的次序与分量去爱，"
                      "一切之爱都在「爱神」之下、并因神而爱。",
        "ladder": LADDER,
        "reorder_steps": [
            "命名：此刻我的心最爱、最放不下的是什么？",
            "分辨：它在我心中的实际排序在哪里？是否已坐上了本属神的位置？",
            "追问：我是不是把它当成了『只有神才能给』的东西（意义、安全、价值、终极）？",
            "重排：把它重新放回神以下——不是丢弃它，而是因着神、在神里去爱它。",
            "操练：为此具体做一件事（一句祷告、一个界限、一次感恩、一个交托的动作）。",
        ],
        "augustine_quote": AUGUSTINE_QUOTE,
    }


def _classify(loves: List[str], text: str) -> List[Dict[str, Any]]:
    """把用户列出的所爱之物匹配到 LOVE_KINDS（含命中计分）。"""
    blob = " ".join(loves) + " " + (text or "")
    scored: List[tuple] = []
    for kind in LOVE_KINDS:
        # 直接命中用户逐条 love 的权重更高
        direct = sum(1 for lv in loves for k in kind["kw"] if k in lv)
        ambient = sum(1 for k in kind["kw"] if k in blob)
        score = direct * 2 + ambient
        if score:
            scored.append((score, kind))
    scored.sort(key=lambda x: -x[0])
    return [k for _, k in scored]


def analyze(loves: List[str], text: Optional[str] = None,
            *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    """
    从用户列出的「所爱之物」推断可能的当前排序，温柔地指出至多 2 个「可能失序」的爱，
    并给出一条重排操练 + 经文（确定性；可选 AI 增强）。**非定罪、非贴标签。**
    """
    loves = [str(x).strip() for x in (loves or []) if str(x).strip()]
    text = (text or "").strip()
    crisis = _detect_crisis(text) if text else False

    kinds = _classify(loves, text)
    # 「可能失序」的爱：取最匹配的至多 2 个；若无匹配则以用户首个所爱作温柔提示
    disordered = kinds[:2]

    # 推断的「当前 de-facto 排序」 vs 「神为中心的排序」
    if loves:
        current_order = list(loves[:6])  # 用户心中此刻浮现的先后，作镜子
    else:
        current_order = ["（你还没有列出——可以先写下此刻心里最放不下的几样）"]

    flagged: List[Dict[str, Any]] = []
    if disordered:
        for kind in disordered:
            flagged.append({
                "key": kind["key"], "name": kind["name"], "hint": kind["hint"],
            })
    elif loves:
        flagged.append({
            "key": "general", "name": loves[0],
            "hint": "「" + loves[0] + "」本身可能是美好的——只是可以轻轻问问自己：它在我心里，"
                    "是不是坐到了本该归神的位置？",
        })

    verse = REORDER_VERSES[0]
    # 若涉及关系类失序，配诗73:25-26（「除你以外……」）更贴切
    if any(f.get("key") == "relationship" for f in flagged):
        verse = REORDER_VERSES[1]

    practice = (
        "试着做一次「重排」：把" +
        ("「" + flagged[0]["name"] + "」" if flagged else "你此刻最放不下的那份爱") +
        "重新放回神以下——不是不再爱它，而是先向神说：『你才是我的终极，我因你而爱它。』"
        "然后为它具体做一个交托的动作（一句祷告、一个界限、或一次单纯的感恩）。"
    )

    result: Dict[str, Any] = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "disclaimer": "这不是给你的爱定罪或贴标签，只帮助你看见爱的次序，好把心重新安放在神里面。",
        "god_centered_order": [{"rank": r["rank"], "name": r["name"]} for r in LADDER],
        "current_order": current_order,
        "possible_disorder": flagged,
        "reorder_steps": meta()["reorder_steps"],
        "practice": practice,
        "scripture": {"ref": verse["ref"], "text": verse["text"]},
        "augustine_quote": AUGUSTINE_QUOTE,
        "encouragement": "失序不是失败——奥古斯丁自己也是一路被爱重新校准过来的。每一次把爱放回正位，"
                         "都是恩典在你心里做重排的工作。",
        "closing": "「你为自己造了我们，我们的心不得安息，直到安息在你里面。」",
        "ai_used": False,
    }

    if use_ai:
        enhanced = _ai_enhance(loves, text, result, settings)
        if enhanced:
            result.update(enhanced)
            result["ai_used"] = True
    return result


def build_prompt(loves: List[str], text: Optional[str], base: Dict[str, Any]) -> str:
    return (
        "你是一位温柔、以福音为中心的属灵陪伴者，熟悉奥古斯丁的 ordo amoris（爱的次序）："
        "罪是失序的爱——爱受造多于爱造物主；德性是按正确次序去爱，一切之爱都在『爱神』之下、"
        "因神而爱。请帮用户看见爱的次序，并给出建设性的『重排』（re-ordering），中文，温暖不说教，"
        "**不定罪、不贴标签、不说『你不够属灵』之类的话**，多用恩典与安息的语气。\n"
        f"用户所爱之物：{('、'.join(loves)) or '（未列出）'}\n用户补充：{text or '（未特别说明）'}\n"
        "请输出 JSON：{\"possible_disorder\":[{\"name\":\"...\",\"hint\":\"...\"}],"
        "\"practice\":\"一个可操作的重排操练\",\"encouragement\":\"一句鼓励\",\"closing\":\"一句话\"}。"
        "hint 要像朋友的提醒，不像审判。"
    )


def _ai_enhance(loves: List[str], text: Optional[str], base: Dict[str, Any], settings: Any) -> Optional[Dict[str, Any]]:
    """可选 AI 增强：任何失败都回退（返回 None）。"""
    prompt = build_prompt(loves, text, base)
    raw = _call_ai(prompt, settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        out: Dict[str, Any] = {}
        dis = data.get("possible_disorder")
        if isinstance(dis, list) and dis:
            flagged = []
            for d in dis:
                if isinstance(d, dict) and d.get("name"):
                    flagged.append({"key": d.get("key", "ai"),
                                    "name": str(d["name"]), "hint": str(d.get("hint", ""))})
            if flagged:
                out["possible_disorder"] = flagged
        if data.get("practice"):
            out["practice"] = str(data["practice"])
        if data.get("encouragement"):
            out["encouragement"] = str(data["encouragement"])
        if data.get("closing"):
            out["closing"] = str(data["closing"])
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
    """回流 formation：爱的重排属于「渴望重排+对齐神」，标注渴望/成长维度。"""
    if result.get("crisis"):
        return (["desire", "growth"], False, True, 2.0)
    return (["desire", "growth"], True, True, 5.0)
