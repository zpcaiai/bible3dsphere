from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from platform_orchestration.arbitration import arbitrate_recommendations
from platform_orchestration.commands import validate_command
from platform_orchestration.context_broker import context_is_fresh, resolve_projection
from platform_orchestration.contracts import (
    Actor,
    AgentCapability,
    ContextRequest,
    RecommendationCandidate,
    UnifiedCommand,
    UnifiedEventEnvelope,
    assert_platform_safe,
    find_forbidden_fields,
)
from platform_orchestration.health import CircuitBreaker, integration_status
from platform_orchestration.data_quality import scan_platform_contracts
from platform_orchestration.notifications import coordinate_notifications
from platform_orchestration.observability import safe_trace_attributes
from platform_orchestration.orchestrator import run_workflow
from platform_orchestration.policy import decide_context_access
from platform_orchestration.registry import (
    AGENT_CAPABILITIES,
    EVENT_SCHEMAS,
    PLATFORM_EVENT_TYPES,
    PROJECTIONS,
    PURPOSE_POLICIES,
    SOURCE_OF_TRUTH,
)
from platform_orchestration.safety import safety_gate


pytestmark = pytest.mark.no_db
NOW = datetime(2026, 7, 17, tzinfo=timezone.utc)
ROOT = Path(__file__).parents[1]


def candidate(title: str = "两分钟反思", **changes) -> RecommendationCandidate:
    data = {
        "source_module": "platform_orchestrator", "recommendation_type": "REFLECTION",
        "title": title, "purpose": "GENERATE_UNIFIED_HOME", "target_module": "platform_orchestrator",
    }
    data.update(changes)
    return RecommendationCandidate(**data)


def context_request(**changes) -> ContextRequest:
    data = {"requester_module": "prayer", "purpose": "GENERATE_PRAYER_PROMPT", "requested_projection": "prayer_context_v1"}
    data.update(changes)
    return ContextRequest(**data)


def test_recursive_sensitive_field_scanner_blocks_platform_boundaries():
    payload = {"safe": [{"nested": {"full_prayer_text": "secret"}}]}
    assert find_forbidden_fields(payload) == ["payload.safe[0].nested.full_prayer_text"]
    with pytest.raises(ValueError):
        assert_platform_safe(payload)


@pytest.mark.parametrize("field", [
    "platform_spiritual_score", "unified_spiritual_health_score", "module_compliance_score",
    "agent_success_on_user_score", "obedience_score", "holiness_score", "salvation_probability", "spiritual_rank",
])
def test_prohibited_platform_scores_are_rejected(field):
    with pytest.raises(ValueError):
        assert_platform_safe({field: 1})


def test_event_envelope_rejects_raw_sensitive_text():
    base = dict(
        event_type="spiritual_planet.command_created", tenant_id="personal:user@example.com",
        subject_user_id="user@example.com", actor=Actor(actor_type="USER", actor_id="user@example.com"),
        producer="platform_orchestrator", occurred_at=NOW, trace_id="12345678", purpose_tags=["COMMAND"],
        schema_uri="spiritual-planet://events/spiritual_planet.command_created/1.0",
    )
    UnifiedEventEnvelope(**base, payload={"command_id": "safe"})
    with pytest.raises(ValidationError):
        UnifiedEventEnvelope(**base, payload={"crisis_narrative": "private"})


def test_every_platform_event_has_a_versioned_registration():
    assert set(PLATFORM_EVENT_TYPES) == set(EVENT_SCHEMAS)
    assert all(item["version"] == "1.0" for item in EVENT_SCHEMAS.values())
    assert all(item["schema_uri"].startswith("spiritual-planet://events/") for item in EVENT_SCHEMAS.values())


def test_event_timestamp_must_be_timezone_aware():
    with pytest.raises(ValidationError):
        UnifiedEventEnvelope(
            event_type="spiritual_planet.command_created", tenant_id="personal:user@example.com",
            subject_user_id="user@example.com", actor=Actor(actor_type="USER"), producer="platform_orchestrator",
            occurred_at=datetime(2026, 7, 17), trace_id="12345678", purpose_tags=["COMMAND"],
            schema_uri="spiritual-planet://events/spiritual_planet.command_created/1.0", payload={},
        )


