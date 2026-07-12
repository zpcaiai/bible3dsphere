from datetime import date

import pytest
from fastapi import HTTPException

from attention_suggest import ATTENTION_PULLS, build_attention_suggestion
import routers.attention as attention_router
from routers.attention import CovenantIn, SuggestIn, _parse_date
from attention_domain import (
    calculate_daily_summary,
    calculate_intensity,
    generate_fallback_diagnosis,
    pattern_definitions,
    safety_check,
    score_warfare_patterns,
)
from attention_reports import (
    build_daily_score_input,
    build_weekly_report,
    compute_daily_score,
)
from attention_accountability import (
    build_share_payload,
    challenge_progress,
    challenge_templates_for_lang,
    default_partner_permissions,
)
from attention_integration import (
    ATTENTION_ROUTES, ATTENTION_TABLES,
    attention_feature_flags,
    attention_environment_check,
    redact_attention_log_payload,
    release_checklist,
)


pytestmark = pytest.mark.no_db


def test_attention_challenge_templates_are_fully_localized_in_english():
    templates = challenge_templates_for_lang('en')

    assert len(templates) == 9
    for template in templates:
        for field in ('title', 'description', 'checkinPrompt', 'gentleGuideline'):
            assert not any('\u3400' <= char <= '\u9fff' for char in template[field])


def test_attention_pull_validation_accepts_known_values():
    body = SuggestIn(primaryOffering="深度工作", mainRisk="资讯焦虑", riskPulls=["fomo", "anxiety"])

    assert body.risk_pulls == ["fomo", "anxiety"]
    assert "fomo" in ATTENTION_PULLS


def test_shipped_attention_module_defaults_enabled_in_production():
    flags = attention_feature_flags({"NODE_ENV": "production"})

    assert flags["ATTENTION_MODULE_ENABLED"] is True
    assert "attention_group_invitations" in ATTENTION_TABLES
    assert "attention_admin_audit_events" in ATTENTION_TABLES


def test_sensitive_prayer_dto_hides_body_from_recipient(monkeypatch):
    class Cursor:
        def __init__(self):
            self.query = ""

        def execute(self, query, params=()):
            self.query = query

        def fetchone(self):
            return (0,) if "COUNT" in self.query else None

    monkeypatch.setattr(attention_router._social, "_display_user", lambda cur, user_id: {"id": user_id, "displayName": user_id})
    row = (
        "prayer-1", "alice@example.test", "ben@example.test", None,
        "private title", "private body", "attention", "summary", True,
        "open", "private answer", date(2026, 7, 10), date(2026, 7, 10), None,
    )

    dto = attention_router._prayer_row_to_dto(Cursor(), row, "ben@example.test")

    assert dto["title"] == "一项敏感代祷需要"
    assert dto["body"] is None
    assert dto["answeredNote"] is None


def test_ended_partner_cannot_open_old_share(monkeypatch):
    class Cursor:
        def execute(self, query, params=()):
            self.row = (
                "share-1", "alice@example.test", "partner", "ben@example.test", None,
                "weekly_report", "report-1", "summary", "summary", {}, "summary", [],
                None, date(2026, 7, 10), date(2026, 7, 10),
            )

        def fetchone(self):
            return self.row

    monkeypatch.setattr(attention_router.accountability, "_has_active_relationship", lambda *args: False)

    try:
        attention_router._require_share_access(Cursor(), "ben@example.test", "share-1")
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("ended partner should not retain access to old shares")


def test_attention_pull_validation_rejects_unknown_values():
    try:
        SuggestIn(primaryOffering="深度工作", riskPulls=["not_real"])
    except Exception as exc:
        assert "invalid attention pull" in str(exc)
    else:
        raise AssertionError("invalid pull should fail validation")


def test_primary_offering_is_required_after_trim():
    try:
        CovenantIn(primaryOffering="   ", riskPulls=[])
    except Exception as exc:
        assert "请写下今天最想把注意力献给什么" in str(exc)
    else:
        raise AssertionError("blank primaryOffering should fail validation")


def test_suggest_fomo_uses_fixed_information_window():
    suggestion = build_attention_suggestion("完成守心模块", "AI 资讯焦虑", ["fomo"])

    assert "上午不看" in suggestion["suggestedDigitalBoundary"]
    assert suggestion["suggestedScripture"]["reference"] == "诗篇 46:10"


def test_suggest_anxiety_uses_handover_prayer():
    suggestion = build_attention_suggestion("完成守心模块", "工作焦虑", ["anxiety"])

    assert "交托祷告" in suggestion["suggestedSpiritualBoundary"]
    assert suggestion["suggestedScripture"]["reference"] == "腓立比书 4:6-7"


