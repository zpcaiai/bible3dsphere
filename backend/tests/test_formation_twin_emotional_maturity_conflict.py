from __future__ import annotations

from pathlib import Path

import pytest

from formation_twin.emotional_maturity import UnsafeContentError
from formation_twin.emotional_maturity_conflict import (
    DIRTY_CONFLICT_CODES,
    RELATIONSHIP_EVIDENCE_LEVELS,
    TRUST_RANK,
    WORKFLOW_NODES,
    build_apology,
    calibrate_motive_uncertainty,
    describe_conflict_engine,
    differentiate_forgiveness,
    facilitate_dialogue,
    frame_conflict_issue,
    map_boundary,
    plan_boundary_enforcement,
    plan_restitution,
    route_repair_outcome,
    train_perspective_taking,
)


pytestmark = pytest.mark.no_db
ROOT = Path(__file__).resolve().parents[2]


# ── EM-44 empathy ────────────────────────────────────────────────────────────

def test_empathy_never_endorses_harmful_behaviour():
    result = train_perspective_taking(
        situation="伴侣查看了我的手机",
        user_experience="我觉得被侵犯了隐私",
        possible_other_experience="对方可能因为害怕失去联系而焦虑",
        harmful_behaviors=["未经允许查看手机", "限制我与朋友见面"],
    )
    assert result["hypothesis_status"] == "UNVERIFIED_HYPOTHESIS"
    assert any("未经允许查看手机" in item for item in result["still_true_regardless"])
    assert "不代表认可对方的行为" in result["empathy_is_not_agreement"]


def test_empathy_output_that_justifies_harm_is_blocked():
    with pytest.raises(UnsafeContentError):
        train_perspective_taking(
            situation="伴侣查看了我的手机",
            user_experience="我觉得被侵犯",
            possible_other_experience="他很焦虑，所以他这样做是合理的",
        )


def test_empathy_adds_a_safety_note_for_unsafe_relationships():
    result = train_perspective_taking(
        situation="领导公开羞辱我", user_experience="我很羞耻",
        possible_other_experience="对方可能压力很大", relationship_safety="CAUTION",
    )
    assert "先保护自己" in result["safety_note"]


# ── EM-45 mentalization ──────────────────────────────────────────────────────

def test_mind_reading_is_converted_into_a_hypothesis_and_a_question():
    result = calibrate_motive_uncertainty("他就是故意打压我")
    assert result["mind_reading_detected"] is True
    assert result["hypothesis_status"] == "UNVERIFIED_HYPOTHESIS"
    assert "还不知道这是不是他的真实意思" in result["hypothesis"]
    assert result["clarification_questions"]


def test_alternative_explanations_include_the_possibility_the_user_is_right():
    result = calibrate_motive_uncertainty("她肯定是不在乎我")
    assert any("确实如你所想" in item for item in result["alternative_explanations"])


def test_a_neutral_observation_is_left_alone():
    result = calibrate_motive_uncertainty("他昨天没有回复我的消息")
    assert result["mind_reading_detected"] is False


# ── EM-46 boundaries ─────────────────────────────────────────────────────────

def boundary(**updates):
    values = {
        "boundary_object": "WORKLOAD",
        "scenario": "负责人连续第四周要求临时补位",
        "boundary_kind": "LIMIT",
        "boundary_statement": "这个月我不能再接额外的服事排班。",
        "my_responsibilities": ["诚实说明精力", "履行已经答应的部分"],
        "their_responsibilities": ["安排人手", "处理自己的失望"],
        "action_if_violated": "如果仍被排入班表，我会书面说明并请另一位负责人协助。",
    }
    values.update(updates)
    return map_boundary(**values)


def test_boundary_maps_four_kinds_of_responsibility():
    result = boundary()
    assert set(result["responsibility_map"]) == {"mine", "theirs", "shared", "not_controllable"}
    assert result["responsibility_map"]["not_controllable"]


def test_control_language_is_rejected_as_a_boundary():
    with pytest.raises(UnsafeContentError):
        boundary(boundary_statement="你必须承认自己错了，否则我就让所有人都不理你")
    with pytest.raises(UnsafeContentError):
        boundary(action_if_violated="不然你就别想我再帮忙")


def test_high_guilt_gets_a_note_that_guilt_is_not_the_judge():
    result = boundary(guilt_level=8)
    assert "内疚感高不代表边界错了" in result["guilt_note"]


def test_unknown_boundary_object_is_rejected():
    with pytest.raises(ValueError):
        boundary(boundary_object="SOMETHING_ELSE")


