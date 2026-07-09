"""Privacy-first accountability helpers for Attention Stewardship."""
from __future__ import annotations

from datetime import date
from typing import Any

SENSITIVE_CATEGORIES = [
    "lust",
    "financial_anxiety",
    "family_conflict",
    "mental_health",
    "trauma",
    "addiction",
    "work_conflict",
    "identity_shame",
]

VISIBILITY_LEVELS = {"private", "status_only", "summary", "selected_details"}
PARTNER_STATUSES = {"pending", "active", "declined", "paused", "ended"}
GROUP_TYPES = {"private", "church_small_group", "discipleship", "challenge_only"}
GROUP_ROLES = {"owner", "leader", "member"}
GROUP_STATUSES = {"active", "archived"}
MEMBER_STATUSES = {"active", "invited", "left", "removed"}
CHALLENGE_TYPES = {
    "morning_covenant", "evening_review", "focus_minutes", "no_phone_morning",
    "scripture_attention", "rest_rhythm", "relationship_presence",
    "digital_boundary", "warfare_checkin", "custom",
}
CHALLENGE_PRIVACY_MODES = {"status_only", "summary", "anonymous_aggregate"}
CHALLENGE_STATUSES = {"draft", "active", "completed", "archived"}
PRAYER_CATEGORIES = {"attention", "anxiety", "temptation", "rest", "relationship", "mission", "gratitude", "other"}
PRAYER_STATUSES = {"open", "answered", "closed"}
SHARE_SCOPES = {"partner", "group", "challenge", "prayer_request"}
SHARE_SOURCE_TYPES = {"weekly_report", "daily_summary", "warfare_plan", "challenge_progress", "prayer_request", "custom"}


DEFAULT_PRIVACY = {
    "defaultPartnerVisibility": "status_only",
    "defaultGroupVisibility": "status_only",
    "defaultChallengeVisibility": "status_only",
    "shareScoresWithPartners": False,
    "shareScoresWithGroups": False,
    "shareWeeklyReportSummary": False,
    "shareWarfarePlanProgress": False,
    "sharePrayerRequests": True,
    "hideSensitiveCategories": SENSITIVE_CATEGORIES,
    "allowPartnerReminders": True,
    "allowGroupChallengeReminders": True,
    "requirePreviewBeforeSharing": True,
}


DEFAULT_PARTNER_PERMISSIONS = {
    "visibilityLevel": "status_only",
    "canSeeDailyCovenantStatus": True,
    "canSeeFocusStatus": True,
    "canSeeReviewStatus": True,
    "canSeeWeeklyReportSummary": False,
    "canSeeScoreSummary": False,
    "canSeeWarfarePlanProgress": False,
    "canSeePrayerRequests": True,
    "canSendReminders": True,
    "hiddenSensitiveCategories": SENSITIVE_CATEGORIES,
}


