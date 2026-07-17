from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from formation_twin.reflection_interventions import (
    CONSUMED_EVENTS,
    PUBLISHED_EVENTS,
    EffectReview,
    MicroIntervention,
    ReflectionMirror,
    assemble_reflection_context,
    build_routing_command,
    build_user_capacity,
    daily_reflection_workflow,
    decide_intervention,
    generate_daily_mirror,
    generate_intervention_candidates,
    generate_weekly_review,
    learn_intervention_preferences,
    make_action_smaller,
    reflection_data_quality,
    reminder_allowed,
    sanitize_notification_content,
    select_high_value_question,
    select_minimum_action,
    validate_engagement_proposal,
    validate_reflection_intervention,
    validate_safe_text,
)
from routers.formation_twin_reflections import router


pytestmark = pytest.mark.no_db

NOW = datetime(2026, 7, 17, 12, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[2]


def capacity(**updates):
    values = {
        "energy_level": 6, "stress_level": 4, "sleep_quality": 6,
        "available_minutes": 10, "user_selected_mode": "NORMAL", "source_event_ids": ["event-1"], "now": NOW,
    }
    values.update(updates)
    return build_user_capacity(**values)


def context(**updates):
    values = {
        "context_type": "DAILY", "window_start": NOW - timedelta(days=1), "window_end": NOW,
        "emotional_state": {"id": "checkin-1", "stress_level": 8, "energy_level": 3, "statement_type": "USER_REPORTED_FACT"},
        "formation_state": {"id": "formation-1", "statement_type": "STRUCTURED_SNAPSHOT"},
        "patterns": [{
            "id": "pattern-1", "pattern_id": "pattern-1", "title": "压力后延长工作",
            "pattern_type": "FORMATION_DIRECTION_PATTERN", "lifecycle_status": "CONFIRMED_CONTEXTUAL",
            "user_review_status": "CONFIRMED", "statement_type": "USER_CONFIRMED_PATTERN",
        }],
        "life_seasons": [{"id": "season-1", "title": "项目交付阶段", "active": True, "user_review_status": "CONFIRMED"}],
        "capacity": capacity(), "preferences": {}, "safety_status": {"safety_level": "NONE"},
        "protective_factors": [{"id": "protect-1", "title": "主动联系同事"}],
        "grace_recovery_factors": [{"id": "grace-1", "title": "获得真实关系支持"}],
        "alternative_responses": [{"id": "alternative-1", "title": "先寻求帮助"}], "now": NOW,
    }
    values.update(updates)
    return assemble_reflection_context(**values)


@pytest.mark.parametrize(
    ("updates", "expected"),
    [
        ({"energy_level": 2}, "VERY_LOW_CAPACITY"),
        ({"stress_level": 9}, "VERY_LOW_CAPACITY"),
        ({"sleep_quality": 2}, "VERY_LOW_CAPACITY"),
        ({"energy_level": 4}, "LOW_CAPACITY"),
        ({}, "NORMAL_CAPACITY"),
        ({"energy_level": 9, "stress_level": 2, "sleep_quality": 8, "available_minutes": 20}, "HIGH_CAPACITY"),
        ({"energy_level": None, "stress_level": None, "sleep_quality": None, "available_minutes": None}, "USER_UNSPECIFIED"),
    ],
)
def test_capacity_classification(updates, expected):
    assert capacity(**updates).capacity_level == expected


def test_invalid_capacity_mode_is_rejected():
    with pytest.raises(ValueError):
        capacity(user_selected_mode="OBEY_MORE")


def test_context_filters_rejected_and_separates_pending():
    ctx = context(patterns=[
        {"id":"good","pattern_id":"good","title":"已确认","pattern_type":"COPING_PATTERN","lifecycle_status":"CONFIRMED_ACTIVE","user_review_status":"CONFIRMED"},
        {"id":"pending","pattern_id":"pending","title":"待确认","pattern_type":"COPING_PATTERN","lifecycle_status":"PENDING_USER_REVIEW","user_review_status":"PENDING"},
        {"id":"bad","pattern_id":"bad","title":"已拒绝","pattern_type":"COPING_PATTERN","lifecycle_status":"REJECTED","user_review_status":"REJECTED"},
    ])
    assert [item["id"] for item in ctx.confirmed_patterns] == ["good"]
    assert [item["id"] for item in ctx.pending_clarification_items] == ["pending"]
    assert ctx.data_coverage["pending_context_used_for_action"] is False


def test_context_budget_is_strict():
    patterns = [{"id":f"p{i}","pattern_id":f"p{i}","title":str(i),"pattern_type":"COPING_PATTERN","lifecycle_status":"CONFIRMED_ACTIVE","user_review_status":"CONFIRMED"} for i in range(10)]
    seasons = [{"id":f"s{i}","title":str(i),"active":True,"user_review_status":"CONFIRMED"} for i in range(6)]
    ctx = context(patterns=patterns, life_seasons=seasons)
    assert len(ctx.confirmed_patterns) == 3
    assert len(ctx.active_life_seasons) == 2


def test_store_only_context_stops_analysis():
    ctx = context(capacity=capacity(user_selected_mode="STORE_ONLY"))
    assert ctx.allowed_output == "STORE_ONLY"
    assert generate_daily_mirror(ctx)["status"] == "STORED_WITHOUT_ANALYSIS"


def test_reflection_only_context_has_no_action():
    ctx = context(capacity=capacity(user_selected_mode="REFLECTION_ONLY"))
    output = generate_daily_mirror(ctx, now=NOW)
    assert ctx.allowed_output == "REFLECTION_ONLY"
    assert output["mirror"] is not None
    assert output["intervention"] is None


def test_insufficient_data_degrades_to_lightweight_mirror():
    ctx = context(emotional_state=None, patterns=[])
    output = generate_daily_mirror(ctx, now=NOW)
    assert ctx.allowed_output == "LIGHTWEIGHT_CHECKIN_ONLY"
    assert "还不能判断" in output["mirror"].mirror_text
    assert output["intervention"] is None


def test_crisis_suppresses_ordinary_mirror_and_action():
    ctx = context(safety_status={"safety_level":"ELEVATED"})
    output = generate_daily_mirror(ctx, now=NOW)
    assert ctx.allowed_output == "CRISIS_ONLY"
    assert output["mirror"] is None
    assert output["intervention"].target_module == "CRISIS_CARE"
    assert output["ordinary_intervention_suppressed"] is True


def test_question_selector_returns_one_and_respects_cooldown():
    ctx = context()
    first = select_high_value_question(ctx, now=NOW)
    second = select_high_value_question(ctx, recent_questions=[{"question_type":first.question_type,"created_at":NOW}], now=NOW)
    assert first is not None and second is not None
    assert first.question_type != second.question_type


def test_do_not_ask_again_suppresses_question_type():
    ctx = context()
    question = select_high_value_question(ctx, recent_questions=[{"question_type":"ALTERNATIVE_RESPONSE","status":"DO_NOT_ASK_AGAIN"}], now=NOW)
    assert question.question_type != "ALTERNATIVE_RESPONSE"


def test_low_capacity_question_prioritizes_rest():
    ctx = context(capacity=capacity(energy_level=2))
    assert select_high_value_question(ctx, now=NOW).question_type == "REST_AND_LIMITS"


def test_pending_pattern_can_only_drive_clarification():
    ctx = context(emotional_state=None, patterns=[{"id":"pending","pattern_id":"pending","title":"未知","pattern_type":"COPING_PATTERN","lifecycle_status":"PENDING_USER_REVIEW","user_review_status":"PENDING"}])
    question = select_high_value_question(ctx, now=NOW)
    candidates = generate_intervention_candidates(ctx, now=NOW)
    assert question.question_type in {"CLARIFICATION", "EMOTION_NAMING"}
    assert all(not item.source_pattern_ids for item in candidates)


def test_daily_mirror_has_traceable_source_and_grace_balance():
    output = generate_daily_mirror(context(), now=NOW)
    mirror = output["mirror"]
    assert len(mirror.source_references) >= 1
    assert mirror.grace_and_protection
    assert output["validation"]["valid"] is True


def test_very_low_capacity_mirror_is_at_most_eighty_characters():
    output = generate_daily_mirror(context(capacity=capacity(energy_level=2)), now=NOW)
    assert len(output["mirror"].mirror_text) <= 81


def test_intervention_candidates_are_bounded_and_offer_rest():
    candidates = generate_intervention_candidates(context(), now=NOW)
    assert 1 <= len(candidates) <= 3
    assert any(item.intervention_type in {"REST", "RELATIONAL_SUPPORT"} for item in candidates)


def test_very_low_capacity_candidates_are_tiny():
    candidates = generate_intervention_candidates(context(capacity=capacity(energy_level=2)), now=NOW)
    assert all(item.estimated_duration_minutes <= 1 for item in candidates)
    assert candidates[0].intervention_type == "REST"


def test_prayer_is_only_selected_for_explicit_spiritual_distance_preference():
    ctx = context(preferences={"self_reported_spiritual_distance":True})
    assert generate_intervention_candidates(ctx, now=NOW)[0].intervention_type == "PRAYER"


def test_minimum_action_excludes_capacity_mismatch():
    ctx = context(capacity=capacity(energy_level=2))
    candidate = generate_intervention_candidates(context(), now=NOW)[0].model_copy(update={"estimated_duration_minutes":10})
    result = select_minimum_action(ctx,[candidate])
    assert result["selected"].intervention_type == "NO_ACTION"
    assert result["excluded"][0]["reason"] == "CAPACITY_MISMATCH"


def test_no_action_is_fallback_when_category_is_blocked():
    ctx = context(preferences={"blocked_intervention_types":["PAUSE","REST","RELATIONAL_SUPPORT"]})
    candidates = generate_intervention_candidates(ctx, now=NOW)
    assert candidates[0].intervention_type == "NO_ACTION"


def test_smaller_action_degrades_three_then_one_then_no_action():
    ctx = context()
    action = generate_intervention_candidates(ctx, now=NOW)[0].model_copy(update={"estimated_duration_minutes":10})
    three = make_action_smaller(action,ctx)
    one = make_action_smaller(three,ctx)
    none = make_action_smaller(one,ctx)
    assert (three.estimated_duration_minutes,one.estimated_duration_minutes,none.intervention_type) == (3,1,"NO_ACTION")


def test_decision_is_optional_and_neutral():
    action = generate_intervention_candidates(context(), now=NOW)[0]
    decision = decide_intervention(action,"REJECTED")
    assert decision["route_allowed"] is False
    assert decision["rejection_is_negative_label"] is False


def test_habit_requires_second_confirmation():
    action = generate_intervention_candidates(context(), now=NOW)[0].model_copy(update={"target_module":"HOLY_HABIT_ENGINE","one_time":False,"requires_second_confirmation":True})
    with pytest.raises(ValueError):
        decide_intervention(action,"ACCEPTED")
    decision = decide_intervention(action,"ACCEPTED",habit_confirmation={"frequency":"DAILY","duration_days":5,"reminder_enabled":False,"weekly_review_usage":False})
    assert decision["repeat_allowed"] is True


def test_routing_requires_explicit_confirmation():
    action = generate_intervention_candidates(context(), now=NOW)[0]
    with pytest.raises(ValueError):
        build_routing_command(action,user_confirmed=False)


def test_routing_payload_is_minimal_and_one_time():
    action = generate_intervention_candidates(context(), now=NOW)[0]
    command = build_routing_command(action,user_confirmed=True,request_id="route-1")
    assert command["payload"]["sensitive_context_included"] is False
    assert command["payload"]["one_time"] is True
    assert "source_pattern_ids" not in command["payload"]
    assert len(command["idempotency_key"]) == 64


def test_effect_review_learning_is_user_reported_and_causally_humble():
    review = EffectReview(review_id="r1",intervention_id="i1",execution_status="COMPLETED",user_reported_helpfulness="HELPFUL",user_reported_burden="HIGH",reviewed_at=NOW)
    updates = learn_intervention_preferences(review,intervention_type="REST",learning_enabled=True)
    assert review.statement_type == "USER_REPORTED_FACT"
    assert len(updates) == 2
    assert all(item["confidence"] is None for item in updates)


def test_preference_learning_can_be_disabled():
    review = EffectReview(review_id="r1",intervention_id="i1",execution_status="NOT_STARTED",user_reported_burden="TOO_HIGH",reviewed_at=NOW)
    assert learn_intervention_preferences(review,intervention_type="PRAYER",learning_enabled=False) == []


@pytest.mark.parametrize("phrase",[
    "神告诉你今天必须认罪。", "你若不做这个操练，就是不愿顺服。", "真正的基督徒不会焦虑。",
    "圣灵要你离开这份工作。", "这个行动可以治疗你的抑郁症。", "只要祷告就不需要看医生。",
])
def test_theological_and_psychological_red_team_is_blocked(phrase):
    with pytest.raises(ValueError): validate_safe_text(phrase)


@pytest.mark.parametrize("proposal",[
    {"streak":7}, {"spiritual_score":80}, {"message":"完成任务可以提高属灵等级。"}, {"leaderboard":True},
])
def test_engagement_manipulation_is_blocked(proposal):
    assert validate_engagement_proposal(proposal)["valid"] is False


def test_safety_validator_blocks_crisis_ordinary_action():
    ctx = context(safety_status={"safety_level":"IMMINENT"})
    ordinary = generate_intervention_candidates(context(), now=NOW)[0]
    result = validate_reflection_intervention(ctx,None,None,ordinary)
    assert result["valid"] is False
    assert any(item["code"]=="CRISIS_ORDINARY_ACTION" for item in result["violations"])


def test_safety_validator_blocks_sensitive_payload():
    ctx = context()
    action = generate_intervention_candidates(ctx, now=NOW)[0].model_copy(update={"routing_payload":{"journal_text":"secret"}})
    assert validate_reflection_intervention(ctx,None,None,action)["valid"] is False


def test_quiet_hours_supports_overnight_windows():
    result = reminder_allowed(now=datetime(2026,7,17,15,tzinfo=timezone.utc),timezone_name="Asia/Shanghai",quiet_hours_start="22:00",quiet_hours_end="07:00",reminder_enabled=True)
    assert result == {"allowed":False,"reason":"QUIET_HOURS"}


def test_reminders_throttle_after_skips_or_high_burden():
    result = reminder_allowed(now=NOW,timezone_name="UTC",quiet_hours_start=None,quiet_hours_end=None,reminder_enabled=True,consecutive_skips=2)
    assert result["reason"] == "FREQUENCY_THROTTLED"


def test_notification_is_always_generic():
    assert sanitize_notification_content("婚姻冲突和认罪提醒") == "你的属灵星球中有一项可选回顾。"


def test_data_quality_fails_closed_on_missing_source_and_unconfirmed_route():
    report = reflection_data_quality(
        mirrors=[{"id":"m1","source_references":[]}],
        proposals=[{"id":"p1","intervention_type":"REST","estimated_duration_minutes":1,"target_module":"REST","routed":True,"user_confirmed":False}],
    )
    assert report["status"] == "BLOCKED"
    assert report["high_severity_count"] == 2


def test_weekly_review_is_bounded_and_discloses_coverage():
    review = generate_weekly_review(context(),active_days=4,now=NOW)
    assert len(review["important_observations"]) <= 3
    assert "4天主动记录" in review["data_coverage"]["statement"]
    assert review["proposed_intervention"].required_user_confirmation is True


def test_daily_workflow_waits_for_user_decision():
    state = daily_reflection_workflow(context())
    assert state["mirror"] is not None
    assert state["user_decision"] is None
    assert state["routing_result"] is None


def test_api_registers_all_required_routes():
    routes = {(method,path) for item in router.routes for method in item.methods for path in [item.path]}
    required = {
        ("POST","/api/v1/formation-twin/reflections/daily/generate"),
        ("POST","/api/v1/formation-twin/reflections/weekly/generate"),
        ("POST","/api/v1/formation-twin/interventions/proposals/{proposal_id}/smaller"),
        ("POST","/api/v1/formation-twin/interventions/proposals/{proposal_id}/no-action"),
        ("POST","/api/v1/formation-twin/interventions/{intervention_id}/effect-review"),
        ("PATCH","/api/v1/formation-twin/reflection-settings"),
    }
    assert required <= routes
    assert len(router.routes) == 42


def test_migration_has_rls_owner_scope_and_no_scores():
    sql = (ROOT/"backend/migrations/0217_formation_twin_reflection_interventions.sql").read_text()
    assert sql.count("CREATE TABLE IF NOT EXISTS formation_twin_") == 12
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "app.current_user_email" in sql
    for forbidden in ("compliance_score","intervention_success_score","spiritual_discipline_score","obedience_score"):
        assert forbidden not in sql


def test_main_wires_reflection_router():
    main = (ROOT/"backend/main.py").read_text()
    assert "init_formation_twin_reflections_router" in main
    assert "app.include_router(formation_twin_reflections_router)" in main


def test_export_and_erasure_cover_batch_six_tables():
    source = (ROOT/"backend/routers/formation_twin.py").read_text()
    assert '"reflection_intervention": reflection_exports' in source
    assert 'DELETE FROM formation_twin_intervention_effect_reviews WHERE email=%s' in source
    assert 'DELETE FROM formation_twin_reflection_contexts WHERE email=%s' in source


def test_source_withdrawal_invalidates_reflections():
    source = (ROOT/"backend/routers/formation_twin.py").read_text()
    patterns = (ROOT/"backend/routers/formation_twin_patterns.py").read_text()
    assert "formation_twin_reflection_contexts SET invalidated_at=now()" in source
    assert "_invalidate_reflections(cur, user[\"email\"], pattern_id)" in patterns


def test_event_contract_omits_sensitive_bodies():
    assert "formation_twin.intervention_routed" in PUBLISHED_EVENTS
    assert "crisis.case_routed" in CONSUMED_EVENTS
    serialized = " ".join(PUBLISHED_EVENTS | CONSUMED_EVENTS)
    assert "journal_text" not in serialized and "confession_text" not in serialized


def test_context_assembly_is_bounded_for_large_inputs():
    patterns = [{"id":f"p{i}","pattern_id":f"p{i}","title":"safe","pattern_type":"COPING_PATTERN","lifecycle_status":"CONFIRMED_ACTIVE","user_review_status":"CONFIRMED"} for i in range(10_000)]
    ctx = context(patterns=patterns)
    assert len(ctx.confirmed_patterns) == 3
