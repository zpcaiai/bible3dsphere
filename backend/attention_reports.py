"""Rule-based weekly reports and stewardship scores for Attention Stewardship.

Scores are rhythm indicators only. These helpers intentionally work from
summaries and booleans rather than sensitive raw notes or prayers.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Any

try:
    from backend.attention_domain import PULL_LABELS, calculate_daily_summary
except Exception:  # pragma: no cover
    from attention_domain import PULL_LABELS, calculate_daily_summary  # type: ignore


CATEGORIES = ("worship", "mission", "relationship", "restoration", "captured")
SCORE_LABELS = {
    "insufficient_data": "记录不足",
    "needs_gentle_attention": "需要温柔留意",
    "returning": "正在归回",
    "steady": "稳定操练",
    "growing": "持续成长",
    "flourishing": "节奏丰盛",
}
COMPONENT_META = {
    "covenant": ("今日立约方向", 15),
    "investedAttention": ("投入型注意力", 25),
    "capturedAwareness": ("被牵引觉察", 20),
    "reflectionReturn": ("复盘与归回", 20),
    "focusAndFollowThrough": ("专注与执行", 10),
    "restorationAndRelationship": ("恢复与关系", 10),
}


def list_dates(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def normalize_week_start(value: date) -> date:
    return value - timedelta(days=value.weekday())


def week_range_from_start(week_start: date) -> tuple[date, date]:
    start = normalize_week_start(week_start)
    return start, start + timedelta(days=6)


def previous_week_range(week_start: date) -> tuple[date, date]:
    start = normalize_week_start(week_start) - timedelta(days=7)
    return start, start + timedelta(days=6)


def pct(part: int | float, total: int | float) -> int:
    return round((float(part) / float(total)) * 100) if total else 0


def score_label(score: int | None, data_completeness: int = 100) -> str:
    if score is None or data_completeness < 30:
        return "insufficient_data"
    if score < 40:
        return "needs_gentle_attention"
    if score < 60:
        return "returning"
    if score < 75:
        return "steady"
    if score < 90:
        return "growing"
    return "flourishing"


def score_confidence(data_completeness: int) -> str:
    if data_completeness < 60:
        return "low"
    if data_completeness < 80:
        return "medium"
    return "high"


def score_trend(current: int | None, previous: int | None) -> str:
    if current is None or previous is None:
        return "insufficient"
    diff = current - previous
    if diff >= 5:
        return "up"
    if diff <= -5:
        return "down"
    return "stable"


def metric_trend(first_avg: float | None, second_avg: float | None) -> str:
    if first_avg is None or second_avg is None or first_avg == 0:
        return "insufficient"
    change = (second_avg - first_avg) / first_avg
    if change <= -0.15:
        return "down"
    if change >= 0.15:
        return "up"
    return "stable"


def change_percent(current: int | float, previous: int | float) -> int | None:
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100)


def top_pulls_from_entries(entries: list[dict], limit: int = 5) -> list[dict]:
    counts: Counter[str] = Counter()
    minutes: Counter[str] = Counter()
    for entry in entries or []:
        duration = int(entry.get("durationMinutes") or entry.get("duration_minutes") or 0)
        for pull in entry.get("pulls") or []:
            if pull in PULL_LABELS:
                counts[pull] += 1
                minutes[pull] += duration
    ranked = sorted(counts, key=lambda p: (-minutes[p], -counts[p], p))
    return [
        {"pull": pull, "label": PULL_LABELS.get(pull, pull), "count": counts[pull], "minutes": minutes[pull]}
        for pull in ranked[:limit]
    ]


def build_daily_score_input(
    *,
    target: date,
    covenant: dict | None,
    entries: list[dict],
    focus_sessions: list[dict],
    review: dict | None,
    checkins: list[dict],
) -> dict:
    summary = calculate_daily_summary(entries)
    focus_completed = [s for s in focus_sessions or [] if s.get("endedAt") or s.get("ended_at")]
    focus_minutes = sum(int(s.get("actualMinutes") or s.get("actual_minutes") or 0) for s in focus_completed)
    completed = len(focus_completed)
    interrupted = [s for s in focus_sessions or [] if s.get("interrupted")]
    invested_categories = [
        key for key in ("worship", "mission", "relationship", "restoration")
        if int(summary["categoryMinutes"].get(key, 0)) > 0
    ]
    total = int(summary["totalMinutes"] or 0)
    captured = int(summary["capturedMinutes"] or 0)
    captured_ratio = pct(captured, total) if total else None
    return {
        "date": target.isoformat(),
        "covenant": covenant,
        "entries": entries or [],
        "summary": summary,
        "focusSessions": focus_sessions or [],
        "focusMinutes": focus_minutes,
        "completedFocusSessions": completed,
        "interruptedFocusSessions": len(interrupted),
        "interruptedWithReflection": any(s.get("closingReflection") or s.get("closing_reflection") for s in interrupted),
        "review": review,
        "checkins": checkins or [],
        "planCheckinsCount": len(checkins or []),
        "capturedRatio": captured_ratio,
        "investedCategoryCount": len(invested_categories),
    }


def data_completeness(input_data: dict) -> int:
    summary = input_data["summary"]
    score = 0
    if input_data.get("covenant"):
        score += 20
    if summary.get("entriesCount", 0) >= 1:
        score += 25
    if summary.get("totalMinutes", 0) >= 60:
        score += 15
    if input_data.get("completedFocusSessions", 0) or summary.get("investedMinutes", 0):
        score += 10
    if input_data.get("review"):
        score += 20
    if input_data.get("planCheckinsCount", 0):
        score += 10
    return min(100, score)


def component(key: str, score: int, reason: str, gentle: str = "") -> dict:
    label, maximum = COMPONENT_META[key]
    return {
        "key": key,
        "label": label,
        "score": min(max(0, score), maximum),
        "max": maximum,
        "reason": reason,
        "gentleSuggestion": gentle or None,
    }


def calculate_components(input_data: dict) -> list[dict]:
    covenant = input_data.get("covenant") or {}
    summary = input_data["summary"]
    categories = summary.get("categoryMinutes") or {}
    review = input_data.get("review") or {}
    checkins = input_data.get("checkins") or []
    entries = input_data.get("entries") or []
    comps: list[dict] = []

    c_score = 0
    if covenant:
        c_score += 8
        if covenant.get("primaryOffering") or covenant.get("primary_offering"):
            c_score += 3
        if covenant.get("digitalBoundary") or covenant.get("timeBoundary") or covenant.get("spiritualBoundary"):
            c_score += 2
        if (covenant.get("digitalBoundary") or covenant.get("timeBoundary") or covenant.get("spiritualBoundary")) and covenant.get("mainRisk"):
            c_score += 2
        comps.append(component("covenant", c_score, "今天完成了注意力立约，已经在一天开始时确认了心的方向。"))
    else:
        comps.append(component("covenant", 0, "今天没有记录早晨立约。可以从明天用一分钟确认注意力方向开始。", "明天先写下：今天我最想把注意力献给什么。"))

    invested = int(summary.get("investedMinutes") or 0)
    i_score = 0
    if invested > 0:
        i_score += 6
    if int(categories.get("mission") or 0) >= 30 or input_data.get("completedFocusSessions", 0):
        i_score += 6
    if int(categories.get("worship") or 0) > 0:
        i_score += 4
    if int(categories.get("relationship") or 0) > 0:
        i_score += 3
    if int(categories.get("restoration") or 0) > 0:
        i_score += 3
    if input_data.get("investedCategoryCount", 0) >= 2:
        i_score += 3
    comps.append(component("investedAttention", i_score, "今天有注意力投入在敬拜、使命、关系或恢复中，这是长期塑造生命的方向。", "明天先保留一段不被打断的使命或敬拜时间。"))

    total = int(summary.get("totalMinutes") or 0)
    captured = int(summary.get("capturedMinutes") or 0)
    ratio = input_data.get("capturedRatio")
    ca_score = 0
    if total > 0:
        if captured == 0 or (ratio is not None and ratio <= 15):
            ca_score += 8
        elif ratio <= 30:
            ca_score += 6
        elif ratio <= 50:
            ca_score += 4
        else:
            ca_score += 2
    if captured > 0 and summary.get("topPulls"):
        ca_score += 5
    if captured > 0 and any(e.get("attentionState") or e.get("attention_state") for e in entries):
        ca_score += 2
    if captured > 0 and review:
        ca_score += 3
    if captured > 0 and any(c.get("status") in {"returned", "escaped", "resisted"} for c in checkins):
        ca_score += 2
    reason = "今天有一段注意力被牵引，但你记录了背后的牵引因素。这不是失败，而是看见模式的开始。" if captured else "今天的记录里没有明显被牵引时长。"
    if total == 0:
        reason = "今天还没有足够账本记录，暂时无法判断注意力被牵引情况。"
    comps.append(component("capturedAwareness", ca_score, reason, "被牵引时，先记录牵引因素，再做一个具体归回动作。"))

    r_score = 0
    if review:
        r_score += 8
    if review.get("biggestGrace"):
        r_score += 4
    if review.get("biggestCapture"):
        r_score += 3
    if review.get("repentancePoint"):
        r_score += 2
    if review.get("tomorrowBoundary"):
        r_score += 2
    if review.get("prayer"):
        r_score += 1
    comps.append(component("reflectionReturn", r_score, "今天完成了晚间复盘，并记录了恩典或明日防线。" if review else "今天还没有晚间复盘。可以用 2 分钟写下一个恩典和一个明日防线。", "睡前只写两句话：一个恩典，一个明日防线。"))

    f_score = 0
    if input_data.get("completedFocusSessions", 0) >= 1:
        f_score += 5
    if input_data.get("focusMinutes", 0) >= 30:
        f_score += 3
    if not input_data.get("interruptedFocusSessions", 0) or input_data.get("interruptedWithReflection"):
        f_score += 2
    elif input_data.get("focusSessions"):
        f_score = max(f_score, 3)
    comps.append(component("focusAndFollowThrough", f_score, "今天完成了一段专注，这是忠心投入的一小步。", "专注前先设定一个小到可以完成的边界。"))

    rr_score = 0
    if int(categories.get("restoration") or 0) > 0:
        rr_score += 3
    if int(categories.get("relationship") or 0) > 0:
        rr_score += 3
    if covenant.get("restorationFocus"):
        rr_score += 1
    if covenant.get("relationshipFocus"):
        rr_score += 1
    grace_text = " ".join([str(review.get("biggestGrace") or ""), *(str(e.get("activityName") or "") for e in entries)])
    if any(word in grace_text for word in ["安息", "陪伴", "散步", "睡眠", "运动", "休息"]):
        rr_score += 2
    comps.append(component("restorationAndRelationship", rr_score, "今天有关系或恢复型注意力记录，说明你没有只把自己当作任务机器。", "安排一个 10 分钟真实恢复或真实陪伴。"))
    return comps


def daily_insights(input_data: dict, components: list[dict]) -> dict:
    summary = input_data["summary"]
    grace = ["你愿意记录和回看注意力，这本身就是归回的一步。"]
    risks: list[str] = []
    if input_data.get("covenant"):
        grace.append("今天有早晨立约，心的方向被温柔确认。")
    if input_data.get("focusMinutes", 0):
        grace.append(f"今天完成了 {input_data['focusMinutes']} 分钟专注。")
    if summary.get("categoryMinutes", {}).get("worship", 0):
        grace.append("今天有敬拜型注意力记录。")
    if summary.get("capturedMinutes", 0):
        top = summary.get("topPulls") or []
        label = top[0]["label"] if top else "某些牵引"
        risks.append(f"{label}今天出现过，可以温柔留意触发场景。")
    if not input_data.get("review"):
        risks.append("今天还没有晚间复盘，可以用两分钟写下恩典和明日防线。")
    if not input_data.get("covenant"):
        next_step = "明天早晨先用 1 分钟写下：今天我最想把注意力献给什么？"
    elif summary.get("topPulls"):
        pull = summary["topPulls"][0]["pull"]
        if pull in {"fomo", "anxiety"}:
            next_step = "明天先完成 60 分钟使命专注，再进入 30 分钟资讯窗口。"
        elif pull == "comparison":
            next_step = "明天打开社交媒体前，先完成自己的一个小使命任务。"
        else:
            next_step = "明天为最容易被牵引的时段预设一个小边界。"
    elif not input_data.get("review"):
        next_step = "今晚或明晚用 2 分钟写下一个恩典和一个明日防线。"
    elif not summary.get("categoryMinutes", {}).get("restoration", 0):
        next_step = "明天安排一个 10 分钟恢复动作，例如散步、拉伸或安静祷告。"
    else:
        next_step = "明天保留当前节奏，并为一个高风险时段预设边界。"
    return {"grace": grace[:4], "risks": risks[:3], "nextStep": next_step}


def compute_daily_score(input_data: dict) -> dict:
    completeness = data_completeness(input_data)
    components = calculate_components(input_data)
    total_score = sum(int(c["score"]) for c in components)
    score = None if completeness < 30 else min(100, total_score)
    summary = input_data["summary"]
    return {
        "date": input_data["date"],
        "score": score,
        "scoreLabel": score_label(score, completeness),
        "scoreLabelText": SCORE_LABELS[score_label(score, completeness)],
        "dataCompleteness": completeness,
        "confidence": score_confidence(completeness),
        "components": components,
        "inputSummary": {
            "hasCovenant": bool(input_data.get("covenant")),
            "entriesCount": int(summary.get("entriesCount") or 0),
            "totalMinutes": int(summary.get("totalMinutes") or 0),
            "investedMinutes": int(summary.get("investedMinutes") or 0),
            "capturedMinutes": int(summary.get("capturedMinutes") or 0),
            "capturedRatio": input_data.get("capturedRatio"),
            "categoryMinutes": summary.get("categoryMinutes") or {},
            "focusMinutes": int(input_data.get("focusMinutes") or 0),
            "completedFocusSessions": int(input_data.get("completedFocusSessions") or 0),
            "reviewExists": bool(input_data.get("review")),
            "planCheckinsCount": int(input_data.get("planCheckinsCount") or 0),
            "topPulls": summary.get("topPulls") or [],
        },
        "insights": daily_insights(input_data, components),
    }


def category_totals(entries: list[dict]) -> dict:
    totals = {key: 0 for key in CATEGORIES}
    for entry in entries or []:
        category = entry.get("category")
        if category in totals:
            totals[category] += int(entry.get("durationMinutes") or entry.get("duration_minutes") or 0)
    return totals


def category_percentages(totals: dict) -> dict:
    total = sum(int(totals.get(key, 0)) for key in CATEGORIES)
    return {key: pct(totals.get(key, 0), total) for key in CATEGORIES}


def average_score(scores: list[dict]) -> int | None:
    values = [int(s["score"]) for s in scores if s.get("score") is not None]
    if len(values) < 2:
        return None
    return round(sum(values) / len(values))


def review_rhythm_label(review_days: int) -> str:
    if review_days <= 0:
        return "尚未建立复盘节奏"
    if review_days <= 2:
        return "刚开始回看"
    if review_days <= 4:
        return "正在建立节奏"
    return "复盘节奏稳定"


def next_week_practice(report_input: dict) -> tuple[str, str]:
    covenant_days = report_input["covenantSummary"]["covenantDays"]
    review_days = report_input["reviewSummary"]["reviewDays"]
    top = (report_input.get("topPulls") or [{}])[0].get("pull")
    totals = report_input["categoryMinutes"]
    if covenant_days <= 2:
        return ("下周操练：连续 3 天早晨完成 1 分钟注意力立约。", "周一到周三，醒来后先写下一句今日注意力奉献。")
    if review_days <= 2:
        return ("下周操练：连续 3 天睡前写下一个恩典和一个明日防线。", "睡前手机放下后，先完成两句话复盘。")
    if top in {"fomo", "anxiety"}:
        return ("下周操练：每天先完成 60 分钟使命专注，再进入 30 分钟资讯窗口。", "上午 11 点前不看资讯；先完成一段使命专注。")
    if top == "comparison":
        return ("下周操练：社交媒体前先完成自己的一个小使命任务；想比较时写下 3 个感恩。", "打开社交媒体前，先完成一个可交付的小任务。")
    if top == "lust":
        return ("下周操练：为高风险时段预设逃离路径，并联系一位可信任守望伙伴。", "高风险时段不独处刷屏，受试探时立即离开场景。")
    if top in {"fatigue", "algorithm", "escape", "boredom"}:
        return ("下周操练：晚上 9 点后手机离开床边，用 10 分钟真实恢复替代推荐流。", "晚上 9 点后手机充电点离开床边。")
    if int(totals.get("restoration", 0)) <= 10:
        return ("下周操练：每天安排一个 10 分钟恢复动作。", "每天固定一个 10 分钟散步、拉伸或安静祷告窗口。")
    if int(totals.get("relationship", 0)) <= 10:
        return ("下周操练：安排一次不看手机的真实陪伴或关怀。", "选择一个关系时段，把手机放远。")
    return ("下周操练：保留当前节奏，并为最容易失守的一个时段预设边界。", "为本周最容易被牵引的时段写下一道具体边界。")


def weekly_sections(report_input: dict) -> dict:
    totals = report_input["categoryMinutes"]
    top_pulls = report_input.get("topPulls") or []
    review_days = report_input["reviewSummary"]["reviewDays"]
    focus_minutes = report_input["focusSummary"]["totalMinutes"]
    covenant_days = report_input["covenantSummary"]["covenantDays"]
    invested = totals["worship"] + totals["mission"] + totals["relationship"] + totals["restoration"]
    captured = totals["captured"]
    if report_input["scoreAverage"] is None:
        weekly_summary = "这一周的记录还不够完整，因此不适合做很强的判断。可以先感谢神：你愿意开始看见注意力的流向，这本身就是归回的起点。"
    else:
        weekly_summary = f"这一周你记录了 {round((invested + captured) / 60, 1)} 小时注意力，其中 {invested} 分钟投入在敬拜、使命、关系与恢复上。"
        if captured:
            weekly_summary += f" 也有 {captured} 分钟注意力被牵引；看见它，是重新设防的开始。"
        if review_days:
            weekly_summary += f" 你完成了 {review_days} 次晚间复盘，说明你不只是看见问题，也在学习归回。"
    grace = ["你愿意回看这一周的注意力，这本身就是恩典的开始。"]
    if covenant_days:
        grace.append(f"你本周有 {covenant_days} 天完成注意力立约。")
    if focus_minutes:
        grace.append(f"你完成了 {focus_minutes} 分钟专注，这是忠心的一步。")
    if totals["restoration"]:
        grace.append("你记录了恢复型注意力，说明你在学习承认自己的有限。")
    if report_input["warfareSummary"].get("returningCheckins", 0):
        grace.append("你有守心计划中的归回记录，这是值得感恩的时刻。")
    if top_pulls:
        main_pattern = f"从记录中看，本周最值得温柔留意的是{top_pulls[0]['label']}。它可能在疲惫、压力或不确定时牵引你的注意力。"
        warning = f"需要温柔留意的是：{top_pulls[0]['label']}出现时，不需要靠自责改变，而是提前安排一个真实边界或恢复动作。"
    else:
        main_pattern = "本周没有明显高频牵引。可以继续保持温柔觉察，不急着下结论。"
        warning = "记录还在累积中，暂时不需要做很强判断。"
    returning = []
    if review_days:
        returning.append(f"你有 {review_days} 天写下复盘，这是在神面前回看的时刻。")
    if report_input["warfareSummary"].get("returningCheckins", 0):
        returning.append("你在守心计划 check-in 中记录了抵挡、逃离或归回。")
    if not returning:
        returning.append("本周没有明显记录归回时刻。下周可以尝试在被牵引后做一次 30 秒祷告，并记录下来。")
    practice, boundary = next_week_practice(report_input)
    return {
        "weeklySummary": weekly_summary,
        "graceHighlights": grace[:5],
        "mainPattern": main_pattern,
        "returningMoments": returning,
        "warningWithoutShame": warning,
        "nextWeekPractice": practice,
        "suggestedBoundary": boundary,
    }


def weekly_prayer(report_input: dict) -> str:
    top = (report_input.get("topPulls") or [{}])[0].get("label") or "分心和疲惫"
    return (
        "主啊，感谢你这一周在我的分心、疲惫和归回中仍然与我同在。"
        f"求你帮助我看见注意力被{top}牵引的路径，也看见你给我的恩典。"
        "下周求你帮助我先把心归给你，不被焦虑、比较和算法牵引，"
        "而是在敬拜、使命、关系和安息中忠心前行。奉主耶稣基督的名祷告，阿们。"
    )


def build_weekly_report(week_start: date, week_end: date, input_data: dict, previous: dict | None = None) -> dict:
    scores = input_data["dailyScores"]
    avg = average_score(scores)
    totals = category_totals(input_data["entries"])
    percentages = category_percentages(totals)
    previous_avg = previous.get("scoreAverage") if previous else None
    focus_by_day: defaultdict[str, int] = defaultdict(int)
    completed = interrupted = 0
    for s in input_data["focusSessions"]:
        day = str(s.get("startedAt") or "")[:10]
        if s.get("endedAt"):
            completed += 1
            focus_by_day[day] += int(s.get("actualMinutes") or 0)
        if s.get("interrupted"):
            interrupted += 1
    review_days = len({r.get("reviewDate") for r in input_data["reviews"]})
    covenant_days = len({c.get("covenantDate") for c in input_data["covenants"]})
    returning_checkins = len([c for c in input_data["checkins"] if c.get("status") in {"returned", "resisted", "escaped"}])
    top_pulls = top_pulls_from_entries(input_data["entries"])
    common_risks = Counter()
    for covenant in input_data["covenants"]:
        for pull in covenant.get("riskPulls") or []:
            if pull in PULL_LABELS:
                common_risks[pull] += 1
    covenant_summary = {
        "covenantDays": covenant_days,
        "totalDays": 7,
        "mostCommonRisk": common_risks.most_common(1)[0][0] if common_risks else None,
        "commonRiskPulls": [
            {"pull": pull, "label": PULL_LABELS.get(pull, pull), "count": count}
            for pull, count in common_risks.most_common(5)
        ],
    }
    report = {
        "id": "",
        "weekStart": week_start.isoformat(),
        "weekEnd": week_end.isoformat(),
        "scoreAverage": avg,
        "scoreLabel": score_label(avg, round(sum(s["dataCompleteness"] for s in scores) / max(1, len(scores)))),
        "scoreTrend": score_trend(avg, previous_avg),
        "dataCompleteness": round(sum(s["dataCompleteness"] for s in scores) / max(1, len(scores))),
        "dailyScores": scores,
        "categoryMinutes": totals,
        "categoryPercentages": percentages,
        "focusSummary": {
            "totalMinutes": sum(focus_by_day.values()),
            "completedSessions": completed,
            "interruptedSessions": interrupted,
            "bestFocusDay": max(focus_by_day, key=focus_by_day.get) if focus_by_day else None,
        },
        "covenantSummary": covenant_summary,
        "reviewSummary": {"reviewDays": review_days, "totalDays": 7, "reviewRhythmLabel": review_rhythm_label(review_days)},
        "warfareSummary": {
            "activePlansCount": len(input_data["activePlans"]),
            "checkinsCount": len(input_data["checkins"]),
            "returningCheckins": returning_checkins,
            "primaryPattern": input_data.get("primaryPattern"),
        },
        "topPulls": top_pulls,
        "growthSignals": {
            "capturedMinutesChangePercent": change_percent(totals["captured"], (previous or {}).get("capturedMinutes", 0)),
            "investedMinutesChangePercent": change_percent(totals["worship"] + totals["mission"] + totals["relationship"] + totals["restoration"], (previous or {}).get("investedMinutes", 0)),
            "focusMinutesChangePercent": change_percent(sum(focus_by_day.values()), (previous or {}).get("focusMinutes", 0)),
            "reviewDaysChange": review_days - previous["reviewDays"] if previous else None,
        },
        "nextWeekPractice": None,
        "prayer": None,
        "status": "generated",
    }
    sections = weekly_sections(report)
    report["reportSections"] = sections
    report["nextWeekPractice"] = sections["nextWeekPractice"]
    report["prayer"] = weekly_prayer(report)
    return report


def growth_summary(points: list[dict]) -> dict:
    scores = [p["score"] for p in points if p.get("score") is not None]
    midpoint = max(1, len(points) // 2)
    first = points[:midpoint]
    second = points[midpoint:]
    def avg(items: list[dict], key: str) -> float | None:
        if len(items) < 2:
            return None
        return sum(float(i.get(key) or 0) for i in items) / len(items)
    top_counts: Counter[str] = Counter()
    top_minutes: Counter[str] = Counter()
    for p in points:
        for pull in p.get("topPulls") or []:
            top_counts[pull["pull"]] += pull.get("count", 0)
            top_minutes[pull["pull"]] += pull.get("minutes", 0)
    pulls = sorted(top_counts, key=lambda key: (-top_minutes[key], -top_counts[key], key))[:5]
    candidates = [p for p in points if p.get("score") is not None and p.get("dataCompleteness", 0) >= 60]
    best = max(candidates, key=lambda p: p["score"])["date"] if candidates else None
    return {
        "averageScore": round(sum(scores) / len(scores)) if scores else None,
        "averageInvestedMinutes": round(sum(p.get("investedMinutes", 0) for p in points) / max(1, len(points))),
        "averageCapturedMinutes": round(sum(p.get("capturedMinutes", 0) for p in points) / max(1, len(points))),
        "capturedTrend": metric_trend(avg(first, "capturedMinutes"), avg(second, "capturedMinutes")),
        "focusTrend": metric_trend(avg(first, "focusMinutes"), avg(second, "focusMinutes")),
        "mostFrequentPulls": [
            {"pull": pull, "label": PULL_LABELS.get(pull, pull), "count": top_counts[pull], "minutes": top_minutes[pull]}
            for pull in pulls
        ],
        "bestRhythmDay": best,
    }