def test_context_policy_is_default_deny_without_consent():
    decision = decide_context_access(context_request(), consent_active=False)
    assert decision.allowed is False
    assert "USER_CONSENT_REQUIRED" in decision.decision_reason_codes


def test_service_identity_does_not_bypass_user_consent():
    decision = decide_context_access(context_request(), consent_active=False, caller_authenticated=True)
    assert not decision.allowed


def test_unknown_purpose_and_projection_are_denied():
    decision = decide_context_access(context_request(purpose="UNKNOWN", requested_projection="everything"), consent_active=True)
    assert not decision.allowed
    assert {"PURPOSE_NOT_REGISTERED", "PROJECTION_NOT_REGISTERED"}.issubset(decision.decision_reason_codes)


def test_context_policy_applies_projection_and_consent_field_allowlists():
    request = context_request(requested_fields=["confirmed_emotional_context", "confirmed_fears", "not_allowed"])
    decision = decide_context_access(request, consent_active=True, consent_fields={"confirmed_emotional_context"})
    assert decision.allowed
    assert decision.allowed_fields == ["confirmed_emotional_context"]
    assert set(decision.denied_fields) == {"confirmed_fears", "not_allowed"}


def test_context_broker_separates_confirmed_and_pending_and_expires():
    request = context_request(requested_fields=["confirmed_emotional_context", "confirmed_fears"])
    decision = decide_context_access(request, consent_active=True, consent_fields=set(PROJECTIONS["prayer_context_v1"]["fields"]))
    response = resolve_projection(
        request, decision,
        confirmed_source={"confirmed_emotional_context": [{"reference_id": "a"}], "confirmed_fears": []},
        pending_source={"confirmed_fears": [{"reference_id": "pending"}]},
        source_references=[{"source_module": "formation_twin", "source_record_type": "formation_node", "source_record_id": "a", "statement_status": "CONFIRMED"}],
        consent_reference_ids=["consent-1"], now=NOW,
    )
    assert response.confirmed_context["confirmed_emotional_context"][0]["reference_id"] == "a"
    assert response.pending_context["confirmed_fears"][0]["reference_id"] == "pending"
    assert response.expires_at <= NOW + timedelta(minutes=5)
    assert context_is_fresh(response, now=NOW)
    assert not context_is_fresh(response, now=NOW + timedelta(hours=1))


def test_crisis_projection_never_contains_pending_context():
    request = ContextRequest(requester_module="crisis", purpose="ROUTE_CRISIS_CASE", requested_projection="crisis_routing_context_v1")
    decision = decide_context_access(request, consent_active=True, consent_fields=set(PROJECTIONS["crisis_routing_context_v1"]["fields"]))
    response = resolve_projection(request, decision, confirmed_source={"safety_level": "ELEVATED"}, pending_source={"safety_level": "IMMINENT"}, now=NOW)
    assert response.pending_context == {}
    assert "CRISIS_NARRATIVE_EXCLUDED" in response.limitations


def test_every_projection_is_versioned_minimum_and_short_lived():
    assert PROJECTIONS
    for item in PROJECTIONS.values():
        assert item["version"] == "1.0"
        assert len(item["fields"]) <= 8
        assert 30 <= item["ttl"] <= 900


def test_all_purposes_reference_registered_projection_and_requester():
    for policy in PURPOSE_POLICIES.values():
        assert policy["modules"]
        assert policy["projections"] <= set(PROJECTIONS)


def test_agent_roles_keep_analysis_proposal_and_execution_separate():
    assert AGENT_CAPABILITIES
    for agent in AGENT_CAPABILITIES:
        if agent.capability_type in {"ANALYZER", "RECOMMENDATION_GENERATOR"}:
            assert not agent.can_execute_commands
        if agent.capability_type == "COMMAND_EXECUTOR":
            assert agent.requires_user_confirmation
    with pytest.raises(ValidationError):
        AgentCapability(
            agent_id="bad", version="1", owner_module="bad", capability_type="ANALYZER",
            accepted_input_schemas=["x"], output_schema="y", allowed_purposes=[],
            allowed_context_projections=[], can_execute_commands=True,
        )


