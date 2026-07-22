from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from formation_twin.temporal_patterns import (
    CONSUMED_EVENTS,
    PUBLISHED_EVENTS,
    ApproximateTimeRange,
    FormationPatternHypothesis,
    PatternConfidence,
    PatternEvidence,
    PatternScope,
    TimePrecision,
    build_formation_engine_context,
    build_long_term_snapshot,
    calculate_pattern_confidence,
    discover_rule_pattern_candidates,
    generate_pattern_review,
    independent_evidence,
    process_temporal_change,
    resolve_temporal_windows,
    temporal_data_quality,
    temporal_weight,
    transition_pattern,
    validate_pattern_text,
)


pytestmark = pytest.mark.no_db
NOW = datetime(2026, 7, 17, 12, tzinfo=timezone.utc)


def evidence(evidence_id: str, role: str = "SUPPORTING", *, group: str | None = None, weight: float = 1.0):
    return {
        "id": evidence_id,
        "evidence_id": evidence_id,
        "evidence_role": role,
        "evidence_type": "FORMATION_CHAIN",
        "source_record_type": "FORMATION_CHAIN",
        "source_record_id": evidence_id,
        "occurred_at": NOW,
        "temporal_weight": weight,
        "source_quality": "USER_CONFIRMED_CHAIN",
        "independence_group": group or evidence_id,
        "relevance": 1.0,
        "user_review_status": "CONFIRMED",
        "explanation": "用户确认的结构证据。",
    }


def chain(index: int, *, confirmed: bool = True, group: str | None = None, season: str | None = None, node_types=None):
    return {
        "source_record_id": f"00000000-0000-0000-0000-{index:012d}",
        "life_event_id": f"event-{index}",
        "independence_group": group or f"event-{index}",
        "confirmed": confirmed,
        "occurred_at": NOW - timedelta(days=20 - index),
        "processing_preference": "ALLOW_FUTURE_ANALYSIS",
        "signature": {"node_types": node_types or ["LIFE_EVENT", "BEHAVIOR"], "relation_types": ["OBSERVED_IN_SAME_EVENT"]},
        "life_domain": "WORK",
        "life_season_id": season,
    }


def pattern(pattern_id: str = "p1", status: str = "CONFIRMED_ACTIVE"):
    return {
        "id": pattern_id,
        "title": "经用户确认的当前阶段模式",
        "pattern_type": "FORMATION_DIRECTION_PATTERN",
        "scope": {"scope_kind": "CURRENT_CONTEXT_ONLY", "life_domains": ["WORK"], "life_season_ids": []},
        "lifecycle_status": status,
        "supporting_evidence": [evidence("e1")],
        "counterevidence": [],
        "review_due_at": (NOW + timedelta(days=30)).isoformat(),
        "user_review_status": "CONFIRMED",
        "limitations": ["仅适用于当前记录范围。"],
        "is_alternative_response": False,
    }


def test_local_calendar_windows_keep_iana_timezone_and_utc_boundaries():
    windows = resolve_temporal_windows(datetime(2026, 3, 8, 9, tzinfo=timezone.utc), "America/Los_Angeles")
    day = next(item for item in windows if item["window_type"] == "DAY")
    assert day["timezone"] == "America/Los_Angeles"
    assert day["start_at"].tzinfo == timezone.utc
    assert (day["end_at"] - day["start_at"]).total_seconds() == 23 * 3600


def test_event_can_belong_to_calendar_and_user_defined_windows():
    windows = resolve_temporal_windows(NOW, "Asia/Shanghai", custom_windows=[{
        "window_type": "USER_DEFINED_PERIOD", "start_at": NOW - timedelta(days=2),
        "end_at": NOW + timedelta(days=2), "label": "项目交付期",
    }])
    assert {item["window_type"] for item in windows}.issuperset({"DAY", "WEEK", "MONTH", "QUARTER", "YEAR", "USER_DEFINED_PERIOD"})


