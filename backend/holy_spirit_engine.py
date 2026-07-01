"""
holy_spirit_engine.py — 圣灵论 / 与圣灵同行（巴刻《字里行间的圣灵》Keep in Step with the Spirit；
Gordon Fee《神赐能力的同在》）

补全三一：系统已有 know_god(父的属性)、incarnation(子)，唯缺**圣灵这一位格**。
注意与 spirits_engine（依纳爵「诸灵分辨」）刻意区分——那是分辨内在运动，本引擎是**圣灵论**本身。

巴刻的核心比喻：圣灵的职事是「**探照灯**」——祂不照亮自己，而是荣耀基督、把基督照亮给我们看
（约16:14）。圣灵是**一位有位格的神**（非一股能力）：祂重生、内住、成圣、赐确据、赐能力、
结果子、赐恩赐、代求、责备罪、安慰、引导进入真理。「随从圣灵而行」（加5:16,25）不是靠力挣扎，
而是靠着那位住在里面的主而活。

纯函数；确定性优先；内置危机词检测；AI 仅作可选增强。附教义护栏（避免灵恩/停止论两极，
守住「圣灵荣耀基督、结果子、合乎圣经」的中心）。不定罪、导向信靠那位住在里面的主。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

NEEDS: List[Dict[str, Any]] = [
    {"key": "powerless", "name": "想改变却无力 / 靠自己撑不住",
     "kw": ["无力", "改变不了", "撑不住", "靠自己", "挣扎", "使不上劲", "软弱", "力不从心", "做不到"],
     "ministry": "圣灵是**成圣之能**：治死罪、结果子，不是靠你咬牙，而是靠那住在你里面的主。",
     "ref": "加5:16", "text": "你们当顺着圣灵而行，就不放纵肉体的情欲了。",
     "practice": "把这场争战交给圣灵：祷告「圣灵啊，我不能，但你能，求你在我里面动工」，再迈出一小步顺服。"},
    {"key": "no_assurance", "name": "不确定自己是不是神的 / 缺确据",
     "kw": ["不确定", "是不是神的", "缺确据", "怀疑得救", "没把握", "是不是真信", "属不属于神"],
     "ministry": "圣灵**赐确据**：祂亲自与你的心同证你是神的儿女，叫你可以喊「阿爸，父」。",
     "ref": "罗8:16", "text": "圣灵与我们的心同证我们是神的儿女。",
     "practice": "安静求圣灵印证：读罗8:15-16，让「阿爸，父」这称呼从你口里说出来。"},
    {"key": "dry", "name": "干枯无力 / 感觉不到神",
     "kw": ["干枯", "感觉不到", "冷淡", "枯干", "没火", "麻木", "属灵低谷", "空", "提不起劲"],
     "ministry": "圣灵是**安慰者/保惠师**：干旱时祂仍在你里面，用说不出的叹息替你祷告，把基督重新照亮。",
     "ref": "约14:16", "text": "我要求父，父就另外赐给你们一位保惠师，叫他永远与你们同在。",
     "practice": "不必先有感觉才来：求圣灵把你的目光从「我感觉如何」转向「基督成就了什么」。"},
    {"key": "guidance", "name": "不知道神的引导 / 想被圣灵带领",
     "kw": ["引导", "带领", "不知道方向", "神的旨意", "被带领", "顺服圣灵", "感动", "该怎么走"],
     "ministry": "圣灵**引导进入真理**：祂的带领总与圣经一致、总荣耀基督、总结出圣灵的果子——用这三把尺检验。",
     "ref": "约16:13", "text": "只等真理的圣灵来了，他要引导你们明白一切的真理。",
     "practice": "用三把尺检验你的「感动」：它合乎圣经吗？荣耀基督吗？带出爱与平安吗？"},
    {"key": "grieve", "name": "怕自己叫圣灵担忧 / 常犯罪",
     "kw": ["叫圣灵担忧", "得罪圣灵", "常犯罪", "亏负", "污秽", "怕失去圣灵", "赶走圣灵"],
     "ministry": "圣灵是**内住**的、也是那位「凭祂受了印记」的：真信徒不会失去圣灵，但可叫祂担忧——回转就是了。",
     "ref": "弗4:30", "text": "不要叫神的圣灵担忧；你们原是受了他的印记，等候得赎的日子来到。",
     "practice": "向圣灵认那具体的罪，谢谢祂没有离开你，求祂重新充满、带你回到基督面前。"},
    {"key": "walk", "name": "想更深与圣灵同行 / 被圣灵充满",
     "kw": ["同行", "充满", "更深", "被圣灵", "结果子", "顺从圣灵", "属灵长进", "更亲近"],
     "ministry": "「随从圣灵而行」是**逐步**的同行：不是一次经历，而是天天让圣灵作主，结出仁爱喜乐和平的果子。",
     "ref": "加5:25", "text": "我们若是靠圣灵得生，就当靠圣灵行事。",
     "practice": "今天选一处让圣灵作主：一个决定、一段关系、一次试探，刻意问「圣灵，这里你要我怎样行？」"},
]

DOCTRINE_NOTE = (
    "【温柔的教义提示】圣灵的标记是荣耀基督、结出圣灵的果子、合乎圣经。避免走向「只追经历」或「否定祂今日作为」"
    "两个极端；一切以圣经为准、以基督为中心。"
)

CRISIS_WORDS = ["自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死",
                "死了算了", "伤害自己", "撑不下去了", "没有意义活着", "想消失"]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = ("我听见你正承受很重的痛。如果你有伤害自己的念头，请现在就联系你信任的人或当地心理危机热线。"
               "圣灵是保惠师，此刻也在你里面——你不必独自扛。（本功能不替代专业帮助。）")


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best, best_hits = None, 0
    for d in NEEDS:
        hits = sum(1 for k in d["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, d
    return best or NEEDS[5]


def meta() -> Dict[str, Any]:
    return {
        "title": "圣灵 · 与圣灵同行",
        "source": "巴刻《字里行间的圣灵》；Gordon Fee《神赐能力的同在》",
        "core": "圣灵是有位格的神，职事如探照灯——荣耀基督；祂重生、内住、成圣、赐确据、赐能力、结果子、引导。",
        "needs": [{"key": d["key"], "name": d["name"]} for d in NEEDS],
        "doctrine_note": DOCTRINE_NOTE,
        "verse": "加5:25",
        "principle": "「我们若是靠圣灵得生，就当靠圣灵行事。」——不是靠力挣扎，而是靠那位住在里面的主而活。",
    }


def analyze(text: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    text = (text or "").strip()
    crisis = _detect_crisis(text)
    picked = _pick(text)
    result: Dict[str, Any] = {
        "crisis": crisis, "crisis_note": CRISIS_NOTE if crisis else "",
        "need": {"key": picked["key"], "name": picked["name"]},
        "spirit_ministry": picked["ministry"],
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "doctrine_note": DOCTRINE_NOTE,
        "prayer": ("圣灵啊，谢谢你——你是有位格的神，住在我里面，把基督照亮给我看。我承认我常常靠自己挣扎、"
                   "又常常忘了你就在这里。求你在我里面成圣、赐我确据、赐我能力，引导我进入真理，结出你的果子。"
                   "叫我不是靠力，而是靠着你而活；愿我天天与你同行，你荣耀基督，我也单单仰望基督。"),
        "practices": [picked["practice"],
                      "求圣灵充满：安静一分钟，把今天交给祂作主，说「圣灵，今天请你带领我」。"],
        "summary": ("圣灵不是一股力量，是那位荣耀基督、住在你里面的神。与圣灵同行不是靠力挣扎，"
                    "而是天天让祂作主——祂成圣、赐确据、赐能力、引导你结出果子。"),
        "closing": "「靠圣灵得生，就当靠圣灵行事。」（加5:25）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return ("你是一位温柔、以福音为中心的属灵陪伴者，熟悉巴刻《字里行间的圣灵》与 Gordon Fee 的圣灵论。"
            "核心：圣灵是有位格的神，职事如探照灯——荣耀基督；祂重生/内住/成圣/赐确据/赐能力/结果子/引导；"
            "『随从圣灵而行』是靠住在里面的主而活，非靠力挣扎。请针对用户的处境，温柔地把对应的圣灵职事说给他，"
            "给经文、祷告与操练，并附一句『圣灵荣耀基督、结果子、合乎圣经；避免灵恩/停止论两极』的教义提示。中文，温暖不说教。\n"
            f"用户处境：{text}\n"
            "请输出 JSON：{\"spirit_ministry\":\"...\",\"prayer\":\"一段可照着祷告的话\",\"summary\":\"...\",\"closing\":\"一句经文\"}。")


def _ai_enhance(text, base, settings):
    raw = _call_ai(build_prompt(text, base), settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        return {k: str(data[k]) for k in ("spirit_ministry", "prayer", "summary", "closing") if data.get(k)} or None
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
        return (["spirit", "power", "trust"], False, True, 2.0)
    return (["spirit", "power", "trust"], True, True, 4.0)