def test_arbitration_defaults_to_one_action_and_suppresses_rest():
    result = arbitrate_recommendations([candidate("A"), candidate("B", safety_priority=8)], now=NOW)
    assert result.selected_recommendation is not None
    assert len(result.suppressed_candidates) == 1
    assert result.suppressed_candidates[0].reason_code == "ONE_VISIBLE_ACTION_LIMIT"


def test_explicit_user_intent_wins_over_ordinary_automatic_candidate():
    automatic = candidate("自动建议", safety_priority=6)
    explicit = candidate("用户选择", safety_priority=7, explicit_user_intent=True)
    result = arbitrate_recommendations([automatic, explicit], now=NOW)
    assert result.selected_recommendation.id == explicit.id


def test_crisis_suppresses_ordinary_workflows():
    crisis = candidate("安全连接", source_module="crisis", safety_priority=1)
    ordinary = candidate("成长计划", safety_priority=7)
    result = arbitrate_recommendations([ordinary, crisis], safety_state="IMMINENT", now=NOW)
    assert result.selected_recommendation.id == crisis.id
    assert any(item.candidate_id == ordinary.id and item.reason_code == "CRISIS_OVERRIDE" for item in result.suppressed_candidates)


def test_pending_hypothesis_cannot_drive_action_or_command():
    pending = candidate(uses_pending_context=True)
    result = arbitrate_recommendations([pending], now=NOW)
    assert result.no_action_selected
    assert result.suppressed_candidates[0].reason_code == "PENDING_CONTEXT_CANNOT_DRIVE_COMMAND"


def test_low_capacity_reduces_burden_and_duration():
    result = arbitrate_recommendations([candidate("十五分钟祷告", recommendation_type="PRAYER", estimated_duration_minutes=15, burden_level="MEDIUM", capacity_mode="VERY_LOW")], now=NOW)
    selected = result.selected_recommendation
    assert selected.estimated_duration_minutes <= 2
    assert selected.burden_level == "VERY_LOW"
    assert "或今天不增加行动" in selected.title


def test_duplicate_human_connection_candidates_are_merged():
    first = candidate("联系守望伙伴", source_module="formation_engine")
    second = candidate("联系可信任真人", source_module="crisis")
    result = arbitrate_recommendations([first, second], now=NOW)
    assert len(result.merged_candidates) == 1
    assert sum(item.reason_code == "MERGED_DUPLICATE" for item in result.suppressed_candidates) == 1


def test_active_action_limit_selects_no_new_action():
    result = arbitrate_recommendations([candidate()], active_action_count=3, now=NOW)
    assert result.no_action_selected
    assert "ACTIVE_ACTION_LIMIT" in result.selection_rationale


def test_safety_gate_has_global_crisis_authority():
    blocked = safety_gate("ELEVATED", "CALLING_PLAN")
    assert not blocked.allowed and blocked.route == "crisis"
    assert safety_gate("ELEVATED", "HUMAN_CONNECTION").allowed
    assert safety_gate("NONE", "CALLING_PLAN").allowed


def test_commands_require_confirmation_consent_expiry_and_allowlist():
    command = UnifiedCommand(
        command_type="CREATE_UNIFIED_ACTION", target_module="platform_orchestrator",
        payload={"title": "小行动", "duration_minutes": 2}, payload_schema="command@1",
        user_confirmation_reference_id=uuid.uuid4(), purpose="GENERATE_UNIFIED_HOME",
        idempotency_key="abcdefgh", expires_at=NOW + timedelta(minutes=5),
    )
    assert validate_command(command, confirmation_active=True, consent_active=True, now=NOW) == []
    assert "USER_CONFIRMATION_REQUIRED" in validate_command(command, confirmation_active=False, consent_active=True, now=NOW)
    assert "CONSENT_REQUIRED" in validate_command(command, confirmation_active=True, consent_active=False, now=NOW)
    assert "COMMAND_EXPIRED" in validate_command(command, confirmation_active=True, consent_active=True, now=NOW + timedelta(hours=1))
    bad = command.model_copy(update={"payload": {"title": "x", "full_journal": "secret"}})
    assert "PAYLOAD_FIELDS_NOT_ALLOWED" in validate_command(bad, confirmation_active=True, consent_active=True, now=NOW)