def test_suggest_comparison_uses_gratitude():
    suggestion = build_attention_suggestion("陪伴家人", "比较", ["comparison"])

    assert "3 个感恩" in suggestion["suggestedSpiritualBoundary"]


def test_suggest_lust_is_non_shaming():
    suggestion = build_attention_suggestion("安静读经", "色情试探", ["lust"])

    assert "守望伙伴" in suggestion["suggestedSpiritualBoundary"]
    assert "羞辱" in suggestion["suggestedSpiritualBoundary"]


def test_parse_date_rejects_non_iso_date():
    try:
        _parse_date("2026/07/09", "from")
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail["error"] == "VALIDATION_ERROR"
    else:
        raise AssertionError("invalid date should fail")


def test_daily_summary_counts_invested_and_captured_minutes():
    summary = calculate_daily_summary([
        {"category": "mission", "durationMinutes": 60, "pulls": []},
        {"category": "captured", "durationMinutes": 30, "pulls": ["fomo", "anxiety"]},
        {"category": "captured", "durationMinutes": 15, "pulls": ["fomo"]},
    ])

    assert summary["investedMinutes"] == 60
    assert summary["capturedMinutes"] == 45
    assert summary["topPulls"][0]["pull"] == "fomo"


def test_diagnosis_safety_detects_crisis_and_sensitive_text():
    assert safety_check("我不想活了")["level"] == "crisis"
    sensitive = safety_check("我被色情试探困住了")
    assert sensitive["level"] == "sensitive"
    assert sensitive["shouldCallModel"] is True


def test_fallback_diagnosis_selects_fomo_pattern():
    result = generate_fallback_diagnosis({
        "userLocalDate": "2026-07-09",
        "diagnosisType": "daily",
        "ledger": {
            "entriesCount": 1,
            "capturedMinutes": 30,
            "topPulls": [{"pull": "fomo", "label": "错失恐惧", "count": 1, "minutes": 30}],
        },
        "focus": {},
        "covenant": {"exists": True, "mainRisk": "AI 资讯焦虑"},
        "review": {"exists": False},
        "entries": [{"activityName": "反复看 AI 资讯", "pulls": ["fomo"], "durationMinutes": 30, "category": "captured"}],
    })

    assert result["primaryPattern"]["key"] == "fomo_information_anxiety"
    assert result["scriptureSuggestions"]
    assert "定罪" in result["repentanceInvitation"]["notShamingReminder"]


def test_warfare_library_and_scoring():
    assert len(pattern_definitions()) == 9
    assert calculate_intensity(0) == "none"
    assert calculate_intensity(15) == "medium"
    scores = score_warfare_patterns({
        "entries": [
            {"category": "captured", "durationMinutes": 30, "pulls": ["fomo", "anxiety"], "activityName": "反复看 AI 资讯"},
            {"category": "mission", "durationMinutes": 60, "pulls": [], "activityName": "深度工作"},
        ],
        "covenants": [{"mainRisk": "AI 资讯焦虑", "riskPulls": ["fomo"]}],
        "focusSessions": [],
        "reviews": [],
        "diagnoses": [],
        "checkins": [],
    })

    assert scores[0]["patternKey"] == "fomo_information_anxiety"
    assert scores[0]["intensity"] in {"medium", "high"}


def test_daily_score_does_not_force_low_score_for_insufficient_data():
    score = compute_daily_score(build_daily_score_input(
        target=date(2026, 7, 9),
        covenant=None,
        entries=[],
        focus_sessions=[],
        review=None,
        checkins=[],
    ))

    assert score["score"] is None
    assert score["scoreLabel"] == "insufficient_data"
    assert "明天早晨" in score["insights"]["nextStep"]


def test_daily_score_rewards_captured_awareness_and_return():
    score = compute_daily_score(build_daily_score_input(
        target=date(2026, 7, 9),
        covenant={"primaryOffering": "深度工作", "mainRisk": "AI 资讯", "digitalBoundary": "上午不看资讯"},
        entries=[
            {"category": "mission", "durationMinutes": 60, "pulls": [], "attentionState": "focused"},
            {"category": "captured", "durationMinutes": 20, "pulls": ["fomo"], "attentionState": "scattered"},
        ],
        focus_sessions=[{"endedAt": "2026-07-09T02:00:00Z", "actualMinutes": 60, "interrupted": False}],
        review={"biggestGrace": "完成使命", "biggestCapture": "资讯焦虑", "tomorrowBoundary": "固定窗口"},
        checkins=[{"status": "returned"}],
    ))

    captured = next(c for c in score["components"] if c["key"] == "capturedAwareness")
    assert score["score"] is not None
    assert captured["score"] >= 10
    assert "不是失败" in captured["reason"]


