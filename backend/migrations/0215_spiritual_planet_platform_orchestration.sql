-- Spiritual Planet Batch 9: platform integration and unified orchestration.
-- Source modules retain canonical data. Platform tables contain contracts,
-- short-lived projections, references, decisions and technical metadata only.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS spiritual_planet_event_schemas (
    event_type TEXT NOT NULL,
    event_version TEXT NOT NULL,
    producer TEXT NOT NULL,
    schema_uri TEXT NOT NULL,
    compatibility TEXT NOT NULL CHECK (compatibility IN ('BACKWARD_COMPATIBLE','FORWARD_COMPATIBLE','FULL_COMPATIBLE','BREAKING_CHANGE')),
    schema_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    allowed_payload_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
    deprecated BOOLEAN NOT NULL DEFAULT FALSE,
    migration_guide TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (event_type,event_version)
);

CREATE TABLE IF NOT EXISTS spiritual_planet_context_projections (
    projection_name TEXT NOT NULL,
    projection_version TEXT NOT NULL,
    owner_module TEXT NOT NULL,
    allowed_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
    default_ttl_seconds INTEGER NOT NULL CHECK(default_ttl_seconds BETWEEN 30 AND 900),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (projection_name,projection_version)
);

CREATE TABLE IF NOT EXISTS spiritual_planet_agent_capabilities (
    agent_id TEXT NOT NULL,
    version TEXT NOT NULL,
    owner_module TEXT NOT NULL,
    capability_type TEXT NOT NULL,
    accepted_input_schemas JSONB NOT NULL DEFAULT '[]'::jsonb,
    output_schema TEXT NOT NULL,
    allowed_purposes JSONB NOT NULL DEFAULT '[]'::jsonb,
    allowed_context_projections JSONB NOT NULL DEFAULT '[]'::jsonb,
    can_read_sensitive_content BOOLEAN NOT NULL DEFAULT FALSE,
    can_create_proposals BOOLEAN NOT NULL DEFAULT FALSE,
    can_execute_commands BOOLEAN NOT NULL DEFAULT FALSE,
    requires_user_confirmation BOOLEAN NOT NULL DEFAULT TRUE,
    safety_policy_ids JSONB NOT NULL DEFAULT '["global-safety-v1"]'::jsonb,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY(agent_id,version),
    CHECK (NOT (capability_type='ANALYZER' AND can_execute_commands)),
    CHECK (NOT (capability_type='RECOMMENDATION_GENERATOR' AND can_execute_commands)),
    CHECK (capability_type!='COMMAND_EXECUTOR' OR requires_user_confirmation)
);

CREATE TABLE IF NOT EXISTS spiritual_planet_context_consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    requester_module TEXT NOT NULL,
    purpose TEXT NOT NULL,
    projection_name TEXT NOT NULL,
    allowed_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
    consent_status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(consent_status IN('ACTIVE','REVOKED','EXPIRED')),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id,email,requester_module,purpose,projection_name)
);

CREATE TABLE IF NOT EXISTS spiritual_planet_context_access_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    context_id UUID,
    requester_module TEXT NOT NULL,
    purpose TEXT NOT NULL,
    projection_name TEXT NOT NULL,
    requested_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
    allowed_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
    denied_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
    decision TEXT NOT NULL CHECK(decision IN('ALLOWED','DENIED')),
    reason_codes JSONB NOT NULL DEFAULT '[]'::jsonb,
    correlation_id UUID NOT NULL,
    consent_reference_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sp_context_access_owner ON spiritual_planet_context_access_audit(tenant_id,email,created_at DESC);

CREATE TABLE IF NOT EXISTS spiritual_planet_orchestration_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    trigger_reference_id TEXT,
    user_intent_present BOOLEAN NOT NULL DEFAULT FALSE,
    requested_outcome_code TEXT,
    correlation_id UUID NOT NULL,
    trace_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN('QUEUED','RUNNING','COMPLETED','STOPPED_FOR_SAFETY','CANCELLED','FAILED','DEGRADED_LIMIT_REACHED')),
    safety_state TEXT NOT NULL DEFAULT 'NONE',
    capacity_mode TEXT NOT NULL DEFAULT 'NORMAL',
    max_nodes INTEGER NOT NULL DEFAULT 8 CHECK(max_nodes BETWEEN 1 AND 20),
    max_model_calls INTEGER NOT NULL DEFAULT 1 CHECK(max_model_calls BETWEEN 0 AND 3),
    steps JSONB NOT NULL DEFAULT '[]'::jsonb,
    result_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sp_runs_owner ON spiritual_planet_orchestration_runs(tenant_id,email,created_at DESC);

