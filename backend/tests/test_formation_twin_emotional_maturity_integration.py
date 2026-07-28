from __future__ import annotations

from pathlib import Path

import pytest

from formation_twin.emotional_maturity import UnsafeContentError
from formation_twin.emotional_maturity_integration import (
    EVIDENCE_TYPES,
    FEEDBACK_WEIGHT_CAP,
    FORBIDDEN_USES,
    NEVER_SHAREABLE_FIELDS,
    TWIN_WRITABLE_TYPES,
    WORKFLOW_NODES,
    TwinEvidence,
    bridge_to_twin,
    build_pastoral_summary,
    compile_rule_of_life,
    coordinate_handoff,
    describe_integration_engine,
    design_group_practice,
    map_identity_alignment,
    orchestrate_plan,
    reconcile_community_feedback,
    route_prayer,
    validate_theological_output,
    withdraw_twin_evidence,
)


pytestmark = pytest.mark.no_db
ROOT = Path(__file__).resolve().parents[2]
FULL_SCOPES = ["EMD_SELF_ASSESSMENT", "EMD_BEHAVIOR_EVIDENCE", "EMD_LONGITUDINAL_TWIN", "EMD_PASTORAL_SHARE"]


# ── EM-62 twin bridge ────────────────────────────────────────────────────────

def test_only_confirmed_writable_evidence_reaches_the_twin():
    result = bridge_to_twin(
        [
            TwinEvidence(evidence_id="e1", evidence_type="SYSTEM_HYPOTHESIS"),
            TwinEvidence(evidence_id="e2", evidence_type="OBSERVABLE_BEHAVIOR", user_confirmed=False),
            TwinEvidence(evidence_id="e3", evidence_type="USER_CONFIRMED_INTEGRATION", user_confirmed=True),
        ],
        consented_scopes=["EMD_LONGITUDINAL_TWIN"],
    )
    assert [item["evidence_id"] for item in result["written"]] == ["e3"]
    reasons = {item["evidence_id"]: item["reason"] for item in result["held_back"]}
    assert reasons["e1"] == "TYPE_NOT_WRITABLE"
    assert reasons["e2"] == "USER_CONFIRMATION_MISSING"


def test_twin_write_requires_longitudinal_consent():
    result = bridge_to_twin(
        [TwinEvidence(evidence_id="e1", evidence_type="USER_CONFIRMED_INTEGRATION", user_confirmed=True)],
        consented_scopes=["EMD_SELF_ASSESSMENT"],
    )
    assert result["status"] == "BLOCKED_NO_CONSENT"
    assert result["written"] == []


def test_evidence_types_are_never_merged():
    result = bridge_to_twin([], consented_scopes=["EMD_LONGITUDINAL_TWIN"])
    assert set(result["evidence_types_never_merged"]) == set(EVIDENCE_TYPES)
    assert "PASTORAL_DISCERNMENT" not in TWIN_WRITABLE_TYPES


def test_withdrawal_propagates_everywhere():
    result = withdraw_twin_evidence("e3")
    assert set(result["effects"]) == {
        "RECOMPUTE_DIMENSION_SNAPSHOT", "REVOKE_DERIVED_SHARES",
        "STOP_RELATED_REMINDERS", "KEEP_VERSION_HISTORY",
    }
    assert result["silent_retention"] is False


def test_unknown_evidence_type_is_rejected():
    with pytest.raises(ValueError):
        TwinEvidence(evidence_id="x", evidence_type="GUESS")


# ── EM-63 identity alignment ─────────────────────────────────────────────────

def test_alignment_reports_gaps_without_judging_sincerity():
    result = map_identity_alignment(layers={
        "VALUES": ["诚实", "忠心"],
        "EMOTIONAL_PATTERN": ["压力下容易讨好"],
    })
    codes = {item["code"] for item in result["gaps"]}
    assert "VALUE_WITHOUT_BEHAVIOR_EVIDENCE" in codes
    assert "不代表你不真诚" in result["not_a_verdict"]


def test_divine_voice_claims_are_blocked_in_identity_content():
    with pytest.raises(UnsafeContentError):
        map_identity_alignment(layers={"IDENTITY_TRUTH": ["神现在对你说你是失败的"]})
    with pytest.raises(UnsafeContentError):
        validate_theological_output("神给你的命定是成为领袖")


def test_unknown_alignment_layer_is_rejected():
    with pytest.raises(ValueError):
        map_identity_alignment(layers={"VIBES": ["x"]})


# ── EM-64 prayer routing ─────────────────────────────────────────────────────

def test_emotions_route_to_matching_prayer_forms():
    result = route_prayer(confirmed_emotions=["GRIEF", "GUILT"])
    forms = {item["form"] for item in result["forms"]}
    assert {"LAMENT", "CONFESSION"} <= forms
    assert result["content_source"] == "CURATED_THEOLOGICAL_PROPOSITION"
    assert result["free_generation_allowed"] is False


def test_prayer_never_claims_to_speak_for_god():
    result = route_prayer(confirmed_emotions=["FEAR"])
    joined = " ".join(result["never_claims"])
    assert "神现在对你说" in joined
    assert "立刻原谅" in joined


def test_safety_comes_before_prayer():
    result = route_prayer(confirmed_emotions=["GRIEF"], safety_level="IMMINENT")
    assert result["status"] == "SAFETY_FIRST"
    assert result["next_action"] == "CRISIS_AND_SAFETY_SYSTEM"


def test_neutral_framework_gets_non_religious_alternatives():
    result = route_prayer(confirmed_emotions=["GRIEF"], spiritual_framework="neutral")
    assert result["status"] == "NOT_APPLICABLE_NEUTRAL_FRAMEWORK"
    assert result["alternatives"]


# ── EM-65 rule of life ───────────────────────────────────────────────────────

def test_habits_are_capped_per_cadence():
    goals = [{"cadence": "DAILY", "habit": f"练习 {index}"} for index in range(5)]
    result = compile_rule_of_life(goals=goals)
    assert len(result["habits"]["DAILY"]) == 3
    assert len(result["deferred"]) == 2


def test_low_capacity_halves_the_caps():
    goals = [{"cadence": "DAILY", "habit": f"练习 {index}"} for index in range(3)]
    result = compile_rule_of_life(goals=goals, capacity="LOW")
    assert len(result["habits"]["DAILY"]) == 1


def test_every_habit_gets_a_smallest_version():
    result = compile_rule_of_life(goals=[{"cadence": "DAILY", "habit": "睡前一分钟命名情绪"}])
    assert result["habits"]["DAILY"][0]["smallest_version"]


def test_missing_a_day_is_never_failure():
    result = compile_rule_of_life(goals=[{"cadence": "WEEKLY", "habit": "一次安息时段"}])
    assert any("漏掉一天不算失败" in note for note in result["principles"])
    assert any("不用打卡数量代表成长" in note for note in result["principles"])


def test_overload_is_warned_about():
    goals = [{"cadence": cadence, "habit": f"{cadence} 练习"} for cadence in ("DAILY", "WEEKLY", "RELATIONAL")]
    result = compile_rule_of_life(goals=goals, current_load=5)
    assert result["overload_warning"]


# ── EM-66 plan orchestration ─────────────────────────────────────────────────

def test_plan_caps_active_tracks_and_queues_the_rest():
    result = orchestrate_plan(
        requested_tracks=["EMOTIONAL", "IDENTITY", "PRAYER", "HABIT"],
        consented_scopes=FULL_SCOPES,
    )
    assert len(result["active_tracks"]) == 3
    assert result["queued_tracks"] == ["HABIT"]


def test_community_track_requires_sharing_consent():
    result = orchestrate_plan(requested_tracks=["EMOTIONAL", "COMMUNITY"], consented_scopes=["EMD_SELF_ASSESSMENT"])
    assert "COMMUNITY" not in result["active_tracks"]
    assert result["dropped_tracks"][0]["reason"] == "CONSENT_MISSING"


def test_safety_overrides_the_whole_plan():
    result = orchestrate_plan(requested_tracks=["EMOTIONAL"], safety_level="ELEVATED")
    assert result["status"] == "SAFETY_FIRST"
    assert result["active_tracks"] == []