def test_weekly_report_sections_are_gentle_and_structured():
    daily = []
    for day in range(7):
        daily.append({
            "date": f"2026-07-{6 + day:02d}",
            "score": 70 if day < 4 else None,
            "scoreLabel": "steady",
            "dataCompleteness": 70,
            "components": [],
            "inputSummary": {},
            "insights": {},
        })
    report = build_weekly_report(
        date(2026, 7, 6),
        date(2026, 7, 12),
        {
            "dailyScores": daily,
            "entries": [
                {"category": "mission", "durationMinutes": 120, "pulls": []},
                {"category": "captured", "durationMinutes": 30, "pulls": ["fomo"]},
            ],
            "focusSessions": [{"startedAt": "2026-07-07T01:00:00Z", "endedAt": "2026-07-07T02:00:00Z", "actualMinutes": 60, "interrupted": False}],
            "covenants": [{"covenantDate": "2026-07-06", "riskPulls": ["fomo"]}],
            "reviews": [{"reviewDate": "2026-07-06"}],
            "checkins": [{"status": "returned"}],
            "activePlans": [{}],
            "primaryPattern": {"label": "资讯焦虑与错失恐惧", "intensity": "medium"},
        },
        {"scoreAverage": 65, "capturedMinutes": 60, "investedMinutes": 90, "focusMinutes": 30, "reviewDays": 1},
    )

    assert report["scoreAverage"] == 70
    assert report["topPulls"][0]["pull"] == "fomo"
    assert "定罪" not in report["reportSections"]["weeklySummary"]
    assert report["nextWeekPractice"].startswith("下周操练")


def test_accountability_default_permissions_are_private_first():
    permissions = default_partner_permissions()

    assert permissions["visibilityLevel"] == "status_only"
    assert permissions["canSeeScoreSummary"] is False
    assert permissions["canSeeWeeklyReportSummary"] is False
    assert "lust" in permissions["hiddenSensitiveCategories"]


def test_weekly_report_share_redacts_sensitive_pulls_and_hides_score_by_default():
    payload, redactions = build_share_payload(
        "weekly_report",
        {
            "weekStart": "2026-07-06",
            "weekEnd": "2026-07-12",
            "scoreAverage": 88,
            "reportSections": {"weeklySummary": "这一周更稳定。"},
            "topPulls": [{"pull": "lust", "label": "色情试探", "count": 2, "minutes": 30}],
            "nextWeekPractice": "早晨先读经。",
        },
        {"includeScore": True, "includeTopPulls": True},
        {"hideSensitiveCategories": ["lust"], "shareScoresWithPartners": False, "shareScoresWithGroups": False},
    )

    assert "scoreAverage" not in payload
    assert payload["topPulls"][0]["label"] == "一个敏感牵引"
    assert "lust" in redactions


def test_challenge_progress_is_aggregate_without_ranking():
    progress = challenge_progress(
        challenge={"startDate": "2026-07-06", "endDate": "2026-07-12"},
        participants=[
            {"userId": "a@example.com", "status": "active"},
            {"userId": "b@example.com", "status": "active"},
        ],
        checkins=[
            {"userId": "b@example.com", "completed": True},
            {"userId": "a@example.com", "completed": False},
        ],
        current_user_id="a@example.com",
        today=date(2026, 7, 7),
    )

    assert progress["activeParticipants"] == 2
    assert progress["completedCheckins"] == 1
    assert "ranking" not in progress


def test_attention_route_registry_includes_admin_but_marks_it_protected():
    routes = {route["key"]: route for route in ATTENTION_ROUTES}

    assert routes["dashboard"]["href"] == "/attention"
    assert routes["admin"]["requiresAdmin"] is True
    assert routes["privacy"]["group"] == "settings"


def test_attention_environment_check_blocks_demo_seed_in_production():
    result = attention_environment_check({"NODE_ENV": "production", "ATTENTION_DEMO_SEED_ENABLED": "true"})

    assert result["ok"] is False
    assert any("DEMO_SEED" in item for item in result["errors"])


def test_attention_log_redaction_hides_sensitive_fields_recursively():
    payload = redact_attention_log_payload({
        "note": "raw note",
        "nested": {"prayer": "raw prayer"},
        "safeCount": 3,
    })

    assert payload["note"] == "[REDACTED_ATTENTION_SENSITIVE]"
    assert payload["nested"]["prayer"] == "[REDACTED_ATTENTION_SENSITIVE]"
    assert payload["safeCount"] == 3
    assert payload["sensitiveFieldsRedacted"] is True


def test_release_checklist_covers_privacy_and_logs():
    labels = " ".join(item["label"] for item in release_checklist())

    assert "Default visibility" in labels
    assert "No raw prayer" in labels