CHALLENGE_TEMPLATES = [
    {
        "key": "morning_covenant_5_days",
        "title": "5 天晨间守心立约",
        "description": "连续 5 天，用 1 分钟在早晨确认今天注意力要献给什么，以及今天要防备什么。",
        "challengeType": "morning_covenant",
        "suggestedDurationDays": 7,
        "defaultTargetDays": 5,
        "defaultTargetMinutes": None,
        "checkinPrompt": "今天是否完成了晨间注意力立约？",
        "privacyMode": "status_only",
        "gentleGuideline": "不是为了打卡完美，而是一起学习在世界争夺我们之前，先把心归给主。",
    },
    {
        "key": "evening_review_3_days",
        "title": "3 次晚间复盘",
        "description": "一周内完成 3 次晚间复盘：一个恩典、一个失守、一个明日防线。",
        "challengeType": "evening_review",
        "suggestedDurationDays": 7,
        "defaultTargetDays": 3,
        "defaultTargetMinutes": None,
        "checkinPrompt": "今天是否完成了晚间复盘？",
        "privacyMode": "status_only",
        "gentleGuideline": "晚间复盘不是总结失败，而是在恩典中回看一天。",
    },
    {
        "key": "focus_180_minutes_week",
        "title": "本周 180 分钟使命专注",
        "description": "本周累计完成 180 分钟敬拜、使命、关系或恢复型专注。",
        "challengeType": "focus_minutes",
        "suggestedDurationDays": 7,
        "defaultTargetDays": None,
        "defaultTargetMinutes": 180,
        "checkinPrompt": "今天完成了多少分钟专注？",
        "privacyMode": "summary",
        "gentleGuideline": "专注不是证明自己，而是把一段注意力忠心献上。",
    },
    {
        "key": "no_phone_morning_3_days",
        "title": "3 天早晨不先看手机",
        "description": "连续或累计 3 天，起床后先完成祷告、读经、立约或安静，再打开资讯流。",
        "challengeType": "no_phone_morning",
        "suggestedDurationDays": 7,
        "defaultTargetDays": 3,
        "defaultTargetMinutes": None,
        "checkinPrompt": "今天早晨是否先把心归给主，而不是先进入资讯流？",
        "privacyMode": "status_only",
        "gentleGuideline": "不是靠意志力证明自己，而是把早晨最清醒的心先给神。",
    },
    {
        "key": "scripture_attention_5_days",
        "title": "5 天经文守心",
        "description": "选择一段经文，每天用它提醒自己的注意力方向。",
        "challengeType": "scripture_attention",
        "suggestedDurationDays": 7,
        "defaultTargetDays": 5,
        "defaultTargetMinutes": None,
        "checkinPrompt": "今天是否用经文提醒自己的注意力方向？",
        "privacyMode": "status_only",
        "gentleGuideline": "经文不是任务清单，而是真理重新整理心的方向。",
    },
    {
        "key": "rest_rhythm_3_days",
        "title": "3 次真实恢复",
        "description": "本周完成 3 次不靠刷手机的真实恢复，例如散步、早睡、运动、安静祷告。",
        "challengeType": "rest_rhythm",
        "suggestedDurationDays": 7,
        "defaultTargetDays": 3,
        "defaultTargetMinutes": None,
        "checkinPrompt": "今天是否选择了一个真实恢复动作？",
        "privacyMode": "summary",
        "gentleGuideline": "你不是机器，安息也是信靠。",
    },
    {
        "key": "relationship_presence_2_times",
        "title": "2 次真实陪伴",
        "description": "本周至少 2 次，把不被手机分散的真实注意力给到家人、朋友、小组或肢体。",
        "challengeType": "relationship_presence",
        "suggestedDurationDays": 7,
        "defaultTargetDays": 2,
        "defaultTargetMinutes": None,
        "checkinPrompt": "今天是否把真实注意力给到一个真实的人？",
        "privacyMode": "status_only",
        "gentleGuideline": "爱不是抽象概念，也需要真实在场。",
    },
    {
        "key": "digital_boundary_5_days",
        "title": "5 天数字边界",
        "description": "选择一个数字边界，并操练 5 天。",
        "challengeType": "digital_boundary",
        "suggestedDurationDays": 7,
        "defaultTargetDays": 5,
        "defaultTargetMinutes": None,
        "checkinPrompt": "今天是否守住了你设立的数字边界？若没有，也可以记录一次归回。",
        "privacyMode": "status_only",
        "gentleGuideline": "边界不是惩罚，而是帮助心重新得自由。",
    },
    {
        "key": "warfare_checkin_5_days",
        "title": "5 天守心计划 Check-in",
        "description": "针对一个守心计划，连续或累计 5 天做轻量 check-in。",
        "challengeType": "warfare_checkin",
        "suggestedDurationDays": 7,
        "defaultTargetDays": 5,
        "defaultTargetMinutes": None,
        "checkinPrompt": "今天是否对你的守心计划做了 check-in？",
        "privacyMode": "status_only",
        "gentleGuideline": "被牵引后归回，也值得记录和感恩。",
    },
]


def default_partner_permissions(overrides: dict | None = None) -> dict:
    result = dict(DEFAULT_PARTNER_PERMISSIONS)
    if overrides:
        for key, value in overrides.items():
            if key in result:
                result[key] = value
    result["visibilityLevel"] = sanitize_visibility(result.get("visibilityLevel"), allow_selected=False)
    result["hiddenSensitiveCategories"] = sanitize_sensitive_categories(result.get("hiddenSensitiveCategories"))
    return result


def sanitize_visibility(value: Any, *, allow_selected: bool = True) -> str:
    value = str(value or "status_only")
    if value == "selected_details" and not allow_selected:
        return "summary"
    return value if value in VISIBILITY_LEVELS else "status_only"


def sanitize_sensitive_categories(values: Any) -> list[str]:
    if not isinstance(values, list):
        return list(SENSITIVE_CATEGORIES)
    known = set(SENSITIVE_CATEGORIES + ["custom_sensitive"])
    cleaned = [str(v) for v in values if str(v) in known]
    return list(dict.fromkeys(cleaned)) or list(SENSITIVE_CATEGORIES)


def sanitize_privacy_update(data: dict) -> dict:
    result: dict[str, Any] = {}
    for key in DEFAULT_PRIVACY:
        if key not in data:
            continue
        value = data[key]
        if key.endswith("Visibility"):
            result[key] = sanitize_visibility(value, allow_selected=False)
        elif key == "hideSensitiveCategories":
            result[key] = sanitize_sensitive_categories(value)
        elif isinstance(DEFAULT_PRIVACY[key], bool):
            result[key] = bool(value)
        else:
            result[key] = value
    return result


def redact_pulls(items: list[dict] | None, hidden: list[str] | None) -> tuple[list[dict], list[str]]:
    hidden_set = set(hidden or SENSITIVE_CATEGORIES)
    redactions: list[str] = []
    result: list[dict] = []
    for item in items or []:
        pull = item.get("pull")
        if pull in hidden_set or pull == "lust":
            redactions.append(str(pull or "sensitive"))
            result.append({"pull": "sensitive", "label": "一个敏感牵引", "count": item.get("count", 1), "minutes": None})
        else:
            result.append({k: item.get(k) for k in ("pull", "label", "count", "minutes")})
    return result, list(dict.fromkeys(redactions))