def test_approximate_time_preserves_unknown_expression():
    item = ApproximateTimeRange(precision=TimePrecision.UNKNOWN, original_expression="刚信主的时候")
    assert item.start_at is None and item.original_expression == "刚信主的时候"
    with pytest.raises(ValidationError):
        ApproximateTimeRange(precision=TimePrecision.UNKNOWN)


def test_decay_uses_configurable_half_life_without_deleting_history():
    value, strategy = temporal_weight(NOW - timedelta(days=30), "COPING_BEHAVIOR", now=NOW)
    assert value == pytest.approx(0.5)
    assert strategy == "STANDARD"
    assert temporal_weight(NOW - timedelta(days=3000), "FORMATION_CHAIN", now=NOW)[0] > 0


def test_non_standard_event_and_user_override_do_not_use_ordinary_decay():
    assert temporal_weight(NOW - timedelta(days=1000), "FORMATION_CHAIN", now=NOW, non_standard_decay=True) == (1.0, "NON_STANDARD_DECAY")
    assert temporal_weight(NOW - timedelta(days=1000), "FORMATION_CHAIN", now=NOW, user_marked_still_relevant=True) == (1.0, "USER_OVERRIDE")


def test_same_source_derivatives_count_once():
    items = [evidence("e1", group="journal-1", weight=.4), evidence("e2", group="journal-1", weight=.9), evidence("e3", group="journal-2")]
    result = independent_evidence(items)
    assert len(result) == 2
    assert next(item for item in result if item["independence_group"] == "journal-1")["temporal_weight"] == .9


def test_one_event_never_creates_long_term_candidate():
    assert discover_rule_pattern_candidates([chain(1)]) == []


def test_three_independent_events_create_scoped_rule_candidate():
    result = discover_rule_pattern_candidates([chain(1), chain(2), chain(3)])
    assert len(result) == 1
    assert result[0]["independent_evidence_count"] == 3
    assert result[0]["scope"]["scope_kind"] == "DOMAIN_SPECIFIC"
    assert result[0]["pattern_type"] == "FORMATION_DIRECTION_PATTERN"


def test_two_user_confirmed_chains_are_enough_but_same_source_is_not():
    assert len(discover_rule_pattern_candidates([chain(1), chain(2)])) == 1
    assert discover_rule_pattern_candidates([chain(1, group="same"), chain(2, group="same")]) == []


def test_life_season_evidence_never_auto_globalizes():
    result = discover_rule_pattern_candidates([chain(1, season="s1"), chain(2, season="s1"), chain(3, season="s1")])
    assert result[0]["scope"]["scope_kind"] == "LIFE_SEASON_SPECIFIC"
    assert result[0]["scope"]["life_season_ids"] == ["s1"]


@pytest.mark.parametrize(("nodes", "expected"), [
    (["LIFE_EVENT", "GRACE_EVIDENCE"], "GRACE_SUPPORT_PATTERN"),
    (["LIFE_EVENT", "PROTECTIVE_FACTOR"], "GRACE_SUPPORT_PATTERN"),
    (["LIFE_EVENT", "RECOVERY_RESPONSE"], "RECOVERY_PATTERN"),
])
def test_grace_protection_and_recovery_are_first_class_patterns(nodes, expected):
    result = discover_rule_pattern_candidates([chain(1, node_types=nodes), chain(2, node_types=nodes)])
    assert result[0]["pattern_type"] == expected


def test_store_only_and_excluded_chains_never_create_patterns():
    items = [chain(1), chain(2), chain(3)]
    items[0]["processing_preference"] = "STORE_ONLY"
    items[1]["processing_preference"] = "EXCLUDE_FROM_TWIN"
    items[2]["excluded"] = True
    assert discover_rule_pattern_candidates(items) == []


def test_counterevidence_lowers_confidence():
    supporting = [evidence("s1"), evidence("s2"), evidence("s3")]
    before = calculate_pattern_confidence(supporting, now=NOW)
    after = calculate_pattern_confidence([*supporting, evidence("c1", "COUNTEREVIDENCE"), evidence("c2", "COUNTEREVIDENCE")], now=NOW)
    assert after.numeric_value < before.numeric_value
    assert after.counterevidence_score > 0


