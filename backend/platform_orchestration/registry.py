"""Static default registries. Database copies are auditable runtime records."""
from __future__ import annotations

from typing import Any

from .contracts import AgentCapability


PLATFORM_EVENT_TYPES = (
    "spiritual_planet.context_projection_created",
    "spiritual_planet.context_access_denied",
    "spiritual_planet.orchestration_started",
    "spiritual_planet.orchestration_completed",
    "spiritual_planet.orchestration_failed",
    "spiritual_planet.recommendation_candidates_created",
    "spiritual_planet.recommendation_selected",
    "spiritual_planet.recommendation_suppressed",
    "spiritual_planet.command_created",
    "spiritual_planet.command_executed",
    "spiritual_planet.command_failed",
    "spiritual_planet.command_expired",
    "spiritual_planet.consent_propagation_started",
    "spiritual_planet.consent_propagation_completed",
    "spiritual_planet.consent_propagation_failed",
    "spiritual_planet.deletion_manifest_created",
    "spiritual_planet.deletion_propagation_completed",
    "spiritual_planet.deletion_propagation_failed",
    "spiritual_planet.rebuild_started",
    "spiritual_planet.rebuild_completed",
    "spiritual_planet.rebuild_failed",
    "spiritual_planet.integration_degraded",
    "spiritual_planet.integration_recovered",
    "spiritual_planet.contract_violation_detected",
    "formation_twin.scenario_created",
    "formation_twin.scenario_generated",
    "formation_twin.scenario_invalidated",
    "formation_twin.scenario_converted_to_proposal",
    "governance.evaluation_dataset_registered",
    "governance.evaluation_run_completed",
    "governance.evaluation_run_failed",
    "governance.component_version_registered",
    "governance.component_version_activated",
    "governance.component_version_deprecated",
    "governance.component_version_rolled_back",
    "governance.release_candidate_created",
    "governance.release_gate_passed",
    "governance.canary_started",
    "governance.canary_paused",
    "governance.release_expanded",
    "governance.release_rolled_back",
    "governance.kill_switch_activated",
    "governance.kill_switch_deactivated",
    "governance.data_quality_issue_resolved",
    "governance.incident_created",
    "governance.incident_contained",
    "governance.incident_resolved",
    "governance.postmortem_published",
    "compliance.rights_request_created",
    "compliance.processing_restricted",
)

EVENT_SCHEMAS: dict[str, dict[str, Any]] = {
    event_type: {
        "event_type": event_type,
        "version": "1.0",
        "producer": "platform_orchestrator",
        "compatibility": "BACKWARD_COMPATIBLE",
        "schema_uri": f"spiritual-planet://events/{event_type}/1.0",
        "allowed_payload_fields": [
            "context_id", "projection_name", "requester_module", "purpose", "reason_codes",
            "run_id", "status", "candidate_ids", "selected_candidate_id", "suppressed_candidate_ids",
            "command_id", "target_module", "target_record_id", "deletion_id", "rebuild_id", "module",
            "schema_version", "action", "result_code",
            "scenario_id", "proposal_id", "engine_version", "dataset_id", "version",
            "component_id", "actor_id", "release_id", "kill_switch_id", "reason_code",
            "issue_id", "incident_id", "severity", "request_id", "request_type",
        ],
        "deprecated": False,
    }
    for event_type in PLATFORM_EVENT_TYPES
}


SOURCE_OF_TRUTH = {
    "identity": {"owner": "Identity OS", "canonical": "identity, account and tenant membership", "projection": None},
    "worldview": {"owner": "Worldview Formation OS", "canonical": "user-authored worldview records", "projection": "formation_context_v1"},
    "formation_twin": {"owner": "Formation Twin", "canonical": "normalized life events and reviewable derived state", "projection": "formation_context_v1"},
    "formation_engine": {"owner": "Formation Engine", "canonical": "formation practices and target outcomes", "projection": "formation_context_v1"},
    "prayer": {"owner": "Prayer OS", "canonical": "prayer records and prayer actions", "projection": "prayer_context_v1"},
    "devotion": {"owner": "Devotion System", "canonical": "devotion sessions and reading progress", "projection": "devotion_context_v1"},
    "holy_habit": {"owner": "Holy Habit Engine", "canonical": "habit definitions and occurrences", "projection": "habit_context_v1"},
    "attention": {"owner": "Attention OS", "canonical": "attention boundaries and observations", "projection": "attention_context_v1"},
    "crisis": {"owner": "Crisis and Healing System", "canonical": "crisis cases, safety plans and risk routing", "projection": "crisis_routing_context_v1"},
    "gift_calling": {"owner": "Gift and Calling OS", "canonical": "confirmed gifts and calling reflections", "projection": "calling_context_v1"},
    "church": {"owner": "Church Health OS", "canonical": "user-authorized church participation records", "projection": "church_context_v1"},
    "mission": {"owner": "Mission System", "canonical": "mission preparation and deployment records", "projection": "mission_context_v1"},
    "bible_kg": {"owner": "Bible Knowledge Graph", "canonical": "scripture entities and references", "projection": "scripture_context_v1"},
    "notification": {"owner": "Notification System", "canonical": "delivery preferences and delivery records", "projection": None},
    "search": {"owner": "Search System", "canonical": "revocable source references only", "projection": None},
    "audit": {"owner": "Audit System", "canonical": "metadata-only access and operation audit", "projection": None},
}


