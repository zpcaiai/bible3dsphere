"""Rule-based Attention Stewardship helpers.

These helpers intentionally avoid model calls and sensitive raw-text logging.
They provide deterministic diagnosis and warfare-map behavior for local/dev
environments and as the fallback when no AI provider is configured.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
import re
from typing import Any, Iterable

ATTENTION_CATEGORIES = {"worship", "mission", "relationship", "restoration", "captured"}
ATTENTION_STATES = {"peaceful", "focused", "scattered", "restless", "tempted", "numb", "repenting", "restored"}
ATTENTION_PULLS = {
    "anxiety", "comparison", "lust", "greed", "boredom", "escape", "control",
    "fomo", "fatigue", "algorithm", "consumerism", "people_pleasing", "vanity",
    "curiosity_without_purpose",
}

PULL_LABELS = {
    "anxiety": "焦虑",
    "comparison": "比较",
    "lust": "情欲",
    "greed": "贪婪",
    "boredom": "无聊",
    "escape": "逃避",
    "control": "控制欲",
    "fomo": "错失恐惧",
    "fatigue": "疲惫",
    "algorithm": "算法牵引",
    "consumerism": "消费主义",
    "people_pleasing": "讨好人",
    "vanity": "虚荣",
    "curiosity_without_purpose": "无目的好奇",
}

SCRIPTURE_LIBRARY = [
    {"id": "proverbs_4_23", "reference": "箴言 4:23", "text": "你要保守你心，胜过保守一切，因为一生的果效是由心发出。", "tags": ["heart", "attention", "vigilance", "default"]},
    {"id": "psalm_46_10", "reference": "诗篇 46:10", "text": "你们要休息，要知道我是神。", "tags": ["anxiety", "control", "fomo", "rest"]},
    {"id": "matthew_6_21", "reference": "马太福音 6:21", "text": "因为你的财宝在哪里，你的心也在那里。", "tags": ["greed", "consumerism", "treasure", "desire"]},
    {"id": "romans_12_2", "reference": "罗马书 12:2", "text": "不要效法这个世界，只要心意更新而变化。", "tags": ["algorithm", "worldliness", "renewal", "identity"]},
    {"id": "colossians_3_2", "reference": "歌罗西书 3:2", "text": "你们要思念上面的事，不要思念地上的事。", "tags": ["attention", "desire", "renewal"]},
    {"id": "first_corinthians_6_12", "reference": "哥林多前书 6:12", "text": "凡事我都可行，但无论哪一件，我总不受它的辖制。", "tags": ["lust", "addiction", "compulsive", "freedom", "captured"]},
    {"id": "ephesians_5_15_16", "reference": "以弗所书 5:15-16", "text": "你们要谨慎行事，不要像愚昧人，当像智慧人，要爱惜光阴。", "tags": ["time", "stewardship", "mission"]},
    {"id": "philippians_4_6_7", "reference": "腓立比书 4:6-7", "text": "应当一无挂虑，只要凡事借着祷告、祈求和感谢，将你们所要的告诉神。", "tags": ["anxiety", "prayer", "peace"]},
    {"id": "matthew_11_28", "reference": "马太福音 11:28", "text": "凡劳苦担重担的人，可以到我这里来，我就使你们得安息。", "tags": ["fatigue", "rest", "restoration"]},
    {"id": "galatians_1_10", "reference": "加拉太书 1:10", "text": "我现在是要得人的心呢？还是要得神的心呢？", "tags": ["people_pleasing", "comparison", "identity"]},
]

SCRIPTURE_BY_REFERENCE = {s["reference"]: s for s in SCRIPTURE_LIBRARY}
DEFAULT_SCRIPTURE = SCRIPTURE_LIBRARY[0]

CRISIS_RE = re.compile(r"(不想活|结束生命|自杀|轻生|伤害自己|伤害别人|杀了自己|杀人|即时危险|性侵|虐待)")
SENSITIVE_RE = re.compile(r"(色情|情欲|自残|焦虑|创伤|羞耻|成瘾|财务恐惧|家庭冲突|试探)")
SHAMING_WORDS = ["你失败了", "你很糟糕", "神对你很失望", "你就是贪婪", "你就是淫乱", "不够属灵"]


def clean_pulls(values: Iterable[str] | None) -> list[str]:
    cleaned: list[str] = []
    for value in values or []:
        value = str(value)
        if value in ATTENTION_PULLS and value not in cleaned:
            cleaned.append(value)
    return cleaned


def scripture_for_tags(tags: Iterable[str], limit: int = 2) -> list[dict]:
    tagset = set(tags or [])
    matched = [s for s in SCRIPTURE_LIBRARY if tagset.intersection(s["tags"])]
    if not matched:
        matched = [DEFAULT_SCRIPTURE]
    return [
        {"reference": s["reference"], "text": s["text"], "reason": "这段经文适合回应当前注意力牵引。"}
        for s in matched[:limit]
    ]


def validate_scriptures(items: list[dict] | None, tags: Iterable[str] = ()) -> list[dict]:
    result = []
    for item in items or []:
        ref = (item or {}).get("reference")
        if ref in SCRIPTURE_BY_REFERENCE:
            s = SCRIPTURE_BY_REFERENCE[ref]
            result.append({"reference": s["reference"], "text": s["text"], "reason": (item or {}).get("reason") or "来自守心经文库。"})
    return result[:3] or scripture_for_tags(tags, 2)


def safety_check(*texts: str | None) -> dict:
    joined = "\n".join([t for t in texts if t])[:6000]
    if CRISIS_RE.search(joined):
        return {"level": "crisis", "reasons": ["crisis_keyword"], "shouldCallModel": False}
    if SENSITIVE_RE.search(joined):
        return {"level": "sensitive", "reasons": ["sensitive_keyword"], "shouldCallModel": True}
    return {"level": "normal", "reasons": [], "shouldCallModel": True}


def calculate_daily_summary(entries: list[dict]) -> dict:
    buckets = {"worship": 0, "mission": 0, "relationship": 0, "restoration": 0, "captured": 0}
    pull_counts: Counter[str] = Counter()
    pull_minutes: Counter[str] = Counter()
    for entry in entries or []:
        category = entry.get("category")
        minutes = int(entry.get("durationMinutes") or entry.get("duration_minutes") or 0)
        if category in buckets:
            buckets[category] += minutes
        for pull in clean_pulls(entry.get("pulls")):
            pull_counts[pull] += 1
            pull_minutes[pull] += minutes
    top_pulls = [
        {"pull": pull, "label": PULL_LABELS.get(pull, pull), "count": count, "minutes": pull_minutes[pull]}
        for pull, count in pull_counts.most_common(5)
    ]
    invested = buckets["worship"] + buckets["mission"] + buckets["relationship"] + buckets["restoration"]
    return {
        "totalMinutes": invested + buckets["captured"],
        "investedMinutes": invested,
        "capturedMinutes": buckets["captured"],
        "categoryMinutes": buckets,
        "entriesCount": len(entries or []),
        "topPulls": top_pulls,
    }


def _pattern_from_context(ctx: dict) -> dict:
    summary = ctx.get("ledger") or {}
    top = [p.get("pull") for p in summary.get("topPulls") or []]
    risk = ((ctx.get("covenant") or {}).get("mainRisk") or "").lower()
    entries = ctx.get("entries") or []
    activity = " ".join([str(e.get("activityName") or e.get("activity_name") or "") for e in entries]).lower()
    text = f"{risk} {activity}"
    if "lust" in top or any(k in text for k in ["色情", "情欲", "擦边"]):
        return {"key": "lust_escape_shame", "label": "情欲试探与逃避牵引", "tags": ["lust", "captured"], "root": "这可能不只是欲望本身，也可能和疲惫、孤独、压力或逃避有关。"}
    if "fomo" in top or any(k in text for k in ["ai", "资讯", "新闻", "股价", "行情", "财经"]):
        return {"key": "fomo_information_anxiety", "label": "资讯焦虑与错失恐惧", "tags": ["fomo", "anxiety"], "root": "你可能在用更多信息寻找安全感，害怕错过机会或落后于时代。"}
    if "anxiety" in top or "control" in top:
        return {"key": "anxiety_control", "label": "焦虑与控制欲", "tags": ["anxiety", "control"], "root": "你可能正在尝试通过更多确认、更多查看或更多掌控来获得安全感。"}
    if "comparison" in top or "vanity" in top:
        return {"key": "comparison_identity", "label": "比较与身份焦虑", "tags": ["comparison", "identity"], "root": "你的注意力可能被别人的成就、形象或评价牵引，导致自我价值变得不稳定。"}
    if any(p in top for p in ["fatigue", "escape", "boredom", "algorithm"]):
        return {"key": "fatigue_escape_algorithm", "label": "疲惫、逃避与算法牵引", "tags": ["fatigue", "rest"], "root": "你可能不是单纯不自律，而是在疲惫或空虚时，被算法提供的即时刺激牵走。"}
    if "greed" in top or "consumerism" in top or any(k in text for k in ["购物", "消费", "投资冲动"]):
        return {"key": "greed_consumerism_security", "label": "消费主义、贪婪与安全感", "tags": ["greed", "consumerism"], "root": "注意力可能被“得到更多就会更安全”的声音牵引。"}
    focus = ctx.get("focus") or {}
    if summary.get("capturedMinutes", 0) == 0 and focus.get("totalActualMinutes", 0) > 0:
        return {"key": "faithful_stewardship", "label": "忠心的注意力管家", "tags": ["mission", "stewardship"], "root": "今天你的注意力有明显投入到敬拜、使命、关系或恢复中，这是可以感恩的忠心一步。"}
    return {"key": "insufficient_data", "label": "记录不足", "tags": ["default"], "root": "目前记录不足，适合先做温柔觉察，而不是急着下结论。"}


def crisis_result() -> dict:
    return {
        "title": "请先确保你的安全",
        "shortSummary": "你提到的内容可能涉及即时安全风险。此刻最重要的是尽快联系现实中的帮助。",
        "safetyLevel": "crisis",
        "confidence": "high",
        "primaryPattern": {"key": "crisis_safety", "label": "即时安全优先", "description": "请先联系身边可信任的人、当地紧急服务或专业危机援助。", "evidence": [], "confidence": "high"},
        "secondaryPatterns": [],
        "attentionPulls": [],
        "graceNoticed": ["你愿意说出危险信号，本身就是寻求帮助的重要一步。"],
        "repentanceInvitation": {"title": "先暂停分析", "content": "现在不需要继续做注意力分析，请优先让自己处在安全环境中。", "notShamingReminder": "这不是定罪，而是安全优先。"},
        "scriptureSuggestions": [{"reference": DEFAULT_SCRIPTURE["reference"], "text": DEFAULT_SCRIPTURE["text"], "reason": "在安全之后，可以再慢慢回到守心反思。"}],
        "prayer": "主啊，求你帮助我现在找到现实中的帮助，也赐给身边的人及时陪伴和保护。",
        "actionPlan": {"todayReset": "现在联系可信任的人或当地紧急服务。", "tomorrowBoundary": "等安全稳定后，再回到守心复盘。", "replacementPractice": "不要独自承受，先寻求现实帮助。", "concreteNextStep": "立刻去一个安全地方，并联系现实中的人。"},
        "reflectionQuestions": ["我现在可以联系谁？", "我如何让自己先处在安全环境中？"],
        "disclaimer": "AI 守心洞察不能替代现实中的紧急帮助、牧者、辅导或专业支持。",
    }


def normalize_diagnosis(result: dict, tags: Iterable[str] = ()) -> dict:
    result = dict(result or {})
    result["safetyLevel"] = result.get("safetyLevel") if result.get("safetyLevel") in {"normal", "sensitive", "crisis"} else "normal"
    result["confidence"] = result.get("confidence") if result.get("confidence") in {"low", "medium", "high"} else "medium"
    result.setdefault("title", "今日守心洞察")
    result.setdefault("shortSummary", "从你的记录中可以观察到一些注意力方向，适合带到神面前温柔省察。")
    result.setdefault("primaryPattern", {"key": "insufficient_data", "label": "记录不足", "description": "记录还不够完整。", "evidence": [], "confidence": "low"})
    result.setdefault("secondaryPatterns", [])
    result.setdefault("attentionPulls", [])
    result.setdefault("graceNoticed", ["你愿意回到这里看见自己的注意力，就是归回的开始。"])
    result.setdefault("repentanceInvitation", {"title": "温柔归回", "content": "可以把今天被牵引的地方带到神面前。", "notShamingReminder": "这不是为了定罪，而是一次重新归回的邀请。"})
    result["scriptureSuggestions"] = validate_scriptures(result.get("scriptureSuggestions"), tags)
    result.setdefault("prayer", "主啊，求你帮助我看见注意力被什么牵引，并在恩典中重新归回。")
    action = dict(result.get("actionPlan") or {})
    action.setdefault("tomorrowBoundary", "明天先设一道小而具体的边界。")
    action.setdefault("replacementPractice", "想分心时，先停下 30 秒祷告。")
    action.setdefault("concreteNextStep", "写下下一步最小行动，并开始 5 分钟。")
    result["actionPlan"] = action
    if len(result.get("reflectionQuestions") or []) < 2:
        result["reflectionQuestions"] = ["今天我的注意力主要献给了什么？", "明天哪一道边界可以帮助我更自由？"]
    result.setdefault("disclaimer", "这是基于你记录的属灵反思辅助，不是定罪、预言或专业心理诊断。")
    as_text = str(result)
    if any(word in as_text for word in SHAMING_WORDS):
        result["shortSummary"] = "这里可能有一个需要被温柔看见的注意力模式。看见不是为了定罪，而是为了重新得自由。"
    return result


def generate_fallback_diagnosis(ctx: dict, safety_level: str = "normal", quick: bool = False) -> dict:
    if safety_level == "crisis":
        return crisis_result()
    pattern = _pattern_from_context(ctx)
    summary = ctx.get("ledger") or {}
    top_pulls = summary.get("topPulls") or []
    tags = pattern["tags"]
    title = "现在归回" if quick else "今日守心洞察"
    evidence = []
    if summary.get("entriesCount"):
        evidence.append(f"今天记录了 {summary.get('entriesCount')} 条注意力账本。")
    if summary.get("capturedMinutes"):
        evidence.append(f"被掳型注意力约 {summary.get('capturedMinutes')} 分钟。")
    if top_pulls:
        evidence.append("主要牵引包含：" + "、".join([p.get("label", p.get("pull")) for p in top_pulls[:3]]) + "。")
    if not evidence:
        evidence = ["今天的记录还不够完整。"]
    pulls = [
        {
            "pull": p["pull"],
            "label": p.get("label") or PULL_LABELS.get(p["pull"], p["pull"]),
            "observation": "从记录中可以观察到这个牵引有出现。",
            "possibleRoot": pattern["root"],
            "gentlePractice": "先设一道小边界，并把冲动转化为一个具体行动。",
        }
        for p in top_pulls[:3]
    ]
    if not pulls and pattern["key"] not in {"insufficient_data", "faithful_stewardship"}:
        for pull in tags[:2]:
            if pull in ATTENTION_PULLS:
                pulls.append({"pull": pull, "label": PULL_LABELS.get(pull, pull), "observation": "这个牵引可能与当前记录有关。", "possibleRoot": pattern["root"], "gentlePractice": "想被牵走时，先停下 30 秒归回。"})
    result = {
        "title": title,
        "shortSummary": "从你的记录中可以观察到：" + pattern["label"] + "可能是今天需要温柔留意的模式。",
        "safetyLevel": safety_level,
        "confidence": "low" if pattern["key"] == "insufficient_data" else "medium",
        "primaryPattern": {"key": pattern["key"], "label": pattern["label"], "description": pattern["root"], "evidence": evidence, "confidence": "low" if pattern["key"] == "insufficient_data" else "medium"},
        "secondaryPatterns": [],
        "attentionPulls": pulls,
        "graceNoticed": ["你愿意记录并回顾注意力，这本身就是归回的开始。", "每一次诚实看见，都可以成为重新自由的一步。"],
        "repentanceInvitation": {"title": "从牵引中归回", "content": pattern["root"] + " 可以把这件事带到神面前，承认自己的有限，并重新选择忠心。", "notShamingReminder": "这不是为了定罪，而是一次重新归回的邀请。"},
        "scriptureSuggestions": scripture_for_tags(tags, 2),
        "prayer": "主啊，求你帮助我不被这些牵引驱赶，而是在你面前重新得自由，忠心回应今天的托付。",
        "actionPlan": {
            "todayReset": "现在停下 30 秒，把正在牵引你的事交托给神。",
            "tomorrowBoundary": _tomorrow_boundary(pattern["key"]),
            "replacementPractice": _replacement_practice(pattern["key"]),
            "concreteNextStep": "接下来 5 分钟只做一个最小行动，而不是继续被牵引。",
            "accountabilityPrompt": "如果这个模式反复出现，可以考虑找可信任的牧者、守望伙伴或专业辅导同行。",
        },
        "reflectionQuestions": ["我真正害怕或渴望的是什么？", "明天哪一道具体边界能帮助我归回？"],
        "disclaimer": "这是基于你记录的属灵反思辅助，不是定罪、预言或专业心理诊断。",
    }
    return normalize_diagnosis(result, tags)


def _tomorrow_boundary(key: str) -> str:
    return {
        "fomo_information_anxiety": "明天先完成一个 60 分钟使命任务，再进入资讯窗口；资讯查看限制在 30 分钟内。",
        "anxiety_control": "把最焦虑的信息源放到固定查看窗口，不在睡前查看。",
        "comparison_identity": "明天减少社交媒体浏览；如果要浏览，先完成一个自己的使命任务。",
        "lust_escape_shame": "避开高风险场景；夜间独处时减少高风险 App；受试探时立即离开环境，并联系守望伙伴。",
        "fatigue_escape_algorithm": "晚上 9 点后减少屏幕使用；睡前手机离开床边。",
        "greed_consumerism_security": "购物或投资冲动前等待 24 小时；先写下真实需要和预算边界。",
    }.get(key, "明天先记录 3 段注意力，并为最容易被牵引的时段设一道小边界。")


def _replacement_practice(key: str) -> str:
    return {
        "fomo_information_anxiety": "每次想刷新资讯前，先写下“我真正害怕错过什么？”",
        "anxiety_control": "焦虑时做 1 分钟交托祷告，并写下今天能忠心做的一件事。",
        "comparison_identity": "想比较时，写下 3 个感恩和 1 个今天被托付的小忠心。",
        "lust_escape_shame": "冲动出现时，不与它谈判，先离开场景、喝水、走动，并做 30 秒祷告。",
        "fatigue_escape_algorithm": "想刷短视频时，先做一个低门槛恢复动作：散步 5 分钟、喝水或安静祷告。",
        "greed_consumerism_security": "做一个知足操练：写下今天已经领受的 3 个供应。",
    }.get(key, "停下 30 秒祷告，然后做一个 5 分钟最小行动。")


def compact_context_summary(ctx: dict) -> dict:
    summary = ctx.get("ledger") or {}
    focus = ctx.get("focus") or {}
    return {
        "date": ctx.get("userLocalDate"),
        "diagnosisType": ctx.get("diagnosisType", "daily"),
        "hasCovenant": bool((ctx.get("covenant") or {}).get("exists")),
        "hasReview": bool((ctx.get("review") or {}).get("exists")),
        "totalMinutes": summary.get("totalMinutes", 0),
        "investedMinutes": summary.get("investedMinutes", 0),
        "capturedMinutes": summary.get("capturedMinutes", 0),
        "topPulls": [p.get("pull") for p in (summary.get("topPulls") or [])[:5]],
        "focusMinutes": focus.get("totalActualMinutes", 0),
        "entriesCount": summary.get("entriesCount", 0),
    }


def calculate_intensity(score: float) -> str:
    if score <= 0:
        return "none"
    if score < 15:
        return "low"
    if score < 35:
        return "medium"
    return "high"


def suggested_next_step(intensity: str) -> str:
    return {
        "none": "近期没有明显记录。可以继续保持觉察。",
        "low": "这个牵引有轻微出现，可以先设一道简单边界。",
        "medium": "这个牵引近期值得留意，建议建立一个守心计划。",
        "high": "这个牵引近期较明显，建议今天就设立具体边界，并考虑邀请守望伙伴同行。",
    }.get(intensity, "可以先保持温柔觉察。")


def pattern_definitions() -> list[dict]:
    def p(key, label, short, primary, related, desc, truth, tags):
        scriptures = scripture_for_tags(tags, 3)
        return {
            "key": key, "label": label, "shortLabel": short, "description": desc,
            "primaryPulls": primary, "relatedPulls": related,
            "commonTriggers": ["任务困难时", "疲惫或不确定时", "睡前或独处时"],
            "commonBehaviors": ["反复查看", "无目的停留", "用更多刺激代替安静行动"],
            "possibleRoots": ["安全感转向可见事物", "用刺激或掌控缓解不安", "疲惫时防线降低"],
            "gospelTruth": truth,
            "scriptureSuggestions": scriptures,
            "boundaryTemplates": {
                "digital": ["把高牵引来源放到固定窗口。"],
                "time": ["给这类活动设定清楚结束时间。"],
                "spiritual": ["想被牵走时，先祷告 30 秒。"],
            },
            "replacementPractices": ["做 5 分钟使命专注", "写下真实需要", "散步或安静祷告"],
            "escapePlanTemplates": ["关闭页面", "离开当前场景", "打开今天的使命任务"],
            "reflectionQuestions": ["我真正害怕或渴望什么？", "今天神托付我忠心的一步是什么？"],
            "gentleWarning": "看见这个模式不是为了定罪，而是为了提前铺好归回路径。",
        }
    return [
        p("fomo_information_anxiety", "资讯焦虑与错失恐惧", "资讯焦虑", ["fomo", "anxiety"], ["control", "curiosity_without_purpose", "algorithm"], "你可能在用更多资讯寻找安全感。", "你的安全感不是来自知道所有信息，而是来自神的同在与今日忠心。", ["fomo", "anxiety"]),
        p("anxiety_control", "焦虑与控制欲", "焦虑控制", ["anxiety", "control"], ["fomo", "fatigue", "escape"], "你可能在不确定中试图通过掌控获得安全感。", "你被呼召忠心，不是被要求掌控所有结果。", ["anxiety", "control"]),
        p("comparison_identity", "比较与身份焦虑", "比较身份", ["comparison", "vanity"], ["people_pleasing", "consumerism", "anxiety"], "你的注意力可能被别人的成就或评价牵引。", "你的价值不是由比较决定，而是在基督里先被认识、被爱、被呼召。", ["comparison", "identity"]),
        p("lust_escape_shame", "情欲试探与逃避牵引", "情欲逃避", ["lust", "escape"], ["fatigue", "boredom", "algorithm"], "这类牵引可能和疲惫、孤独、压力或逃避有关。", "认罪与归回不是羞耻的终点，而是恩典和自由的开始。", ["lust", "captured"]),
        p("greed_consumerism_security", "消费主义、贪婪与安全感", "消费安全感", ["greed", "consumerism"], ["anxiety", "comparison", "control"], "你的注意力可能被更多拥有带来的安全感牵引。", "真正的供应和身份来自神的看顾与知足中的自由。", ["greed", "consumerism"]),
        p("fatigue_escape_algorithm", "疲惫、逃避与算法牵引", "疲惫逃避", ["fatigue", "escape", "algorithm"], ["boredom", "curiosity_without_purpose", "anxiety"], "你可能在疲惫或任务压力下被即时刺激牵走。", "真正的安息不是被算法麻醉，而是在神面前承认有限并被恢复。", ["fatigue", "rest"]),
        p("people_pleasing_approval", "讨好人、认可焦虑与过度回应", "讨好认可", ["people_pleasing", "anxiety"], ["comparison", "vanity", "control"], "你的注意力可能过度被别人的期待和评价牵引。", "爱人不等于被所有人的期待掌控；你先属于神，才能更自由地爱人。", ["people_pleasing"]),
        p("anger_controversy", "争论、怒气与情绪喂养", "争论怒气", ["control", "vanity"], ["anxiety", "comparison", "curiosity_without_purpose"], "你的注意力可能被争论、热点或证明自己正确的冲动牵引。", "真理不需要靠怒气来证明；你可以选择温柔、节制和真实的和平。", ["renewal", "identity"]),
        p("numbness_escape", "麻木、空虚与无目的逃避", "麻木逃避", ["escape", "boredom"], ["fatigue", "algorithm", "curiosity_without_purpose"], "注意力可能在麻木、空虚或无方向中慢慢流失。", "在麻木中，也可以从一个很小的归回动作开始。", ["rest", "default"]),
    ]


KEYWORDS = {
    "fomo_information_anxiety": ["AI", "资讯", "新闻", "股价", "行情", "热点", "错过", "FOMO", "新工具", "趋势", "财经"],
    "anxiety_control": ["焦虑", "控制", "反复确认", "查消息", "等回复", "担心", "不安"],
    "comparison_identity": ["比较", "羡慕", "嫉妒", "别人成功", "社交媒体", "认可", "不够好"],
    "lust_escape_shame": ["色情", "情欲", "擦边", "试探", "黄色", "私欲"],
    "greed_consumerism_security": ["购物", "消费", "优惠", "投资冲动", "贪心", "赚钱", "暴富", "下单"],
    "fatigue_escape_algorithm": ["短视频", "刷视频", "推荐", "算法", "无聊", "逃避", "疲惫", "熬夜"],
    "people_pleasing_approval": ["讨好", "认可", "立刻回复", "怕别人失望", "消息", "评价"],
    "anger_controversy": ["争论", "评论区", "生气", "怒气", "热点", "反驳", "骂战"],
    "numbness_escape": ["麻木", "空虚", "发呆", "无目的", "不知道做什么", "切换 App"],
}


def match_pattern_keywords(text: str | None, pattern_key: str) -> bool:
    value = str(text or "")
    return any(k.lower() in value.lower() for k in KEYWORDS.get(pattern_key, []))


def score_warfare_patterns(data: dict) -> list[dict]:
    patterns = pattern_definitions()
    entries = data.get("entries") or []
    covenants = data.get("covenants") or []
    focus_sessions = data.get("focusSessions") or []
    reviews = data.get("reviews") or []
    diagnoses = data.get("diagnoses") or []
    checkins = data.get("checkins") or []
    scores = []
    for pattern in patterns:
        key = pattern["key"]
        score = 0.0
        entries_count = 0
        captured_minutes = 0
        focus_interruptions = 0
        pull_counts: Counter[str] = Counter()
        pull_minutes: Counter[str] = Counter()
        covenant_signals: list[str] = []
        review_signals: list[str] = []
        diagnosis_signals: list[str] = []
        primary = set(pattern["primaryPulls"])
        related = set(pattern["relatedPulls"])
        for entry in entries:
            pulls = set(clean_pulls(entry.get("pulls")))
            minutes = int(entry.get("durationMinutes") or entry.get("duration_minutes") or 0)
            matched_primary = pulls.intersection(primary)
            matched_related = pulls.intersection(related)
            if matched_primary or matched_related or match_pattern_keywords(entry.get("activityName") or entry.get("activity_name"), key):
                entries_count += 1
            for pull in matched_primary:
                score += 8
                pull_counts[pull] += 1
                pull_minutes[pull] += minutes
            for pull in matched_related:
                score += 4
                pull_counts[pull] += 1
                pull_minutes[pull] += minutes
            if (entry.get("category") == "captured") and (matched_primary or match_pattern_keywords(entry.get("activityName") or entry.get("activity_name"), key)):
                captured_minutes += minutes
                score += minutes / (5 if matched_primary else 8)
        for covenant in covenants:
            if set(clean_pulls(covenant.get("riskPulls") or covenant.get("risk_pulls"))).intersection(primary):
                score += 10
                covenant_signals.append("最近立约中多次选择了相关牵引。")
            if match_pattern_keywords(covenant.get("mainRisk") or covenant.get("main_risk"), key):
                score += 8
                covenant_signals.append("最近立约中出现了与该模式相关的风险。")
        for session in focus_sessions:
            if session.get("interrupted"):
                if match_pattern_keywords(session.get("interruptionReason") or session.get("interruption_reason"), key):
                    score += 8
                    focus_interruptions += 1
                elif key in {"fatigue_escape_algorithm", "anxiety_control"}:
                    score += 3
                    focus_interruptions += 1
        for review in reviews:
            text = " ".join([str(review.get(k) or "") for k in ["biggestCapture", "biggest_capture", "repentancePoint", "repentance_point"]])
            if match_pattern_keywords(text, key):
                score += 8
                review_signals.append("晚间复盘中出现与该模式相关的描述。")
        for diag in diagnoses:
            result = diag.get("result") or {}
            primary_pattern = (result.get("primaryPattern") or {})
            if primary_pattern.get("key") == key:
                score += 20
                diagnosis_signals.append(f"最近 AI 守心洞察识别到：{primary_pattern.get('label') or pattern['label']}")
            elif match_pattern_keywords(result.get("shortSummary"), key):
                score += 5
                diagnosis_signals.append("最近 AI 守心洞察摘要中出现相关模式。")
        for checkin in checkins:
            if checkin.get("patternKey") == key or checkin.get("pattern_key") == key:
                score += {"captured": 8, "returned": 4, "resisted": 2, "escaped": 2}.get(checkin.get("status"), 0)
        intensity = calculate_intensity(score)
        scores.append({
            "patternKey": key,
            "label": pattern["label"],
            "intensity": intensity,
            "score": round(score, 1),
            "evidence": {
                "entriesCount": entries_count,
                "capturedMinutes": captured_minutes,
                "pullMatches": [{"pull": p, "label": PULL_LABELS.get(p, p), "count": c, "minutes": pull_minutes[p]} for p, c in pull_counts.most_common(5)],
                "covenantRiskMatches": list(dict.fromkeys(covenant_signals))[:3],
                "reviewSignals": list(dict.fromkeys(review_signals))[:3],
                "diagnosisSignals": list(dict.fromkeys(diagnosis_signals))[:3],
                "focusInterruptions": focus_interruptions,
            },
            "suggestedNextStep": suggested_next_step(intensity),
        })
    return sorted(scores, key=lambda item: item["score"], reverse=True)


def build_warfare_map(data: dict, from_date: date, to_date: date) -> dict:
    scores = score_warfare_patterns(data)
    entries = data.get("entries") or []
    summary = calculate_daily_summary(entries)
    active_plans = data.get("activePlans") or []
    checkins = data.get("checkins") or []
    interrupted = len([s for s in (data.get("focusSessions") or []) if s.get("interrupted")])
    primary = next((s for s in scores if s["intensity"] != "none"), None)
    return {
        "range": {"from": from_date.isoformat(), "to": to_date.isoformat(), "days": (to_date - from_date).days + 1},
        "summary": {
            "totalEntries": len(entries),
            "totalCapturedMinutes": summary["capturedMinutes"],
            "totalInvestedMinutes": summary["investedMinutes"],
            "focusInterruptedCount": interrupted,
            "activePlansCount": len(active_plans),
            "checkinsCount": len(checkins),
        },
        "primaryPattern": primary,
        "patternScores": scores,
        "activePlans": active_plans,
        "recentCheckins": checkins[:10],
        "recentDiagnosisPatterns": data.get("recentDiagnosisPatterns") or [],
    }