CREATE TABLE IF NOT EXISTS spiritual_planet_recommendation_candidates (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    orchestration_run_id UUID NOT NULL REFERENCES spiritual_planet_orchestration_runs(id) ON DELETE CASCADE,
    source_module TEXT NOT NULL,
    recommendation_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    purpose TEXT NOT NULL,
    estimated_duration_minutes INTEGER NOT NULL DEFAULT 2 CHECK(estimated_duration_minutes BETWEEN 0 AND 180),
    burden_level TEXT NOT NULL,
    safety_priority INTEGER NOT NULL CHECK(safety_priority BETWEEN 1 AND 8),
    urgency TEXT NOT NULL,
    requires_user_confirmation BOOLEAN NOT NULL DEFAULT TRUE,
    supporting_context_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    target_module TEXT,
    proposed_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    uses_pending_context BOOLEAN NOT NULL DEFAULT FALSE,
    decision_status TEXT NOT NULL DEFAULT 'PENDING' CHECK(decision_status IN('PENDING','ACCEPTED','MODIFIED','SMALLER_REQUESTED','ALTERNATIVE_REQUESTED','SKIPPED','REJECTED')),
    decision_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sp_candidates_run ON spiritual_planet_recommendation_candidates(orchestration_run_id,created_at);

CREATE TABLE IF NOT EXISTS spiritual_planet_arbitration_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    orchestration_run_id UUID NOT NULL UNIQUE REFERENCES spiritual_planet_orchestration_runs(id) ON DELETE CASCADE,
    selected_recommendation_id UUID,
    merged_candidate_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    suppressed_candidates JSONB NOT NULL DEFAULT '[]'::jsonb,
    selection_rationale JSONB NOT NULL DEFAULT '[]'::jsonb,
    no_action_selected BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS spiritual_planet_unified_commands (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    source_recommendation_id UUID,
    command_type TEXT NOT NULL,
    target_module TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    payload_schema TEXT NOT NULL,
    user_confirmation_reference_id UUID NOT NULL,
    purpose TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'CONFIRMED' CHECK(status IN('CONFIRMED','EXECUTING','EXECUTED','REJECTED','EXPIRED','FAILED','DEGRADED')),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id,email,idempotency_key)
);

CREATE TABLE IF NOT EXISTS spiritual_planet_command_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    command_id UUID NOT NULL UNIQUE REFERENCES spiritual_planet_unified_commands(id) ON DELETE CASCADE,
    target_module TEXT NOT NULL,
    target_record_id TEXT,
    result_status TEXT NOT NULL,
    reason_codes JSONB NOT NULL DEFAULT '[]'::jsonb,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS spiritual_planet_unified_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    source_module TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    source_recommendation_id UUID,
    title TEXT NOT NULL,
    action_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN('PROPOSED','CONFIRMED','SCHEDULED','IN_PROGRESS','COMPLETED','PARTIAL','SKIPPED','STOPPED','CANCELLED','EXPIRED')),
    estimated_duration_minutes INTEGER CHECK(estimated_duration_minutes BETWEEN 0 AND 180),
    scheduled_at TIMESTAMPTZ,
    one_time BOOLEAN NOT NULL DEFAULT TRUE,
    recurrence_summary TEXT,
    sensitivity TEXT NOT NULL DEFAULT 'SENSITIVE',
    user_visible_context TEXT,
    focus_action BOOLEAN NOT NULL DEFAULT FALSE,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    UNIQUE(tenant_id,email,source_module,source_record_id)
);
CREATE INDEX IF NOT EXISTS idx_sp_actions_owner ON spiritual_planet_unified_actions(tenant_id,email,status,created_at DESC) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_sp_one_focus_action ON spiritual_planet_unified_actions(tenant_id,email) WHERE focus_action AND status IN('CONFIRMED','SCHEDULED','IN_PROGRESS') AND deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS spiritual_planet_notification_candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    source_module TEXT NOT NULL,
    notification_type TEXT NOT NULL,
    urgency TEXT NOT NULL,
    sensitivity TEXT NOT NULL,
    generic_title TEXT NOT NULL,
    generic_body TEXT NOT NULL,
    intended_delivery_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    quiet_hours_exempt BOOLEAN NOT NULL DEFAULT FALSE,
    grouping_key TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN('PENDING','GROUPED','DELIVERED','SUPPRESSED','CANCELLED','EXPIRED')),
    purpose TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS spiritual_planet_consent_propagation_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    consent_id UUID NOT NULL,
    affected_modules JSONB NOT NULL DEFAULT '[]'::jsonb,
    invalidated_contexts INTEGER NOT NULL DEFAULT 0,
    cancelled_workflows INTEGER NOT NULL DEFAULT 0,
    cancelled_notifications INTEGER NOT NULL DEFAULT 0,
    stale_derived_outputs INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL CHECK(status IN('RUNNING','COMPLETED','PARTIAL','FAILED_RETRYABLE')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS spiritual_planet_deletion_manifests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    source_module TEXT NOT NULL,
    source_record_type TEXT NOT NULL,
    source_record_ids JSONB NOT NULL,
    deletion_scope TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN('REQUESTED','PROPAGATING','PARTIALLY_COMPLETED','COMPLETED','FAILED_RETRYABLE','FAILED_MANUAL_REVIEW')),
    required_modules JSONB NOT NULL DEFAULT '[]'::jsonb,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS spiritual_planet_deletion_acknowledgements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    deletion_id UUID NOT NULL REFERENCES spiritual_planet_deletion_manifests(id) ON DELETE CASCADE,
    module TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN('PENDING','COMPLETED','NOT_AVAILABLE','FAILED_RETRYABLE','FAILED_MANUAL_REVIEW')),
    deleted_reference_count INTEGER NOT NULL DEFAULT 0,
    reason_code TEXT,
    acknowledged_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(deletion_id,module)
);