PROJECTIONS: dict[str, dict[str, Any]] = {
    "prayer_context_v1": {"version": "1.0", "source_module": "formation_twin", "fields": ["user_selected_prayer_needs", "confirmed_emotional_context", "confirmed_fears", "grace_factors", "selected_scripture_themes"], "ttl": 300},
    "habit_context_v1": {"version": "1.0", "source_module": "formation_twin", "fields": ["user_selected_goal", "capacity_mode", "preferred_duration_minutes", "blocked_intervention_types", "confirmed_alternative_response"], "ttl": 300},
    "attention_context_v1": {"version": "1.0", "source_module": "formation_twin", "fields": ["user_confirmed_attention_pattern", "preferred_boundary_type", "risk_time_window", "sensitive_reason_included"], "ttl": 180},
    "calling_context_v1": {"version": "1.0", "source_module": "formation_twin", "fields": ["active_life_seasons", "user_confirmed_gifts", "service_experience", "capacity_constraints", "unresolved_calling_questions"], "ttl": 300},
    "church_context_v1": {"version": "1.0", "source_module": "formation_twin", "fields": ["participation_goals", "relationship_support_needs", "pastoral_conversation_questions", "church_experience_summaries"], "ttl": 180},
    "mission_context_v1": {"version": "1.0", "source_module": "formation_twin", "fields": ["confirmed_calling_directions", "equipping_progress", "language_culture_preparation", "family_health_readiness", "user_shared_constraints"], "ttl": 300},
    "formation_context_v1": {"version": "1.0", "source_module": "formation_twin", "fields": ["confirmed_patterns", "confirmed_practices", "capacity_mode", "grace_factors", "limitations"], "ttl": 300},
    "devotion_context_v1": {"version": "1.0", "source_module": "formation_twin", "fields": ["selected_scripture_themes", "preferred_duration_minutes", "capacity_mode", "grace_factors"], "ttl": 300},
    "scripture_context_v1": {"version": "1.0", "source_module": "bible_kg", "fields": ["selected_scripture_themes", "scripture_references"], "ttl": 900},
    "unified_home_context_v1": {"version": "1.0", "source_module": "platform_orchestrator", "fields": ["today_report", "capacity_mode", "safety_summary", "confirmed_theme", "grace_factors", "active_action_references"], "ttl": 120},
    "unified_timeline_context_v1": {"version": "1.0", "source_module": "platform_orchestrator", "fields": ["timeline_references"], "ttl": 120},
    "unified_search_context_v1": {"version": "1.0", "source_module": "platform_orchestrator", "fields": ["confirmed_search_references"], "ttl": 120},
    "crisis_routing_context_v1": {"version": "1.0", "source_module": "crisis", "fields": ["safety_level", "safety_plan_available", "human_connection_available", "professional_support_route"], "ttl": 60},
}