def test_notification_coordinator_redacts_sensitive_and_batches_ordinary():
    sensitive = coordinate_notifications([{"source_module": "prayer", "notification_type": "reminder", "urgency": "TODAY", "sensitivity": "HIGHLY_SENSITIVE", "title": "private", "body": "private"}])
    assert sensitive["title"] == "有一项可选提醒"
    assert sensitive["body"] == "打开应用查看详情。"
    batched = coordinate_notifications([
        {"source_module": "prayer", "notification_type": "prayer", "urgency": "TODAY", "sensitivity": "SENSITIVE"},
        {"source_module": "attention", "notification_type": "boundary", "urgency": "TODAY", "sensitivity": "SENSITIVE"},
    ])
    assert "ORDINARY_NOTIFICATIONS_BATCHED" in batched["reason_codes"]


def test_crisis_notification_preempts_quiet_hours_without_sensitive_body():
    result = coordinate_notifications([{"source_module": "crisis", "notification_type": "safety", "urgency": "IMMEDIATE", "sensitivity": "HIGHLY_SENSITIVE", "title": "secret", "body": "secret"}], quiet_hours=True)
    assert result["deliver"]
    assert result["source_modules"] == ["crisis"]
    assert "secret" not in json.dumps(result)


def test_circuit_breaker_degrades_and_recovers_without_user_labels():
    breaker = CircuitBreaker(failure_threshold=2, recovery_seconds=60)
    breaker.record_failure(now=NOW)
    assert breaker.state(now=NOW) == "CLOSED"
    breaker.record_failure(now=NOW)
    assert breaker.state(now=NOW) == "OPEN"
    assert breaker.state(now=NOW + timedelta(seconds=61)) == "HALF_OPEN"
    breaker.record_success()
    assert breaker.state(now=NOW) == "CLOSED"
    assert integration_status(registered=True, feature_enabled=True, adapter_available=False)[0] == "DEGRADED"


def test_observability_attributes_are_allowlisted_and_reject_user_labels():
    assert safe_trace_attributes({"module": "prayer", "workflow": "home", "result": "ok", "ignored": "x"}) == {"module": "prayer", "workflow": "home", "result": "ok"}
    with pytest.raises(ValueError):
        safe_trace_attributes({"module": "prayer", "search_query": "private"})


def test_platform_contract_data_quality_has_no_high_severity_issue():
    report = scan_platform_contracts()
    assert report["ok"]
    assert report["high_severity_count"] == 0


def test_orchestrator_is_bounded_and_uses_no_model_calls_for_deterministic_flow():
    from platform_orchestration.contracts import OrchestrationRequest
    request = OrchestrationRequest(trigger_type="USER_REQUEST", user_intent="a small reflection", candidate_recommendations=[candidate(explicit_user_intent=True)])
    result = run_workflow(request)
    assert result["status"] == "COMPLETED"
    assert result["model_calls_used"] == 0
    assert len(result["steps"]) <= request.max_nodes


def test_orchestrator_stops_ordinary_work_on_crisis():
    from platform_orchestration.contracts import OrchestrationRequest
    request = OrchestrationRequest(trigger_type="CRISIS_STATE_CHANGED", safety_state="IMMINENT", candidate_recommendations=[candidate()])
    result = run_workflow(request)
    assert result["status"] == "STOPPED_FOR_SAFETY"
    assert "ROUTE_TO_CRISIS_AUTHORITY" in result["steps"]


def test_source_of_truth_matrix_covers_required_modules_and_keeps_twin_bounded():
    required = {"identity", "worldview", "formation_twin", "formation_engine", "prayer", "devotion", "holy_habit", "attention", "crisis", "gift_calling", "church", "mission", "bible_kg", "notification", "search", "audit"}
    assert required <= set(SOURCE_OF_TRUTH)
    assert "normalized life events" in SOURCE_OF_TRUTH["formation_twin"]["canonical"]
    assert "identity" not in SOURCE_OF_TRUTH["formation_twin"]["canonical"]


def test_migration_has_required_tables_rls_tenant_and_no_spiritual_scores():
    sql = (ROOT / "migrations" / "0215_spiritual_planet_platform_orchestration.sql").read_text()
    required = {
        "spiritual_planet_event_schemas", "spiritual_planet_context_projections",
        "spiritual_planet_context_access_audit", "spiritual_planet_agent_capabilities",
        "spiritual_planet_orchestration_runs", "spiritual_planet_recommendation_candidates",
        "spiritual_planet_arbitration_results", "spiritual_planet_unified_commands",
        "spiritual_planet_command_results", "spiritual_planet_deletion_manifests",
        "spiritual_planet_deletion_acknowledgements", "spiritual_planet_rebuild_jobs",
        "spiritual_planet_integration_health", "spiritual_planet_unified_actions",
    }
    assert all(f"CREATE TABLE IF NOT EXISTS {table}" in sql for table in required)
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "app.current_user_email" in sql
    assert "tenant_id TEXT NOT NULL" in sql
    lowered = sql.lower()
    for field in ("platform_spiritual_score", "unified_spiritual_health_score", "obedience_score", "holiness_score", "salvation_probability", "spiritual_rank"):
        assert field not in lowered


def test_migration_and_router_do_not_define_raw_sensitive_platform_columns():
    text = ((ROOT / "migrations" / "0215_spiritual_planet_platform_orchestration.sql").read_text() + (ROOT / "routers" / "platform_orchestration.py").read_text()).lower()
    for field in ("full_journal text", "full_prayer text", "crisis_narrative text", "model_prompt text", "confession_text text"):
        assert field not in text


def test_router_exposes_required_batch_9_contracts():
    from routers.platform_orchestration import router
    routes = {(method, route.path) for route in router.routes for method in route.methods}
    required = {
        ("POST", "/api/v1/platform/context/resolve"), ("GET", "/api/v1/platform/context/access-log"),
        ("POST", "/api/v1/platform/orchestrations/run"), ("GET", "/api/v1/platform/orchestrations/{run_id}"),
        ("POST", "/api/v1/platform/orchestrations/{run_id}/cancel"),
        ("GET", "/api/v1/platform/recommendations/current"), ("GET", "/api/v1/platform/recommendations/{recommendation_id}"),
        ("POST", "/api/v1/platform/recommendations/{recommendation_id}/accept"),
        ("POST", "/api/v1/platform/recommendations/{recommendation_id}/modify"),
        ("POST", "/api/v1/platform/recommendations/{recommendation_id}/smaller"),
        ("POST", "/api/v1/platform/recommendations/{recommendation_id}/alternative"),
        ("POST", "/api/v1/platform/recommendations/{recommendation_id}/skip"),
        ("POST", "/api/v1/platform/recommendations/{recommendation_id}/reject"),
        ("GET", "/api/v1/platform/actions"), ("GET", "/api/v1/platform/actions/current"),
        ("POST", "/api/v1/platform/actions/{action_id}/start"), ("POST", "/api/v1/platform/actions/{action_id}/complete"),
        ("POST", "/api/v1/platform/actions/{action_id}/skip"), ("POST", "/api/v1/platform/actions/{action_id}/cancel"),
        ("GET", "/api/v1/platform/timeline"), ("GET", "/api/v1/platform/search"),
        ("POST", "/api/v1/platform/deletions"), ("GET", "/api/v1/platform/deletions/{deletion_id}"),
        ("POST", "/api/v1/platform/deletions/{deletion_id}/retry"),
        ("POST", "/api/v1/platform/rebuilds"), ("GET", "/api/v1/platform/rebuilds/{rebuild_id}"),
        ("POST", "/api/v1/platform/rebuilds/{rebuild_id}/cancel"),
        ("GET", "/api/v1/platform/integrations/health"), ("GET", "/api/v1/platform/integrations/health/{module}"),
        ("GET", "/api/v1/platform/agents"), ("GET", "/api/v1/platform/agents/{agent_id}"),
        ("GET", "/api/v1/platform/data-quality"),
    }
    assert required <= routes


def test_main_wires_platform_router_once():
    text = (ROOT / "main.py").read_text()
    assert text.count("app.include_router(platform_orchestration_router)") == 1
    assert "init_platform_orchestration_router(" in text


def test_arbitration_performance_is_bounded_for_maximum_contract_batch():
    items = [candidate(f"候选 {index}", dedupe_key=f"k-{index}") for index in range(20)]
    started = time.perf_counter()
    for _ in range(100):
        arbitrate_recommendations(items, now=NOW)
    assert time.perf_counter() - started < 1.0