CREATE TABLE IF NOT EXISTS spiritual_planet_rebuild_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    scope TEXT NOT NULL,
    source_module TEXT,
    source_record_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    reason_code TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN('QUEUED','RUNNING','COMPLETED','CANCELLED','FAILED_RETRYABLE','FAILED_MANUAL_REVIEW')),
    preserved_confirmations INTEGER NOT NULL DEFAULT 0,
    preserved_rejections INTEGER NOT NULL DEFAULT 0,
    preserved_corrections INTEGER NOT NULL DEFAULT 0,
    new_derived_references JSONB NOT NULL DEFAULT '[]'::jsonb,
    invalidated_derived_references JSONB NOT NULL DEFAULT '[]'::jsonb,
    engine_versions JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS spiritual_planet_integration_health (
    module TEXT PRIMARY KEY,
    registration_status TEXT NOT NULL,
    adapter_status TEXT NOT NULL,
    circuit_state TEXT NOT NULL DEFAULT 'CLOSED',
    reason_codes JSONB NOT NULL DEFAULT '[]'::jsonb,
    contract_version TEXT,
    last_success_at TIMESTAMPTZ,
    last_failure_at TIMESTAMPTZ,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS spiritual_planet_circuit_breakers (
    module TEXT PRIMARY KEY,
    failure_count INTEGER NOT NULL DEFAULT 0,
    failure_threshold INTEGER NOT NULL DEFAULT 3,
    state TEXT NOT NULL DEFAULT 'CLOSED' CHECK(state IN('CLOSED','OPEN','HALF_OPEN')),
    opened_at TIMESTAMPTZ,
    recover_after TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS spiritual_planet_search_references (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    source_module TEXT NOT NULL,
    source_record_type TEXT NOT NULL,
    source_record_id TEXT NOT NULL,
    confirmed_title TEXT NOT NULL,
    confirmed_summary TEXT,
    scripture_references JSONB NOT NULL DEFAULT '[]'::jsonb,
    sensitivity TEXT NOT NULL DEFAULT 'SENSITIVE',
    display_route TEXT NOT NULL,
    occurred_at TIMESTAMPTZ,
    excluded BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id,email,source_module,source_record_id)
);
CREATE INDEX IF NOT EXISTS idx_sp_search_owner ON spiritual_planet_search_references(tenant_id,email,occurred_at DESC) WHERE deleted_at IS NULL AND excluded=FALSE;

-- Global registries contain no user data. All owner-scoped tables enforce RLS.
DO $$
DECLARE table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'spiritual_planet_context_consents','spiritual_planet_context_access_audit',
    'spiritual_planet_orchestration_runs','spiritual_planet_recommendation_candidates',
    'spiritual_planet_arbitration_results','spiritual_planet_unified_commands',
    'spiritual_planet_command_results','spiritual_planet_unified_actions',
    'spiritual_planet_notification_candidates','spiritual_planet_consent_propagation_jobs',
    'spiritual_planet_deletion_manifests','spiritual_planet_deletion_acknowledgements',
    'spiritual_planet_rebuild_jobs','spiritual_planet_search_references'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS spiritual_planet_owner_policy ON %I', table_name);
    EXECUTE format(
      'CREATE POLICY spiritual_planet_owner_policy ON %I USING (LOWER(email)=LOWER(COALESCE(current_setting(''app.current_user_email'',true),''''))) WITH CHECK (LOWER(email)=LOWER(COALESCE(current_setting(''app.current_user_email'',true),'''')))',
      table_name
    );
  END LOOP;
END $$;

-- Registry seed is idempotent; application startup also exposes the canonical definitions.
INSERT INTO spiritual_planet_event_schemas(event_type,event_version,producer,schema_uri,compatibility,allowed_payload_fields)
SELECT event_type,'1.0','platform_orchestrator','spiritual-planet://events/'||event_type||'/1.0','BACKWARD_COMPATIBLE',
       '["context_id","projection_name","requester_module","purpose","reason_codes","run_id","status","candidate_ids","selected_candidate_id","suppressed_candidate_ids","command_id","target_module","target_record_id","deletion_id","rebuild_id","module","schema_version","action","result_code"]'::jsonb
FROM unnest(ARRAY[
 'spiritual_planet.context_projection_created','spiritual_planet.context_access_denied',
 'spiritual_planet.orchestration_started','spiritual_planet.orchestration_completed','spiritual_planet.orchestration_failed',
 'spiritual_planet.recommendation_candidates_created','spiritual_planet.recommendation_selected','spiritual_planet.recommendation_suppressed',
 'spiritual_planet.command_created','spiritual_planet.command_executed','spiritual_planet.command_failed','spiritual_planet.command_expired',
 'spiritual_planet.consent_propagation_started','spiritual_planet.consent_propagation_completed','spiritual_planet.consent_propagation_failed',
 'spiritual_planet.deletion_manifest_created','spiritual_planet.deletion_propagation_completed','spiritual_planet.deletion_propagation_failed',
 'spiritual_planet.rebuild_started','spiritual_planet.rebuild_completed','spiritual_planet.rebuild_failed',
 'spiritual_planet.integration_degraded','spiritual_planet.integration_recovered','spiritual_planet.contract_violation_detected'
]) AS event_type
ON CONFLICT(event_type,event_version) DO UPDATE SET allowed_payload_fields=EXCLUDED.allowed_payload_fields,updated_at=NOW();

INSERT INTO spiritual_planet_context_projections(projection_name,projection_version,owner_module,allowed_fields,default_ttl_seconds)
VALUES
 ('prayer_context_v1','1.0','formation_twin','["user_selected_prayer_needs","confirmed_emotional_context","confirmed_fears","grace_factors","selected_scripture_themes"]',300),
 ('habit_context_v1','1.0','formation_twin','["user_selected_goal","capacity_mode","preferred_duration_minutes","blocked_intervention_types","confirmed_alternative_response"]',300),
 ('attention_context_v1','1.0','formation_twin','["user_confirmed_attention_pattern","preferred_boundary_type","risk_time_window","sensitive_reason_included"]',180),
 ('calling_context_v1','1.0','formation_twin','["active_life_seasons","user_confirmed_gifts","service_experience","capacity_constraints","unresolved_calling_questions"]',300),
 ('church_context_v1','1.0','formation_twin','["participation_goals","relationship_support_needs","pastoral_conversation_questions","church_experience_summaries"]',180),
 ('mission_context_v1','1.0','formation_twin','["confirmed_calling_directions","equipping_progress","language_culture_preparation","family_health_readiness","user_shared_constraints"]',300),
 ('formation_context_v1','1.0','formation_twin','["confirmed_patterns","confirmed_practices","capacity_mode","grace_factors","limitations"]',300),
 ('devotion_context_v1','1.0','formation_twin','["selected_scripture_themes","preferred_duration_minutes","capacity_mode","grace_factors"]',300),
 ('scripture_context_v1','1.0','bible_kg','["selected_scripture_themes","scripture_references"]',900),
 ('unified_home_context_v1','1.0','platform_orchestrator','["today_report","capacity_mode","safety_summary","confirmed_theme","grace_factors","active_action_references"]',120),
 ('unified_timeline_context_v1','1.0','platform_orchestrator','["timeline_references"]',120),
 ('unified_search_context_v1','1.0','platform_orchestrator','["confirmed_search_references"]',120),
 ('crisis_routing_context_v1','1.0','crisis','["safety_level","safety_plan_available","human_connection_available","professional_support_route"]',60)
ON CONFLICT(projection_name,projection_version) DO UPDATE SET allowed_fields=EXCLUDED.allowed_fields,default_ttl_seconds=EXCLUDED.default_ttl_seconds,active=TRUE;

INSERT INTO spiritual_planet_agent_capabilities(
 agent_id,version,owner_module,capability_type,accepted_input_schemas,output_schema,
 allowed_purposes,allowed_context_projections,can_create_proposals,can_execute_commands,requires_user_confirmation
)
VALUES
 ('platform.context-provider','1.0','platform_orchestrator','CONTEXT_PROVIDER','["ContextRequest@1"]','ContextResponse@1','["GENERATE_PRAYER_PROMPT","CREATE_FORMATION_PRACTICE","CREATE_ATTENTION_BOUNDARY","PREPARE_CALLING_REFLECTION","PREPARE_PASTORAL_BRIEF","PREPARE_MISSION_REFLECTION","GENERATE_DEVOTION_PROMPT","GENERATE_UNIFIED_HOME","GENERATE_UNIFIED_TIMELINE","SEARCH_CONFIRMED_USER_DATA","GENERATE_WEEKLY_REVIEW","ROUTE_CRISIS_CASE"]','["prayer_context_v1","habit_context_v1","attention_context_v1","calling_context_v1","church_context_v1","mission_context_v1","formation_context_v1","devotion_context_v1","unified_home_context_v1","unified_timeline_context_v1","unified_search_context_v1","crisis_routing_context_v1"]',FALSE,FALSE,FALSE),
 ('platform.safety-gate','1.0','crisis','SAFETY_CLASSIFIER','["SafetyGateRequest@1"]','SafetyDecision@1','["ROUTE_CRISIS_CASE","GENERATE_UNIFIED_HOME"]','["crisis_routing_context_v1"]',FALSE,FALSE,FALSE),
 ('platform.recommendation-arbitrator','1.0','platform_orchestrator','ANALYZER','["RecommendationCandidate@1"]','RecommendationArbitrationResult@1','["GENERATE_UNIFIED_HOME"]','["unified_home_context_v1"]',FALSE,FALSE,FALSE),
 ('formation.recommendation-generator','1.0','formation_engine','RECOMMENDATION_GENERATOR','["formation_context_v1"]','RecommendationCandidate@1','["CREATE_FORMATION_PRACTICE"]','["formation_context_v1"]',TRUE,FALSE,TRUE),
 ('prayer.recommendation-generator','1.0','prayer','RECOMMENDATION_GENERATOR','["prayer_context_v1"]','RecommendationCandidate@1','["GENERATE_PRAYER_PROMPT"]','["prayer_context_v1"]',TRUE,FALSE,TRUE),
 ('attention.command-executor','1.0','attention','COMMAND_EXECUTOR','["UnifiedCommand@1"]','CommandResult@1','["CREATE_ATTENTION_BOUNDARY"]','[]',FALSE,TRUE,TRUE),
 ('habit.command-executor','1.0','holy_habit','COMMAND_EXECUTOR','["UnifiedCommand@1"]','CommandResult@1','["CREATE_FORMATION_PRACTICE"]','[]',FALSE,TRUE,TRUE),
 ('platform.notification-coordinator','1.0','notification','NOTIFICATION_GENERATOR','["NotificationCandidate@1"]','NotificationPlan@1','["GENERATE_UNIFIED_HOME"]','[]',TRUE,FALSE,TRUE)
ON CONFLICT(agent_id,version) DO UPDATE SET accepted_input_schemas=EXCLUDED.accepted_input_schemas,allowed_purposes=EXCLUDED.allowed_purposes,allowed_context_projections=EXCLUDED.allowed_context_projections,active=TRUE,updated_at=NOW();

INSERT INTO spiritual_planet_integration_health(module,registration_status,adapter_status,reason_codes,contract_version)
SELECT module,'REGISTERED',CASE WHEN module IN('formation_twin','platform_orchestrator') THEN 'HEALTHY' ELSE 'DEGRADED' END,
       CASE WHEN module IN('formation_twin','platform_orchestrator') THEN '[]'::jsonb ELSE '["CONTEXT_OR_COMMAND_ADAPTER_NOT_REGISTERED"]'::jsonb END,'1.0'
FROM unnest(ARRAY['identity','worldview','formation_twin','formation_engine','prayer','devotion','holy_habit','attention','crisis','gift_calling','church','mission','bible_kg','notification','search','audit','platform_orchestrator']) AS module
ON CONFLICT(module) DO UPDATE SET registration_status=EXCLUDED.registration_status,adapter_status=EXCLUDED.adapter_status,reason_codes=EXCLUDED.reason_codes,contract_version=EXCLUDED.contract_version,checked_at=NOW();

-- Rollback guide: disable the platform feature flags, drain active jobs, export
-- manifests/audits, then drop tables in reverse dependency order. Source-module
-- records are never mutated by this migration and therefore need no rollback.
