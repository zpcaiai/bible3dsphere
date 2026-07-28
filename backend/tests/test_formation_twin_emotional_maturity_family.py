from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from formation_twin.emotional_maturity import UnsafeContentError
from formation_twin.emotional_maturity_family import (
    DEPTH_RANK,
    FACTUAL_MEMORY_SOURCES,
    FAMILY_PATTERN_LEVELS,
    MASKS,
    SD_RANK,
    TWIN_WRITE_MINIMUM,
    WORKFLOW_NODES,
    GenogramMember,
    GenogramRelationship,
    analyze_family_scripts,
    assess_differentiation,
    build_genogram,
    build_true_self_compass,
    describe_family_engine,
    design_vulnerability_experiment,
    evidence_level,
    may_write_to_twin,
    profile_attachment_cycle,
    profile_masks,
    reframe_survival_oath,
    validate_third_party_language,
)


pytestmark = pytest.mark.no_db
NOW = datetime(2026, 7, 28, 12, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[2]


def member(**updates) -> GenogramMember:
    values = {
        "member_id": "m_mother",
        "generation": "G2_PARENTS",
        "role_label": "母亲",
        "observed_behaviors": ["在争吵后连续两天不说话"],
        "memory_source": "direct_memory",
    }
    values.update(updates)
    return GenogramMember(**values)


# ── evidence levels ──────────────────────────────────────────────────────────

def test_abstract_statements_stay_at_fp0():
    assert evidence_level(concrete_events=0, distinct_periods=0, relationships_involved=0) == "FP0"


def test_repeated_events_reach_fp2_and_multi_relationship_fp3():
    assert evidence_level(concrete_events=2, distinct_periods=2, relationships_involved=1) == "FP2"
    assert evidence_level(concrete_events=3, distinct_periods=2, relationships_involved=2) == "FP3"


def test_only_fp4_and_above_may_be_written_to_the_twin():
    assert may_write_to_twin("FP4") is True
    assert may_write_to_twin("FP5") is True
    assert may_write_to_twin("FP3") is False
    assert TWIN_WRITE_MINIMUM == "FP4"
    assert set(FAMILY_PATTERN_LEVELS) == {"FP0", "FP1", "FP2", "FP3", "FP4", "FP5"}


def test_longitudinal_confirmation_is_needed_for_fp5():
    assert evidence_level(
        concrete_events=4, distinct_periods=3, relationships_involved=2,
        linked_to_current_behavior=True, longitudinally_confirmed=True, user_confirmed=True,
    ) == "FP5"
    assert evidence_level(
        concrete_events=4, distinct_periods=3, relationships_involved=2,
        linked_to_current_behavior=True, longitudinally_confirmed=True, user_confirmed=False,
    ) == "FP4"


# ── EM-36 genogram ───────────────────────────────────────────────────────────

def test_genogram_keeps_only_observable_behaviour():
    result = build_genogram([member(), member(member_id="m_self", generation="G3_SELF", role_label="我")], [], now=NOW)
    assert result["member_count"] == 2
    assert result["third_party_diagnosis_blocked"] is True
    assert result["editable_by_user"] is True


def test_remote_diagnosis_of_a_family_member_is_rejected():
    # pydantic wraps the guard in a ValidationError, which is a ValueError subclass
    with pytest.raises(ValueError):
        member(observed_behaviors=["我妈是自恋型人格"])
    with pytest.raises(UnsafeContentError):
        validate_third_party_language("他有边缘型人格")


def test_system_hypothesis_material_never_enters_family_history():
    result = build_genogram(
        [member(), member(member_id="m_guess", memory_source="system_hypothesis")], [], now=NOW,
    )
    assert result["excluded_hypothesis_members"] == ["m_guess"]
    assert result["member_count"] == 1
    assert set(result["memory_sources_used"]) <= FACTUAL_MEMORY_SOURCES


def test_relationships_must_reference_known_members():
    with pytest.raises(ValueError):
        build_genogram([member()], [GenogramRelationship(from_member_id="m_mother", to_member_id="ghost")], now=NOW)


# ── EM-37 scripts, roles, triangles ──────────────────────────────────────────

def test_scripts_carry_their_own_evidence_level():
    result = analyze_family_scripts(script_candidates=[
        {"script_code": "SURFACE_PEACE_FIRST", "concrete_events": 3, "distinct_periods": 2,
         "relationships_involved": 2, "linked_to_current_behavior": True},
        {"script_code": "NEEDS_ARE_BURDENS", "concrete_events": 0},
    ])
    strong, weak = result["scripts"]
    assert strong["evidence_level"] == "FP4" and strong["may_write_to_twin"] is True
    assert weak["evidence_level"] == "FP0" and weak["may_write_to_twin"] is False
    assert result["twin_writable_scripts"] == ["SURFACE_PEACE_FIRST"]


def test_triangles_are_recorded_as_observable_patterns():
    result = analyze_family_scripts(
        script_candidates=[],
        roles_reported=["MEDIATOR"],
        triangles=[{
            "member_a": "m_father", "member_b": "m_mother", "third_party": "m_self",
            "user_function": "MEDIATOR", "observable_pattern": "母亲向我倾诉，然后我去劝父亲",
            "evidence_events": 3,
        }],
    )
    assert result["triangles"][0]["user_function"] == "MEDIATOR"
    assert result["roles"][0]["label"] == "调停者"


def test_unknown_scripts_and_roles_are_rejected():
    with pytest.raises(ValueError):
        analyze_family_scripts(script_candidates=[{"script_code": "MADE_UP"}])
    with pytest.raises(ValueError):
        analyze_family_scripts(script_candidates=[], roles_reported=["SUPERSTAR"])


# ── EM-38 attachment cycle ───────────────────────────────────────────────────

def cycle_events(count: int = 3, context: str | None = None) -> list[dict]:
    return [
        {"protective_action": "PURSUE", "period": f"p{index}", "user_confirmed": True,
         "relationship_context": context, "repaired": index == 0}
        for index in range(count)
    ]


def test_cycle_needs_at_least_two_events():
    result = profile_attachment_cycle(
        relationship_context="partner", events=cycle_events(1),
        trigger_condition="延迟回应",
    )
    assert result["status"] == "INSUFFICIENT_EVENTS"
    assert "不代表你有依恋问题" in result["note"]


def test_no_permanent_attachment_type_is_assigned():
    result = profile_attachment_cycle(
        relationship_context="partner", events=cycle_events(), trigger_condition="延迟回应",
    )
    assert result["attachment_type_assigned"] is None
    assert "永久的依恋类型" in " ".join(result["limitations"])
    assert "焦虑型" in " ".join(result["limitations"])


def test_cycle_is_bound_to_relationship_trigger_pressure_and_timeframe():
    result = profile_attachment_cycle(
        relationship_context="partner", events=cycle_events(), trigger_condition="延迟回应",
        pressure_level="high", timeframe_days=90,
    )
    assert result["relationship_context"] == "partner"
    assert result["trigger_condition"] == "延迟回应"
    assert result["pressure_level"] == "high"
    assert result["timeframe_days"] == 90
    assert "在其他关系情境中没有观察到同样模式" in result["user_facing_statement"]


def test_cycle_reports_other_contexts_when_they_exist():
    events = cycle_events() + [{"protective_action": "WITHDRAW", "period": "p9",
                                "relationship_context": "workplace", "user_confirmed": True}]
    result = profile_attachment_cycle(
        relationship_context="partner", events=events, trigger_condition="延迟回应",
    )
    assert result["other_contexts_observed"] == ["workplace"]
    assert result["context_specific"] is False


def test_unknown_protective_action_family_is_rejected():
    with pytest.raises(ValueError):
        profile_attachment_cycle(
            relationship_context="partner",
            events=[{"protective_action": "EXPLODE"}, {"protective_action": "EXPLODE"}],
            trigger_condition="延迟回应",
        )


# ── EM-39 differentiation ────────────────────────────────────────────────────

def test_compliance_or_cutoff_only_is_sd1():
    result = assess_differentiation(events=[{"complied_completely": True}, {"cut_off_contact": True}])
    assert result["stage"] == "SD1"


def test_position_under_pressure_with_repair_reaches_sd5():
    result = assess_differentiation(events=[
        {"stated_position": True, "under_pressure": True, "returned_responsibility": True, "repaired_after": True},
    ])
    assert result["stage"] == "SD5"
    assert SD_RANK[result["stage"]] == 5


def test_protocol_has_five_steps_including_returning_responsibility():
    result = assess_differentiation(events=[])
    codes = [step["code"] for step in result["protocol"]]
    assert codes == [
        "STEADY_SELF", "STATE_POSITION", "ACKNOWLEDGE_RELATIONSHIP",
        "RETURN_RESPONSIBILITY", "STAY_CONNECTED_OR_SAFE_DISTANCE",
    ]
    assert any("不是断联" in note for note in result["not_required"])


def test_high_activation_defers_the_practice():
    result = assess_differentiation(events=[], activation_level=8)
    assert result["practice_blocked_while_activated"] is True
    assert "暂停协议" in result["practice_note"]


# ── EM-40 survival oath ──────────────────────────────────────────────────────

def oath(**updates):
    values = {
        "oath_text": "我必须照顾所有人",
        "memory_source": "direct_memory",
        "current_repetition": "成年后我仍然觉得必须解决所有家庭冲突",
        "user_consent": True,
        "activation_level": 3,
    }
    values.update(updates)
    return reframe_survival_oath(**values)


def test_oath_work_requires_consent_low_activation_and_no_crisis():
    assert "USER_CONSENT_MISSING" in oath(user_consent=False)["blocks"]
    assert "ACTIVATION_TOO_HIGH" in oath(activation_level=8)["blocks"]
    assert "CRISIS_ACTIVE" in oath(in_crisis=True)["blocks"]


def test_vague_impression_is_not_enough_material():
    result = oath(memory_source="vague_impression")
    assert "MATERIAL_NOT_FACTUAL" in result["blocks"]
    assert "不是抗拒" in result["note"]


def test_memory_induction_phrasing_is_blocked():
    with pytest.raises(UnsafeContentError):
        oath(current_repetition="你小时候一定曾经被父亲抛弃")


def test_reframe_keeps_responsibility_with_the_adult():
    result = oath(adult_commitment="我可以关心家人，但我不负责让所有人满意。")
    assert result["status"] == "REFRAMED_DRAFT"
    assert "仍然需要由我们自己负责" in result["responsibility_note"]
    assert result["not_a_diagnosis"].startswith("这不是诊断")


def test_inner_child_language_is_optional_and_declinable():
    result = oath(preferred_language="EARLY_SURVIVAL_RESPONSE")
    assert result["language_used"] == "EARLY_SURVIVAL_RESPONSE"
    assert result["user_can_decline"] is True
    assert "过去的自己" in result["decline_note"]


def test_spiritual_integration_is_optional_and_never_a_proof_of_maturity():
    with_spiritual = oath(spiritual_integration_enabled=True)
    assert with_spiritual["optional_spiritual_integration"]
    assert "不替代现实中的界限" in " ".join(with_spiritual["optional_spiritual_integration"])
    assert oath()["optional_spiritual_integration"] == []


# ── EM-41 masks ──────────────────────────────────────────────────────────────

def test_masks_report_protective_function_and_current_cost():
    result = profile_masks([{
        "mask_code": "SPIRITUAL_PERFORMER", "concrete_events": 3, "distinct_periods": 2,
        "contexts": 2, "linked_to_current_behavior": True,
    }])
    record = result["masks"][0]
    assert record["what_it_protected"]
    assert record["current_cost"]
    assert record["evidence_level"] == "FP4"
    assert any("不是虚伪" in note for note in result["framing"])


def test_masks_are_not_a_personality_verdict():
    result = profile_masks([{"mask_code": "PLEASER", "concrete_events": 1}])
    assert result["masks"][0]["may_write_to_twin"] is False
    assert any("不是你这个人的定义" in note for note in result["framing"])


def test_unknown_mask_codes_are_rejected():
    with pytest.raises(ValueError):
        profile_masks([{"mask_code": "SUPERHERO"}])


def test_every_documented_mask_is_available():
    assert len(MASKS) == 8
    assert "SPIRITUAL_PERFORMER" in MASKS and "MORAL_SUPERIORITY_DEFENSE" in MASKS


# ── EM-42 true self compass ──────────────────────────────────────────────────

def test_compass_has_six_parts_and_reports_what_is_missing():
    result = build_true_self_compass(
        parts={"IDENTITY": ["我是被神所爱的人，不只是有用的人"], "VALUES": ["诚实", "忠心"]},
        adult_commitment="我可以关心家人，但我不负责让所有人满意。",
    )
    assert len(result["parts"]) == 6
    assert "LIMITS" in result["missing_parts"]
    assert result["completeness"] < 1


def test_true_self_is_explicitly_not_self_indulgence():
    result = build_true_self_compass(parts={}, adult_commitment="我为自己的表达负责。")
    assert "我想做什么就做什么" in result["true_self_is_not"]
    assert any("只有权利没有责任不是真我" in note for note in result["consistency_check"])


def test_compass_can_link_the_masks_it_replaces():
    result = build_true_self_compass(
        parts={"LIMITS": ["我不能替别人做决定"]},
        adult_commitment="我为自己的表达负责。",
        mask_codes=["RESCUER"],
    )
    assert result["masks_this_replaces"][0]["label"] == "全能拯救者"


def test_unknown_compass_part_is_rejected():
    with pytest.raises(ValueError):
        build_true_self_compass(parts={"SUPERPOWERS": ["飞"]}, adult_commitment="x")


# ── EM-43 vulnerability experiment ───────────────────────────────────────────

def experiment(**updates):
    values = {
        "target_relationship_type": "partner",
        "safety_status": "SAFE",
        "target_issue": "对方临时取消约定且没有提前说明",
        "preferred_depth": "V2",
        "activation_level": 3,
        "prior_experiment_count": 1,
    }
    values.update(updates)
    return design_vulnerability_experiment(**values)


def test_unsafe_relationships_get_no_experiment():
    result = experiment(safety_status="UNSAFE")
    assert result["status"] == "NOT_GENERATED_UNSAFE"
    assert result["depth"] is None
    assert result["alternatives"]


def test_caution_limits_depth_and_structure():
    result = experiment(safety_status="CAUTION", preferred_depth="V4")
    assert result["depth"] == "V2"
    assert "RELATIONSHIP_SAFETY_CAUTION" in result["depth_caps_applied"]
    assert {item["code"] for item in result["expression_structure"]} == {"FACT", "REQUEST", "BOUNDARY"}


def test_first_experiment_starts_low_even_in_a_safe_relationship():
    result = experiment(preferred_depth="V4", prior_experiment_count=0)
    assert DEPTH_RANK[result["depth"]] <= DEPTH_RANK["V2"]
    assert "FIRST_EXPERIMENT_STARTS_LOW" in result["depth_caps_applied"]


def test_high_power_asymmetry_caps_disclosure():
    result = experiment(preferred_depth="V4", power_asymmetry="HIGH", prior_experiment_count=3)
    assert result["depth"] == "V2"
    assert "POWER_ASYMMETRY" in result["depth_caps_applied"]


def test_experiment_is_deferred_when_the_user_is_highly_activated():
    result = experiment(activation_level=8)
    assert result["status"] == "DEFERRED_HIGH_ACTIVATION"
    assert result["next_action"] == "SACRED_PAUSE_PROTOCOL"


def test_success_is_defined_by_the_users_own_behaviour():
    result = experiment()
    assert "对方是否同意" in result["not_success_criteria"]
    assert any("保留了自己的边界" in item for item in result["success_criteria"])
    assert [item["code"] for item in result["expression_structure"]][:3] == ["FACT", "FEELING", "MEANING"]


# ── module description and wiring ────────────────────────────────────────────

def test_module_description_states_its_refusals():
    described = describe_family_engine()
    assert len(described["skills"]) == len(WORKFLOW_NODES) == 8
    assert any("不远程诊断" in item for item in described["does_not"])
    assert any("不诱导或补全童年记忆" in item for item in described["does_not"])
    assert any("不把饶恕等同于重新信任" in item for item in described["does_not"])
    assert described["twin_write_minimum"] == "FP4"


def test_forgiveness_is_distinguished_from_reconciliation():
    described = describe_family_engine()
    codes = {item["code"] for item in described["forgiveness_distinctions"]}
    assert {"FORGIVENESS", "REBUILD_TRUST", "RESUME_CONTACT", "RECONCILIATION"} <= codes


def test_router_exposes_the_batch_five_surface():
    from routers.formation_twin_emotional_maturity import router

    paths = {route.path for route in router.routes}
    for suffix in (
        "family/overview", "family/genogram", "family/scripts", "family/attachment-cycle",
        "family/differentiation", "family/oath-reframe", "family/masks",
        "family/true-self", "family/vulnerability-experiment",
    ):
        assert f"/api/v1/formation-twin/emotional-maturity/{suffix}" in paths


def test_migration_file_exists_for_batch_five():
    migration = ROOT / "backend/migrations/0227_formation_twin_emd_family_self.sql"
    rollback = ROOT / "backend/migrations/rollback/0227_formation_twin_emd_family_self_down.sql"
    assert migration.exists() and rollback.exists()
    sql = migration.read_text(encoding="utf-8")
    assert "formation_twin_emd_genograms" in sql
    assert "formation_twin_emd_vulnerability_experiments" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql


def test_erasure_covers_every_batch_five_table():
    source = (ROOT / "backend/routers/formation_twin_emotional_maturity.py").read_text(encoding="utf-8")
    erase_block = source.split("def emotional_maturity_erase")[1]
    for table in (
        "formation_twin_emd_genograms", "formation_twin_emd_family_patterns",
        "formation_twin_emd_attachment_cycles", "formation_twin_emd_differentiation_assessments",
        "formation_twin_emd_survival_oaths", "formation_twin_emd_mask_profiles",
        "formation_twin_emd_true_self_compasses", "formation_twin_emd_vulnerability_experiments",
    ):
        assert table in erase_block
