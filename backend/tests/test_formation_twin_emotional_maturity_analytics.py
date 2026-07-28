from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from formation_twin.emotional_maturity import UnsafeContentError
from formation_twin.emotional_maturity_analytics import (
    FORBIDDEN_REPORT_PHRASES,
    GENERALIZATION_LEVELS,
    REPORT_VIEWS,
    VERSIONED_COMPONENTS,
    WORKFLOW_NODES,
    MetricDefinition,
    analyze_generalization,
    analyze_trajectory,
    calibrate_attribution,
    compose_reassessment,
    describe_analytics_engine,
    publish_growth_report,
    reconcile_comparability,
    register_metric,
    validate_report_text,
)


pytestmark = pytest.mark.no_db
NOW = datetime(2026, 7, 28, 12, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[2]


def metric(**updates) -> MetricDefinition:
    values = {
        "metric_code": "pause_success_rate",
        "display_name": "现实暂停成功率",
        "domain": "BEHAVIOR",
        "description": "出现明确冲动机会时，用户在实际行动前成功插入暂停的比例。",
        "unit": "RATE",
        "numerator_definition": "发生暂停且没有立即执行原冲动行为的事件数",
        "denominator_definition": "出现明确冲动行为机会的现实事件数",
        "eligible_evidence_types": ["REAL_LIFE_EVENT", "TIMELINE_CONFIRMED"],
    }
    values.update(updates)
    return MetricDefinition(**values)


# ── EM-71 metric catalog ─────────────────────────────────────────────────────

def test_rate_metrics_must_define_numerator_and_denominator():
    with pytest.raises(ValueError):
        metric(numerator_definition="", denominator_definition="")


def test_a_metric_must_declare_its_eligible_evidence_types():
    with pytest.raises(ValueError):
        metric(eligible_evidence_types=[])


def test_frozen_metrics_cannot_be_redefined_in_place():
    frozen = metric(status="FROZEN")
    catalog = {(frozen.metric_code, frozen.version): frozen}
    result = register_metric(metric(numerator_definition="用户点击暂停按钮的次数"), catalog=catalog)
    assert result["status"] == "REJECTED"
    assert "FROZEN_METRIC_REDEFINED" in result["errors"]
    assert "必须发新版本号" in result["fix"]


def test_the_same_metric_name_cannot_change_unit_across_versions():
    first = metric(status="ACTIVE")
    catalog = {(first.metric_code, first.version): first}
    result = register_metric(
        metric(version="v2", unit="COUNT", numerator_definition="n", denominator_definition="d"),
        catalog=catalog,
    )
    assert "UNIT_CONFLICT_ACROSS_VERSIONS" in result["errors"]


def test_metric_names_may_not_contain_score_language():
    # pydantic wraps the guard in a ValidationError, which is a ValueError subclass
    with pytest.raises(ValueError):
        metric(display_name="综合生命指数")
    with pytest.raises(UnsafeContentError):
        validate_report_text("综合生命指数")


# ── EM-72 reassessment composition ───────────────────────────────────────────

def test_reassessment_reuses_baseline_items_and_skips_declined_ones():
    result = compose_reassessment(
        day=30,
        baseline_item_ids=["D2-SR-001", "D2-BE-001", "D9-SF-001"],
        priority_dimensions=["D2", "D9"],
        skipped_last_time=["D9-SF-001"],
    )
    assert "D9-SF-001" not in result["selected_items"]
    assert result["excluded_previously_skipped"] == ["D9-SF-001"]
    assert "跳过任何一题都不会影响你的阶段" in result["skipping_is_free"]


def test_fatigue_halves_the_reassessment_budget():
    items = [f"item-{index}" for index in range(20)]
    calm = compose_reassessment(day=30, baseline_item_ids=items, priority_dimensions=["D2"])
    tired = compose_reassessment(day=30, baseline_item_ids=items, priority_dimensions=["D2"], fatigue=0.8)
    assert len(tired["selected_items"]) < len(calm["selected_items"])


def test_only_same_version_items_are_used_for_comparison():
    result = compose_reassessment(day=14, baseline_item_ids=["a"], priority_dimensions=["D2"])
    assert "只有与基线同版本的题目才用于比较" in result["comparability_rule"]


def test_unknown_checkpoint_day_is_rejected():
    with pytest.raises(ValueError):
        compose_reassessment(day=45, baseline_item_ids=[], priority_dimensions=[])


# ── EM-73 comparability ──────────────────────────────────────────────────────

def test_rubric_version_change_makes_results_incomparable():
    result = reconcile_comparability(
        baseline={"rubric_bundle_version": "v1"},
        current={"rubric_bundle_version": "v2"},
        stage_change=2,
    )
    assert result["comparable"] is False
    assert result["verdict"] == "NOT_COMPARABLE"
    assert result["recompute_required"] is True


def test_change_smaller_than_measurement_error_is_not_confirmed():
    result = reconcile_comparability(baseline={}, current={}, stage_change=0)
    assert result["verdict"] == "CHANGE_NOT_CONFIRMED"
    assert "无法确认" in result["user_statement"]


def test_same_versions_and_large_change_is_comparable():
    result = reconcile_comparability(baseline={}, current={}, stage_change=2)
    assert result["verdict"] == "COMPARABLE_CHANGE"
    assert result["next_action"] == "ANALYSE_TRAJECTORY"


def test_all_versioned_components_are_checked():
    for component in VERSIONED_COMPONENTS:
        result = reconcile_comparability(
            baseline={component: "a"}, current={component: "b"}, stage_change=3,
        )
        assert result["changed_components"] == [component]


# ── EM-74 trajectory ─────────────────────────────────────────────────────────

def points(values: list[float]) -> list[dict]:
    return [
        {"at": NOW - timedelta(days=len(values) * 5 - index * 5), "value": value}
        for index, value in enumerate(values)
    ]


def test_trend_needs_at_least_three_points():
    result = analyze_trajectory(domain="RECOVERY", points=points([7200, 5400]))
    assert result["status"] == "INSUFFICIENT_POINTS"
    assert "不代表没有变化" in result["note"]


def test_shorter_recovery_time_reads_as_improving():
    result = analyze_trajectory(domain="RECOVERY", points=points([7200, 5400, 1800, 900]))
    assert result["direction"] == "IMPROVING"


def test_change_points_carry_no_causal_claim():
    result = analyze_trajectory(domain="RECOVERY", points=points([7200, 7000, 1200, 1100]))
    assert result["change_point"]["causal_claim"] is False
    assert "不说明原因" in result["no_causal_claim"]


def test_higher_is_better_metrics_are_supported():
    result = analyze_trajectory(
        domain="REPAIR", points=points([1, 1, 3, 4]), lower_is_better=False,
    )
    assert result["direction"] == "IMPROVING"


def test_unknown_metric_domain_is_rejected():
    with pytest.raises(ValueError):
        analyze_trajectory(domain="VIBES", points=points([1, 2, 3]))


# ── EM-75 generalization ─────────────────────────────────────────────────────

def test_single_context_stays_at_g1():
    result = analyze_generalization(observations=[{"context": "family"}])
    assert result["level"] == "G1"


def test_two_contexts_with_pressure_reach_g3():
    result = analyze_generalization(observations=[
        {"context": "family", "high_pressure": True}, {"context": "workplace"},
    ])
    assert result["level"] == "G3"


def test_longitudinal_repetition_reaches_g4():
    result = analyze_generalization(
        observations=[
            {"context": "family", "high_pressure": True},
            {"context": "workplace"},
            {"context": "church_service"},
        ],
        longitudinal_days=40,
    )
    assert result["level"] == "G4"
    assert set(GENERALIZATION_LEVELS) == {"G0", "G1", "G2", "G3", "G4"}


def test_contexts_are_reported_separately_not_averaged():
    result = analyze_generalization(observations=[{"context": "family"}, {"context": "workplace"}])
    assert set(result["per_context"]) == {"family", "workplace"}
    assert "不合并为一个平均值" in result["not_averaged"]


# ── EM-76 attribution and regression ─────────────────────────────────────────

def test_attribution_is_always_correlation_only():
    result = calibrate_attribution(observed_change="恢复时间变短", comparable_event_count=3)
    assert result["attribution_claim"] == "CORRELATION_ONLY"
    assert result["causal_claim"] is False
    assert any("触发机会" in note for note in result["alternative_explanations"])


def test_concurrent_support_is_listed_as_an_alternative_explanation():
    result = calibrate_attribution(observed_change="情绪更稳定", comparable_event_count=2)
    assert any("咨询" in note or "药物" in note for note in result["alternative_explanations"])


def test_limited_evidence_is_marked_when_events_are_few():
    result = calibrate_attribution(observed_change="修复变快", comparable_event_count=1)
    assert result["evidence_sufficiency"] == "LIMITED"


def test_safety_signals_escalate_immediately():
    result = calibrate_attribution(
        observed_change="恢复变慢", regression_signals=["SAFETY_SIGNAL"], comparable_event_count=3,
    )
    assert result["regression_severity"] == "SAFETY_FIRST"
    assert result["next_action"] == "ROUTE_TO_SAFETY_SUPPORT"


def test_two_regression_signals_raise_severity():
    result = calibrate_attribution(
        observed_change="退步", regression_signals=["RECOVERY_SLOWING", "REPAIR_STOPPED"],
        comparable_event_count=3,
    )
    assert result["regression_severity"] == "ELEVATED"


def test_unknown_regression_signal_is_rejected():
    with pytest.raises(ValueError):
        calibrate_attribution(observed_change="x", regression_signals=["BAD_VIBES"])


# ── EM-77 growth report ──────────────────────────────────────────────────────

def test_report_never_contains_a_score_or_ranking():
    result = publish_growth_report(view="PRIVATE", sections={"WHAT_CHANGED": "你连续两次先离开十分钟"})
    assert result["total_score"] is None
    assert result["ranking"] is None
    with pytest.raises(UnsafeContentError):
        publish_growth_report(view="PRIVATE", sections={"WHAT_CHANGED": "情感成熟度：78 分"})
    with pytest.raises(UnsafeContentError):
        validate_report_text("你排名前 20%")


def test_report_requires_user_approval_before_publishing():
    draft = publish_growth_report(view="PRIVATE", sections={"WHAT_CHANGED": "x"})
    assert draft["status"] == "DRAFT_AWAITING_USER_APPROVAL"
    published = publish_growth_report(view="PRIVATE", sections={"WHAT_CHANGED": "x"}, approved_by_user=True)
    assert published["status"] == "PUBLISHED"
    assert published["auto_shared"] is False


def test_pastoral_and_group_views_require_sharing_consent():
    blocked = publish_growth_report(view="PASTORAL", sections={"WHAT_CHANGED": "x"})
    assert blocked["status"] == "BLOCKED_NO_CONSENT"
    allowed = publish_growth_report(
        view="PASTORAL", sections={"WHAT_CHANGED": "x"},
        consented_scopes=["EMD_PASTORAL_SHARE"], approved_by_user=True,
    )
    assert allowed["status"] == "PUBLISHED"
    assert allowed["revocable"] is True
    assert allowed["expires_in_days"] == 30


def test_shared_views_only_include_selected_fields():
    result = publish_growth_report(
        view="GROUP",
        sections={"WHAT_YOU_PRACTISED": "每天一次暂停", "WHAT_CHANGED": "冲突后更快澄清"},
        consented_scopes=["EMD_PASTORAL_SHARE"],
        selected_fields=["WHAT_YOU_PRACTISED"],
        approved_by_user=True,
    )
    contents = {item["code"]: item["content"] for item in result["sections"]}
    assert contents["WHAT_YOU_PRACTISED"]
    assert contents["WHAT_CHANGED"] is None


def test_report_always_has_room_for_no_change_and_unknowns():
    result = publish_growth_report(view="PRIVATE", sections={})
    codes = [item["code"] for item in result["sections"]]
    assert "WHAT_DID_NOT_CHANGE" in codes
    assert "STILL_UNKNOWN" in codes
    assert any("没有变化和仍然未知都要写出来" in rule for rule in result["language_rules"])


def test_charts_avoid_false_precision():
    result = publish_growth_report(view="PRIVATE", sections={})
    codes = {item["code"] for item in result["recommended_charts"]}
    assert "CONFIDENCE_BANDS" in codes
    assert "RECOVERY_TIME_BUCKETS" in codes


def test_unknown_view_or_section_is_rejected():
    with pytest.raises(ValueError):
        publish_growth_report(view="PUBLIC", sections={})
    with pytest.raises(ValueError):
        publish_growth_report(view="PRIVATE", sections={"RANDOM": "x"})


# ── module description and wiring ────────────────────────────────────────────

def test_module_description_declares_the_three_planes():
    described = describe_analytics_engine()
    assert len(described["skills"]) == len(WORKFLOW_NODES) == 7
    assert set(described["planes"]) == {"measurement", "analytics", "reporting"}
    assert set(described["report_views"]) == set(REPORT_VIEWS)
    refusals = " ".join(described["does_not"])
    assert "不生成单一总分" in refusals
    assert "不对趋势作因果断言" in refusals
    assert set(FORBIDDEN_REPORT_PHRASES) <= set(described["forbidden_report_phrases"])


def test_router_exposes_the_batch_nine_surface():
    from routers.formation_twin_emotional_maturity import router

    paths = {route.path for route in router.routes}
    for suffix in (
        "analytics/overview", "analytics/metrics", "analytics/reassessment",
        "analytics/comparability", "analytics/trajectory", "analytics/generalization",
        "analytics/attribution", "analytics/report",
    ):
        assert f"/api/v1/formation-twin/emotional-maturity/{suffix}" in paths


def test_migration_file_exists_for_batch_nine():
    migration = ROOT / "backend/migrations/0231_formation_twin_emd_analytics.sql"
    rollback = ROOT / "backend/migrations/rollback/0231_formation_twin_emd_analytics_down.sql"
    assert migration.exists() and rollback.exists()
    sql = migration.read_text(encoding="utf-8")
    assert "formation_twin_emd_metric_catalog" in sql
    assert "formation_twin_emd_growth_reports" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql


def test_erasure_covers_every_batch_nine_table():
    """The erase list moved into `emotional_maturity_erasure` so the deletion-propagation
    suite can re-derive it from the migrations; assert against that list directly."""
    from formation_twin.emotional_maturity_erasure import EMD_PERSONAL_TABLES

    for table in (
        "formation_twin_emd_metric_observations", "formation_twin_emd_reassessment_compositions",
        "formation_twin_emd_comparability_checks", "formation_twin_emd_trajectories",
        "formation_twin_emd_generalizations", "formation_twin_emd_attributions",
        "formation_twin_emd_growth_reports",
    ):
        assert table in EMD_PERSONAL_TABLES
