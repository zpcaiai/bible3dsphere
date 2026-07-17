-- Formation Twin Batch 5: temporal patterns, evidence, life seasons, trajectories and reviews.
-- Sensitive source bodies remain in the encrypted source tables and are never copied here.

CREATE TABLE IF NOT EXISTS formation_twin_temporal_settings (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    temporal_engine_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    pattern_discovery_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    model_inference_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    semantic_retrieval_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    life_season_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    trajectory_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    graph_evidence_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    review_cadence VARCHAR(20) NOT NULL DEFAULT 'MONTHLY',
    timezone VARCHAR(80) NOT NULL DEFAULT 'Asia/Shanghai',
    consent_version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(tenant_id,profile_id), CHECK (review_cadence IN ('WEEKLY','MONTHLY','QUARTERLY','MANUAL'))
);

CREATE TABLE IF NOT EXISTS formation_twin_temporal_windows (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    window_type VARCHAR(30) NOT NULL, label VARCHAR(160), start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ NOT NULL, timezone VARCHAR(80) NOT NULL, source VARCHAR(40) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE', created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), CHECK (end_at>start_at)
);
CREATE INDEX IF NOT EXISTS idx_ft_temporal_windows_owner_time
    ON formation_twin_temporal_windows(email,start_at DESC,end_at DESC);

CREATE TABLE IF NOT EXISTS formation_twin_event_clusters (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    title VARCHAR(160), cluster_type VARCHAR(40) NOT NULL, creation_method VARCHAR(30) NOT NULL,
    shared_context_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    grouping_reasons_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    confidence NUMERIC CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    user_review_status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    started_at TIMESTAMPTZ NOT NULL, ended_at TIMESTAMPTZ NOT NULL,
    rule_version VARCHAR(60), rejection_cooldown_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ, CHECK (ended_at>=started_at),
    CHECK (creation_method<>'MODEL_SUGGESTED' OR user_review_status='PENDING')
);
CREATE INDEX IF NOT EXISTS idx_ft_event_clusters_owner
    ON formation_twin_event_clusters(email,started_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_event_cluster_members (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    cluster_id UUID NOT NULL REFERENCES formation_twin_event_clusters(id) ON DELETE CASCADE,
    member_type VARCHAR(40) NOT NULL, member_id UUID NOT NULL, membership_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    added_reason VARCHAR(200) NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), removed_at TIMESTAMPTZ,
    UNIQUE(cluster_id,member_type,member_id)
);