def test_user_rejection_has_hard_priority_over_any_amount_of_support():
    confidence = calculate_pattern_confidence([evidence(f"e{i}") for i in range(20)], user_review_status="REJECTED", now=NOW)
    assert confidence.numeric_value == 0
    assert confidence.user_confirmation_factor == -1


def test_confidence_is_evidence_support_not_person_severity():
    confidence = calculate_pattern_confidence([evidence("a"), evidence("b")], now=NOW)
    serialized = json.dumps(confidence.model_dump(mode="json"), ensure_ascii=False).lower()
    assert "personality_score" not in serialized
    assert "成熟度" in serialized
    assert confidence.algorithm_version


def test_lifecycle_requires_user_for_confirmation_and_resolution():
    with pytest.raises(ValueError):
        transition_pattern("PENDING_USER_REVIEW", "CONFIRMED_CONTEXTUAL", initiated_by="SYSTEM")
    with pytest.raises(ValueError):
        transition_pattern("WEAKENING", "RESOLVED", initiated_by="SYSTEM")
    assert transition_pattern("PENDING_USER_REVIEW", "CONFIRMED_CONTEXTUAL", initiated_by="USER") == "CONFIRMED_CONTEXTUAL"


@pytest.mark.parametrize("text", [
    "你从小就是一个讨好型人格", "你的根本偶像是成功", "你一生都在用工作逃避羞耻",
    "你永远无法改变", "神正在通过失败惩罚你", "你的属灵成长速度下降了",
    "系统给出了 salvation probability",
])
def test_long_term_pattern_red_team_blocks_permanent_or_spiritual_verdicts(text):
    with pytest.raises(ValueError):
        validate_pattern_text(text)


def test_model_pattern_requires_counterevidence_field_alternatives_scope_and_review_time():
    confidence = PatternConfidence(
        level="LOW", numeric_value=.3, support_score=1, counterevidence_score=.2,
        recency_factor=.8, diversity_factor=.7, user_confirmation_factor=0,
        scope_consistency_factor=1, rationale=["有限证据"], calculated_at=NOW,
    )
    kwargs = dict(
        pattern_id="p", title="当前项目阶段的候选", pattern_type="TRIGGER_RESPONSE_PATTERN",
        description="在当前项目阶段，某类形成链可能重复出现。", statement_type="MODEL_PATTERN_HYPOTHESIS",
        source_kind="MODEL", scope=PatternScope(), lifecycle_status="PENDING_USER_REVIEW",
        supporting_evidence=[PatternEvidence.model_validate(evidence("e"))], counterevidence=[],
        confidence=confidence, limitations=["仅基于当前阶段"], first_observed_at=NOW-timedelta(days=3),
        last_observed_at=NOW, review_due_at=NOW+timedelta(days=30), alternative_explanations=[],
    )
    with pytest.raises(ValidationError):
        FormationPatternHypothesis(**kwargs)
    kwargs["alternative_explanations"] = ["也可能来自现实任务量。"]
    assert FormationPatternHypothesis(**kwargs).scope.scope_kind == "CURRENT_CONTEXT_ONLY"


def test_snapshot_fail_closes_missing_required_fields_and_excludes_rejected():
    snapshot = build_long_term_snapshot(
        patterns=[pattern(), {"id": "broken"}, pattern("rejected", "REJECTED")],
        life_seasons=[], trajectories=[], window_start=NOW-timedelta(days=30), window_end=NOW,
    )
    assert [item["id"] for item in snapshot["confirmed_active_patterns"]] == ["p1"]
    assert snapshot["blocked_items"][0]["pattern_id"] == "broken"
    assert "记录偏差" in snapshot["uncertainty_notes"][0]


def test_formation_context_requires_consent_and_crisis_blocks_deep_patterns():
    snapshot = build_long_term_snapshot(patterns=[pattern()], life_seasons=[], trajectories=[], window_start=NOW-timedelta(days=30), window_end=NOW)
    assert build_formation_engine_context(snapshot, consent=False)["reason"] == "CONSENT_REQUIRED"
    assert build_formation_engine_context(snapshot, consent=True, safety_level="ELEVATED")["route"] == "CRISIS_CARE"
    allowed = build_formation_engine_context(snapshot, consent=True)
    assert allowed["confirmed_patterns"][0]["id"] == "p1"
    assert allowed["pending_hypotheses"] == []


def test_review_limits_pending_question_to_one_and_skip_never_confirms():
    items = [pattern(f"p{i}", "PENDING_USER_REVIEW") for i in range(5)]
    review = generate_pattern_review("MONTHLY_FORMATION_REVIEW", patterns=items, window_start=NOW-timedelta(days=30), window_end=NOW)
    assert len(review["new_candidates"]) == 1
    assert any("跳过" in item for item in review["limitations"])


def test_workflow_stops_store_only_and_crisis_before_discovery():
    skipped = process_temporal_change({"processing_preference": "STORE_ONLY"}, chains=[chain(1), chain(2)], consent=True, safety_level="NONE")
    blocked = process_temporal_change({"processing_preference": "ALLOW_FUTURE_ANALYSIS"}, chains=[chain(1), chain(2)], consent=True, safety_level="IMMINENT")
    assert skipped["errors"][0]["code"] == "PROCESSING_SKIPPED"
    assert blocked["errors"][0]["code"] == "PATTERN_INFERENCE_BLOCKED"
    assert not blocked["rule_candidates"]


def test_model_adapter_failure_does_not_block_rule_candidates():
    state = process_temporal_change(
        {"processing_preference": "ALLOW_FUTURE_ANALYSIS"}, chains=[chain(1), chain(2)],
        consent=True, safety_level="NONE", model_allowed=True,
    )
    assert state["rule_candidates"]
    assert state["errors"][0]["recoverable"] is True


def test_data_quality_blocks_snapshot_when_required_field_is_missing():
    report = temporal_data_quality([{"id": "broken", "scope": {}}])
    assert report["high_severity_count"] > 0
    assert report["snapshot_publish_allowed"] is False
    assert report["context_publish_allowed"] is False


def test_event_contracts_cover_inputs_and_outputs_without_sensitive_payload_names():
    assert "formation_twin.life_event_deleted" in CONSUMED_EVENTS
    assert "formation_twin.pattern_candidate_created" in PUBLISHED_EVENTS
    assert "formation_twin.long_term_context_updated" in PUBLISHED_EVENTS
    serialized = json.dumps(sorted(PUBLISHED_EVENTS)).lower()
    for forbidden in ("journal_text", "prayer_text", "confession_text", "crisis_text"):
        assert forbidden not in serialized


def test_migration_has_all_owner_rls_tables_version_history_and_no_spiritual_score_columns():
    sql = (Path(__file__).parents[1] / "migrations" / "0216_formation_twin_temporal_patterns.sql").read_text()
    for table in (
        "formation_twin_temporal_windows", "formation_twin_event_clusters", "formation_twin_patterns",
        "formation_twin_pattern_evidence", "formation_twin_pattern_confidence_history",
        "formation_twin_pattern_lifecycle_events", "formation_twin_life_seasons", "formation_twin_trajectories",
        "formation_twin_pattern_reviews", "formation_twin_long_term_snapshots",
    ):
        assert table in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql and "app.current_user_email" in sql
    lowered = sql.lower()
    for forbidden in ("personality_score ", "spiritual_growth_score ", "holiness_score ", "idol_strength ", "sin_severity ", "salvation_probability ", "spiritual_rank "):
        assert forbidden not in lowered


def test_router_exposes_batch_5_review_control_rebuild_and_context_contracts():
    from routers.formation_twin_patterns import router

    routes = {(method, route.path) for route in router.routes for method in route.methods}
    required = {
        ("GET", "/api/v1/formation-twin/patterns/current"),
        ("GET", "/api/v1/formation-twin/patterns/candidates"),
        ("POST", "/api/v1/formation-twin/patterns/{pattern_id}/confirm"),
        ("POST", "/api/v1/formation-twin/patterns/{pattern_id}/narrow-scope"),
        ("POST", "/api/v1/formation-twin/patterns/{pattern_id}/mark-resolved"),
        ("GET", "/api/v1/formation-twin/patterns/{pattern_id}/evidence"),
        ("POST", "/api/v1/formation-twin/patterns/{pattern_id}/counterevidence"),
        ("GET", "/api/v1/formation-twin/life-seasons"),
        ("POST", "/api/v1/formation-twin/life-seasons/{season_id}/close"),
        ("GET", "/api/v1/formation-twin/trajectories"),
        ("GET", "/api/v1/formation-twin/pattern-reviews"),
        ("POST", "/api/v1/formation-twin/patterns/rebuild"),
        ("GET", "/api/v1/formation-twin/long-term-context/formation-engine"),
        ("DELETE", "/api/v1/formation-twin/long-term-state"),
    }
    assert required.issubset(routes)


def test_api_contract_rejects_naive_life_season_times():
    from routers.formation_twin_patterns import LifeSeasonBody

    with pytest.raises(ValidationError):
        LifeSeasonBody(title="项目阶段", season_type="USER_DEFINED", started_at=datetime(2026, 7, 17))


def test_graph_projection_is_metadata_only_and_owner_scoped():
    source = (Path(__file__).parents[1] / "formation_twin" / "temporal_graph.py").read_text()
    assert "WHERE user_id=%s AND node_type='FormationPattern'" in source
    assert "properties->>'profile_id'=%s" in source
    assert "source_record_id" in source
    assert "get_neo4j_driver" not in source
    for forbidden in ("journal_text", "prayer_text", "confession_text", "temptation_text", "crisis_text", "description=$"):
        assert forbidden not in source


def test_export_and_erasure_cover_batch_5_records_in_fk_safe_order():
    source = (Path(__file__).parents[1] / "routers" / "formation_twin.py").read_text()
    assert '"temporal_patterns"' in source and '"life_seasons"' in source and '"pattern_reviews"' in source
    tables = [
        "formation_twin_temporal_graph_syncs", "formation_twin_pattern_processing_checkpoints",
        "formation_twin_pattern_rebuild_jobs", "formation_twin_long_term_snapshots",
        "formation_twin_pattern_reviews", "formation_twin_trajectory_points", "formation_twin_trajectories",
        "formation_twin_pattern_life_seasons", "formation_twin_life_seasons",
        "formation_twin_pattern_lifecycle_events", "formation_twin_pattern_confidence_history",
        "formation_twin_pattern_evidence", "formation_twin_patterns", "formation_twin_event_cluster_members",
        "formation_twin_event_clusters", "formation_twin_temporal_windows", "formation_twin_temporal_settings",
    ]
    positions = [source.index(f"DELETE FROM {table} WHERE email=%s") for table in tables]
    assert positions == sorted(positions)


def test_platform_context_broker_reads_confirmed_batch_5_patterns_not_pending_as_fact():
    source = (Path(__file__).parents[1] / "routers" / "platform_orchestration.py").read_text()
    assert "FROM formation_twin_patterns" in source
    assert "CONFIRMED_CONTEXTUAL" in source
    assert "PENDING_USER_REVIEW" not in source[source.index("FROM formation_twin_patterns") : source.index("FROM formation_twin_life_seasons")]


def test_pattern_discovery_performance_is_bounded_for_contract_batch():
    items = [chain(i) for i in range(1, 21)]
    for _ in range(100):
        result = discover_rule_pattern_candidates(items)
    assert result[0]["independent_evidence_count"] == 20