# ── EM-47 enforcement ────────────────────────────────────────────────────────

def test_first_violation_starts_at_the_lowest_rung():
    assert plan_boundary_enforcement(violation_count=0)["recommended_level"] == "L0"
    assert plan_boundary_enforcement(violation_count=1)["recommended_level"] == "L1"


def test_safety_risk_jumps_straight_to_safe_exit():
    result = plan_boundary_enforcement(violation_count=0, safety_risk=True)
    assert result["recommended_level"] == "L5"
    assert result["may_skip_levels"] is True


def test_repeated_violations_with_support_reach_third_party_level():
    result = plan_boundary_enforcement(
        violation_count=4, available_support=["另一位负责人", "书面排班记录"],
    )
    assert result["recommended_level"] == "L4"


def test_enforcement_is_explicitly_non_retaliatory():
    result = plan_boundary_enforcement(violation_count=2, retaliation_risk="HIGH")
    assert "不是让对方难堪" in result["non_retaliation_rule"]
    assert "书面记录" in result["retaliation_note"]


# ── EM-48 clean conflict framing ─────────────────────────────────────────────

DIRTY = "他永远都不尊重我，从结婚开始就这样，他就是故意的，他和他家人都只会控制我！"


def test_dirty_components_are_detected():
    result = frame_conflict_issue(
        raw_complaint=DIRTY, activation_level=4, single_issue="这次临时取消约定希望提前告诉我",
    )
    codes = {item["code"] for item in result["dirty_components"]}
    assert {"MIND_READING", "ABSOLUTE_LANGUAGE", "HISTORY_FLOODING"} <= codes
    assert result["status"] == "READY"


def test_high_activation_defers_the_conflict():
    result = frame_conflict_issue(raw_complaint=DIRTY, activation_level=8, single_issue="x")
    assert result["status"] == "NOT_READY"
    assert "ACTIVATION_TOO_HIGH" in result["blocks"]
    assert result["next_action"] == "SACRED_PAUSE_PROTOCOL"


def test_violence_risk_blocks_conflict_preparation():
    result = frame_conflict_issue(
        raw_complaint="他昨天推了我", activation_level=3, violence_risk=True, single_issue="x",
    )
    assert "VIOLENCE_RISK" in result["blocks"]


def test_clean_conflict_still_allows_anger_and_tears():
    result = frame_conflict_issue(raw_complaint="我很生气", activation_level=3, single_issue="希望提前告诉我")
    assert "愤怒" in result["clean_conflict_allows"]
    assert "哭泣" in result["clean_conflict_allows"]
    assert "不是没有情绪的冲突" in result["note"]


def test_every_documented_dirty_component_is_covered():
    assert len(DIRTY_CONFLICT_CODES) == 8
    assert "MORAL_OR_SPIRITUAL_COERCION" in DIRTY_CONFLICT_CODES


# ── EM-49 dialogue ───────────────────────────────────────────────────────────

def test_dialogue_protocol_has_ten_steps_with_a_pause_contract():
    result = facilitate_dialogue(mode="SOLO_REHEARSAL", single_issue="临时取消约定")
    assert len(result["protocol"]) == 10
    assert result["pause_contract"]["action"].startswith("暂停并约定返回时间")


def test_solo_rehearsal_labels_simulated_replies():
    result = facilitate_dialogue(mode="SOLO_REHEARSAL", single_issue="x")
    assert "模拟回应" in result["simulated_reply_label"]


def test_mutual_workspace_requires_both_consents():
    blocked = facilitate_dialogue(mode="MUTUAL_WORKSPACE", single_issue="x")
    assert blocked["status"] == "BLOCKED_CONSENT"
    ready = facilitate_dialogue(mode="MUTUAL_WORKSPACE", single_issue="x", both_parties_consented=True)
    assert ready["status"] == "READY"
    assert ready["shared_content_requires_consent"] is True


def test_unsafe_relationship_gets_no_dialogue_flow():
    result = facilitate_dialogue(mode="SOLO_REHEARSAL", single_issue="x", relationship_safety="UNSAFE")
    assert result["status"] == "NOT_GENERATED_UNSAFE"


def test_system_never_arbitrates_who_is_right():
    result = facilitate_dialogue(mode="SOLO_REHEARSAL", single_issue="x")
    assert any("不裁决谁对谁错" in item for item in result["system_does_not"])


# ── EM-50 apology ────────────────────────────────────────────────────────────