CREATE TABLE IF NOT EXISTS formation_twin_patterns (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    pattern_key VARCHAR(64) NOT NULL, title VARCHAR(160) NOT NULL, pattern_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL, trigger_signature_json JSONB, response_signature_json JSONB,
    outcome_signature_json JSONB, scope_json JSONB NOT NULL, lifecycle_status VARCHAR(40) NOT NULL,
    confidence_json JSONB NOT NULL, evidence_quality VARCHAR(40) NOT NULL,
    source_kind VARCHAR(30) NOT NULL, statement_type VARCHAR(50) NOT NULL,
    user_review_status VARCHAR(40) NOT NULL, alternative_explanations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    limitations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    first_observed_at TIMESTAMPTZ NOT NULL, last_observed_at TIMESTAMPTZ NOT NULL,
    last_confirmed_at TIMESTAMPTZ, review_due_at TIMESTAMPTZ NOT NULL,
    model_version VARCHAR(80), rule_version VARCHAR(80), engine_version VARCHAR(80) NOT NULL,
    is_alternative_response BOOLEAN NOT NULL DEFAULT FALSE,
    version INTEGER NOT NULL DEFAULT 1, supersedes_pattern_id UUID REFERENCES formation_twin_patterns(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ, CHECK(last_observed_at>=first_observed_at), CHECK(review_due_at>last_observed_at),
    CHECK(lifecycle_status NOT IN ('CONFIRMED_ACTIVE','CONFIRMED_CONTEXTUAL') OR
          user_review_status IN ('CONFIRMED','PARTIALLY_CONFIRMED','SCOPE_NARROWED','SCOPE_EXPANDED'))
);
CREATE INDEX IF NOT EXISTS idx_ft_patterns_owner_status
    ON formation_twin_patterns(email,lifecycle_status,review_due_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_ft_patterns_owner_key
    ON formation_twin_patterns(email,pattern_key,version DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_pattern_evidence (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    pattern_id UUID NOT NULL REFERENCES formation_twin_patterns(id) ON DELETE CASCADE,
    evidence_role VARCHAR(30) NOT NULL, evidence_type VARCHAR(40) NOT NULL,
    source_record_type VARCHAR(40) NOT NULL, source_record_id UUID NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL, temporal_weight NUMERIC NOT NULL CHECK(temporal_weight BETWEEN 0 AND 1),
    decay_strategy VARCHAR(30) NOT NULL DEFAULT 'STANDARD', source_quality VARCHAR(40) NOT NULL,
    independence_group VARCHAR(160), relevance NUMERIC NOT NULL CHECK(relevance BETWEEN 0 AND 1),
    user_review_status VARCHAR(40) NOT NULL, explanation VARCHAR(400) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), invalidated_at TIMESTAMPTZ,
    UNIQUE(pattern_id,source_record_type,source_record_id,evidence_role)
);
CREATE INDEX IF NOT EXISTS idx_ft_pattern_evidence_owner_pattern
    ON formation_twin_pattern_evidence(email,pattern_id,evidence_role) WHERE invalidated_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_pattern_confidence_history (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    pattern_id UUID NOT NULL REFERENCES formation_twin_patterns(id) ON DELETE CASCADE,
    confidence_level VARCHAR(20) NOT NULL, numeric_value NUMERIC NOT NULL CHECK(numeric_value BETWEEN 0 AND 1),
    support_score NUMERIC NOT NULL, counterevidence_score NUMERIC NOT NULL,
    recency_factor NUMERIC NOT NULL, diversity_factor NUMERIC NOT NULL,
    user_confirmation_factor NUMERIC NOT NULL, scope_consistency_factor NUMERIC NOT NULL,
    rationale_json JSONB NOT NULL, algorithm_version VARCHAR(80) NOT NULL,
    calculated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS formation_twin_pattern_lifecycle_events (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    pattern_id UUID NOT NULL REFERENCES formation_twin_patterns(id) ON DELETE CASCADE,
    previous_status VARCHAR(40), new_status VARCHAR(40) NOT NULL, reason_code VARCHAR(60) NOT NULL,
    reason_description VARCHAR(400), initiated_by VARCHAR(30) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS formation_twin_life_seasons (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    title VARCHAR(160) NOT NULL, season_type VARCHAR(50) NOT NULL, started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ, time_precision VARCHAR(20) NOT NULL, life_domains JSONB NOT NULL DEFAULT '[]'::jsonb,
    roles_json JSONB NOT NULL DEFAULT '[]'::jsonb, user_description TEXT, context_summary VARCHAR(500),
    source_kind VARCHAR(50) NOT NULL, user_review_status VARCHAR(40) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    CHECK(ended_at IS NULL OR ended_at>=started_at),
    CHECK(source_kind<>'USER_CONFIRMED_MODEL_SUGGESTION' OR user_review_status IN ('CONFIRMED','PARTIALLY_CONFIRMED'))
);
CREATE INDEX IF NOT EXISTS idx_ft_life_seasons_owner
    ON formation_twin_life_seasons(email,active,started_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_pattern_life_seasons (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    pattern_id UUID NOT NULL REFERENCES formation_twin_patterns(id) ON DELETE CASCADE,
    life_season_id UUID NOT NULL REFERENCES formation_twin_life_seasons(id) ON DELETE CASCADE,
    relation_type VARCHAR(40) NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(pattern_id,life_season_id,relation_type)
);

CREATE TABLE IF NOT EXISTS formation_twin_trajectories (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    title VARCHAR(160) NOT NULL, trajectory_type VARCHAR(50) NOT NULL, scope_json JSONB NOT NULL,
    started_at TIMESTAMPTZ NOT NULL, ended_at TIMESTAMPTZ, current_direction VARCHAR(30) NOT NULL,
    evidence_quality VARCHAR(40) NOT NULL, user_review_status VARCHAR(40) NOT NULL,
    source_pattern_ids_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    limitations_json JSONB NOT NULL DEFAULT '[]'::jsonb, version INTEGER NOT NULL DEFAULT 1,
    supersedes_trajectory_id UUID REFERENCES formation_twin_trajectories(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ, CHECK(ended_at IS NULL OR ended_at>=started_at)
);

CREATE TABLE IF NOT EXISTS formation_twin_trajectory_points (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    trajectory_id UUID NOT NULL REFERENCES formation_twin_trajectories(id) ON DELETE CASCADE,
    window_start TIMESTAMPTZ NOT NULL, window_end TIMESTAMPTZ NOT NULL, direction VARCHAR(30) NOT NULL,
    supporting_pattern_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    counterevidence_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    summary_json JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK(window_end>=window_start)
);

CREATE TABLE IF NOT EXISTS formation_twin_pattern_reviews (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    review_type VARCHAR(50) NOT NULL, window_start TIMESTAMPTZ NOT NULL, window_end TIMESTAMPTZ NOT NULL,
    review_payload_json JSONB NOT NULL, status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), completed_at TIMESTAMPTZ, skipped_at TIMESTAMPTZ,
    CHECK(window_end>=window_start)
);

CREATE TABLE IF NOT EXISTS formation_twin_interpretation_preferences (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    preference_type VARCHAR(50) NOT NULL, preference_payload_json JSONB NOT NULL,
    scope VARCHAR(40) NOT NULL, source_review_id UUID, active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), revoked_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS formation_twin_long_term_snapshots (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    window_start TIMESTAMPTZ NOT NULL, window_end TIMESTAMPTZ NOT NULL,
    active_life_seasons_json JSONB NOT NULL, confirmed_active_patterns_json JSONB NOT NULL,
    confirmed_contextual_patterns_json JSONB NOT NULL, weakening_patterns_json JSONB NOT NULL,
    dormant_patterns_json JSONB NOT NULL, pending_candidates_json JSONB NOT NULL,
    alternative_responses_json JSONB NOT NULL, grace_patterns_json JSONB NOT NULL,
    recovery_patterns_json JSONB NOT NULL, trajectories_json JSONB NOT NULL,
    counterevidence_json JSONB NOT NULL, unresolved_questions_json JSONB NOT NULL,
    data_coverage_json JSONB NOT NULL, uncertainty_json JSONB NOT NULL, limitations_json JSONB NOT NULL,
    blocked_items_json JSONB NOT NULL DEFAULT '[]'::jsonb, input_hash VARCHAR(64) NOT NULL,
    engine_version VARCHAR(80) NOT NULL, version INTEGER NOT NULL DEFAULT 1,
    supersedes_snapshot_id UUID REFERENCES formation_twin_long_term_snapshots(id), superseded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), CHECK(window_end>=window_start),
    UNIQUE(email,input_hash)
);

CREATE TABLE IF NOT EXISTS formation_twin_pattern_rebuild_jobs (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    trigger_reason VARCHAR(60) NOT NULL, status VARCHAR(30) NOT NULL,
    checkpoint_json JSONB NOT NULL DEFAULT '{}'::jsonb, report_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    engine_version VARCHAR(80) NOT NULL, rule_version VARCHAR(80) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ, failed_at TIMESTAMPTZ, error_code VARCHAR(80)
);

CREATE TABLE IF NOT EXISTS formation_twin_pattern_processing_checkpoints (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    job_name VARCHAR(80) NOT NULL, last_processed_event_at TIMESTAMPTZ,
    last_processed_event_id UUID, engine_version VARCHAR(80) NOT NULL,
    rule_version VARCHAR(80) NOT NULL, model_version VARCHAR(80),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(email,job_name)
);

CREATE TABLE IF NOT EXISTS formation_twin_temporal_graph_syncs (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    pattern_id UUID REFERENCES formation_twin_patterns(id) ON DELETE SET NULL,
    sync_status VARCHAR(30) NOT NULL, node_count INTEGER NOT NULL DEFAULT 0,
    relationship_count INTEGER NOT NULL DEFAULT 0, error_code VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$
DECLARE table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'formation_twin_temporal_settings','formation_twin_temporal_windows','formation_twin_event_clusters',
    'formation_twin_event_cluster_members','formation_twin_patterns','formation_twin_pattern_evidence',
    'formation_twin_pattern_confidence_history','formation_twin_pattern_lifecycle_events',
    'formation_twin_life_seasons','formation_twin_pattern_life_seasons','formation_twin_trajectories',
    'formation_twin_trajectory_points','formation_twin_pattern_reviews','formation_twin_interpretation_preferences',
    'formation_twin_long_term_snapshots','formation_twin_pattern_rebuild_jobs',
    'formation_twin_pattern_processing_checkpoints','formation_twin_temporal_graph_syncs'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS ft_owner_policy ON %I', table_name);
    EXECUTE format(
      'CREATE POLICY ft_owner_policy ON %I USING (email=current_setting(''app.current_user_email'',true)) '
      'WITH CHECK (email=current_setting(''app.current_user_email'',true))', table_name
    );
  END LOOP;
END $$;

COMMENT ON TABLE formation_twin_patterns IS 'Versioned, scoped and reviewable hypotheses; never permanent user profiles.';
COMMENT ON TABLE formation_twin_pattern_evidence IS 'Metadata-only evidence references with counterevidence and independent-source controls.';
COMMENT ON TABLE formation_twin_temporal_graph_syncs IS 'Optional metadata graph receipts; no sensitive source body is projected.';

-- Operator-controlled rollback order:
-- DROP TABLE formation_twin_temporal_graph_syncs, formation_twin_pattern_processing_checkpoints,
-- formation_twin_pattern_rebuild_jobs, formation_twin_long_term_snapshots,
-- formation_twin_interpretation_preferences, formation_twin_pattern_reviews,
-- formation_twin_trajectory_points, formation_twin_trajectories, formation_twin_pattern_life_seasons,
-- formation_twin_life_seasons, formation_twin_pattern_lifecycle_events,
-- formation_twin_pattern_confidence_history, formation_twin_pattern_evidence,
-- formation_twin_patterns, formation_twin_event_cluster_members, formation_twin_event_clusters,
-- formation_twin_temporal_windows, formation_twin_temporal_settings;
