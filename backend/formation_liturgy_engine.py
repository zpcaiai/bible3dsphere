"""
formation_liturgy_engine.py — 塑造礼仪 / You Are What You Love（James K.A. Smith）

本引擎的独一件事：接住一个「日常习惯」，指认它背后暗中演练的「礼仪(liturgy)」——
它悄悄把你的心导向哪一种假的「美好生活」愿景——并开出一套基督徒的「反礼仪(counter-liturgy)」。

与 `cultural_engine`（文化辨识/内容 discernment）刻意区分、不重叠：
本引擎不做文化批判，而做**欲望塑造**——习惯即敬拜，反复演练的仪式在塑造我们的爱。

Smith：人首先是「爱的动物 / 敬拜的动物」，不是先思考再行动，而是被习惯所塑造的爱所驱动。
世俗的礼仪（滑手机、消费、绩效、追剧、社媒比较）反复演练，就把我们的爱悄悄导向假的
「美好生活」愿景。对策是「反礼仪」——用有意的基督徒操练，重新校准心的所爱。

纯函数；确定性优先；内置危机词检测；AI 仅作可选增强，失败回退确定性结果。
不定罪、不贴标签，只帮助人看见习惯在塑造什么，并给出一条更美的操练之路。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ── 暗中的礼仪：日常习惯 → 它训练的「美好生活」愿景 + 反礼仪操练 ──
SECRET_LITURGIES: List[Dict[str, Any]] = [
    {"key": "scroll",
     "name": "无意识刷手机 / 信息流",
     "kw": ["刷手机", "刷视频", "刷抖音", "刷短视频", "信息流", "刷屏", "刷朋友圈", "无意识刷", "停不下来刷", "一直看手机"],
     "vision": "训练你渴望「被认可、别错过、永远有新鲜」——把心的默认姿态调成焦躁与贪多。",
     "counter": "固定的静默与安息：把每天头 10 分钟的『刷屏』换成读经与祷告，让神的话先塑造你的渴望。",
     "step": "今天醒来第一件事，先不碰手机，读一节经文、安静一分钟。"},
    {"key": "consume",
     "name": "消费 / 购物",
     "kw": ["购物", "买东西", "剁手", "下单", "消费", "网购", "买买买", "购物车", "花钱", "血拼"],
     "vision": "「买到就幸福、身份靠拥有」——训练你相信匮乏，用占有来喂养安全感。",
     "counter": "感恩清点已有 + 简朴与施舍：在想买之前，先数点神已经给的，再刻意送出一样。",
     "step": "今天列出 5 样你已经拥有、值得感恩的东西，并把一样东西送人或奉献。"},
    {"key": "hustle",
     "name": "绩效与忙碌",
     "kw": ["绩效", "忙碌", "加班", "效率", "产出", "停不下来", "内卷", "拼命", "证明自己", "闲不住", "停下就焦虑"],
     "vision": "「价值靠产出、停下就没用」——训练你把身份押在表现上，不敢休息。",
     "counter": "守安息日、领受「你是被爱的儿女」：定时停工安息，在什么都不做时，仍相信自己被神所爱。",
     "step": "本周划出一段固定的安息时间，什么都不产出，只领受你是神所爱的。"},
    {"key": "compare",
     "name": "社媒比较",
     "kw": ["比较", "攀比", "羡慕", "别人过得", "点赞", "社媒", "朋友圈比", "看别人", "焦虑别人", "不如别人", "嫉妒"],
     "vision": "「人生是一场排名」——训练你用别人的高光衡量自己，活在评判与嫉妒里。",
     "counter": "为他人祝福代祷 + 隐藏的善行：每当想比较，就转为为对方祝福，并做一件不为人知的善事。",
     "step": "今天为一个你曾羡慕的人诚心祷告祝福，并悄悄做一件不让人知道的好事。"},
    {"key": "binge",
     "name": "追剧 / 无尽娱乐",
     "kw": ["追剧", "刷剧", "看剧", "煲剧", "娱乐", "打游戏", "游戏", "麻木", "逃避", "消遣", "一集接一集"],
     "vision": "「逃避胜过面对、麻木胜过临在」——训练你用娱乐麻醉，逃开真实的自己与他人。",
     "counter": "临在的操练 + 与真实的人同席：刻意练习专注临在，把一段娱乐时间换成与真人好好相处。",
     "step": "今晚把一段追剧的时间，换成与一个真实的人面对面吃饭或深谈。"},
    {"key": "news",
     "name": "新闻 / 焦虑循环",
     "kw": ["新闻", "刷新闻", "焦虑循环", "世界大事", "灾难", "看新闻停不下", "追消息", "恐慌", "担忧世界", "越看越慌"],
     "vision": "「世界靠我的掌控」——训练你用不停的关注换取掌控感，心却越来越被恐惧辖制。",
     "counter": "交托祷告 + 默想神掌权：设定新闻的界限，把担忧一件件交托，默想那位真正掌权的神。",
     "step": "今天限定看新闻的时间，把每一个担忧写下来，逐一祷告交托给掌权的神。"},
]
LITURGY_INDEX = {d["key"]: d for d in SECRET_LITURGIES}

# 反礼仪锚点经文
COUNTER_SCRIPTURES: List[Dict[str, str]] = [
    {"ref": "西3:1-2", "text": "你们要求在上面的事……要思念上面的事，不要思念地上的事。"},
    {"ref": "太6:21", "text": "因为你的财宝在哪里，你的心也在那里。"},
]

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


def _pick_liturgy(habit: str) -> Dict[str, Any]:
    """确定性关键词匹配，选出最贴近这个习惯的暗中礼仪；无匹配则回退到最普遍的一条。"""
    t = habit or ""
    best: Optional[Dict[str, Any]] = None
    best_hits = 0
    for d in SECRET_LITURGIES:
        hits = sum(1 for k in d["kw"] if k in t)
        if hits > best_hits:
            best_hits = hits
            best = d
    if best is None:
        best = LITURGY_INDEX["scroll"]  # 最普遍的暗中礼仪：无意识刷屏
    return best


def meta() -> Dict[str, Any]:
    """核心原理 + 暗中礼仪对照表 + 反礼仪总纲（供前端展示）。"""
    return {
        "principle": "你被你所爱的塑造，而你的爱被你反复演练的『礼仪』塑造。",
        "secret_liturgies": [
            {"key": d["key"], "name": d["name"], "vision": d["vision"], "counter": d["counter"]}
            for d in SECRET_LITURGIES
        ],
        "counter": "用有意的操练，重新校准心的所爱。",
        "scriptures": COUNTER_SCRIPTURES,
    }


def analyze(habit: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    """接住一个日常习惯，指认它背后的礼仪与所训练的愿景，并开出反礼仪（确定性；可选 AI 增强）。"""
    habit = (habit or "").strip()
    crisis = _detect_crisis(habit)
    chosen = _pick_liturgy(habit)
    scripture = COUNTER_SCRIPTURES[0]

    naming = (
        "你说的这个习惯——「" + chosen["name"] + "」——其实是一场暗中的『礼仪』。"
        "它反复演练，就在悄悄塑造你的爱：" + chosen["vision"]
    )

    parts: List[str] = []
    if crisis:
        parts.append(CRISIS_NOTE)
    parts.append(naming)
    parts.append("反礼仪：" + chosen["counter"] + "（" + scripture["ref"] + "：" + scripture["text"] + "）")
    parts.append("第一小步：" + chosen["step"])

    result: Dict[str, Any] = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "liturgy": chosen["name"],
        "vision": chosen["vision"],
        "counter_liturgy": chosen["counter"],
        "scripture": scripture,
        "first_step": chosen["step"],
        "naming": naming,
        "message": "\n\n".join(parts),
        "principle": "你被你所爱的塑造，而你的爱被你反复演练的『礼仪』塑造。",
        "ai_used": False,
    }

    if use_ai:
        enhanced = _ai_enhance(habit, result, settings)
        if enhanced:
            result.update(enhanced)
            result["ai_used"] = True
    return result


def build_prompt(habit: str, base: Dict[str, Any]) -> str:
    return (
        "你是一位温柔、以福音为中心的属灵陪伴者，熟悉 James K.A. Smith《You Are What You Love "
        "文化礼仪》所讲的欲望塑造：人首先是『爱的动物/敬拜的动物』，日常习惯是暗中的『礼仪』，"
        "反复演练就把我们的爱导向假的『美好生活』愿景；对策是『反礼仪』——用有意的基督徒操练"
        "重新校准心的所爱。请接住用户描述的习惯，指认它背后的礼仪与所训练的愿景，"
        "并开出一套基督徒的反礼仪与一个极小的第一步。中文，温暖不说教，"
        "绝不定罪、不贴标签、不羞辱。\n"
        f"系统判断的礼仪：{base.get('liturgy', '')}\n用户描述的习惯：{habit}\n"
        "请输出 JSON：{\"vision\":\"这习惯训练的假『美好生活』愿景\","
        "\"counter_liturgy\":\"对应的基督徒反礼仪操练\",\"first_step\":\"一个极小可行的第一步\"}。"
    )


def _ai_enhance(habit: str, base: Dict[str, Any], settings: Any) -> Optional[Dict[str, Any]]:
    """可选 AI 增强：任何失败都回退（返回 None）。"""
    prompt = build_prompt(habit, base)
    raw = _call_ai(prompt, settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        vision = str(data["vision"]) if data.get("vision") else base["vision"]
        counter = str(data["counter_liturgy"]) if data.get("counter_liturgy") else base["counter_liturgy"]
        step = str(data["first_step"]) if data.get("first_step") else base["first_step"]
        naming = (
            "你说的这个习惯——「" + base["liturgy"] + "」——其实是一场暗中的『礼仪』。"
            "它反复演练，就在悄悄塑造你的爱：" + vision
        )
        parts: List[str] = []
        if base.get("crisis"):
            parts.append(CRISIS_NOTE)
        parts.append(naming)
        parts.append("反礼仪：" + counter + "（" + base["scripture"]["ref"] + "：" + base["scripture"]["text"] + "）")
        parts.append("第一小步：" + step)
        return {
            "vision": vision,
            "counter_liturgy": counter,
            "first_step": step,
            "naming": naming,
            "message": "\n\n".join(parts),
        }
    except Exception:
        return None


def _call_ai(prompt: str, settings: Any) -> Optional[str]:
    """尽力调用既有 provider；不可用则返回 None（引擎保持零硬依赖）。"""
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
    """回流 formation：塑造礼仪属于「欲望/习惯的重新校准」，标注成长维度。"""
    if result.get("crisis"):
        return (["desire", "habit", "growth"], False, True, 2.0)
    return (["desire", "habit", "growth"], True, True, 5.0)