PURPOSE_POLICIES = {
    "GENERATE_PRAYER_PROMPT": {"modules": {"prayer"}, "projections": {"prayer_context_v1"}},
    "CREATE_FORMATION_PRACTICE": {"modules": {"formation_engine", "formation_twin"}, "projections": {"formation_context_v1", "habit_context_v1"}},
    "CREATE_ATTENTION_BOUNDARY": {"modules": {"attention"}, "projections": {"attention_context_v1"}},
    "PREPARE_CALLING_REFLECTION": {"modules": {"gift_calling"}, "projections": {"calling_context_v1"}},
    "PREPARE_PASTORAL_BRIEF": {"modules": {"church"}, "projections": {"church_context_v1"}},
    "PREPARE_MISSION_REFLECTION": {"modules": {"mission"}, "projections": {"mission_context_v1"}},
    "GENERATE_DEVOTION_PROMPT": {"modules": {"devotion"}, "projections": {"devotion_context_v1"}},
    "GENERATE_UNIFIED_HOME": {"modules": {"platform_orchestrator"}, "projections": {"unified_home_context_v1"}},
    "GENERATE_UNIFIED_TIMELINE": {"modules": {"platform_orchestrator"}, "projections": {"unified_timeline_context_v1"}},
    "SEARCH_CONFIRMED_USER_DATA": {"modules": {"platform_orchestrator"}, "projections": {"unified_search_context_v1"}},
    "GENERATE_WEEKLY_REVIEW": {"modules": {"formation_twin"}, "projections": {"formation_context_v1"}},
    "ROUTE_CRISIS_CASE": {"modules": {"crisis"}, "projections": {"crisis_routing_context_v1"}},
}


AGENT_CAPABILITIES = [
    AgentCapability(agent_id="platform.context-provider", version="1.0", owner_module="platform_orchestrator", capability_type="CONTEXT_PROVIDER", accepted_input_schemas=["ContextRequest@1"], output_schema="ContextResponse@1", allowed_purposes=list(PURPOSE_POLICIES), allowed_context_projections=list(PROJECTIONS), requires_user_confirmation=False),
    AgentCapability(agent_id="platform.safety-gate", version="1.0", owner_module="crisis", capability_type="SAFETY_CLASSIFIER", accepted_input_schemas=["SafetyGateRequest@1"], output_schema="SafetyDecision@1", allowed_purposes=["ROUTE_CRISIS_CASE", "GENERATE_UNIFIED_HOME"], allowed_context_projections=["crisis_routing_context_v1"], requires_user_confirmation=False),
    AgentCapability(agent_id="platform.recommendation-arbitrator", version="1.0", owner_module="platform_orchestrator", capability_type="ANALYZER", accepted_input_schemas=["RecommendationCandidate@1"], output_schema="RecommendationArbitrationResult@1", allowed_purposes=list(PURPOSE_POLICIES), allowed_context_projections=list(PROJECTIONS), requires_user_confirmation=False),
    AgentCapability(agent_id="formation.recommendation-generator", version="1.0", owner_module="formation_engine", capability_type="RECOMMENDATION_GENERATOR", accepted_input_schemas=["formation_context_v1"], output_schema="RecommendationCandidate@1", allowed_purposes=["CREATE_FORMATION_PRACTICE"], allowed_context_projections=["formation_context_v1"], can_create_proposals=True),
    AgentCapability(agent_id="prayer.recommendation-generator", version="1.0", owner_module="prayer", capability_type="RECOMMENDATION_GENERATOR", accepted_input_schemas=["prayer_context_v1"], output_schema="RecommendationCandidate@1", allowed_purposes=["GENERATE_PRAYER_PROMPT"], allowed_context_projections=["prayer_context_v1"], can_create_proposals=True),
    AgentCapability(agent_id="attention.command-executor", version="1.0", owner_module="attention", capability_type="COMMAND_EXECUTOR", accepted_input_schemas=["UnifiedCommand@1"], output_schema="CommandResult@1", allowed_purposes=["CREATE_ATTENTION_BOUNDARY"], allowed_context_projections=[], can_execute_commands=True),
    AgentCapability(agent_id="habit.command-executor", version="1.0", owner_module="holy_habit", capability_type="COMMAND_EXECUTOR", accepted_input_schemas=["UnifiedCommand@1"], output_schema="CommandResult@1", allowed_purposes=["CREATE_FORMATION_PRACTICE"], allowed_context_projections=[], can_execute_commands=True),
    AgentCapability(agent_id="platform.notification-coordinator", version="1.0", owner_module="notification", capability_type="NOTIFICATION_GENERATOR", accepted_input_schemas=["NotificationCandidate@1"], output_schema="NotificationPlan@1", allowed_purposes=list(PURPOSE_POLICIES), allowed_context_projections=[], can_create_proposals=True),
]


def event_registration(event_type: str, version: str = "1.0") -> dict[str, Any] | None:
    item = EVENT_SCHEMAS.get(event_type)
    return item if item and item["version"] == version else None


def agent_registration(agent_id: str) -> AgentCapability | None:
    return next((item for item in AGENT_CAPABILITIES if item.agent_id == agent_id and item.active), None)
