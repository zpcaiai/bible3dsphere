from fastapi import HTTPException

from attention_suggest import ATTENTION_PULLS, build_attention_suggestion
from routers.attention import CovenantIn, SuggestIn, _parse_date
from attention_domain import (
    calculate_daily_summary,
    calculate_intensity,
    generate_fallback_diagnosis,
    pattern_definitions,
    safety_check,
    score_warfare_patterns,
)


def test_attention_pull_validation_accepts_known_values():
    body = SuggestIn(primaryOffering="深度工作", mainRisk="资讯焦虑", riskPulls=["fomo", "anxiety"])

    assert body.risk_pulls == ["fomo", "anxiety"]
    assert "fomo" in ATTENTION_PULLS


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
