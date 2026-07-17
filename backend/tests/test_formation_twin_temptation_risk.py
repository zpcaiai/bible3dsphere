from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from formation_twin.temptation_risk import (
    CONSUMED_EVENTS,
    PUBLISHED_EVENTS,
    WORKFLOW_NODES,
    ActiveProtection,
    CycleCondition,
    EvidenceReference,
    ProtectionAction,
    TemptationCycle,
    apply_warning_policy,
    build_protection_route,
    condition_is_current,
    generate_warning,
    learn_warning_feedback,
    make_protection_action_smaller,
    match_risk_context,
    risk_data_quality,
    sanitize_notification_content,
    select_protection_action,
    start_recovery,
    validate_model_candidates,
    validate_passive_signal,
    validate_safe_text,
)
from routers.formation_twin_protection import router


pytestmark = pytest.mark.no_db
NOW = datetime(2026, 7, 17, 12, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[2]


def cycle(**updates):
    values = {
        "cycle_id": "cycle-1", "title": "深夜数字逃避", "cycle_type": "DIGITAL_ESCAPE",
        "trigger_conditions": ["WORK_REJECTION"], "vulnerability_conditions": ["SLEEP_DEPRIVATION"],
        "environmental_conditions": ["ALONE_AT_NIGHT"],
        "required_conditions": ["WORK_REJECTION", "SLEEP_DEPRIVATION", "ALONE_AT_NIGHT"],
        "protective_factors": ["DEVICE_BOUNDARY"], "interruption_points": ["BEFORE_DEVICE_ACCESS"],
        "recovery_paths": ["RECONNECT_WITH_SUPPORT"], "minimum_independent_conditions": 2,
        "lifecycle_status": "ACTIVE", "user_review_status": "USER_CONFIRMED",
        "user_confirmed": True, "limitations": ["只适用于当前阶段。"],
    }
    values.update(updates)
    return TemptationCycle(**values)


def condition(code="SLEEP_DEPRIVATION", **updates):
    values = {
        "condition_type": "VULNERABILITY", "condition_code": code,
        "user_visible_description": code.replace("_", " ").lower(),
        "occurred_at": NOW - timedelta(hours=1), "expires_at": NOW + timedelta(hours=5),
        "evidence_references": [{"reference_type": "CHECKIN", "reference_id": f"ref-{code}"}],
        "user_confirmed": True,
    }
    values.update(updates)
    return CycleCondition(**values)


def matched_snapshot(**updates):
    values = {
        "cycles": [cycle()],
        "conditions": [condition("SLEEP_DEPRIVATION"), condition("WORK_REJECTION")],
        "warnings_enabled": True, "now": NOW,
    }
    values.update(updates)
    return match_risk_context(**values)


def test_condition_requires_expiry_after_occurrence():
    with pytest.raises(ValueError):
        condition(expires_at=NOW - timedelta(hours=2))


def test_expired_condition_is_not_current():
    item = condition(expires_at=NOW - timedelta(minutes=1))
    assert condition_is_current(item, NOW) is False


def test_unconfirmed_condition_is_not_current():
    assert condition_is_current(condition(user_confirmed=False), NOW) is False


def test_sensitive_cycle_requires_confirmation():
    with pytest.raises(ValueError):
        cycle(cycle_type="PORNOGRAPHY_SELF_REPORTED", user_confirmed=False, lifecycle_status="DRAFT", user_review_status="PENDING")


def test_active_cycle_requires_confirmation():
    with pytest.raises(ValueError):
        cycle(cycle_type="USER_DEFINED", user_confirmed=False)


def test_temptation_node_cannot_claim_behavior_occurred():
    with pytest.raises(ValueError):
        cycle(temptation_nodes=[{"node_type": "TEMPTATION", "behavior_occurred": True}])


def test_single_ordinary_condition_never_generates_high_warning():
    snapshot = match_risk_context(cycles=[cycle()], conditions=[condition()], warnings_enabled=True, now=NOW)
    assert snapshot.internal_risk_band == "CONTEXT_PRESENT"
    assert snapshot.user_visible_warning_level == "AWARENESS"
    assert "一个普通条件" in snapshot.limitations[0]


def test_multiple_confirmed_conditions_generate_protection_suggestion():
    snapshot = matched_snapshot()
    assert snapshot.internal_risk_band == "MULTIPLE_CONDITIONS"
    assert snapshot.user_visible_warning_level == "PROTECTION_SUGGESTED"
    assert snapshot.matched_cycle_ids == ["cycle-1"]


def test_unknown_condition_remains_unknown():
    snapshot = matched_snapshot()
    assert "ALONE_AT_NIGHT" in snapshot.unknown_conditions
    assert all(item["condition_code"] != "ALONE_AT_NIGHT" for item in snapshot.active_conditions)


def test_independence_group_prevents_duplicate_counting():
    shared = EvidenceReference(reference_type="JOURNAL_DERIVATIVE", reference_id="a", independence_group="journal-1")
    one = condition("SLEEP_DEPRIVATION", evidence_references=[shared])
    two = condition("WORK_REJECTION", evidence_references=[shared])
    snapshot = match_risk_context(cycles=[cycle()], conditions=[one, two], warnings_enabled=True, now=NOW)
    assert snapshot.user_visible_warning_level == "AWARENESS"


def test_active_protections_reduce_or_suppress_warning():
    protections = [
        ActiveProtection(protection_type="DEVICE_BOUNDARY", description="设备边界已经开启"),
        ActiveProtection(protection_type="HUMAN_SUPPORT", description="支持伙伴当前可联系"),
    ]
    snapshot = matched_snapshot(active_protections=protections)
    assert snapshot.user_visible_warning_level in {"AWARENESS", "NO_WARNING"}
    assert snapshot.counterevidence == ["设备边界已经开启", "支持伙伴当前可联系"]


def test_explicit_urge_prioritizes_immediate_support_without_claiming_behavior():
    snapshot = matched_snapshot(conditions=[], explicit_urge=True)
    assert snapshot.internal_risk_band == "STRONG_URGE_SELF_REPORTED"
    assert snapshot.user_visible_warning_level == "IMMEDIATE_SUPPORT_SUGGESTED"
    assert snapshot.matched_cycle_ids == []


def test_behavior_started_is_distinct_from_temptation():
    snapshot = matched_snapshot(conditions=[], behavior_started=True)
    assert snapshot.internal_risk_band == "BEHAVIOR_STARTED"


def test_continuation_risk_prioritizes_stopping():
    assert matched_snapshot(conditions=[], continuation_risk=True).internal_risk_band == "CONTINUATION_RISK"


def test_crisis_bypasses_ordinary_warning():
    snapshot = matched_snapshot(crisis_level="IMMINENT")
    assert snapshot.internal_risk_band == "CRISIS_RELATED"
    assert snapshot.user_visible_warning_level == "CRISIS_HANDOFF"


def test_disabled_or_paused_warning_fails_closed():
    assert matched_snapshot(warnings_enabled=False).warning_eligible is False
    assert matched_snapshot(paused=True).warning_eligible is False


def test_warning_policy_enforces_cooldown():
    policy = apply_warning_policy(matched_snapshot(), last_warning_at=NOW-timedelta(hours=1), now=NOW)
    assert policy["deliver"] is False
    assert "COOLDOWN_ACTIVE" in policy["suppression_reasons"]


def test_warning_policy_enforces_quiet_hours():
    policy = apply_warning_policy(
        matched_snapshot(), now=datetime(2026,7,17,15,tzinfo=timezone.utc),
        quiet_hours={"start":"22:00","end":"07:00","timezone":"Asia/Shanghai"},
    )
    assert policy["deliver"] is False
    assert "QUIET_HOURS" in policy["suppression_reasons"]


def test_user_requested_immediate_help_can_bypass_quiet_hours():
    snapshot = matched_snapshot(conditions=[], explicit_urge=True)
    policy = apply_warning_policy(
        snapshot, user_requested_help=True, now=datetime(2026,7,17,15,tzinfo=timezone.utc),
        quiet_hours={"start":"22:00","end":"07:00","timezone":"Asia/Shanghai"},
    )
    assert policy["deliver"] is True


def test_false_positive_feedback_extends_cooldown_without_stronger_copy():
    learned = learn_warning_feedback(["INACCURATE", "TOO_FREQUENT", "INACCURATE"])
    assert learned["cooldown_hours"] == 24
    assert learned["request_recalibration"] is True
    assert learned["stronger_language"] is False


@pytest.mark.parametrize("level", ["AWARENESS", "PROTECTION_SUGGESTED", "IMMEDIATE_SUPPORT_SUGGESTED", "CRISIS_HANDOFF"])
def test_warning_content_is_explainable_and_non_probabilistic(level):
    snapshot = matched_snapshot().model_copy(update={
        "internal_risk_band": "CRISIS_RELATED" if level == "CRISIS_HANDOFF" else "MULTIPLE_CONDITIONS",
        "user_visible_warning_level": level, "warning_eligible": True,
    })
    warning = generate_warning(snapshot, now=NOW)
    assert warning.uncertainty_notes
    assert "%" not in warning.message
    assert warning.sharing_status == "PRIVATE"


@pytest.mark.parametrize("phrase", [
    "你今晚很可能犯罪。", "你即将复发！", "你是一个成瘾者。",
    "真正悔改的人不会复发。", "神正在警告你，否则会惩罚你。", "必须立刻联系牧者认罪。",
    "开启更多监控才能证明你认真悔改。",
])
def test_shame_prediction_theology_and_surveillance_red_team(phrase):
    with pytest.raises(ValueError):
        validate_safe_text(phrase)


def test_numeric_relapse_probability_is_rejected():
    with pytest.raises(ValueError):
        validate_safe_text("你有85%复发概率。")


@pytest.mark.parametrize(("band","expected"), [
    ("CONTEXT_PRESENT", "DELAY_DECISION"),
    ("MULTIPLE_CONDITIONS", "MOVE_DEVICE"),
    ("STRONG_URGE_SELF_REPORTED", "LEAVE_ENVIRONMENT"),
    ("BEHAVIOR_STARTED", "LEAVE_ENVIRONMENT"),
    ("CRISIS_RELATED", "CRISIS_HANDOFF"),
    ("NONE", "NO_ACTION"),
])
def test_minimum_protection_action_by_internal_band(band, expected):
    snapshot = matched_snapshot().model_copy(update={"internal_risk_band":band})
    assert select_protection_action(snapshot).action_type == expected


def test_human_support_action_is_draft_only():
    snapshot = matched_snapshot(conditions=[], explicit_urge=True)
    action = select_protection_action(snapshot, human_support_available=True)
    assert action.action_type == "MESSAGE_SUPPORT_PERSON"
    assert "不会自动发送" in action.description


def test_smaller_action_ladder_preserves_choice():
    action = select_protection_action(matched_snapshot().model_copy(update={"internal_risk_band":"BEHAVIOR_STARTED"}))
    smaller = make_protection_action_smaller(action)
    assert smaller.action_type == "CHANGE_ROOM"
    assert smaller.required_user_confirmation is True


def test_protection_route_requires_current_confirmation():
    action = select_protection_action(matched_snapshot())
    with pytest.raises(ValueError):
        build_protection_route(action, user_confirmed=False)


def test_protection_route_is_minimal_and_idempotent():
    route = build_protection_route(select_protection_action(matched_snapshot()), user_confirmed=True, request_id="request-1")
    assert route["sensitive_reason_included"] is False
    assert "internal_risk_band" not in route
    assert len(route["idempotency_key"]) == 64


def test_high_impact_route_requires_visible_recovery_method():
    action = ProtectionAction(
        action_id="a", action_type="DISABLE_ACCESS", title="边界", description="用户选择的边界",
        target_module="ATTENTION_OS", routing_payload={}, high_impact=True,
        default_execution_mode="HARD_BLOCK",
    )
    with pytest.raises(ValueError):
        build_protection_route(action, user_confirmed=True)


def test_model_candidate_requires_consent_and_never_triggers_warning():
    payload = {
        "possible_cycle_matches":[{"cycle_id":"cycle-1","user_confirmation_required":True}],
        "relapse_prediction_attempted":False,"moral_judgment_attempted":False,"diagnosis_attempted":False,
    }
    assert validate_model_candidates(payload,consent=False,allowed_cycle_ids=["cycle-1"])["accepted"] == []
    result = validate_model_candidates(payload,consent=True,allowed_cycle_ids=["cycle-1"])
    assert len(result["accepted"]) == 1 and result["can_trigger_warning"] is False


def test_model_prediction_attempt_is_rejected():
    result = validate_model_candidates({"relapse_prediction_attempted":True},consent=True,allowed_cycle_ids=[])
    assert result["rejected"] == ["PROHIBITED_MODEL_OUTPUT"]


@pytest.mark.parametrize("signal", [
    "RAW_BROWSER_HISTORY", "MESSAGE_CONTENT", "KEYSTROKES", "CAMERA_STREAM", "PRECISE_LOCATION_STREAM",
])
def test_content_level_passive_monitoring_is_blocked(signal):
    assert validate_passive_signal(signal,consent=True)["accepted"] is False


def test_allowlisted_passive_metadata_requires_separate_consent():
    assert validate_passive_signal("BOUNDARY_STATUS",consent=False)["accepted"] is False
    accepted = validate_passive_signal("BOUNDARY_STATUS",consent=True)
    assert accepted["accepted"] is True and accepted["local_processing_preferred"] is True


@pytest.mark.parametrize("content", ["色情风险", "今晚可能复发", "赌博冲动", "temptation warning"])
def test_lock_screen_notification_is_always_generic_for_sensitive_content(content):
    assert sanitize_notification_content(content) == "你有一项可选的保护提醒。"


def test_recovery_starts_with_safety_not_analysis():
    recovery = start_recovery()
    assert recovery["first_step"] == "IMMEDIATE_SAFETY"
    assert recovery["questions"][0] == "你现在安全吗？"
    assert recovery["deep_analysis_allowed"] is False


def test_crisis_recovery_hands_off_and_stops_analysis():
    recovery = start_recovery(crisis_level="IMMINENT")
    assert recovery["status"] == "CRISIS_HANDOFF"
    assert recovery["target_module"] == "CRISIS_CARE"


def test_data_quality_blocks_unconfirmed_sensitive_cycle_and_sharing():
    report = risk_data_quality(
        cycles=[{"id":"c","cycle_type":"PORNOGRAPHY_SELF_REPORTED","user_confirmed":False,"lifecycle_status":"ACTIVE","user_review_status":"PENDING"}],
        warnings=[{"id":"w","warning_level":"PROTECTION_SUGGESTED","active_conditions":["one"],"uncertainty_notes":[]}],
        support_requests=[{"id":"s","delivery_status":"SENT","user_confirmed":False}],
        recoveries=[{"id":"r","first_step":"WHY_ANALYSIS"}],
    )
    assert report["status"] == "FAIL_CLOSED"
    assert report["high_severity_count"] >= 5


def test_workflows_are_crisis_first_and_recovery_separate():
    assert WORKFLOW_NODES["risk_monitoring"].index("run_crisis_gateway") < WORKFLOW_NODES["risk_monitoring"].index("match_cycle_conditions")
    assert WORKFLOW_NODES["recovery"][1] == "immediate_safety_check"


def test_event_contract_has_no_sensitive_body_or_internal_band():
    events = " ".join(PUBLISHED_EVENTS + CONSUMED_EVENTS)
    for forbidden in ("journal_text", "confession_text", "internal_risk_band", "relapse_probability"):
        assert forbidden not in events
    assert "formation_twin.crisis_handoff_requested" in PUBLISHED_EVENTS


def test_api_registers_required_batch_seven_routes():
    routes={(method,item.path) for item in router.routes for method in item.methods}
    required={
        ("POST","/api/v1/formation-twin/temptation-cycles"),
        ("POST","/api/v1/formation-twin/protection/current/recalculate"),
        ("POST","/api/v1/formation-twin/protection/warnings/{warning_id}/inaccurate"),
        ("POST","/api/v1/formation-twin/protection/actions/{action_id}/accept"),
        ("POST","/api/v1/formation-twin/protection-plans/{plan_id}/share"),
        ("POST","/api/v1/formation-twin/protection/support-contacts/{contact_id}/draft-message"),
        ("POST","/api/v1/formation-twin/recovery/start"),
        ("DELETE","/api/v1/formation-twin/protection/data"),
    }
    assert required <= routes
    assert len(router.routes) == 66


def test_migration_has_rls_and_no_risk_scoring_columns():
    sql=(ROOT/"backend/migrations/0218_formation_twin_temptation_risk.sql").read_text()
    assert sql.count("CREATE TABLE IF NOT EXISTS formation_twin_") == 15
    assert "ENABLE ROW LEVEL SECURITY" in sql and "app.current_user_email" in sql
    for forbidden in ("relapse_probability ","sin_risk_score ","purity_score ","sobriety_rank ","obedience_score "):
        assert forbidden not in sql
    rollback=(ROOT/"backend/migrations/rollback/0218_formation_twin_temptation_risk_down.sql").read_text()
    assert "MANUAL ROLLBACK ONLY" in rollback
    assert rollback.count("DROP TABLE IF EXISTS formation_twin_") == 15


def test_main_wires_protection_router():
    main=(ROOT/"backend/main.py").read_text()
    assert "init_formation_twin_protection_router" in main
    assert "app.include_router(formation_twin_protection_router)" in main


def test_export_erasure_and_source_invalidation_cover_batch_seven():
    source=(ROOT/"backend/routers/formation_twin.py").read_text()
    patterns=(ROOT/"backend/routers/formation_twin_patterns.py").read_text()
    assert '"temptation_risk_protection": protection_exports' in source
    assert 'DELETE FROM formation_twin_early_warnings WHERE email=%s' in source
    assert "formation_twin_risk_conditions SET invalidated_at=now()" in source
    assert "formation_twin_risk_snapshots SET invalidated_at=now()" in patterns


def test_large_condition_input_is_bounded_by_deduplication():
    conditions=[condition("SLEEP_DEPRIVATION",evidence_references=[{"reference_type":"X","reference_id":str(i),"independence_group":f"g-{i}"}]) for i in range(10_000)]
    snapshot=match_risk_context(cycles=[cycle()],conditions=conditions,warnings_enabled=True,now=NOW)
    assert len(snapshot.active_conditions) <= 10_000
    assert snapshot.user_visible_warning_level == "AWARENESS"