def test_healthy_apology_has_seven_parts_and_is_not_auto_sent():
    result = build_apology(
        specific_behavior="在群里未经核实就说你不负责任",
        impact="伤害了你的声誉",
        amends="公开更正",
        change_plan="以后先做事实确认",
    )
    assert len(result["parts"]) == 7
    assert result["status"] == "READY"
    assert result["auto_sent"] is False
    assert "不会催你原谅" in result["composed_draft"]


def test_conditional_and_but_apologies_are_flagged():
    result = build_apology(
        specific_behavior="说了重话", impact="让你难受",
        draft_text="如果你觉得受伤，我道歉，但是你也有问题。",
    )
    codes = {item["code"] for item in result["invalid_patterns"]}
    assert {"IF_APOLOGY", "BUT_APOLOGY"} <= codes
    assert result["status"] == "NEEDS_REVISION"


def test_self_condemnation_is_flagged_as_an_invalid_apology():
    result = build_apology(
        specific_behavior="说了重话", impact="让你难受",
        draft_text="我就是个垃圾，你别生气了。",
    )
    assert any(item["code"] == "SELF_CONDEMNATION" for item in result["invalid_patterns"])


def test_pressuring_for_forgiveness_is_flagged():
    result = build_apology(
        specific_behavior="爽约", impact="让你白等",
        draft_text="我都道歉了，你必须翻篇。",
    )
    assert any(item["code"] == "FORGIVENESS_PRESSURE" for item in result["invalid_patterns"])


def test_missing_amends_and_change_plan_are_reported():
    result = build_apology(specific_behavior="爽约", impact="让你白等")
    assert set(result["missing_parts"]) == {"AMENDS", "CHANGE_PLAN"}


# ── EM-51 forgiveness ────────────────────────────────────────────────────────

def test_eight_concepts_are_separated_with_dependency_flags():
    result = differentiate_forgiveness(harm_type="严重背叛并持续撒谎")
    assert len(result["separation_model"]) == 8
    assert "TRUST" in result["requires_other_party"]
    assert "FORGIVENESS_PROCESS" in result["independent_of_other_party"]


def test_anger_does_not_prove_a_lack_of_forgiveness():
    result = differentiate_forgiveness(harm_type="背叛", still_feels_anger=True)
    assert result["anger_does_not_disprove_forgiveness"] is True
    assert result["system_conclusion"] is None
    assert "系统不判定你是否已经宽恕" in result["conclusion_note"]


def test_forgiveness_never_cancels_boundaries_or_consequences():
    principles = differentiate_forgiveness(harm_type="背叛")["principles"]
    assert "宽恕不取消边界" in principles
    assert "宽恕不取消现实后果" in principles
    assert "宽恕速度不能作为属灵成熟评分" in principles


def test_unsafe_relationship_gets_the_distance_note():
    result = differentiate_forgiveness(harm_type="持续操控", relationship_safety="UNSAFE")
    assert "保持距离可能正是成熟的边界" in result["contact_note"]


def test_theological_framework_source_must_be_declared():
    with pytest.raises(ValueError):
        differentiate_forgiveness(harm_type="背叛", framework_source="MODEL_OPINION")


# ── EM-52 restitution ────────────────────────────────────────────────────────

def test_unilateral_repair_is_possible_without_the_other_party():
    result = plan_restitution(
        mode="MUTUAL",
        items=[{"kind": "PUBLIC_CORRECTION", "description": "在同一个群里更正我说错的话"}],
    )
    assert result["status"] == "DOWNGRADED_TO_UNILATERAL"
    assert "仍然可以完成你自己那一部分" in result["note"]


def test_restitution_items_are_concrete_and_verifiable():
    result = plan_restitution(
        mode="UNILATERAL",
        items=[
            {"kind": "FINANCIAL_REPAYMENT", "description": "两周内归还借款", "due_in_days": 14},
            {"kind": "STOP_BEHAVIOR", "description": "不再在群里评论对方的工作"},
        ],
    )
    assert result["status"] == "READY"
    assert result["items"][0]["due_in_days"] == 14
    assert all(item["verifiable_by"] for item in result["items"])


def test_completing_repair_does_not_guarantee_the_relationship():
    result = plan_restitution(mode="UNILATERAL", items=[{"kind": "STOP_BEHAVIOR", "description": "停止翻旧账"}])
    assert "不保证关系恢复" in result["outcome_not_guaranteed"]
    assert "不催促对方" in result["user_responsible_for"]