def test_one_plan_across_systems_is_explicit():
    result = orchestrate_plan(requested_tracks=["EMOTIONAL"], consented_scopes=FULL_SCOPES)
    assert "共用一个计划" in result["single_plan_note"]
    assert result["user_can_decline_any_track"] is True


# ── EM-67 pastoral summary ───────────────────────────────────────────────────

def summary(**updates):
    values = {
        "selected_fields": ["CURRENT_FOCUS", "SUPPORT_NEEDED"],
        "field_values": {"CURRENT_FOCUS": "练习冲突后先暂停", "SUPPORT_NEEDED": "希望有人每周问我一次"},
        "recipient_label": "我的牧者",
        "consented_scopes": FULL_SCOPES,
    }
    values.update(updates)
    return build_pastoral_summary(**values)


def test_summary_requires_explicit_sharing_consent():
    result = summary(consented_scopes=["EMD_SELF_ASSESSMENT"])
    assert result["status"] == "BLOCKED_NO_CONSENT"
    assert result["content"] == {}


def test_summary_is_previewed_editable_expiring_and_revocable():
    result = summary()
    assert result["user_must_preview"] is True
    assert result["user_can_edit_each_field"] is True
    assert result["auto_sent"] is False
    assert result["revocable_any_time"] is True
    assert result["expires_in_days"] == 30


def test_private_material_can_never_enter_a_summary():
    with pytest.raises(UnsafeContentError):
        summary(field_values={"CURRENT_FOCUS": "x", "journal_text": "我的日记正文"})
    assert "childhood_material" in NEVER_SHAREABLE_FIELDS
    assert "prayer_text" in NEVER_SHAREABLE_FIELDS


def test_summary_lists_forbidden_uses():
    result = summary()
    assert "服事资格判断" in result["forbidden_uses"]
    assert "属灵成熟排名" in result["forbidden_uses"]


# ── EM-68 handoff ────────────────────────────────────────────────────────────

def test_signals_route_to_the_right_human_support():
    result = coordinate_handoff(signals=["MEDICAL_RED_FLAG", "SELF_HARM_OR_HARM_TO_OTHERS"])
    targets = {item["target"] for item in result["targets"]}
    assert {"MEDICAL", "CRISIS"} <= targets


def test_the_system_never_contacts_anyone_itself():
    result = coordinate_handoff(signals=["FAITH_QUESTION"])
    assert result["auto_contact"] is False
    assert any("不会替你联系任何人" in note for note in result["system_does_not"])


def test_church_involved_harm_is_never_routed_back_to_the_church():
    result = coordinate_handoff(signals=["FAITH_QUESTION", "SPIRITUAL_AUTHORITY_HARM"], church_involved_in_harm=True)
    targets = {item["target"] for item in result["targets"]}
    assert "PASTORAL" not in targets
    assert "LEGAL_OR_SAFETY" in targets


# ── EM-69 group practice ─────────────────────────────────────────────────────

def test_group_practice_rejects_forced_disclosure_and_leader_surveillance():
    forced = design_group_practice(kind="CHECK_IN_QUESTION", group_size=6, disclosure_required=True)
    assert forced["status"] == "REJECTED"
    assert "DISCLOSURE_REQUIREMENT_NOT_ALLOWED" in forced["blocks"]
    watched = design_group_practice(kind="CHECK_IN_QUESTION", group_size=6, leader_can_view_records=True)
    assert "LEADER_RECORD_ACCESS_NOT_ALLOWED" in watched["blocks"]


def test_anyone_may_pass_without_explaining():
    result = design_group_practice(kind="SHARED_PRACTICE", group_size=5)
    assert result["pass_allowed"] is True
    assert "不需要解释" in result["pass_note"]


def test_group_practice_is_not_therapy_or_ranking():
    result = design_group_practice(kind="SKILL_REHEARSAL", group_size=4)
    forbidden = " ".join(result["forbidden_patterns"])
    assert "治疗小组" in forbidden
    assert "公开比较成员的成熟度" in forbidden


def test_unknown_group_practice_kind_is_rejected():
    with pytest.raises(ValueError):
        design_group_practice(kind="CONFESSION_CIRCLE", group_size=5)