def build_share_payload(source_type: str, source: dict | None, options: dict | None, privacy: dict | None) -> tuple[dict, list[str]]:
    source = source or {}
    options = options or {}
    privacy = privacy or DEFAULT_PRIVACY
    hidden = privacy.get("hideSensitiveCategories") or SENSITIVE_CATEGORIES
    include_score = bool(options.get("includeScore")) and bool(
        privacy.get("shareScoresWithPartners") or privacy.get("shareScoresWithGroups")
    )
    if source_type == "weekly_report":
        sections = source.get("reportSections") or {}
        top_pulls, redactions = redact_pulls(source.get("topPulls") or [], hidden)
        payload = {
            "weekStart": source.get("weekStart"),
            "weekEnd": source.get("weekEnd"),
            "summary": sections.get("weeklySummary") or source.get("summary"),
            "graceHighlights": sections.get("graceHighlights") or [],
            "nextWeekPractice": source.get("nextWeekPractice") or sections.get("nextWeekPractice"),
            "prayerRequestPrompt": "请为我下周的守心操练祷告。",
        }
        if options.get("includeTopPulls"):
            payload["topPulls"] = top_pulls
        if include_score:
            payload["scoreAverage"] = source.get("scoreAverage")
            payload["scoreLabel"] = source.get("scoreLabel")
        return payload, redactions
    if source_type == "daily_summary":
        payload = {
            "date": source.get("date"),
            "covenantDone": bool(source.get("covenant")),
            "focusMinutes": ((source.get("focus") or {}).get("totalActualMinutes") or 0),
            "reviewDone": bool((source.get("review") or {}).get("exists")),
            "summary": "今天的分享只包含完成状态和温柔摘要，不包含原始账本或复盘内容。",
        }
        return payload, []
    if source_type == "warfare_plan":
        sensitive = source.get("patternKey") == "lust_escape_shame" or "lust" in (source.get("primaryPulls") or [])
        title = "一个敏感守心计划" if sensitive else source.get("title")
        return {
            "title": title,
            "patternLabel": None if sensitive else source.get("patternKey"),
            "boundary": source.get("digitalBoundary") or source.get("timeBoundary"),
            "replacementPractice": source.get("replacementPractice"),
            "checkinSummary": "这份分享只包含计划进展摘要，不包含原始触发内容。",
        }, ["lust"] if sensitive else []
    if source_type == "challenge_progress":
        return {
            "challengeTitle": source.get("title"),
            "completedDays": (source.get("progress") or {}).get("currentUserCompletedDays", 0),
            "targetDays": source.get("targetDays"),
            "encouragementText": (source.get("progress") or {}).get("encouragementText", "正在建立节奏。"),
        }, []
    if source_type == "prayer_request":
        return {
            "title": source.get("title"),
            "body": source.get("body"),
            "category": source.get("category"),
            "isSensitive": bool(source.get("isSensitive")),
        }, ["prayer_request_sensitive"] if source.get("isSensitive") else []
    return {"message": str(options.get("customMessage") or "我想分享一个守心摘要，请为我祷告。")[:1000]}, []


def challenge_progress(*, challenge: dict, participants: list[dict], checkins: list[dict], current_user_id: str, today: date | None = None) -> dict:
    start = challenge.get("startDate")
    end = challenge.get("endDate")
    if isinstance(start, str):
        start_date = date.fromisoformat(start)
    else:
        start_date = start
    if isinstance(end, str):
        end_date = date.fromisoformat(end)
    else:
        end_date = end
    today = today or date.today()
    total_days = max(1, (end_date - start_date).days + 1)
    days_elapsed = min(total_days, max(1, (min(today, end_date) - start_date).days + 1))
    active = [p for p in participants if p.get("status") == "active"]
    completed = [c for c in checkins if c.get("completed")]
    current = [c for c in checkins if c.get("userId") == current_user_id]
    rate = round((len(completed) / max(1, len(active) * days_elapsed)) * 100)
    if rate >= 70:
        encouragement = "小组正在建立稳定节奏。"
    elif len(checkins):
        encouragement = "已经有一些轻量 check-in，继续温柔同行。"
    else:
        encouragement = "可以从今天一个很小的 check-in 开始。"
    return {
        "totalParticipants": len(participants),
        "activeParticipants": len(active),
        "totalCheckins": len(checkins),
        "completedCheckins": len(completed),
        "groupCompletionRate": min(100, rate),
        "currentUserCheckins": len(current),
        "currentUserCompletedDays": len([c for c in current if c.get("completed")]),
        "daysElapsed": days_elapsed,
        "totalDays": total_days,
        "encouragementText": encouragement,
    }
