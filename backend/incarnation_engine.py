"""
incarnation_engine.py — 道成肉身与「与神性有份」/ Incarnation & Union
（亚他那修《论道成肉身》On the Incarnation；彼后1:4 与神的性情有份）

深化 union_engine 的古典/东方线。亚他那修的名句意译：**「祂成为我们的样子，为要使我们成为祂的样子」**
——神的儿子取了肉身，为要：(1)恢复我们里面失落的神的形像；(2)胜过死亡；(3)使我们得儿子的名分、
与神的性情有份（theosis / 神化——**在改革宗框架下理解为：得着儿子名分、被更新成基督的样式、有份于
神的生命与性情，而非在本体上成为神**）。

三个落点：
  · **神明白我**：道成了肉身，神亲自尝过软弱、疲乏、试探、眼泪——你不是向一位不懂的神呼求（来4:15）。
  · **物质与身体是好的**：神取了真实的身体，就否定了「属灵=逃离身体/物质」的错误；日常、身体、受造界都要紧。
  · **我要被更新**：祂成为我所是，为使我成为祂所是——我的终局不是被改良，而是被更新成基督的样式，与神的生命联合。

教义护栏：theosis 指「有份于神的性情/生命、被更新成基督样式、得儿子名分」，**不是**人变成神、
或抹去造物主与受造物之别。以圣经与基督为中心。
纯函数；确定性优先；内置危机词检测；AI 仅作可选增强。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

FACETS: List[Dict[str, Any]] = [
    {"key": "not_understood", "name": "觉得没人懂我 / 神不懂我的软弱与痛",
     "kw": ["没人懂", "神不懂", "软弱", "试探", "疲惫", "眼泪", "孤独", "痛没人知", "不被理解", "撑"],
     "truth": "道成了肉身——神的儿子亲自成为人，尝过饥饿、疲乏、被弃、流泪、被试探。你不是向一位高高在上、"
              "不懂人间苦的神呼求；你有一位「能体恤你软弱」的大祭司，祂懂，且祂就在。",
     "ref": "来4:15", "text": "因我们的大祭司并非不能体恤我们的软弱，他也曾凡事受过试探，与我们一样，只是他没有犯罪。"},
    {"key": "despise_body", "name": "厌恶身体/物质 / 觉得属灵就该逃离现实",
     "kw": ["厌恶身体", "逃离", "物质", "身体", "现实", "俗务", "不属灵", "肉身", "世界很脏", "只想属灵"],
     "truth": "神取了真实的身体、活在真实的世界——这就永远否定了「属灵＝逃离身体与物质」的谎言。"
              "你的身体、你的日常、你手上的工作，都不是属灵的障碍，而是神所看重、要被救赎的领域。",
     "ref": "约1:14", "text": "道成了肉身，住在我们中间，充充满满地有恩典有真理。"},
    {"key": "cant_change", "name": "觉得自己改变不了 / 只能这样了",
     "kw": ["改变不了", "只能这样", "没救", "本性难移", "老样子", "无法改", "认命", "改不掉", "就这样了", "绝望于自己"],
     "truth": "亚他那修说：祂成为我所是，为使我成为祂所是。你的终局不是「被稍微改良」，而是被圣灵更新、"
              "更新成基督的样式，与神的生命有份。改变的动力不在你的意志，而在那位取了你肉身、要把你更新的主。",
     "ref": "彼后1:4", "text": "叫你们既脱离世上从情欲来的败坏，就得与神的性情有份。"},
    {"key": "who_am_i", "name": "不知道自己是谁 / 想更深认识在基督里的身份",
     "kw": ["我是谁", "身份", "价值", "在基督里", "更深", "认识自己", "归属", "名分", "属于", "定义"],
     "truth": "因着道成肉身与联合，你得着了「神儿女」的名分——不是外加的头衔，而是真实地有份于神的生命。"
              "你是谁？你是被神的儿子取了肉身、赎回、并要更新成祂样式的人。这是比任何成就都深的身份。",
     "ref": "约1:12", "text": "凡接待他的，就是信他名的人，他就赐他们权柄，作神的儿女。"},
]

DOCTRINE_NOTE = (
    "【温柔的教义提示】「与神的性情有份」(theosis) 指有份于神的生命、被更新成基督的样式、得儿子的名分，"
    "**不是**人在本体上成为神，也不抹去造物主与受造物之别。以圣经与基督为中心。"
)

CRISIS_WORDS = [
    "自杀", "想死", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死", "死了算了",
    "伤害自己", "撑不下去了", "没有意义活着", "想消失",
]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = (
    "我听见你正承受很重的痛。我想先温柔地说：如果你有伤害自己的念头，请现在就联系你信任的人"
    "或当地心理危机热线。那位道成肉身的主亲自尝过人的痛，祂懂你，也在你身边——你不必独自扛。"
    "（本功能不替代专业帮助。）"
)


def _pick(text: str) -> Dict[str, Any]:
    t = text or ""
    best, best_hits = None, 0
    for f in FACETS:
        hits = sum(1 for k in f["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, f
    return best or FACETS[3]


def meta() -> Dict[str, Any]:
    return {
        "title": "道成肉身 · 与神性情有份",
        "source": "亚他那修《论道成肉身》；彼后1:4",
        "core": "祂成为我们的样子，为要使我们成为祂的样子——恢复形像、胜过死亡、得儿子名分、与神性情有份。",
        "facets": [{"key": f["key"], "name": f["name"]} for f in FACETS],
        "doctrine_note": DOCTRINE_NOTE,
        "verse": "约1:14",
        "principle": "「道成了肉身，住在我们中间」——神没有隔岸观火，祂进到我们的血肉、我们的痛里，为要把我们提到祂里面。",
    }


def analyze(text: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    text = (text or "").strip()
    crisis = _detect_crisis(text)
    picked = _pick(text)
    result: Dict[str, Any] = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "facet": {"key": picked["key"], "name": picked["name"]},
        "truth": picked["truth"],
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "doctrine_note": DOCTRINE_NOTE,
        "prayer": ("主耶稣，谢谢你——你没有从远处看我，而是取了我的肉身，进到我的软弱、我的眼泪、我的日常里。"
                   "你成为我所是，为要使我成为你所是。求你恢复我里面你的形像，把我更新成你的样式，"
                   "叫我有份于你的生命。当我以为自己改变不了，求你提醒我：改变的能力在你，不在我。"),
        "practices": [
            "把一处软弱交给「那懂的主」：说出一件你以为神不懂的痛，然后读来4:15，让「祂也曾受过」安慰你。",
            "看见身体与日常的神圣：今天做一件平凡小事（吃饭/走路/工作）时，对神说「这也是你所看重、要救赎的」。",
        ],
        "summary": ("道成肉身意味着：神懂你的痛、你的身体与日常都要紧、而你的终局是被更新成基督的样式。"
                    "祂成为你所是，为使你成为祂所是。"),
        "closing": "「道成了肉身，住在我们中间，充充满满地有恩典有真理。」（约1:14）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(text, result, settings)
        if enh:
            result.update(enh); result["ai_used"] = True
    return result


def build_prompt(text: str, base: Dict[str, Any]) -> str:
    return (
        "你是一位温柔、以福音为中心的属灵陪伴者，熟悉亚他那修《论道成肉身》与『与神性情有份』(彼后1:4)。"
        "核心：祂成为我们的样子为使我们成为祂的样子——神明白人的软弱(来4:15)、身体与物质是好的(约1:14)、"
        "我们要被更新成基督的样式(theosis，但非人变成神)。请针对用户处境，温柔应用道成肉身的真理，"
        "给经文、祷告与操练，并附一句『theosis 指有份于神的生命/被更新成基督样式、非本体成神』的教义提示。"
        "中文，温暖不说教。\n"
        f"用户处境：{text}\n"
        "请输出 JSON：{\"truth\":\"...\",\"prayer\":\"一段可照着祷告的话\",\"summary\":\"...\",\"closing\":\"一句经文\"}。"
    )


def _ai_enhance(text: str, base: Dict[str, Any], settings: Any) -> Optional[Dict[str, Any]]:
    raw = _call_ai(build_prompt(text, base), settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        return {k: str(data[k]) for k in ("truth", "prayer", "summary", "closing") if data.get(k)} or None
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
    if result.get("crisis"):
        return (["identity", "union", "wonder"], False, True, 2.0)
    return (["identity", "union", "wonder"], True, True, 4.0)