def test_unsafe_relationship_gets_no_restitution_workflow():
    result = plan_restitution(
        mode="UNILATERAL", items=[{"kind": "STOP_BEHAVIOR", "description": "x"}],
        relationship_safety="UNSAFE",
    )
    assert result["status"] == "NOT_GENERATED_UNSAFE"


# ── EM-53 outcome routing ────────────────────────────────────────────────────

def test_words_only_stays_at_tr1():
    result = route_repair_outcome(
        domain="FINANCE", apology_delivered=True, restitution_completed=False,
    )
    assert result["trust_level"] == "TR1"


def test_sustained_change_moves_up_the_trust_ladder():
    result = route_repair_outcome(
        domain="TIME_RELIABILITY", apology_delivered=True, restitution_completed=True,
        old_behavior_stopped_weeks=14, boundary_respected=True,
    )
    assert TRUST_RANK[result["trust_level"]] >= TRUST_RANK["TR4"]


def test_safety_concern_resets_trust_and_offers_exit():
    result = route_repair_outcome(
        domain="PHYSICAL_SAFETY", apology_delivered=True, restitution_completed=True,
        old_behavior_stopped_weeks=30, boundary_respected=True, safety_concern=True,
    )
    assert result["trust_level"] == "TR0"
    assert any(item["option"] == "EXIT_RELATIONSHIP" for item in result["options"])


def test_repeated_violation_offers_limits_and_mediation():
    result = route_repair_outcome(
        domain="EMOTIONAL_CONFIDENTIALITY", apology_delivered=True, restitution_completed=True,
        old_behavior_stopped_weeks=6, boundary_respected=False, repeated_violation=True,
    )
    options = {item["option"] for item in result["options"]}
    assert {"LIMIT_CONTACT", "REQUEST_MEDIATION"} <= options


def test_trust_is_never_binary_and_the_system_does_not_decide():
    result = route_repair_outcome(domain="FINANCE", apology_delivered=False, restitution_completed=False)
    assert "0 或 100" in result["trust_is_not"]
    assert result["system_decides"] is False
    assert set(RELATIONSHIP_EVIDENCE_LEVELS) == {"RE0", "RE1", "RE2", "RE3", "RE4", "RE5", "RE6"}


def test_unknown_trust_domain_is_rejected():
    with pytest.raises(ValueError):
        route_repair_outcome(domain="EVERYTHING", apology_delivered=True, restitution_completed=True)


# ── module description and wiring ────────────────────────────────────────────

def test_module_description_lists_all_seven_distinctions():
    described = describe_conflict_engine()
    assert len(described["skills"]) == len(WORKFLOW_NODES) == 10
    refusals = " ".join(described["does_not"])
    assert "不把同理心当作认可对方的行为" in refusals
    assert "不把控制包装成边界" in refusals
    assert "不把宽恕等同于信任" in refusals
    assert "不替用户决定是否维持关系" in refusals


def test_router_exposes_the_batch_six_surface():
    from routers.formation_twin_emotional_maturity import router

    paths = {route.path for route in router.routes}
    for suffix in (
        "conflict/overview", "conflict/perspective", "conflict/motive-calibration",
        "conflict/boundary", "conflict/enforcement", "conflict/issue",
        "conflict/dialogue", "conflict/apology", "conflict/forgiveness",
        "conflict/restitution", "conflict/outcome",
    ):
        assert f"/api/v1/formation-twin/emotional-maturity/{suffix}" in paths


def test_migration_file_exists_for_batch_six():
    migration = ROOT / "backend/migrations/0228_formation_twin_emd_conflict_repair.sql"
    rollback = ROOT / "backend/migrations/rollback/0228_formation_twin_emd_conflict_repair_down.sql"
    assert migration.exists() and rollback.exists()
    sql = migration.read_text(encoding="utf-8")
    assert "formation_twin_emd_boundaries" in sql
    assert "formation_twin_emd_trust_assessments" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql


def test_erasure_covers_every_batch_six_table():
    source = (ROOT / "backend/routers/formation_twin_emotional_maturity.py").read_text(encoding="utf-8")
    erase_block = source.split("def emotional_maturity_erase")[1]
    for table in (
        "formation_twin_emd_boundaries", "formation_twin_emd_boundary_enforcements",
        "formation_twin_emd_conflict_issues", "formation_twin_emd_dialogues",
        "formation_twin_emd_apologies", "formation_twin_emd_forgiveness_maps",
        "formation_twin_emd_restitution_plans", "formation_twin_emd_trust_assessments",
    ):
        assert table in erase_block