# ── EM-70 community feedback ─────────────────────────────────────────────────

def test_feedback_weight_is_capped_and_authority_is_downweighted():
    result = reconcile_community_feedback(
        feedback_items=[
            {"feedback_id": "f1", "power_level": "PEER", "observation": "这次你先停下来再说话了"},
            {"feedback_id": "f2", "power_level": "HIGH_AUTHORITY", "observation": "我注意到你更少打断别人"},
        ],
        user_evidence_count=5,
    )
    weights = {item["feedback_id"]: item["weight"] for item in result["accepted"]}
    assert weights["f1"] == FEEDBACK_WEIGHT_CAP
    assert weights["f2"] < weights["f1"]
    assert result["community_cannot_outrank_user"] is True


def test_eligibility_language_in_feedback_is_excluded():
    result = reconcile_community_feedback(
        feedback_items=[{"feedback_id": "f1", "power_level": "HIGH_AUTHORITY",
                         "observation": "他还不够属灵，应该被撤下小组长"}],
        user_evidence_count=3,
    )
    assert result["accepted"] == []
    assert result["excluded"][0]["reason"] == "ELIGIBILITY_MISUSE"


def test_the_user_can_dispute_any_feedback_item():
    result = reconcile_community_feedback(
        feedback_items=[{"feedback_id": "f1", "power_level": "PEER", "observation": "你最近很冷淡"}],
        user_evidence_count=4,
        user_disputes=["f1"],
    )
    assert result["excluded"][0]["reason"] == "USER_DISPUTED"
    assert result["user_may_dispute_any_item"] is True


def test_feedback_is_observation_only():
    result = reconcile_community_feedback(
        feedback_items=[{"feedback_id": "f1", "power_level": "PEER", "observation": "你这次主动澄清了"}],
        user_evidence_count=2,
    )
    assert result["accepted"][0]["status"] == "OBSERVATION_ONLY"
    assert set(FORBIDDEN_USES) <= set(result["forbidden_uses"])


# ── module description and wiring ────────────────────────────────────────────

def test_module_description_lists_the_integration_refusals():
    described = describe_integration_engine()
    assert len(described["skills"]) == len(WORKFLOW_NODES) == 9
    refusals = " ".join(described["does_not"])
    assert "不让模型自由生成神对用户说的话" in refusals
    assert "不因为角色是牧者或小组长就给予访问权" in refusals
    assert "不把情感成熟度用于服事资格、按立或纪律" in refusals


def test_router_exposes_the_batch_eight_surface():
    from routers.formation_twin_emotional_maturity import router

    paths = {route.path for route in router.routes}
    for suffix in (
        "integration/overview", "integration/twin-bridge", "integration/identity",
        "integration/prayer", "integration/rule-of-life", "integration/plan",
        "integration/pastoral-summary", "integration/handoff",
        "integration/group-practice", "integration/community-feedback",
    ):
        assert f"/api/v1/formation-twin/emotional-maturity/{suffix}" in paths


def test_migration_file_exists_for_batch_eight():
    migration = ROOT / "backend/migrations/0230_formation_twin_emd_integration.sql"
    rollback = ROOT / "backend/migrations/rollback/0230_formation_twin_emd_integration_down.sql"
    assert migration.exists() and rollback.exists()
    sql = migration.read_text(encoding="utf-8")
    assert "formation_twin_emd_pastoral_summaries" in sql
    assert "formation_twin_emd_community_feedback" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql


def test_erasure_covers_every_batch_eight_table():
    source = (ROOT / "backend/routers/formation_twin_emotional_maturity.py").read_text(encoding="utf-8")
    erase_block = source.split("def emotional_maturity_erase")[1]
    for table in (
        "formation_twin_emd_twin_bridges", "formation_twin_emd_identity_alignments",
        "formation_twin_emd_prayer_routings", "formation_twin_emd_rules_of_life",
        "formation_twin_emd_formation_plans", "formation_twin_emd_pastoral_summaries",
        "formation_twin_emd_handoffs", "formation_twin_emd_group_practices",
        "formation_twin_emd_community_feedback",
    ):
        assert table in erase_block
