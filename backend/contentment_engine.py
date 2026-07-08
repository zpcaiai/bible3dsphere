"""
contentment_engine.py — 知足 / Christian Contentment（Jeremiah Burroughs《基督徒知足的秘诀》
The Rare Jewel of Christian Contentment）

补足「对『缺乏』之心态」的属灵之药。区别于焦虑引擎：焦虑处理『对未来的忧惧』，
本引擎处理『对当下缺乏的不满』——按 Burroughs 的「知足的学校」把心从环境转向神的护理。

Burroughs 对知足的意译定义：「基督徒的知足，是一种甜美、内在、安静、恩典所结的心灵状态；
甘心顺服并喜悦于神在每一处境中智慧慈父般的安排。」

要点：(1)知足是「学」来的（腓4:11 我已经学会），不是天生；(2)不是斯多亚式的冷漠、也不是
压抑不满，而是恩典带来的内在安宁；(3)「奥秘」——知足不靠加增所拥有的，而靠减去过度的欲望、
靠信靠神的护理；(4)不满常源于把「暂时的/次好的」当成「终极的必需」。

纯函数；确定性优先；内置危机词检测；AI 仅作可选增强，失败回退确定性结果。
不定罪、不贴标签，只帮助人在基督里让心安息。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ── 知足的「学校功课」（Burroughs：知足是在学校里一门门学来的） ──
SCHOOL_LESSONS: List[Dict[str, str]] = [
    {"key": "portion", "lesson": "我的境况是神亲手量给我的",
     "note": "不是命运的偶然，是慈父的分配；祂量给我的这一份，够用且合宜。",
     "ref": "诗16:5", "text": "耶和华是我的产业，是我杯中的份；我所得的，你为我持守。"},
    {"key": "in_christ", "lesson": "我在基督里已经拥有了一切",
     "note": "真正的富足不在手中的多寡，而在我是否在基督里——祂就是我最大的产业。",
     "ref": "林前3:21-23", "text": "万有全是你们的……并且你们是属基督的。"},
    {"key": "not_env", "lesson": "心的富足不在环境，而在里面",
     "note": "环境安静不叫人知足，心里安静才叫人知足；知足是从里面长出来的。",
     "ref": "箴15:15", "text": "心中欢畅的，常享丰筵。"},
    {"key": "subtract", "lesson": "减去过度的欲望，比加增拥有更能带来安宁",
     "note": "世界叫你加增拥有来填满欲望；基督叫你缩减欲望来安息在神里——这才是知足的奥秘。",
     "ref": "提前6:6-8", "text": "然而敬虔加上知足的心便是大利……有衣有食，就当知足。"},
]
LESSON_INDEX = {l["key"]: l for l in SCHOOL_LESSONS}

# ── 缺乏 → 常被误当作「终极必需」的次好之物 + 对应的学校功课 + 祈求 ──
LACKS: List[Dict[str, Any]] = [
    {"key": "money", "name": "钱财 / 供应", "kw": ["钱", "穷", "债", "收入", "供应", "买不起", "经济", "工资", "贫"],
     "idol": "把「财务的宽裕」当成了心安的终极必需", "lesson": "subtract",
     "ref": "腓4:19", "text": "我的神必照祂荣耀的丰富，在基督耶稣里，使你们一切所需用的都充足。",
     "ask": "求你叫我在你里面知足，把对钱财的倚靠交给你——你是我真正的供应者。"},
    {"key": "job", "name": "工作 / 前途", "kw": ["工作", "失业", "事业", "前途", "升职", "机会", "职业", "没成就"],
     "idol": "把「成就与出人头地」当成了价值的终极必需", "lesson": "in_christ",
     "ref": "西3:23-24", "text": "无论做什么，都要从心里做，像是给主做的……你们所事奉的乃是主基督。",
     "ask": "求你叫我在基督里认识自己的价值，不靠成就定义我，把前途交托给你的护理。"},
    {"key": "relationship", "name": "关系 / 婚姻", "kw": ["单身", "婚姻", "另一半", "孤单", "没人", "被拒", "感情", "伴侣", "结婚"],
     "idol": "把「一段亲密关系」当成了满足的终极必需", "lesson": "in_christ",
     "ref": "诗73:25", "text": "除你以外，在天上我有谁呢？除你以外，在地上我也没有所爱慕的。",
     "ask": "求你先作我心里最深的满足，叫我在你的爱里被充满，而不必用人来填满你的位置。"},
    {"key": "health", "name": "健康 / 身体", "kw": ["病", "健康", "身体", "痛", "医", "虚弱", "残", "康复"],
     "idol": "把「身体的康健」当成了平安的终极必需", "lesson": "portion",
     "ref": "林后12:9", "text": "我的恩典够你用的，因为我的能力是在人的软弱上显得完全。",
     "ask": "求你在我软弱里作我的力量，叫我看见：你量给我的这一份，够我倚靠你走过。"},
    {"key": "status", "name": "地位 / 被看见", "kw": ["比较", "别人", "羡慕", "不如", "面子", "认可", "看不起", "落后", "地位"],
     "idol": "把「他人的认可与比较中的胜出」当成了安全感的终极必需", "lesson": "not_env",
     "ref": "加1:10", "text": "我现在是要得人的心呢？还是要得神的心呢？……我就不是基督的仆人了。",
     "ask": "求你叫我从与人比较里出来，安息在「我已被你悦纳」这件事上，不再靠别人的眼光活着。"},
    {"key": "control", "name": "掌控 / 确定", "kw": ["计划", "失控", "不确定", "未知", "掌控", "安排", "变化", "打乱"],
     "idol": "把「一切在我掌控中」当成了安稳的终极必需", "lesson": "portion",
     "ref": "箴16:9", "text": "人心筹算自己的道路，惟耶和华指引他的脚步。",
     "ask": "求你叫我甘心交出掌控，喜悦于你智慧慈父般的安排——你的引导比我的计划更可靠。"},
    {"key": "general", "name": "说不清的空缺 / 总觉得不够", "kw": ["不够", "空", "不满", "缺", "少", "总觉得", "得不到", "遗憾"],
     "idol": "把「某个『还没得到的东西』」当成了满足的终极必需——但心的空缺唯有神能填", "lesson": "subtract",
     "ref": "诗23:1", "text": "耶和华是我的牧者，我必不致缺乏。",
     "ask": "求你让我看见：这份『不够』的感觉，是心在呼求你；求你亲自作我够用的那一位。"},
]

CRISIS_WORDS = [
    "自杀", "自残", "不想活", "活不下去", "结束生命", "了结", "轻生", "去死", "死了算了",
    "伤害自己", "撑不下去了", "没有意义活着", "想消失",
]


def _detect_crisis(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in CRISIS_WORDS)


CRISIS_NOTE = (
    "我听见你正承受很重的痛。在我们一起谈知足之前，我想先温柔地说：如果你有伤害自己的念头，"
    "请现在就联系你信任的人，或当地的心理危机热线——你值得有人此刻真实地陪着你。神爱你，"
    "你不必独自扛。（本功能不替代专业帮助。）"
)


def _pick_lack(text: str) -> Dict[str, Any]:
    t = text or ""
    best: Optional[Dict[str, Any]] = None
    best_hits = 0
    for lk in LACKS:
        if lk["key"] == "general":
            continue
        hits = sum(1 for k in lk["kw"] if k in t)
        if hits > best_hits:
            best_hits, best = hits, lk
    if best is None:
        # 「说不清的空缺」的普遍诊断——心的空缺唯有神能填
        return next(lk for lk in LACKS if lk["key"] == "general")
    return best


def meta() -> Dict[str, Any]:
    """知足的定义 + 学校功课 + 奥秘 + 锚点经文（供前端展示）。"""
    return {
        "definition": ("基督徒的知足，是一种甜美、内在、安静、恩典所结的心灵状态；"
                       "甘心顺服并喜悦于神在每一处境中智慧慈父般的安排。"
                       "（意译自 Jeremiah Burroughs《基督徒知足的秘诀》）"),
        "school_lessons": SCHOOL_LESSONS,
        "mystery": "知足的奥秘：不是得着更多，而是让心在神里安息——靠减去过度的欲望、靠信靠神的护理。",
        "verse": "腓4:11-13",
        "principle": "知足不是天生的脾气，是在「知足的学校」里一门门学来的功课（腓4:11「我已经学会」）。",
    }


def analyze(lack: str, *, settings: Any = None, use_ai: bool = False) -> Dict[str, Any]:
    """诊断被错置的期待（把什么次好的当成了终极必需），对照一门学校功课，给腓4锚点 + 操练。"""
    lack = (lack or "").strip()
    crisis = _detect_crisis(lack)
    picked = _pick_lack(lack)
    lesson = LESSON_INDEX[picked["lesson"]]

    diagnosis = (
        "你说的这份缺乏，背后常藏着一个被错置的期待：" + picked["idol"] + "。"
        "Burroughs 会温柔地提醒：不满往往不是因为我们缺了什么，而是因为我们把一个"
        "「暂时的、次好的」东西，当成了「终极的、非有不可」的必需。"
    )
    contrast = (
        "在「知足的学校」里，有一门功课正对着它——" + lesson["lesson"] + "。"
        + lesson["note"] + "（" + lesson["ref"] + "：" + lesson["text"] + "）"
    )
    practices = [
        "数算已有的恩典：今天写下三样你已经从神手里领受的（哪怕很小），"
        "让「拥有」的眼光盖过「缺乏」的眼光。",
        "把这缺乏交托：照着下面的祷告，把「" + picked["name"] + "」这件事，"
        "连同你对它的紧抓，一起交在神智慧慈父般的安排里。",
    ]

    result: Dict[str, Any] = {
        "crisis": crisis,
        "crisis_note": CRISIS_NOTE if crisis else "",
        "lack": {"key": picked["key"], "name": picked["name"]},
        "diagnosis": diagnosis,
        "misplaced_expectation": picked["idol"],
        "school_lesson": {"key": lesson["key"], "lesson": lesson["lesson"], "note": lesson["note"],
                          "scripture": {"ref": lesson["ref"], "text": lesson["text"]}},
        "contrast": contrast,
        "anchor": {"ref": picked["ref"], "text": picked["text"]},
        "phil4_anchor": {"ref": "腓4:11-13",
                         "text": "我并不是因缺乏说这话……我无论在什么景况都可以知足，这是我已经学会了的……"
                                 "我靠着那加给我力量的，凡事都能做。"},
        "prayer": picked["ask"],
        "practices": practices,
        "summary": ("知足不是等环境变好才有的心情，而是此刻就可以在基督里学的功课。"
                    "把过度的欲望减一点，把对神的信靠加一点，心就能在祂里面安息。"),
        "closing": "「敬虔加上知足的心便是大利了。」（提前6:6）",
        "ai_used": False,
    }

    if use_ai:
        enhanced = _ai_enhance(lack, result, settings)
        if enhanced:
            result.update(enhanced)
            result["ai_used"] = True
    return result


def build_prompt(lack: str, base: Dict[str, Any]) -> str:
    return (
        "你是一位温柔、以福音为中心的属灵陪伴者，熟悉 Jeremiah Burroughs《基督徒知足的秘诀》"
        "（The Rare Jewel of Christian Contentment）。知足是在「知足的学校」里学来的功课，"
        "不是斯多亚式的冷漠、也不是压抑不满，而是恩典带来的内在安宁；其奥秘是减去过度的欲望、"
        "信靠神的护理，而非加增所拥有的。请针对用户所说的缺乏，温柔地指出那个被错置的期待"
        "（把什么次好的当成了终极必需），对照一门学校功课，给一个腓立比书4章的锚点和一个可行的操练。"
        "中文，温暖不说教，绝不定罪、不贴标签、不说『你信心不够』『你太贪心』之类的话。\n"
        f"用户所说的缺乏：{lack}\n"
        "请输出 JSON：{\"diagnosis\":\"...\",\"contrast\":\"...\",\"prayer\":\"一段可照着祷告的话\","
        "\"summary\":\"...\",\"closing\":\"一句经文\"}。"
    )


def _ai_enhance(lack: str, base: Dict[str, Any], settings: Any) -> Optional[Dict[str, Any]]:
    """可选 AI 增强：任何失败都回退（返回 None）。"""
    prompt = build_prompt(lack, base)
    raw = _call_ai(prompt, settings)
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        out: Dict[str, Any] = {}
        for k in ("diagnosis", "contrast", "prayer", "summary", "closing"):
            if data.get(k):
                out[k] = str(data[k])
        return out or None
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
    """回流 formation：知足属于「欲望被神安顿 + 盼望 + 成长」。"""
    if result.get("crisis"):
        return (["desire", "hope", "growth"], False, True, 2.0)
    return (["desire", "hope", "growth"], True, True, 5.0)
