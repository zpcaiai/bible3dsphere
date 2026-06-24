"""
narrative_engine.py — Narrative Rewriter Agent / 福音叙事重写 Agent

人不只活在概念里，也活在故事里。本引擎识别用户的「旧生命叙事模板」，并生成清晰、
可默想、可操练的「福音新叙事」：旧叙事 → 核心恐惧 → 隐藏偶像 → 核心谎言 →
福音真理 → 新叙事 → 操练。

安全原则
========
- 不强迫立刻「正能量」；苦难/创伤/哀伤类叙事允许哀哭。
- 不把真实受伤简单改写成「你要感恩」。
- 新叙事以恩典、身份、盼望、顺服为核心。
- 复用 truth_mapper_engine 获取福音真理 / 经文 / 圣经人物 / 操练。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from backend import truth_mapper_engine as tm
except Exception:  # pragma: no cover
    import truth_mapper_engine as tm  # type: ignore

try:
    from backend import worldview_llm as _llm
except Exception:  # pragma: no cover
    try:
        import worldview_llm as _llm  # type: ignore
    except Exception:
        _llm = None  # type: ignore


# 7 个旧叙事模板
TEMPLATES: List[Dict[str, Any]] = [
    {
        "key": "achievement", "idol": "success",
        "keywords": ["成就", "成功", "失败", "证明", "赢", "超过别人", "没价值"],
        "old_template": "我必须 ______，否则我就是个失败者。",
        "core_fear": "被证明没有价值、被忽视。",
        "core_lie": "我的价值取决于我的成就。",
        "new_template": "我可以忠心工作、追求卓越，但不再用成就定义我的价值——因为在基督里我已被接纳。",
    },
    {
        "key": "control", "idol": "control",
        "keywords": ["掌控", "控制", "确定", "计划", "不确定", "崩溃"],
        "old_template": "只有当 ______ 都在我掌控中，我才安全。",
        "core_fear": "失控、不可预测带来的灾难。",
        "core_lie": "我必须掌控一切才安全。",
        "new_template": "我可以尽责地预备，然后把结果交托给那位真正掌权、且爱我的神，在有限中安息。",
    },
    {
        "key": "money", "idol": "money",
        "keywords": ["钱", "财务", "资产", "安全感", "贫穷", "收入"],
        "old_template": "只要我拥有 ______，我才有底气和安全感。",
        "core_fear": "匮乏、失去保障。",
        "core_lie": "金钱是我的安全感。",
        "new_template": "我可以智慧地管理钱财，但我的安全感建立在那位信实供应的天父身上，而非余额。",
    },
    {
        "key": "relationship", "idol": "relationship",
        "keywords": ["被爱", "认可", "关系", "孤独", "离不开", "某个人"],
        "old_template": "如果 ______ 不爱我 / 不认可我，我就没有价值。",
        "core_fear": "被拒绝、被抛弃。",
        "core_lie": "被人爱和认可决定我的价值。",
        "new_template": "我可以真诚地爱人、被爱，但我的终极身份来自神永不离弃的接纳，所以我能自由地爱而非抓取。",
    },
    {
        "key": "technology", "idol": "technology",
        "keywords": ["技术", "ai", "效率", "淘汰", "未来", "跟不上"],
        "old_template": "只要我掌握 ______，我就能掌握命运、不被淘汰。",
        "core_fear": "被时代淘汰、被取代。",
        "core_lie": "技术决定我的未来与价值。",
        "new_template": "我可以受呼召地学习与使用技术作治理的工具，但我的价值与未来在神手中，不在算力或效率里。",
    },
    {
        "key": "victim", "idol": "victimhood",
        "keywords": ["受害", "没人懂", "过去", "都怪", "永远", "无意义"],
        "old_template": "因为 ______ 发生过，所以我永远只能是 ______。",
        "core_fear": "再次受伤、痛苦不被看见。",
        "core_lie": "我的过去决定我的全部人生。",
        "new_template": "我承认真实的伤害（不否认、不假装），同时把定义我的权利交还给神——我的过去是故事的一部分，不是结局。",
    },
    {
        "key": "spiritual_performance", "idol": "spiritual_performance",
        "keywords": ["灵修", "表现", "配得", "不喜悦", "够好", "属灵"],
        "old_template": "只有我做到 ______，神才会接纳我。",
        "core_fear": "不够好、被神拒绝。",
        "core_lie": "我必须表现属灵，神才接纳我。",
        "new_template": "我可以渴慕亲近神、操练敬虔，但我被接纳是因为基督的义，不是我的表现——我可以停止表演，开始相交。",
    },
]
_TEMPLATE_INDEX = {t["key"]: t for t in TEMPLATES}
_IDOL_TO_TEMPLATE = {t["idol"]: t["key"] for t in TEMPLATES}


def _detect_template(raw_text: str, idol_category: Optional[str]) -> Optional[Dict[str, Any]]:
    if idol_category and idol_category in _IDOL_TO_TEMPLATE:
        return _TEMPLATE_INDEX[_IDOL_TO_TEMPLATE[idol_category]]
    low = (raw_text or "").lower()
    best, best_hits = None, 0
    for t in TEMPLATES:
        hits = sum(1 for kw in t["keywords"] if kw.lower() in low)
        if hits > best_hits:
            best, best_hits = t, hits
    return best if best_hits >= 1 else None


def rewrite(*, raw_text: str = "", idol_category: Optional[str] = None,
            domain: Optional[str] = None, use_ai: bool = False) -> Dict[str, Any]:
    """生成福音叙事重写；use_ai 时润色 newNarrative / gospelTruth（经文与操练保持确定性）。"""
    out = _rewrite_deterministic(raw_text=raw_text, idol_category=idol_category, domain=domain)
    if not use_ai or _llm is None:
        return out
    system = ("你是福音叙事辅导助手。基于给定的旧叙事/核心恐惧/核心谎言/福音真理，用温柔、"
              "以恩典与身份为中心的中文，改写 newNarrative（2-4句，第一人称）与 gospelTruth（1-2句）。"
              "允许哀伤，不强行正能量；**不要**引用具体经文出处。"
              "只输出 JSON：{\"newNarrative\":\"...\",\"gospelTruth\":\"...\"}")
    user = (f"旧叙事：{out.get('oldNarrative')}\n核心恐惧：{out.get('coreFear')}\n"
            f"核心谎言：{out.get('coreLie')}\n隐藏偶像：{out.get('hiddenIdol')}\n"
            f"当前 gospelTruth：{out.get('gospelTruth')}\n当前 newNarrative：{out.get('newNarrative')}")
    try:
        ai = _llm.enhance(system, user, temperature=0.55, max_tokens=400)
        return _llm.merge_fields(out, ai, ["newNarrative", "gospelTruth"])
    except Exception:
        return out


def _rewrite_deterministic(*, raw_text: str = "", idol_category: Optional[str] = None,
                           domain: Optional[str] = None) -> Dict[str, Any]:
    """
    生成一份福音叙事重写。若识别不到模板，返回通用的恩典叙事兜底。
    """
    tpl = _detect_template(raw_text, idol_category)
    if tpl is None:
        # 兜底：用 truth_mapper 的通用福音
        gm = tm.map_one(domain=domain, idol_category=idol_category, lie=raw_text)
        return {
            "oldNarrative": raw_text or "（未提供旧叙事）",
            "oldNarrativeTemplate": "我必须 ______，否则 ______。",
            "coreFear": "未能明确识别——值得在神面前慢慢省察。",
            "hiddenIdol": idol_category or "unknown",
            "coreLie": "我在用某样东西代替神，作为我的安全与价值。",
            "gospelTruth": gm["biblicalTruth"],
            "newNarrative": gm["gospelReframe"],
            "scriptureRefs": gm["scriptureRefs"],
            "recommendedBiblePersons": gm["recommendedBiblePersons"],
            "practicePlan": _practice_plan(gm["practiceSuggestions"]),
            "reflectionQuestions": _reflection_questions(),
        }

    gm = tm.map_one(domain=domain, idol_category=tpl["idol"], lie=tpl["core_lie"])
    return {
        "oldNarrative": raw_text or tpl["old_template"],
        "oldNarrativeTemplate": tpl["old_template"],
        "coreFear": tpl["core_fear"],
        "hiddenIdol": tpl["idol"],
        "coreLie": tpl["core_lie"],
        "gospelTruth": gm["biblicalTruth"],
        "newNarrative": tpl["new_template"],
        "scriptureRefs": gm["scriptureRefs"],
        "recommendedBiblePersons": gm["recommendedBiblePersons"],
        "practicePlan": _practice_plan(gm["practiceSuggestions"]),
        "reflectionQuestions": _reflection_questions(),
    }


def _practice_plan(suggestions: List[str]) -> List[str]:
    """规格：今日默想 / 一句反谎言祷告 / 一个具体顺服行动 / 一个关系连接行动。"""
    plan = ["今日默想：把新叙事读三遍，记下神在其中向你说的一句话。",
            "反谎言祷告：『主啊，我承认我曾相信那个谎言；今天我选择相信你的真理。』"]
    if suggestions:
        plan.append("顺服行动：" + suggestions[0])
    plan.append("关系连接：把这份新叙事告诉一位属灵同伴，请他为你祷告。")
    return plan


def _reflection_questions() -> List[str]:
    return [
        "当我相信旧叙事时，我的情绪、行为、关系受到了什么影响？",
        "新叙事里，神向我启示了祂怎样的性情？",
        "这周有哪一个具体处境，可以让我开始照新叙事而活？",
    ]


def meta() -> Dict[str, Any]:
    return {"templates": [{"key": t["key"], "idol": t["idol"],
                           "old_template": t["old_template"]} for t in TEMPLATES]}
