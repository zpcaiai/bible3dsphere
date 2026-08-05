"""The remaining MUST_DO items, enforced in code rather than in a runbook.

    MODEL_TRAINING_OPTOUT  P3 材料不得进入训练，未登记的供应商直接拒绝
    UI_LABELS              阶段展示必须带情境/时间/置信度，禁止分数、排名与诊断
    SHARING_OFF            试点档不提供分享同意项，分享接口一律 403
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from formation_twin.emotional_maturity import CONSENT_SCOPES, STAGE_IS_NOT
from formation_twin.emotional_maturity_pilot_gate import (
    FEATURE_REQUIREMENTS,
    PilotGateError,
    available_consent_scopes,
    capabilities,
    enforce_scope_request,
    feature_matrix,
    guard_feature,
)
from formation_twin.emotional_maturity_presentation import (
    CONFIDENCE_DISPLAY,
    FORBIDDEN_KEYS,
    REQUIRED_DISPLAY_FIELDS,
    PresentationContractError,
    build_stage_display,
    display_contract,
    required_labels,
    validate_ui_payload,
)
from formation_twin.emotional_maturity_training_optout import (
    AUDIT_QUESTIONS,
    PROVIDER_OPT_OUT,
    TrainingOptOutError,
    assert_no_training_material,
    audit_provider_config,
    classify_material,
    describe_training_optout,
    sanitize_provider_call,
    training_optout_headers,
)


pytestmark = pytest.mark.no_db
BACKEND = Path(__file__).resolve().parents[1]


# ═════════════════════════════════════════════════════════════════════════════
# MODEL_TRAINING_OPTOUT
# ═════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("field", [
    "prayer_text", "confession_text", "journal_text", "family_history",
    "genogram_notes", "trauma_material", "minor_profile",
])
def test_p3_fields_are_forbidden_from_training(field):
    verdict = classify_material(field=field)
    assert verdict["sensitivity"] == "P3_HIGHLY_SENSITIVE"
    assert verdict["training_forbidden"] is True
    assert verdict["retention_forbidden"] is True


def test_crisis_material_is_sealed_not_merely_sensitive():
    assert classify_material(field="crisis_text")["sensitivity"] == "P4_SEALED_SAFETY"
    assert classify_material(field="safety_notes")["sensitivity"] == "P4_SEALED_SAFETY"


@pytest.mark.parametrize("text,expected", [
    ("我昨天为父亲的病祷告了很久", "P3_HIGHLY_SENSITIVE"),
    ("我小时候他总是骂我", "P3_HIGHLY_SENSITIVE"),
    ("上周被确诊为抑郁症，开始服药", "P3_HIGHLY_SENSITIVE"),
    ("他昨天又打我", "P4_SEALED_SAFETY"),
    ("我很生气，跟同事吵架了", "P2_SENSITIVE"),
])
def test_content_is_classified_even_when_the_field_name_looks_harmless(text, expected):
    verdict = classify_material(field="notes", text=text)
    assert verdict["sensitivity"] == expected
    assert verdict["training_forbidden"] is True


def test_unknown_emd_fields_default_to_sensitive_not_public():
    assert classify_material(field="emd_something_new")["training_forbidden"] is True


def test_ordinary_metadata_is_not_over_classified():
    assert classify_material(field="locale", text="zh-CN")["training_forbidden"] is False


def test_every_registered_provider_carries_an_opt_out_mechanism():
    for provider, config in PROVIDER_OPT_OUT.items():
        assert config["console_setting"], provider
        assert config["zero_retention_available"] is True, provider


def test_an_unregistered_provider_is_refused_outright():
    with pytest.raises(TrainingOptOutError):
        training_optout_headers("some-new-vendor")
    with pytest.raises(TrainingOptOutError):
        sanitize_provider_call(provider="some-new-vendor")


def test_sanitized_calls_carry_the_opt_out_flags():
    call = sanitize_provider_call(provider="openai", body={"model": "gpt-4o-mini"})
    assert call["body"]["store"] is False
    assert call["headers"]["OpenAI-Beta"] == "no-training=1"
    assert call["retention"] == "ZERO"
    assert call["training_opt_out_applied"] is True


def test_caller_supplied_flags_cannot_override_the_opt_out():
    call = sanitize_provider_call(
        provider="openai", body={"store": True}, headers={"OpenAI-Beta": "assistants=v2"},
    )
    assert call["body"]["store"] is False
    assert call["headers"]["OpenAI-Beta"] == "no-training=1"


def test_public_material_does_not_claim_zero_retention():
    call = sanitize_provider_call(provider="anthropic", material_sensitivity="P0_PUBLIC")
    assert call["retention"] == "PROVIDER_DEFAULT"


def test_training_candidate_builder_is_blocked_on_emd_material():
    with pytest.raises(TrainingOptOutError):
        assert_no_training_material([
            {"field": "locale", "text": "zh-CN"},
            {"field": "prayer_text", "text": "求主帮助我"},
        ])


def test_training_candidate_builder_accepts_non_personal_records():
    result = assert_no_training_material([{"field": "locale", "text": "zh-CN"}])
    assert result["status"] == "CLEAN"
    assert result["training_candidates"] == 0


def test_provider_audit_fails_until_every_question_is_answered():
    partial = audit_provider_config(
        provider="openai",
        answers={key: True for key, _ in AUDIT_QUESTIONS[:3]},
        verified_by="ethan",
    )
    assert partial["status"] == "FAIL"
    assert partial["emd_material_allowed"] is False
    assert len(partial["unanswered_or_failed"]) == len(AUDIT_QUESTIONS) - 3


def test_a_fully_verified_provider_passes_and_is_attributable():
    passed = audit_provider_config(
        provider="openai",
        answers={key: True for key, _ in AUDIT_QUESTIONS},
        verified_by="ethan",
    )
    assert passed["status"] == "PASS"
    assert passed["emd_material_allowed"] is True
    assert passed["verified_by"] == "ethan"
    assert passed["verified_at"]
    assert passed["console_setting"]


def test_audit_of_an_unknown_provider_can_never_pass():
    result = audit_provider_config(
        provider="mystery-llm",
        answers={key: True for key, _ in AUDIT_QUESTIONS},
        verified_by="ethan",
    )
    assert result["status"] == "FAIL"
    assert result["provider_recognised"] is False


def test_optout_module_states_that_it_raises_rather_than_warns():
    assert "抛异常" in describe_training_optout()["enforcement"]


# ═════════════════════════════════════════════════════════════════════════════
# UI_LABELS
# ═════════════════════════════════════════════════════════════════════════════

def test_a_stage_display_carries_context_timeframe_and_confidence():
    display = build_stage_display(
        dimension_code="D2", dimension_name="情绪调节与恢复能力", stage="E3",
        context="与伴侣的冲突", timeframe="最近 30 天", confidence="MODERATE",
        evidence_count=4,
    )
    for field in REQUIRED_DISPLAY_FIELDS:
        assert display[field]
    assert display["score"] is None
    assert display["comparable_across_users"] is False
    assert display["confidence_label"] == CONFIDENCE_DISPLAY["MODERATE"]


def test_a_stage_without_context_or_timeframe_is_refused():
    with pytest.raises(PresentationContractError):
        build_stage_display(
            dimension_code="D2", dimension_name="x", stage="E3",
            context="", timeframe="最近 30 天", confidence="MODERATE",
        )
    with pytest.raises(PresentationContractError):
        build_stage_display(
            dimension_code="D2", dimension_name="x", stage="E3",
            context="工作", timeframe="", confidence="MODERATE",
        )


def test_pilot_displays_carry_the_exploratory_labels():
    display = build_stage_display(
        dimension_code="D1", dimension_name="情绪觉察", stage="E2",
        context="工作压力", timeframe="最近 14 天", confidence="PROVISIONAL",
        profile="PILOT",
    )
    assert "exploratory" in display["labels"]
    assert "非临床" in display["labels"]
    assert "个人反思用途" in display["labels"]
    assert list(display["disclaimers"]) == list(STAGE_IS_NOT)


def test_progress_bars_and_leaderboards_are_named_as_forbidden():
    display = build_stage_display(
        dimension_code="D1", dimension_name="情绪觉察", stage="E2",
        context="工作", timeframe="最近 14 天", confidence="PROVISIONAL",
    )
    assert "PROGRESS_BAR" in display["render_as_forbidden"]
    assert "LEADERBOARD" in display["render_as_forbidden"]


@pytest.mark.parametrize("payload", [
    {"total_score": 72},
    {"profile": {"maturity_percentile": 88}},
    {"items": [{"peer_ranking": 3}]},
    {"personality_type": "回避型"},
])
def test_score_shaped_payloads_are_rejected(payload):
    result = validate_ui_payload(payload)
    assert result["valid"] is False
    assert result["violations"][0]["code"] == "FORBIDDEN_KEY"


@pytest.mark.parametrize("text,code", [
    ("你的情感成熟度得分为 72 分", "SCORE_LANGUAGE"),
    ("你超过了 80%的用户", "PERCENT_LANGUAGE"),
    ("你在小组里排名第 3", "RANKING_LANGUAGE"),
    ("你被诊断为回避型依恋", "DIAGNOSIS_LANGUAGE"),
    ("你就是一个逃避的人", "PERMANENCE_LANGUAGE"),
    ("神告诉你要顺服", "SPIRITUAL_VERDICT"),
])
def test_score_shaped_language_is_rejected(text, code):
    result = validate_ui_payload({"summary": text})
    assert result["valid"] is False
    assert result["violations"][0]["code"] == code


def test_a_compliant_display_passes_validation():
    display = build_stage_display(
        dimension_code="D9", dimension_name="冲突与修复", stage="E3",
        context="与同事的冲突", timeframe="最近 30 天", confidence="MODERATE",
    )
    assert validate_ui_payload(display)["valid"] is True


def test_violations_report_where_the_problem_is():
    result = validate_ui_payload({"a": {"b": [{"total_score": 1}]}})
    assert result["violations"][0]["path"] == "$.a.b[0].total_score"


def test_a_null_score_field_is_allowed_so_the_backend_can_keep_the_key():
    assert validate_ui_payload({"total_score": None})["valid"] is True


def test_the_contract_is_served_not_just_documented():
    contract = display_contract("PILOT")
    assert contract["required_fields_per_stage"] == list(REQUIRED_DISPLAY_FIELDS)
    assert set(contract["forbidden_keys"]) == FORBIDDEN_KEYS
    assert "PROGRESS_BAR" in contract["forbidden_visualisations"]
    assert "exploratory" in contract["required_labels"]


def test_unknown_profile_has_no_labels_to_offer():
    with pytest.raises(PresentationContractError):
        required_labels("WHATEVER")


# ═════════════════════════════════════════════════════════════════════════════
# SHARING_OFF
# ═════════════════════════════════════════════════════════════════════════════

def test_the_default_profile_is_the_conservative_one(monkeypatch):
    monkeypatch.delenv("EMD_ASSURANCE_PROFILE", raising=False)
    assert capabilities()["profile"] == "PILOT"
    assert capabilities()["sharing_allowed"] is False


def test_pilot_withholds_the_pastoral_share_consent_scope(monkeypatch):
    monkeypatch.delenv("EMD_ASSURANCE_PROFILE", raising=False)
    available = available_consent_scopes()
    assert "EMD_PASTORAL_SHARE" not in available["scopes"]
    assert "EMD_PASTORAL_SHARE" in available["withheld_scopes"]
    assert "EMD_SELF_ASSESSMENT" in available["scopes"]


def test_production_profile_offers_every_declared_scope():
    available = available_consent_scopes("PRODUCTION")
    assert set(available["scopes"]) == set(CONSENT_SCOPES)
    assert available["withheld_scopes"] == {}


def test_a_direct_request_for_a_withheld_scope_is_stripped(monkeypatch):
    monkeypatch.delenv("EMD_ASSURANCE_PROFILE", raising=False)
    result = enforce_scope_request(["EMD_SELF_ASSESSMENT", "EMD_PASTORAL_SHARE"])
    assert result["granted_scopes"] == ["EMD_SELF_ASSESSMENT"]
    assert result["blocked_by_profile"] == ["EMD_PASTORAL_SHARE"]
    assert result["modified"] is True


def test_unknown_scopes_are_reported_rather_than_silently_granted():
    result = enforce_scope_request(["EMD_SELF_ASSESSMENT", "EMD_MAKE_IT_UP"], profile="PRODUCTION")
    assert result["unknown_scopes"] == ["EMD_MAKE_IT_UP"]
    assert "EMD_MAKE_IT_UP" not in result["granted_scopes"]


@pytest.mark.parametrize("feature", sorted(FEATURE_REQUIREMENTS))
def test_every_sharing_and_group_feature_is_blocked_in_pilot(feature, monkeypatch):
    monkeypatch.delenv("EMD_ASSURANCE_PROFILE", raising=False)
    with pytest.raises(PilotGateError) as exc:
        guard_feature(feature)
    assert "RESTRICTED_PILOT" in str(exc.value)


@pytest.mark.parametrize("feature", sorted(FEATURE_REQUIREMENTS))
def test_the_same_features_are_available_in_production(feature):
    assert guard_feature(feature, profile="PRODUCTION")["allowed"] is True


def test_an_unknown_feature_is_refused_rather_than_allowed():
    with pytest.raises(PilotGateError):
        guard_feature("SOMETHING_NEW", profile="PRODUCTION")


def test_environment_can_select_the_profile_explicitly(monkeypatch):
    monkeypatch.setenv("EMD_ASSURANCE_PROFILE", "PRODUCTION")
    assert capabilities()["sharing_allowed"] is True
    assert available_consent_scopes()["withheld_scopes"] == {}


def test_feature_matrix_summarises_the_deployment(monkeypatch):
    monkeypatch.delenv("EMD_ASSURANCE_PROFILE", raising=False)
    matrix = feature_matrix()
    assert matrix["profile"] == "PILOT"
    assert all(allowed is False for allowed in matrix["features"].values())
    assert "EMD_PASTORAL_SHARE" in matrix["consent_scopes_withheld"]


# ── 路由层确实接上了 ─────────────────────────────────────────────────────────

ROUTER_SOURCE = (BACKEND / "routers" / "formation_twin_emotional_maturity.py").read_text(encoding="utf-8")


@pytest.mark.parametrize("feature", ["PASTORAL_SUMMARY", "PASTORAL_HANDOFF", "GROUP_PRACTICE", "COMMUNITY_FEEDBACK"])
def test_sharing_endpoints_call_the_guard(feature):
    assert f'guard_feature("{feature}")' in ROUTER_SOURCE


def test_consent_endpoint_filters_scopes_through_the_gate():
    assert "enforce_scope_request(" in ROUTER_SOURCE
    assert "available_consent_scopes()" in ROUTER_SOURCE


def test_new_pilot_endpoints_are_registered():
    from routers.formation_twin_emotional_maturity import router

    paths = {route.path for route in router.routes}
    for suffix in (
        "display-contract", "display-contract/validate", "deletion-plan",
        "pilot-capabilities", "training-optout", "training-optout/audit",
    ):
        assert f"/api/v1/formation-twin/emotional-maturity/{suffix}" in paths


# ── 前端调用的端点必须真的存在 ───────────────────────────────────────────────

def test_every_endpoint_the_web_client_calls_exists():
    """端点名对不上会静默 404，而前端把 404 当成「还没做过评估」——
    于是一个接线错误会伪装成「你还没有数据」，最难被发现的那种失败。

    这条曾经真的发生过：客户端写的是 `/growth-route`，后端是 `/route`。
    """
    import re

    from routers.formation_twin_emotional_maturity import router

    # Web 仓库是 bible3dsphere 的同级目录，不是它的子目录。
    relative = Path("src/features/formation-twin/emotionalMaturityApi.js")
    candidates = [
        BACKEND.parent.parent / "bible3dsphereWeb" / relative,
        BACKEND.parent / "bible3dsphereWeb" / relative,
    ]
    client = next((path for path in candidates if path.exists()), None)
    if client is None:
        pytest.skip("web client not checked out alongside the backend")

    paths = {route.path for route in router.routes}
    prefix = "/api/v1/formation-twin/emotional-maturity"
    called = set(re.findall(r"request\(\s*[`'\"]([^`'\"]+)[`'\"]", client.read_text(encoding="utf-8")))
    missing = sorted(
        path for path in called
        if not path.startswith("$") and f"{prefix}{path}" not in paths
    )
    assert missing == [], f"web client calls endpoints the router does not expose: {missing}"
