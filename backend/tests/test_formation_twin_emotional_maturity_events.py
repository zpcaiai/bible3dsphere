from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from formation_twin.emotional_maturity import STAGE_RANK, score_dimension
from formation_twin.emotional_maturity_events import (
    CHECKPOINT_DAYS,
    EVENT_STAGE_CODES,
    REAL_EVIDENCE_LEVELS,
    REPAIR_STAGE_RANK,
    TRANSFER_STAGE_RANK,
    WORKFLOW_NODES,
    EmotionalEventInput,
    RecoveryInput,
    analyze_recurrence,
    bucket_for,
    build_timeline,
    capture_event,
    compute_recovery_metrics,
    describe_event_engine,
    detect_transfer,
    evaluate_growth,
    event_to_batch1_evidence,
    handle_checkpoint_without_events,
    schedule_checkpoints,
    verify_repair,
)


pytestmark = pytest.mark.no_db
NOW = datetime(2026, 7, 28, 12, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[2]
FULL_SCOPES = ["EMD_SELF_ASSESSMENT", "EMD_BEHAVIOR_EVIDENCE", "EMD_LONGITUDINAL_TWIN"]
GOOD_QUALITY = {element: True for element in (
    "specificity", "ownership", "impact_acknowledgment", "no_counterattack",
    "concrete_repair", "boundary_integrity", "follow_through", "respect_for_other_choice",
)}


def event(**updates) -> EmotionalEventInput:
    values = {
        "occurred_at": NOW - timedelta(hours=3),
        "captured_at": NOW - timedelta(hours=2),
        "context": "family",
        "objective_facts": ["他说我从不听他说话"],
        "user_interpretations": ["我当时觉得他在否定我"],
        "first_response": "我提高了音量",
        "regulation_attempts": ["先离开客厅十分钟"],
        "later_response": "回来后我说了我的感受",
        "relationship_outcome": "partially_resolved",
        "related_dimensions": ["D9"],
    }
    values.update(updates)
    return EmotionalEventInput(**values)


# ── EM-20 event capture ──────────────────────────────────────────────────────

def test_capture_requires_behavior_evidence_consent():
    result = capture_event(event(), consented_scopes=["EMD_SELF_ASSESSMENT"], now=NOW)
    assert result["status"] == "BLOCKED_NO_CONSENT"


def test_recent_capture_is_rl2_and_separates_fact_from_interpretation():
    result = capture_event(event(), consented_scopes=FULL_SCOPES, now=NOW)
    assert result["status"] == "CAPTURED"
    assert result["evidence_level"] == "RL2"
    assert result["fact_interpretation_separated"] is True
    assert set(REAL_EVIDENCE_LEVELS) == {"RL0", "RL1", "RL2", "RL3", "RL4", "RL5"}


def test_third_party_identities_are_minimised():
    result = capture_event(event(third_party_labels=["配偶", "牧师"]), consented_scopes=FULL_SCOPES, now=NOW)
    assert result["third_party_labels"] == ["对方", "对方"]


def test_unsafe_relationship_routes_to_safety_and_blocks_repair_workflow():
    result = capture_event(
        event(safety_flags=["DOMESTIC_VIOLENCE"]), consented_scopes=FULL_SCOPES, now=NOW
    )
    assert result["status"] == "ROUTED_TO_SAFETY"
    assert result["repair_workflow_allowed"] is False
    assert "安全退出" in result["note"]


def test_urge_without_action_is_recorded_as_control_not_harm():
    result = capture_event(
        event(urge_only_actions=["想摔门"], harmful_actions=[]), consented_scopes=FULL_SCOPES, now=NOW
    )
    assert result["urge_recorded_without_action"] is True


def test_abstract_report_without_any_action_is_rl0():
    result = capture_event(
        event(first_response=None, later_response=None, regulation_attempts=[]),
        consented_scopes=FULL_SCOPES, now=NOW,
    )
    assert result["evidence_level"] == "RL0"


# ── EM-21 timeline ───────────────────────────────────────────────────────────

def test_timeline_has_all_stages_and_keeps_gaps_unknown():
    timeline = build_timeline(event(), stage_times={"T0": NOW - timedelta(hours=3)})
    assert [node["stage"] for node in timeline["nodes"]] == list(EVENT_STAGE_CODES)
    assert "T7" in timeline["unknown_nodes"]
    assert any("不会替你补全记忆" in note for note in timeline["notes"])


def test_turning_point_is_an_observation_not_a_causal_claim():
    timeline = build_timeline(event())
    assert timeline["turning_point"]["causal_claim"] is False


def test_pre_event_vulnerability_is_kept_separate():
    timeline = build_timeline(event(), pre_event_factors=["前一晚只睡四小时"])
    assert timeline["pre_event_vulnerability"] == ["前一晚只睡四小时"]


# ── EM-22 recovery metrics ───────────────────────────────────────────────────

def recovery(**updates) -> RecoveryInput:
    values = {
        "trigger_at": NOW - timedelta(hours=3),
        "first_regulation_at": NOW - timedelta(hours=2, minutes=58),
        "harmful_action_stopped_at": NOW - timedelta(hours=2, minutes=45),
        "functional_recovery_at": NOW - timedelta(hours=2),
        "emotional_recovery_at": NOW - timedelta(minutes=30),
        "harmful_action_occurred": True,
        "relationship_resolution_status": "partially_resolved",
    }
    values.update(updates)
    return RecoveryInput(**values)


def test_four_recoveries_are_reported_separately():
    result = compute_recovery_metrics(recovery())
    for name in ("behavioral_control_recovery", "functional_recovery", "emotional_recovery"):
        assert name in result["metrics_seconds"]
    assert result["buckets"]["behavioral_control_recovery"] != result["buckets"]["emotional_recovery"]


def test_long_emotion_with_controlled_behavior_is_not_penalised():
    result = compute_recovery_metrics(recovery(
        emotional_recovery_at=NOW + timedelta(days=3), harmful_action_occurred=False,
    ))
    assert result["metrics_seconds"]["behavioral_control_recovery"] == 0.0
    assert result["buckets"]["emotional_recovery"] in {"DAYS", "WEEKS"}
    assert any("不等于不成熟" in rule for rule in result["interpretation_rules"])


def test_cold_shoulder_shows_up_as_unresolved_relationship():
    result = compute_recovery_metrics(recovery(
        functional_recovery_at=NOW - timedelta(hours=2, minutes=50),
        relationship_resolution_status="unresolved",
    ))
    assert result["relationship_resolution_status"] == "unresolved"


def test_comparison_needs_the_users_own_history():
    without = compute_recovery_metrics(recovery())
    assert without["within_user_comparison"]["status"] == "INSUFFICIENT_HISTORY"
    with_history = compute_recovery_metrics(recovery(), previous_events=[
        {"behavioral_control_recovery": 7200}, {"behavioral_control_recovery": 9000},
    ])
    assert with_history["within_user_comparison"]["changes"]["behavioral_control_recovery"] == "FASTER"


def test_recovery_times_may_not_precede_the_trigger():
    with pytest.raises(ValueError):
        recovery(first_regulation_at=NOW - timedelta(hours=4))


def test_bucketing_is_deterministic():
    assert bucket_for(60) == "IMMEDIATE"
    assert bucket_for(3600 * 5) == "HOURS"
    assert bucket_for(None) == "UNKNOWN"


# ── EM-23 repair verification ────────────────────────────────────────────────

def test_full_repair_with_follow_through_reaches_r5():
    result = verify_repair(
        repair_actions=["apologised"], quality_flags=GOOD_QUALITY,
        completed=True, follow_through_events=2,
    )
    assert result["repair_stage"] == "R5"


def test_apology_with_counterattack_stops_at_r2():
    flags = dict(GOOD_QUALITY, no_counterattack=False)
    result = verify_repair(repair_actions=["apologised"], quality_flags=flags, completed=True)
    assert result["repair_stage"] == "R2"
    assert "no_counterattack" in result["missing_quality_elements"]


def test_other_party_refusal_never_lowers_the_repair_stage():
    accepted = verify_repair(repair_actions=["apologised"], quality_flags=GOOD_QUALITY, completed=True,
                             follow_through_events=1, other_party_response="accepted")
    refused = verify_repair(repair_actions=["apologised"], quality_flags=GOOD_QUALITY, completed=True,
                            follow_through_events=1, other_party_response="refused")
    assert accepted["repair_stage"] == refused["repair_stage"]
    assert refused["other_party_response_affects_stage"] is False


def test_unsafe_relationship_never_enters_the_repair_workflow():
    result = verify_repair(
        repair_actions=["apologised"], quality_flags=GOOD_QUALITY, completed=True,
        safety_flags=["COERCIVE_CONTROL"],
    )
    assert result["repair_stage"] == "R0"
    assert result["workflow"] == "SAFETY_FIRST"
    assert any("安全退出" in note for note in result["notes"])


def test_boundary_exit_is_treated_as_a_valid_outcome():
    result = compute_recovery_metrics(recovery(relationship_resolution_status="boundary_exit"))
    assert result["relationship_resolution_status"] == "boundary_exit"


# ── EM-24 transfer detection ─────────────────────────────────────────────────

def test_understanding_without_events_is_t0_and_not_a_failure():
    result = detect_transfer(skill_id="pause", events=[{"event_id": "e1", "skill_used": False}], trained_context="family")
    assert result["transfer_stage"] == "T0"
    assert "不是失败" in result["note"]


def test_full_script_success_still_counts_but_keeps_high_prompt_dependence():
    result = detect_transfer(
        skill_id="pause",
        events=[{"event_id": "e1", "skill_used": True, "prompt_dependence": "P4", "context": "family"}],
        trained_context="family",
    )
    assert TRANSFER_STAGE_RANK[result["transfer_stage"]] >= TRANSFER_STAGE_RANK["T1"]
    assert result["prompt_dependence"] == "P4"


def test_self_initiated_use_in_a_new_context_reaches_context_transfer():
    result = detect_transfer(
        skill_id="pause",
        events=[{"event_id": "e1", "skill_used": True, "prompt_dependence": "P1", "context": "workplace"}],
        trained_context="family",
    )
    assert "context_transfer" in result["transfer_types"]
    assert TRANSFER_STAGE_RANK[result["transfer_stage"]] >= TRANSFER_STAGE_RANK["T4"]


def test_pressure_and_maintenance_transfer_are_detected():
    result = detect_transfer(
        skill_id="pause",
        events=[
            {"event_id": "e1", "skill_used": True, "prompt_dependence": "P1", "context": "family", "under_pressure": True},
            {"event_id": "e2", "skill_used": True, "prompt_dependence": "P0", "context": "family"},
        ],
        trained_context="family", days_since_training=95,
    )
    assert "pressure_transfer" in result["transfer_types"]
    assert result["transfer_stage"] == "T6"


# ── EM-25 recurrence ─────────────────────────────────────────────────────────

def sample_events(count: int = 3) -> list[dict]:
    return [
        {
            "occurred_at": NOW - timedelta(days=days),
            "context": context,
            "intensity": intensity,
            "behavioral_control_recovery": recovery_seconds,
            "repair_stage": repair,
            "regulation_attempted": True,
        }
        for days, context, intensity, recovery_seconds, repair in [
            (40, "family", 9, 10800, "R1"),
            (25, "family", 7, 5400, "R3"),
            (10, "workplace", 6, 1800, "R4"),
        ][:count]
    ]


def test_pattern_needs_at_least_three_events():
    result = analyze_recurrence(sample_events(2), now=NOW)
    assert result["status"] == "INSUFFICIENT_EVENTS"
    assert "不代表用户有问题" in result["note"]


def test_pattern_is_described_as_events_not_personality():
    result = analyze_recurrence(sample_events(), pattern_name="conflict_avoidance_cycle", now=NOW)
    assert result["status"] == "ANALYSED"
    assert result["pattern_description"]
    assert any("不是对人格的判断" in rule for rule in result["language_rules"])


def test_recurrence_reports_generalisation_and_trends():
    result = analyze_recurrence(sample_events(), now=NOW)
    assert result["context_generalization"] is True
    assert result["behavioral_recovery_trend"] == "DECREASING"
    assert result["repair_trend"] == "修复行为在增加"


def test_unknown_cycle_names_are_not_invented():
    result = analyze_recurrence(sample_events(), pattern_name="totally_made_up", now=NOW)
    assert result["pattern_name"] is None


# ── EM-26 checkpoints ────────────────────────────────────────────────────────

def test_checkpoints_require_longitudinal_consent():
    result = schedule_checkpoints(plan_started_at=NOW, consented_scopes=["EMD_SELF_ASSESSMENT"])
    assert result["status"] == "NOT_SCHEDULED"


def test_checkpoints_have_windows_and_stay_skippable():
    result = schedule_checkpoints(plan_started_at=NOW, consented_scopes=FULL_SCOPES)
    assert [item["day"] for item in result["checkpoints"]] == list(CHECKPOINT_DAYS)
    assert all(item["skippable"] for item in result["checkpoints"])
    assert result["checkpoints"][0]["closes_at"] > result["checkpoints"][0]["due_at"]


def test_no_event_checkpoint_never_asks_the_user_to_create_a_conflict():
    result = handle_checkpoint_without_events(30)
    assert result["conclusion"] == "INSUFFICIENT_EVIDENCE_FOR_CHANGE"
    assert any("不得要求或暗示用户制造一次冲突" in rule for rule in result["forbidden"])


# ── EM-27 growth evaluation ──────────────────────────────────────────────────

BASELINE = {
    "regulation_start_latency": 600,
    "behavioral_control_recovery": 7200,
    "emotional_recovery": 86400,
    "repair_initiation_latency": 172800,
}
IMPROVED = {
    "regulation_start_latency": 120,
    "behavioral_control_recovery": 900,
    "emotional_recovery": 80000,
    "repair_initiation_latency": 3600,
}


def test_day_fourteen_only_reports_first_application():
    transfer = detect_transfer(
        skill_id="pause",
        events=[{"event_id": "e1", "skill_used": True, "prompt_dependence": "P3", "context": "family"}],
        trained_context="family",
    )
    result = evaluate_growth(
        day=14, baseline_metrics=BASELINE, checkpoint_metrics=IMPROVED,
        transfer=transfer, comparable_event_count=1,
    )
    assert result["result"] == "EARLY_APPLICATION"


def test_no_comparable_event_means_insufficient_evidence_not_regression():
    result = evaluate_growth(
        day=30, baseline_metrics=BASELINE, checkpoint_metrics=IMPROVED, comparable_event_count=0,
    )
    assert result["result"] == "INSUFFICIENT_EVIDENCE"


def test_day_ninety_generalisation_requires_two_contexts_and_pressure_transfer():
    transfer = detect_transfer(
        skill_id="pause",
        events=[
            {"event_id": "e1", "skill_used": True, "prompt_dependence": "P1", "context": "workplace", "under_pressure": True},
        ],
        trained_context="family", days_since_training=95,
    )
    result = evaluate_growth(
        day=90, baseline_metrics=BASELINE, checkpoint_metrics=IMPROVED, transfer=transfer,
        repair_stages=["R4"], comparable_event_count=4, contexts_observed=["family", "workplace"],
    )
    assert result["result"] == "MAINTAINED_AND_GENERALISED"


def test_evaluation_always_lists_alternative_explanations():
    result = evaluate_growth(
        day=30, baseline_metrics=BASELINE, checkpoint_metrics=IMPROVED, comparable_event_count=3,
    )
    assert any("不能证明是训练造成的" in note for note in result["attribution_limits"])
    assert any("触发机会" in note for note in result["attribution_limits"])
    assert any("一次成功" in rule for rule in result["not_allowed"])


def test_consistently_worse_metrics_are_reported_as_regression():
    worse = {name: value * 3 for name, value in BASELINE.items()}
    result = evaluate_growth(
        day=30, baseline_metrics=BASELINE, checkpoint_metrics=worse, comparable_event_count=3,
    )
    assert result["result"] == "REGRESSION_OBSERVED"


# ── bridge into Batch 1 ──────────────────────────────────────────────────────

def test_captured_events_bridge_into_the_batch_one_scorer():
    items = []
    for index in range(2):
        capture = capture_event(
            event(occurred_at=NOW - timedelta(days=index + 1, hours=1),
                  captured_at=NOW - timedelta(days=index + 1)),
            consented_scopes=FULL_SCOPES, now=NOW - timedelta(days=index + 1),
        )
        items.append(event_to_batch1_evidence(
            capture, dimension_code="D9", stage_signal="E3",
            occurred_at=NOW - timedelta(days=index + 1),
            behavior_summary="先离开十分钟，回来后说明感受并主动澄清。",
        ))
    assert {item.evidence_kind for item in items} == {"REAL_LIFE_EVENT"}
    assert {item.context for item in items} == {"FAMILY"}
    snapshot = score_dimension("D9", items, now=NOW)
    assert STAGE_RANK[snapshot.stage] >= STAGE_RANK["E0"]


def test_uncaptured_events_cannot_become_evidence():
    blocked = capture_event(event(), consented_scopes=["EMD_SELF_ASSESSMENT"], now=NOW)
    with pytest.raises(ValueError):
        event_to_batch1_evidence(
            blocked, dimension_code="D9", stage_signal="E3", occurred_at=NOW, behavior_summary="x",
        )


# ── module description and migration ─────────────────────────────────────────

def test_module_description_states_its_refusals():
    described = describe_event_engine()
    assert len(described["skills"]) == len(WORKFLOW_NODES) == 8
    assert set(described["repair_stages"]) == set(REPAIR_STAGE_RANK)
    assert any("不要求用户制造冲突" in item for item in described["does_not"])
    assert "DOMESTIC_VIOLENCE" in described["unsafe_relationship_flags"]


def test_router_exposes_the_batch_three_surface():
    from routers.formation_twin_emotional_maturity import router

    paths = {route.path for route in router.routes}
    for suffix in (
        "events", "events/overview", "events/recovery", "events/repair",
        "transfer", "patterns", "checkpoints", "checkpoints/evaluate",
    ):
        assert f"/api/v1/formation-twin/emotional-maturity/{suffix}" in paths


def test_erasure_covers_every_batch_three_table():
    source = (ROOT / "backend/routers/formation_twin_emotional_maturity.py").read_text(encoding="utf-8")
    erase_block = source.split("def emotional_maturity_erase")[1]
    for table in (
        "formation_twin_emd_real_life_events", "formation_twin_emd_event_timelines",
        "formation_twin_emd_recovery_metric_sets", "formation_twin_emd_repair_verifications",
        "formation_twin_emd_transfer_observations", "formation_twin_emd_patterns",
        "formation_twin_emd_checkpoints", "formation_twin_emd_growth_evaluations",
    ):
        assert table in erase_block


def test_migration_file_exists_for_batch_three():
    migration = ROOT / "backend/migrations/0225_formation_twin_emd_real_life_events.sql"
    rollback = ROOT / "backend/migrations/rollback/0225_formation_twin_emd_real_life_events_down.sql"
    assert migration.exists() and rollback.exists()
    sql = migration.read_text(encoding="utf-8")
    assert "formation_twin_emd_real_life_events" in sql
    assert "formation_twin_emd_recovery_metric_sets" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql
