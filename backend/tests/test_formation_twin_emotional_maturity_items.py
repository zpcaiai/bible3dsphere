from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from formation_twin.emotional_maturity import (
    DIMENSION_CODES,
    STAGE_RANK,
    UnsafeContentError,
    score_dimension,
)
from formation_twin.emotional_maturity_items import (
    BANK_VERSION,
    EVIDENCE_LEVELS,
    ITEM_TYPES,
    MAX_COUNTERFACTUALS_PER_ITEM,
    SOURCE_WEIGHTS,
    WORKFLOW_NODES,
    AssessmentItem,
    AssessmentResponse,
    SelectionState,
    build_pressure_scenario,
    calibrate_consistency,
    classify_difference,
    describe_item_engine,
    dimension_readiness,
    evaluate_sufficiency,
    extract_evidence,
    generate_counterfactual_probe,
    register_item_bank,
    render_item,
    score_rubric,
    seed_item_bank,
    select_next_item,
    to_batch1_evidence,
)


pytestmark = pytest.mark.no_db
NOW = datetime(2026, 7, 28, 12, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[2]
BANK = seed_item_bank()
BY_ID = {item.item_id: item for item in BANK}


def response(text: str, *, rid: str = "r1", real: bool = False, skipped: bool = False, ms: int | None = None):
    return AssessmentResponse(
        response_id=rid, assessment_id="ema_test", item_id="D9-BE-001",
        raw_response=text, occurred_in_real_life=real, skipped=skipped,
        response_time_ms=ms, submitted_at=NOW,
    )


def evidence_for(text: str, *, dimension="D9", source="recent_behavior", context="FAMILY", real=True, rid="r1"):
    return extract_evidence(
        response(text, rid=rid, real=real), dimension_code=dimension, source_type=source, context=context
    )


# ── EM-11 item bank registry ─────────────────────────────────────────────────

def test_seed_bank_covers_every_dimension_with_four_item_types():
    result = register_item_bank(BANK)
    assert result["status"] == "REGISTERED"
    assert result["registered_item_count"] == 40
    for code in DIMENSION_CODES:
        for item_type in ("SR", "BE", "SF", "RV"):
            assert result["coverage"][code][item_type] == 1


def test_bank_rejects_missing_dimension_coverage():
    partial = [item for item in BANK if item.dimension_code != "D7"]
    result = register_item_bank(partial)
    assert result["status"] == "REJECTED"
    assert any(item["code"] == "DIMENSION_TYPE_COVERAGE_MISSING" for item in result["errors"])


def test_bank_rejects_likert_only_instrument():
    likert = [item for item in BANK if item.response_mode == "likert"]
    result = register_item_bank(likert)
    assert any(item["code"] == "LIKERT_ONLY_BANK_NOT_ALLOWED" for item in result["errors"])


def test_registered_item_text_is_immutable():
    existing = {item.item_id: item for item in BANK}
    edited = BY_ID["D2-SR-001"].model_copy(update={"canonical_text": "情绪上来时，我一定能停下来。"})
    result = register_item_bank([edited], existing=existing)
    assert any(item["code"] == "IMMUTABLE_ITEM_MODIFIED" for item in result["errors"])


def test_difficulty_is_only_estimated_before_calibration():
    assert all(item.calibration_status == "estimated" for item in BANK)


def test_scenario_and_behavior_items_must_be_open_text():
    with pytest.raises(ValueError):
        AssessmentItem(
            item_id="D2-BE-999", dimension_code="D2", item_type="BE",
            canonical_text="最近一次你差点说出伤人的话时，后来实际做了什么？",
            response_mode="likert", rubric_id="rubric-D2-v1",
        )


# ── EM-12 adaptive selection ─────────────────────────────────────────────────

def test_selection_prefers_behavior_items_when_only_self_report_exists():
    state = SelectionState(
        priority_dimensions=["D7"],
        evidence_by_dimension={"D7": ["self_report"]},
        contexts_by_dimension={"D7": ["family"]},
        behavior_evidence_allowed=True,
    )
    result = select_next_item(state, BANK)
    assert result["decision"] == "ask_item"
    assert result["dimension_code"] == "D7"
    assert result["item_type"] in {"BE", "SF"}
    assert "当前只有自我描述证据" in result["selection_reasons"]


def test_selection_never_offers_real_behavior_without_behavior_consent():
    state = SelectionState(priority_dimensions=["D7"], behavior_evidence_allowed=False)
    for _ in range(20):
        result = select_next_item(state, BANK)
        if result["decision"] != "ask_item":
            break
        assert result["item_type"] != "BE"
        state.asked_item_ids.append(result["selected_item_id"])


def test_selection_is_deterministic_and_never_repeats_an_item():
    state = SelectionState(priority_dimensions=["D9"])
    first = select_next_item(state, BANK)
    assert select_next_item(state, BANK)["selected_item_id"] == first["selected_item_id"]
    state.asked_item_ids.append(first["selected_item_id"])
    assert select_next_item(state, BANK)["selected_item_id"] != first["selected_item_id"]


def test_blocked_topics_are_never_reselected():
    state = SelectionState(priority_dimensions=["D6"], blocked_topics=["D6"])
    result = select_next_item(state, BANK)
    assert result.get("dimension_code") != "D6"


def test_selection_stops_on_safety_fatigue_and_budget():
    assert select_next_item(SelectionState(safety_level="ELEVATED"), BANK)["decision"] == "stop"
    assert "FATIGUE_TOO_HIGH" in select_next_item(SelectionState(fatigue=0.9), BANK)["stop_reasons"]
    assert "NO_NEW_EVIDENCE_FOR_THREE_ITEMS" in select_next_item(
        SelectionState(consecutive_no_new_evidence=3), BANK
    )["stop_reasons"]


def test_unsafe_relationship_hides_sensitive_behavior_items():
    state = SelectionState(priority_dimensions=["D9"], relationship_safety="CAUTION")
    for _ in range(6):
        result = select_next_item(state, BANK)
        if result["decision"] != "ask_item":
            break
        assert not (result["dimension_code"] in {"D6", "D9"} and result["item_type"] in {"BE", "CF"})
        state.asked_item_ids.append(result["selected_item_id"])


def test_no_five_high_burden_items_in_a_row_from_one_dimension():
    state = SelectionState(priority_dimensions=["D3"], recent_dimensions=["D3", "D3", "D3", "D3"])
    result = select_next_item(state, BANK)
    assert result["dimension_code"] != "D3"


# ── EM-13 contextual rendering ───────────────────────────────────────────────

def test_renderer_changes_wording_but_not_the_construct():
    rendered = render_item(BY_ID["D1-SF-001"], life_context="workplace")
    assert "同事" in rendered["rendered_text"]
    assert rendered["canonical_text"] == BY_ID["D1-SF-001"].canonical_text
    assert rendered["skippable"] is True


def test_renderer_supports_a_neutral_non_religious_framework():
    rendered = render_item(BY_ID["D7-SF-001"], spiritual_framework="neutral")
    assert "爱主" not in rendered["rendered_text"]
    assert rendered["substitutions"]


def test_renderer_rejects_leading_or_moralising_wording():
    item = BY_ID["D2-SR-001"].model_copy(update={"canonical_text": "情绪上来时，你一定能停下来吧？"})
    with pytest.raises(UnsafeContentError):
        render_item(item)


# ── EM-14 pressure scenario ──────────────────────────────────────────────────

def test_scenario_has_three_stages_and_maps_to_an_evidence_context():
    scenario = build_pressure_scenario(target_dimension="D9", axes={"life_context": "partner", "stress_level": "high"})
    assert [stage["stage"] for stage in scenario["stages"]][:2] == ["A_INITIAL_TRIGGER", "B_PRESSURE_ESCALATION"]
    assert scenario["evidence_context"] == "CLOSE_RELATIONSHIP"
    assert any("L2" in note for note in scenario["limitations"])


def test_escalation_may_change_only_one_variable():
    base = {"life_context": "workplace", "stress_level": "low", "power_relation": "equal"}
    with pytest.raises(ValueError):
        build_pressure_scenario(
            target_dimension="D7",
            axes={"life_context": "workplace", "stress_level": "high", "power_relation": "strong_asymmetry"},
            previous_axes={axis: value for axis, value in base.items()},
        )


def test_scenario_is_blocked_while_crisis_route_is_open():
    scenario = build_pressure_scenario(target_dimension="D9", axes={}, safety_level="IMMINENT")
    assert scenario["status"] == "BLOCKED_BY_SAFETY"
    assert scenario["stages"] == []


def test_unsafe_relationship_removes_the_repair_branch():
    scenario = build_pressure_scenario(
        target_dimension="D9", axes={"life_context": "partner"}, relationship_safety="CAUTION"
    )
    assert all(stage["stage"] != "C_REPAIR_WINDOW" for stage in scenario["stages"])
    assert scenario["restrictions"]


def test_spiritualised_power_pressure_is_restricted():
    scenario = build_pressure_scenario(
        target_dimension="D7",
        axes={"life_context": "church_service", "power_relation": "strong_asymmetry", "spiritualized_pressure": "manipulative"},
    )
    assert any("自我保护" in note for note in scenario["restrictions"])


# ── EM-15 evidence extraction ────────────────────────────────────────────────

def test_every_extracted_feature_carries_a_supporting_span():
    evidence = evidence_for("昨天吵完我先离开了十分钟，冷静下来我告诉他我很难受。")
    assert evidence.extracted_features
    assert all(payload["supporting_span"] for payload in evidence.extracted_features.values())


def test_absent_features_are_unknown_not_low():
    evidence = evidence_for("我不知道。")
    assert evidence.extracted_features == {}
    assert evidence.behavior_specificity == 0.0
    assert evidence.requires_user_confirmation is True
    assert "repair_orientation" in evidence.unsupported_fields


def test_prayer_alone_does_not_prove_regulation():
    evidence = evidence_for("祷告一下就好了，基督徒不该有这种情绪。", dimension="D2", source="scenario_intention")
    assert "spiritual_bypassing" in evidence.extracted_features
    assert "impulse_delay" not in evidence.extracted_features


def test_short_but_concrete_answers_produce_full_evidence():
    evidence = evidence_for("昨天我先走开，等我冷静再回来说。", dimension="D2")
    assert "impulse_delay" in evidence.extracted_features
    assert evidence.behavior_specificity > 0


def test_claimed_real_event_without_the_real_life_flag_is_downgraded():
    evidence = evidence_for("上周我先离开十分钟再回来。", source="recent_behavior", real=False)
    assert evidence.evidence_reliability <= SOURCE_WEIGHTS["scenario_intention"]
    assert evidence.requires_user_confirmation is True


def test_evidence_level_distinguishes_intention_from_real_repair():
    intention = evidence_for("我会先深呼吸再回应。", dimension="D2", source="scenario_intention", real=False)
    repair = evidence_for("上周我去找他道歉，并说明我做不到每周加班。", dimension="D9", source="post_repair")
    assert intention.evidence_level == "L2"
    assert repair.evidence_level == "L5"
    assert set(EVIDENCE_LEVELS) == {"L1", "L2", "L3", "L4", "L5"}


# ── EM-16 rubric scoring ─────────────────────────────────────────────────────

def test_rich_emotion_words_do_not_lift_a_conflict_stage():
    evidence = evidence_for("我觉得又失望又羞耻又愤怒，所以我直接吼了回去，还翻旧账，之后一周没理她。")
    result = score_rubric(evidence)
    assert result["provisional_stage"] == "E1"
    assert "attack_tendency" in result["harmful_markers"]


def test_scenario_intention_cannot_prove_stable_capacity():
    evidence = evidence_for(
        "我会先停一下，告诉他我很难受，问他具体的意思，然后我会去道歉，也承认我有责任。",
        dimension="D9", source="scenario_intention", real=False,
    )
    result = score_rubric(evidence)
    assert STAGE_RANK[result["provisional_stage"]] <= STAGE_RANK["E3"]
    assert result["is_stable_capacity"] is False


def test_general_self_report_is_capped_at_e2():
    evidence = evidence_for("昨天我先停一下，告诉他我很难受，也问他的意思。", source="self_report", real=False)
    result = score_rubric(evidence)
    assert result["provisional_stage"] == "E2"
    assert "SELF_REPORT_ONLY" in result["caps_applied"]


def test_real_repair_behavior_can_reach_e4_with_high_source_confidence():
    evidence = evidence_for(
        "昨天吵完以后我先离开了十分钟，冷静下来我告诉他我很难受，问他具体觉得哪里不成熟，第二天我去找他道歉。",
        source="post_repair",
    )
    result = score_rubric(evidence)
    assert result["provisional_stage"] in {"E4", "E5"}
    assert result["source_confidence"] == "high"


def test_extreme_boundary_is_not_counted_as_proportional():
    evidence = evidence_for(
        "上周我告诉负责人我做不到每周都来，如果他还是敷衍，我以后就不再参加这个团队。",
        dimension="D7", source="recent_behavior",
    )
    result = score_rubric(evidence)
    assert evidence.extracted_features["boundary_proportionality"]["value"] == "uncertain"
    assert STAGE_RANK[result["provisional_stage"]] <= STAGE_RANK["E3"]


def test_same_features_always_produce_the_same_stage():
    text = "昨天我先离开十分钟，告诉她我很难受，也问了她的想法。"
    first = score_rubric(evidence_for(text, rid="a"))
    second = score_rubric(evidence_for(text, rid="b"))
    assert first["provisional_stage"] == second["provisional_stage"]
    assert first["stage_support"] == second["stage_support"]


def test_language_ability_is_declared_out_of_scope():
    result = score_rubric(evidence_for("昨天我先离开十分钟，告诉她我很难受，也问了她的想法。"))
    assert "引用经文" in result["language_not_scored"]
    assert result["stage_support"]["missing_anchors"] is not None


def test_rubric_result_bridges_into_the_batch_one_scorer():
    items = []
    for index, text in enumerate((
        "昨天吵完我先离开十分钟，告诉他我很难受，问他具体的意思，第二天我去找他道歉。",
        "上周我们又吵了，我先停下来，说了我的感受，问他怎么想，然后我主动道歉。",
    )):
        evidence = evidence_for(text, source="post_repair", rid=f"r{index}")
        result = score_rubric(evidence)
        items.append(to_batch1_evidence(result, evidence, occurred_at=NOW - timedelta(days=index + 1)))
    assert {item.evidence_kind for item in items} == {"REAL_LIFE_EVENT"}

    # Batch 1 still requires a second evidence kind before it will leave E0.
    intention = evidence_for("我会先停一下，说出我的感受，再问他的想法。", source="scenario_intention", real=False, rid="r9")
    items.append(to_batch1_evidence(score_rubric(intention), intention, occurred_at=NOW - timedelta(days=4)))

    snapshot = score_dimension("D9", items, now=NOW)
    assert snapshot.stage != "E0"
    assert snapshot.evidence_count == 3
    assert "REAL_LIFE_EVENT" in snapshot.evidence_kinds


# ── EM-17 counterfactual probes ──────────────────────────────────────────────

def test_probe_changes_exactly_one_condition():
    probe = generate_counterfactual_probe(
        base_item_id="D7-SF-001", target_dimension="D7",
        base_response_summary="用户表示会温和拒绝额外服事",
        uncertainty_type="power_asymmetry_sensitivity",
    )
    assert probe["decision"] == "ask_probe"
    assert probe["changed_variable"] == "power_relation"
    assert probe["single_variable_change"] is True


def test_probe_budget_is_capped_per_base_item():
    probe = generate_counterfactual_probe(
        base_item_id="D7-SF-001", target_dimension="D7", base_response_summary="",
        uncertainty_type="unspecified", probes_for_base_item=MAX_COUNTERFACTUALS_PER_ITEM,
    )
    assert probe["decision"] == "no_probe"


def test_probe_never_treats_a_changed_answer_as_dishonesty():
    probe = generate_counterfactual_probe(
        base_item_id="D7-SF-001", target_dimension="D7", base_response_summary="",
        uncertainty_type="unspecified",
    )
    assert any("不说明用户之前不诚实" in rule for rule in probe["interpretation_rules"])


# ── EM-18 consistency calibration ────────────────────────────────────────────

def test_context_variance_is_described_not_punished():
    result = calibrate_consistency("D7", [
        {"context": "WORK", "provisional_stage": "E4", "source_type": "recent_behavior"},
        {"context": "FAMILY", "provisional_stage": "E2", "source_type": "recent_behavior"},
    ])
    assert result["consistency_status"] == "context_dependent"
    assert result["confidence_adjustments"]["general_stage_confidence"] < 0
    assert result["score_adjustments"] == {}


def test_self_report_behavior_gap_lowers_confidence_only():
    result = calibrate_consistency("D9", [
        {"context": "FAMILY", "provisional_stage": "E4", "source_type": "self_report"},
        {"context": "FAMILY", "provisional_stage": "E1", "source_type": "recent_behavior"},
    ])
    assert any(item["type"] == "self_report_behavior_gap" for item in result["patterns"])
    assert result["score_adjustments"] == {}


def test_temporal_change_may_mean_growth():
    result = calibrate_consistency("D2", [
        {"context": "FAMILY", "provisional_stage": "E1", "source_type": "recent_behavior", "time_period": "old"},
        {"context": "FAMILY", "provisional_stage": "E3", "source_type": "recent_behavior", "time_period": "recent"},
    ])
    assert any("成长" in item["interpretation"] for item in result["patterns"])


def test_calibration_never_uses_dishonesty_language():
    result = calibrate_consistency("D7", [
        {"context": "WORK", "provisional_stage": "E4", "source_type": "self_report"},
        {"context": "FAMILY", "provisional_stage": "E1", "source_type": "recent_behavior"},
    ])
    text = " ".join(item["interpretation"] for item in result["patterns"])
    for word in ("撒谎", "虚伪", "不诚实", "诚实度"):
        assert word not in text


def test_difference_classifier_matches_the_specification():
    assert classify_difference({"context": "WORK"}, {"context": "FAMILY"}) == "context_variance"
    assert classify_difference(
        {"context": "WORK", "time_period": "old"}, {"context": "WORK", "time_period": "new"}
    ) == "temporal_change"
    assert classify_difference(
        {"context": "WORK", "source_type": "self_report"},
        {"context": "WORK", "source_type": "recent_behavior"},
    ) == "self_report_behavior_gap"


# ── EM-19 sufficiency control ────────────────────────────────────────────────

def test_only_abstract_self_report_is_insufficient():
    readiness = dimension_readiness({"self_report": 4, "contexts": ["family"]})
    assert readiness["status"] == "insufficient"
    assert "缺少近期真实行为证据" in readiness["missing_evidence"]


def test_provisional_requires_three_evidence_two_sources_and_one_concrete():
    readiness = dimension_readiness({
        "self_report": 1, "scenario_intention": 1, "recent_behavior": 1, "contexts": ["family"],
    })
    assert readiness["status"] == "provisional"


def test_higher_confidence_requires_escalation_and_repair_evidence():
    readiness = dimension_readiness({
        "self_report": 1, "scenario_intention": 1, "recent_behavior": 1,
        "escalated_behavior": 1, "post_repair": 1,
        "contexts": ["family", "workplace"], "unresolved_contradictions": 0,
        "user_confirmed_evidence": 3,
    })
    assert readiness["status"] == "higher_confidence"


def test_fatigue_with_minimum_evidence_pauses_instead_of_forcing_completion():
    coverage = {"D7": {"self_report": 1, "scenario_intention": 1, "recent_behavior": 1, "contexts": ["family"]}}
    result = evaluate_sufficiency(coverage_by_dimension=coverage, priority_dimensions=["D7"], fatigue=0.9)
    assert result["decision"] == "pause_and_save"


def test_fatigue_without_evidence_stops_and_marks_insufficient():
    coverage = {"D7": {"self_report": 1, "contexts": ["family"]}}
    result = evaluate_sufficiency(coverage_by_dimension=coverage, priority_dimensions=["D7"], fatigue=0.9)
    assert result["decision"] == "stop_assessment"
    assert result["assessment_status"] == "insufficient_evidence"


def test_safety_change_stops_the_assessment_immediately():
    result = evaluate_sufficiency(coverage_by_dimension={}, safety_changed=True)
    assert result["decision"] == "stop_for_safety"


def test_completion_reports_what_is_still_unknown():
    coverage = {
        "D7": {"self_report": 1, "scenario_intention": 1, "recent_behavior": 2,
               "contexts": ["family", "workplace"], "unresolved_contradictions": 0},
        "D9": {"self_report": 1, "scenario_intention": 1, "contexts": ["family"]},
    }
    result = evaluate_sufficiency(coverage_by_dimension=coverage, priority_dimensions=["D7", "D9"], item_budget=6, items_asked=6)
    assert result["decision"] == "complete_assessment"
    assert result["remaining_unknowns"]
    assert "MATURITY_DIMENSION_SCORER" in result["next_actions"]


def test_missing_real_behavior_routes_to_a_behavior_item():
    coverage = {"D9": {"self_report": 2, "scenario_intention": 1, "contexts": ["family"]}}
    result = evaluate_sufficiency(coverage_by_dimension=coverage, priority_dimensions=["D9"], item_budget=24, items_asked=3)
    assert result["decision"] == "continue_assessment"
    assert any("BE" in hint for hint in result["next_item_hints"])


# ── module description and wiring ────────────────────────────────────────────

def test_module_description_declares_the_llm_boundary():
    described = describe_item_engine()
    assert len(described["skills"]) == len(WORKFLOW_NODES) == 9
    assert set(described["item_types"]) == set(ITEM_TYPES)
    assert "最终评分" in described["llm_role"]
    assert described["bank_version"] == BANK_VERSION


def test_router_exposes_the_batch_two_surface():
    from routers.formation_twin_emotional_maturity import router

    paths = {route.path for route in router.routes}
    for suffix in ("item-bank", "items/next", "scenarios", "responses", "probes", "calibrate", "sufficiency"):
        assert f"/api/v1/formation-twin/emotional-maturity/{suffix}" in paths


def test_erasure_covers_every_batch_two_table():
    source = (ROOT / "backend/routers/formation_twin_emotional_maturity.py").read_text(encoding="utf-8")
    erase_block = source.split("def emotional_maturity_erase")[1]
    for table in (
        "formation_twin_emd_responses", "formation_twin_emd_behavior_evidence",
        "formation_twin_emd_rubric_results", "formation_twin_emd_scenarios",
        "formation_twin_emd_counterfactual_probes", "formation_twin_emd_calibrations",
        "formation_twin_emd_sufficiency_runs",
    ):
        assert table in erase_block


def test_migration_file_exists_for_batch_two():
    migration = ROOT / "backend/migrations/0224_formation_twin_emd_item_bank.sql"
    rollback = ROOT / "backend/migrations/rollback/0224_formation_twin_emd_item_bank_down.sql"
    assert migration.exists() and rollback.exists()
    sql = migration.read_text(encoding="utf-8")
    assert "formation_twin_emd_items" in sql
    assert "formation_twin_emd_rubric_results" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql
