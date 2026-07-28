-- EMD-OS Batch 3: real-life emotional events, timelines, four separate recovery metrics,
-- relationship repair verification, training transfer, recurrence patterns,
-- 14/30/90 checkpoints and longitudinal growth evaluations.
-- No third-party identity, no raw narrative body, no personality label may be stored here.

CREATE TABLE IF NOT EXISTS formation_twin_emd_real_life_events (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    event_id VARCHAR(80) NOT NULL,
    growth_plan_id UUID REFERENCES formation_twin_emd_reassessment_plans(id) ON DELETE SET NULL,
    context VARCHAR(24) NOT NULL DEFAULT 'other',
    evidence_context VARCHAR(40) NOT NULL DEFAULT 'OTHER',
    evidence_level VARCHAR(4) NOT NULL DEFAULT 'RL0',
    related_dimensions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    objective_facts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    user_interpretations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    emotions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    body_signals_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    regulation_attempts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    first_response VARCHAR(240), later_response VARCHAR(240),
    relationship_outcome VARCHAR(24),
    safety_flags_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    urge_without_action BOOLEAN NOT NULL DEFAULT FALSE,
    harmful_action_occurred BOOLEAN NOT NULL DEFAULT FALSE,
    fact_interpretation_separated BOOLEAN NOT NULL DEFAULT FALSE,
    private_mode BOOLEAN NOT NULL DEFAULT TRUE,
    status VARCHAR(24) NOT NULL DEFAULT 'CAPTURED',
    occurred_at TIMESTAMPTZ NOT NULL, captured_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, event_id),
    CHECK(evidence_level IN ('RL0','RL1','RL2','RL3','RL4','RL5')),
    CHECK(status IN ('CAPTURED','ROUTED_TO_SAFETY','BLOCKED_NO_CONSENT','SUPERSEDED')),
    CHECK(relationship_outcome IS NULL OR relationship_outcome IN
        ('not_needed','unsafe_to_attempt','attempted','partially_resolved','resolved','boundary_exit','unresolved')),
    CHECK(captured_at >= occurred_at)
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_event_owner ON formation_twin_emd_real_life_events(email,occurred_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_emd_event_timelines (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    timeline_id VARCHAR(80) NOT NULL, event_id VARCHAR(80) NOT NULL,
    nodes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    unknown_nodes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    pre_event_vulnerability_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    turning_point_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, timeline_id)
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_recovery_metric_sets (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    metric_set_id VARCHAR(80) NOT NULL, event_id VARCHAR(80) NOT NULL,
    regulation_start_latency_seconds NUMERIC,
    behavioral_control_recovery_seconds NUMERIC,
    functional_recovery_seconds NUMERIC,
    emotional_recovery_seconds NUMERIC,
    repair_initiation_latency_seconds NUMERIC,
    rumination_duration_seconds NUMERIC,
    buckets_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    harmful_action_occurrence BOOLEAN NOT NULL DEFAULT FALSE,
    urge_without_action BOOLEAN NOT NULL DEFAULT FALSE,
    relationship_resolution_status VARCHAR(24) NOT NULL DEFAULT 'not_needed',
    within_user_comparison_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, metric_set_id),
    CHECK(regulation_start_latency_seconds IS NULL OR regulation_start_latency_seconds >= 0),
    CHECK(behavioral_control_recovery_seconds IS NULL OR behavioral_control_recovery_seconds >= 0),
    CHECK(relationship_resolution_status IN
        ('not_needed','unsafe_to_attempt','attempted','partially_resolved','resolved','boundary_exit','unresolved'))
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_metric_owner ON formation_twin_emd_recovery_metric_sets(email,created_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_emd_repair_verifications (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    repair_result_id VARCHAR(80) NOT NULL, event_id VARCHAR(80) NOT NULL,
    repair_stage VARCHAR(4) NOT NULL,
    quality_flags_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    missing_quality_elements_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    completed_by_user BOOLEAN NOT NULL DEFAULT FALSE,
    follow_through_events INTEGER NOT NULL DEFAULT 0 CHECK(follow_through_events >= 0),
    -- recorded for the user's own reflection only; it never changes the repair stage
    other_party_response VARCHAR(40),
    workflow VARCHAR(24) NOT NULL DEFAULT 'STANDARD',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, repair_result_id),
    CHECK(repair_stage IN ('R0','R1','R2','R3','R4','R5')),
    CHECK(workflow IN ('STANDARD','SAFETY_FIRST'))
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_transfer_observations (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    transfer_id VARCHAR(80) NOT NULL, skill_id VARCHAR(80) NOT NULL,
    transfer_stage VARCHAR(4) NOT NULL, prompt_dependence VARCHAR(4) NOT NULL,
    transfer_types_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    contexts_observed_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence_event_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    days_since_training INTEGER NOT NULL DEFAULT 0 CHECK(days_since_training >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, transfer_id),
    CHECK(transfer_stage IN ('T0','T1','T2','T3','T4','T5','T6')),
    CHECK(prompt_dependence IN ('P0','P1','P2','P3','P4'))
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_patterns (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    pattern_id VARCHAR(80) NOT NULL, pattern_name VARCHAR(60),
    recurrence_count INTEGER NOT NULL DEFAULT 0 CHECK(recurrence_count >= 0),
    contexts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    context_generalization BOOLEAN NOT NULL DEFAULT FALSE,
    intensity_trend VARCHAR(24) NOT NULL DEFAULT 'INSUFFICIENT_DATA',
    behavioral_recovery_trend VARCHAR(24) NOT NULL DEFAULT 'INSUFFICIENT_DATA',
    repair_trend VARCHAR(40),
    event_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    first_seen_at TIMESTAMPTZ, last_seen_at TIMESTAMPTZ,
    user_review_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, pattern_id),
    CHECK(user_review_status IN ('PENDING','USER_CONFIRMED','USER_DISPUTED','USER_CORRECTED'))
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_checkpoints (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    schedule_id VARCHAR(80) NOT NULL,
    growth_plan_id UUID REFERENCES formation_twin_emd_reassessment_plans(id) ON DELETE CASCADE,
    day INTEGER NOT NULL CHECK(day IN (14,30,90)),
    goal VARCHAR(80) NOT NULL,
    due_at TIMESTAMPTZ NOT NULL, opens_at TIMESTAMPTZ NOT NULL, closes_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'SCHEDULED',
    recommended_evidence_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, schedule_id, day),
    CHECK(status IN ('SCHEDULED','OPEN','COMPLETED','SKIPPED','NO_COMPARABLE_EVENT','EXPIRED')),
    CHECK(closes_at >= opens_at)
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_checkpoint_due ON formation_twin_emd_checkpoints(email,status,due_at) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_emd_growth_evaluations (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    evaluation_id VARCHAR(80) NOT NULL, day INTEGER NOT NULL CHECK(day IN (14,30,90)),
    result VARCHAR(40) NOT NULL,
    metric_changes_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    comparable_event_count INTEGER NOT NULL DEFAULT 0 CHECK(comparable_event_count >= 0),
    contexts_observed_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    transfer_stage VARCHAR(4), prompt_dependence VARCHAR(4),
    highlights_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    attribution_limits_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    user_review_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, evaluation_id),
    CHECK(result IN ('INSUFFICIENT_EVIDENCE','NO_CONFIRMED_CHANGE','EARLY_APPLICATION',
                     'IMPROVING','STABILISING','MAINTAINED_AND_GENERALISED','REGRESSION_OBSERVED')),
    -- a conclusion about change always requires at least one comparable real event
    CHECK(result = 'INSUFFICIENT_EVIDENCE' OR comparable_event_count >= 1)
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_growth_owner ON formation_twin_emd_growth_evaluations(email,day,created_at DESC) WHERE deleted_at IS NULL;

-- Owner RLS is defense in depth; application queries also retain email predicates.
DO $$
DECLARE table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'formation_twin_emd_real_life_events','formation_twin_emd_event_timelines',
    'formation_twin_emd_recovery_metric_sets','formation_twin_emd_repair_verifications',
    'formation_twin_emd_transfer_observations','formation_twin_emd_patterns',
    'formation_twin_emd_checkpoints','formation_twin_emd_growth_evaluations'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS ft_owner_policy ON %I', table_name);
    EXECUTE format(
      'CREATE POLICY ft_owner_policy ON %I USING (email=current_setting(''app.current_user_email'',true)) '
      'WITH CHECK (email=current_setting(''app.current_user_email'',true))', table_name
    );
  END LOOP;
END $$;
