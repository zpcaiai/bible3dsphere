"""
renovation_engine.py — 心意更新 / Renovation of the Heart（达拉斯·魏乐德 Dallas Willard）

魏乐德的命题：属灵塑造是圣灵把「整个人」逐渐更新成基督的样式——不是加信息，而是内在生命
各个层面的转化。他的 VIM 框架：Vision 异象（看见在神国里的生命该是什么样）→ Intention 决意
（真心决定要成为门徒）→ Means 途径（借着操练与恩典）。本引擎按五个层面自评，给出各层面的
VIM 塑造小方案。纯函数；确定性优先；AI 可选增强；内置危机词检测；不定罪、导向恩典。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ── 五个层面（魏乐德「全人」维度：思想/意志/身体/社会/灵魂） ──
DIMENSIONS: List[Dict[str, Any]] = [
    {"key": "mind", "name": "心思意念", "hint": "我的思想被什么占据？我在喂养它什么？",
     "ref": "罗12:2", "text": "不要效法这个世界，只要心意更新而变化。"},
    {"key": "will", "name": "意志 / 心", "hint": "我真正决意要的是什么？我的心定在哪里？",
     "ref": "箴4:23", "text": "你要保守你心，胜过保守一切，因为一生的果效是由心发出。"},
    {"key": "body", "name": "身体 / 习惯", "hint": "我的身体被训练成自动做什么？习惯把我带向哪里？",
     "ref": "罗12:1", "text": "将身体献上，当作活祭，是圣洁的，是神所喜悦的。"},
    {"key": "social", "name": "社会 / 关系", "hint": "谁在塑造我？我活在怎样的关系里？",
     "ref": "林前15:33", "text": "滥交是败坏善行。"},
    {"key": "soul", "name": "灵魂 / 深处", "hint": "我最深处安息在哪里？我里面是整合还是分裂？",
     "ref": "诗62:1", "text": "我的心默默无声，专等候神；我的救恩是从祂而来。"},
]
DIM_INDEX = {d["key"]: d for d in DIMENSIONS}

VIM = {
    "vision": "异象 Vision：先看见——在神的国里，这一面的生命本该是什么样子。",
    "intention": "决意 Intention：真心决定——我要成为那样的人，不只是想要，而是定意。",
    "means": "途径 Means：借着恩典中的操练——具体、可行、重复的一小步，让圣灵动工。",
}

REMEDY: Dict[str, Dict[str, str]] = {
    "mind": {
        "vision": "在神国里，我的思想被真理、良善、可爱的事充满，而非忧虑与比较。",
        "intention": "我决意主动选择喂养心思的内容，把神的话放进思想的中心。",
        "means": "每天晨起先读一段经文并默想一句；察觉忧虑时，用一句真理向自己宣告。",
    },
    "will": {
        "vision": "在神国里，我的心定意跟随基督，我的选择由爱神所主导。",
        "intention": "我决意把一个反复摇摆的选择，明确交在神面前定意顺服。",
        "means": "写下「我决意要的一件事」，每天早上重申一次，晚上省察是否照着行。",
    },
    "body": {
        "vision": "在神国里，我的身体是活祭，习惯自动把我带向亲近神而非逃避。",
        "intention": "我决意用一个新的身体习惯，替换一个把我拉离神的旧习惯。",
        "means": "选一个微习惯（如固定时间祷告/放下手机/安息），连续七天在同一处境操练。",
    },
    "social": {
        "vision": "在神国里，我活在能塑造我更像基督的关系里，也塑造别人。",
        "intention": "我决意靠近一段能造就我的关系，并温柔地远离拉我下坠的。",
        "means": "本周主动约一位能在信仰上彼此扶持的人；对一段有害关系设立温柔的界限。",
    },
    "soul": {
        "vision": "在神国里，我的灵魂在神里面安息，各部分被整合为一。",
        "intention": "我决意停下奔忙，让灵魂在神面前安静，重新被整合。",
        "means": "每天留 5 分钟静默，只在神面前安息，不求什么，单单与祂同在。",
    },
}

CRISIS_WORDS = [
    "自杀", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死", "死了算了",
    "伤害自己", "撑不下去了", "没有意义活着", "想消失",
]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = (
    "我听见你正承受很重的东西。在谈塑造之前想先温柔地说：如果你有伤害自己的念头，请现在就"
    "联系你信任的人或当地心理危机热线——你值得此刻有人真实地陪着你。（本功能不替代专业帮助。）"
)


def _n(v: Any) -> float:
    try:
        return max(0.0, min(1.0, float(v)))
    except Exception:
        return 0.5


def meta() -> Dict[str, Any]:
    return {
        "vim": VIM,
        "dimensions": DIMENSIONS,
        "principle": "灵命塑造 = 圣灵把整个人（心思 / 意志 / 身体 / 社会 / 灵魂）逐渐更新成基督的样式。"
                     "不是靠意志硬撑，而是有异象、真决意、走对途径，让恩典动工。",
    }


def assess(ratings: Dict[str, Any], text: Optional[str] = None,
           *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    scores = {d["key"]: _n(ratings.get(d["key"], 0.5)) for d in DIMENSIONS}
    crisis = _detect_crisis(text or "")
    ordered = sorted(DIMENSIONS, key=lambda d: scores[d["key"]])
    weak = ordered[:2]
    strong = ordered[-1]

    plans = []
    for d in weak:
        r = REMEDY[d["key"]]
        plans.append({
            "key": d["key"], "name": d["name"],
            "score": round(scores[d["key"]], 2),
            "vision": r["vision"], "intention": r["intention"], "means": r["means"],
            "scripture": {"ref": d["ref"], "text": d["text"]},
        })

    result: Dict[str, Any] = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "scores": {k: round(v, 2) for k, v in scores.items()},
        "strength": {"key": strong["key"], "name": strong["name"],
                     "word": "这一面是神已经在你身上动工的记号，为它感恩，也让它带动其余。"},
        "plans": plans,
        "summary": "先从最弱的一两面入手，走 VIM：先看见异象，再真心决意，再走一个具体的小途径——"
                   "让圣灵在整个人里做更新的工。这不是评分定优劣，只是看见邀请。",
        "closing": "「那把你们召来的本是信实的，祂必成就这事。」（帖前5:24）",
        "ai_used": False,
    }
    if use_ai:
        enh = _ai_enhance(ratings, text, result, settings)
        if enh:
            result.update(enh)
            result["ai_used"] = True
    return result


def build_prompt(ratings: Dict[str, Any], text: Optional[str], base: Dict[str, Any]) -> str:
    return (
        "你是一位熟悉达拉斯·魏乐德《心意更新而变化》(Renovation of the Heart) 的属灵导师。"
        "用户按五个层面（心思/意志/身体/社会/灵魂）自评。请针对最弱的一两面，给出温柔、以恩典为中心、"
        "非评判的 VIM 塑造建议（异象 Vision / 决意 Intention / 途径 Means），中文。\n"
        f"自评：{json.dumps(base.get('scores', {}), ensure_ascii=False)}；补充：{text or '（无）'}\n"
        "输出 JSON：{\"plans\":[{\"key\":\"...\",\"vision\":\"...\",\"intention\":\"...\",\"means\":\"...\"}],\"summary\":\"...\"}"
    )


def _ai_enhance(ratings, text, base, settings) -> Optional[Dict[str, Any]]:
    raw = _call_ai(build_prompt(ratings, text, base), settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        by = {p.get("key"): p for p in data.get("plans", []) if isinstance(p, dict)}
        plans = []
        for p in base["plans"]:
            np = dict(p)
            src = by.get(p["key"])
            if src:
                for f in ("vision", "intention", "means"):
                    if src.get(f):
                        np[f] = str(src[f])
            plans.append(np)
        out = {"plans": plans}
        if data.get("summary"):
            out["summary"] = str(data["summary"])
        return out
    except Exception:
        return None


def _call_ai(prompt: str, settings: Any) -> Optional[str]:
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
    if result.get("crisis"):
        return (["growth", "fear"], False, True, 2.0)
    return (["growth"], True, True, 5.0)
