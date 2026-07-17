-- Formation Twin Batch 3: source-separated emotional observations and snapshots.

CREATE TABLE IF NOT EXISTS formation_twin_emotion_settings (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    emotion_engine_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    trends_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    model_inference_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    provider_policy VARCHAR(30) NOT NULL DEFAULT 'DISABLED',
    consent_version VARCHAR(20) NOT NULL DEFAULT '1.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, profile_id)
);

CREATE TABLE IF NOT EXISTS formation_twin_emotion_observations (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    life_event_id UUID REFERENCES formation_twin_life_events(id), parent_observation_id UUID,
    emotion_label VARCHAR(40) NOT NULL, custom_label VARCHAR(80), intensity INTEGER CHECK (intensity BETWEEN 0 AND 10),
    valence NUMERIC CHECK (valence BETWEEN -1 AND 1), arousal NUMERIC CHECK (arousal BETWEEN 0 AND 1),
    dominance NUMERIC CHECK (dominance BETWEEN 0 AND 1), source_kind VARCHAR(30) NOT NULL,
    statement_type VARCHAR(40) NOT NULL, occurred_at TIMESTAMPTZ NOT NULL, observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    confidence NUMERIC CHECK (confidence BETWEEN 0 AND 1), model_version VARCHAR(120), prompt_version VARCHAR(60),
    schema_version VARCHAR(40), rule_version VARCHAR(60), evidence_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    alternative_labels JSONB NOT NULL DEFAULT '[]'::jsonb, user_review_status VARCHAR(30) NOT NULL,
    processing_status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE', revision INTEGER NOT NULL DEFAULT 1,
    supersedes_id UUID REFERENCES formation_twin_emotion_observations(id), created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='ft_emotion_parent_fk') THEN
    ALTER TABLE formation_twin_emotion_observations ADD CONSTRAINT ft_emotion_parent_fk
      FOREIGN KEY (parent_observation_id) REFERENCES formation_twin_emotion_observations(id);
  END IF;
END $$;
CREATE UNIQUE INDEX IF NOT EXISTS idx_ft_emotion_event_label_source
    ON formation_twin_emotion_observations(email, life_event_id, emotion_label, COALESCE(custom_label, ''), source_kind)
    WHERE life_event_id IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_ft_emotion_owner_time ON formation_twin_emotion_observations(email, occurred_at DESC);

CREATE TABLE IF NOT EXISTS formation_twin_emotion_evidence (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, email TEXT NOT NULL,
    emotion_observation_id UUID NOT NULL REFERENCES formation_twin_emotion_observations(id) ON DELETE CASCADE,
    life_event_id UUID REFERENCES formation_twin_life_events(id), content_reference_id UUID REFERENCES formation_twin_sensitive_contents(id),
    evidence_type VARCHAR(30) NOT NULL, start_offset INTEGER, end_offset INTEGER, evidence_hash VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), CHECK (start_offset IS NULL OR end_offset > start_offset)
);

CREATE TABLE IF NOT EXISTS formation_twin_body_observations (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    life_event_id UUID REFERENCES formation_twin_life_events(id), body_label VARCHAR(60) NOT NULL,
    custom_label VARCHAR(80), body_region VARCHAR(60), intensity INTEGER CHECK (intensity BETWEEN 0 AND 10),
    source_kind VARCHAR(30) NOT NULL, statement_type VARCHAR(40) NOT NULL, occurred_at TIMESTAMPTZ NOT NULL,
    confidence NUMERIC CHECK (confidence BETWEEN 0 AND 1), user_review_status VARCHAR(30) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ft_body_event_label
    ON formation_twin_body_observations(email, life_event_id, body_label)
    WHERE life_event_id IS NOT NULL AND deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_energy_stress_observations (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    life_event_id UUID REFERENCES formation_twin_life_events(id), energy_level INTEGER CHECK (energy_level BETWEEN 0 AND 10),
    stress_level INTEGER CHECK (stress_level BETWEEN 0 AND 10), sleep_quality INTEGER CHECK (sleep_quality BETWEEN 0 AND 10),
    restfulness INTEGER CHECK (restfulness BETWEEN 0 AND 10), mental_load INTEGER CHECK (mental_load BETWEEN 0 AND 10),
    source_kind VARCHAR(30) NOT NULL, statement_type VARCHAR(40) NOT NULL, occurred_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ft_energy_event ON formation_twin_energy_stress_observations(email, life_event_id) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_emotional_episodes (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    title VARCHAR(160), episode_type VARCHAR(40) NOT NULL, creation_method VARCHAR(30) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL, ended_at TIMESTAMPTZ, life_domains JSONB NOT NULL DEFAULT '[]'::jsonb,
    primary_emotions JSONB NOT NULL DEFAULT '[]'::jsonb, secondary_emotions JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(30) NOT NULL, user_review_status VARCHAR(30) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS formation_twin_episode_events (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, email TEXT NOT NULL,
    episode_id UUID NOT NULL REFERENCES formation_twin_emotional_episodes(id) ON DELETE CASCADE,
    life_event_id UUID NOT NULL REFERENCES formation_twin_life_events(id), relation_type VARCHAR(30) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(episode_id, life_event_id)
);

CREATE TABLE IF NOT EXISTS formation_twin_emotional_snapshots (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    snapshot_type VARCHAR(40) NOT NULL, window_start TIMESTAMPTZ NOT NULL, window_end TIMESTAMPTZ NOT NULL,
    data_status VARCHAR(30) NOT NULL, data_coverage_json JSONB NOT NULL, user_reported_state_json JSONB NOT NULL,
    rule_derived_state_json JSONB NOT NULL, model_inferred_state_json JSONB NOT NULL,
    current_candidates_json JSONB NOT NULL, conflicts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    uncertainty_json JSONB NOT NULL, limitations_json JSONB NOT NULL, user_review_status VARCHAR(30) NOT NULL,
    version INTEGER NOT NULL, engine_version VARCHAR(60) NOT NULL, input_hash VARCHAR(64) NOT NULL,
    supersedes_snapshot_id UUID REFERENCES formation_twin_emotional_snapshots(id), superseded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(email, snapshot_type, input_hash),
    CHECK (window_end >= window_start)
);

CREATE TABLE IF NOT EXISTS formation_twin_inference_reviews (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    emotion_observation_id UUID NOT NULL REFERENCES formation_twin_emotion_observations(id), review_action VARCHAR(30) NOT NULL,
    original_label VARCHAR(40), user_label VARCHAR(40), user_comment TEXT, created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), revoked_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS formation_twin_emotion_rule_results (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    metric_type VARCHAR(50) NOT NULL, metric_value JSONB NOT NULL, window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL, rule_version VARCHAR(60) NOT NULL, data_point_count INTEGER NOT NULL,
    coverage NUMERIC CHECK (coverage BETWEEN 0 AND 1), evidence_event_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS formation_twin_emotion_model_runs (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, email TEXT NOT NULL, request_id UUID NOT NULL,
    provider VARCHAR(40), model_name VARCHAR(120), model_version VARCHAR(120), prompt_template_version VARCHAR(60),
    schema_version VARCHAR(40), latency_ms INTEGER, token_usage JSONB NOT NULL DEFAULT '{}'::jsonb,
    result_status VARCHAR(40) NOT NULL, redacted_error_code VARCHAR(80), created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS is defense in depth; application queries remain explicitly owner-scoped.
DO $$
DECLARE table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'formation_twin_emotion_settings','formation_twin_emotion_observations','formation_twin_emotion_evidence',
    'formation_twin_body_observations','formation_twin_energy_stress_observations','formation_twin_emotional_episodes',
    'formation_twin_episode_events','formation_twin_emotional_snapshots','formation_twin_inference_reviews',
    'formation_twin_emotion_rule_results','formation_twin_emotion_model_runs'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS ft_owner_policy ON %I', table_name);
    EXECUTE format('CREATE POLICY ft_owner_policy ON %I USING (email = current_setting(''app.current_user_email'', true)) WITH CHECK (email = current_setting(''app.current_user_email'', true))', table_name);
  END LOOP;
END $$;

COMMENT ON TABLE formation_twin_emotion_observations IS 'Source-separated emotional observations; no diagnosis or full sensitive text.';

-- Rollback (repository convention; destructive and operator-controlled):
-- DROP TABLE formation_twin_emotion_model_runs, formation_twin_emotion_rule_results,
-- formation_twin_inference_reviews, formation_twin_emotional_snapshots,
-- formation_twin_episode_events, formation_twin_emotional_episodes,
-- formation_twin_energy_stress_observations, formation_twin_body_observations,
-- formation_twin_emotion_evidence, formation_twin_emotion_observations,
-- formation_twin_emotion_settings;
