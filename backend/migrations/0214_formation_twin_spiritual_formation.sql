-- Formation Twin Batch 4: source-separated spiritual formation chains.
-- No salvation, maturity, holiness, sin, idol, or spiritual score is stored.

CREATE TABLE IF NOT EXISTS formation_twin_formation_settings (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    spiritual_engine_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    formation_chain_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    belief_hypothesis_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    graph_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    theological_validator_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    prayer_context_consent BOOLEAN NOT NULL DEFAULT FALSE,
    habit_context_consent BOOLEAN NOT NULL DEFAULT FALSE,
    attention_context_consent BOOLEAN NOT NULL DEFAULT FALSE,
    formation_context_consent BOOLEAN NOT NULL DEFAULT FALSE,
    provider_policy VARCHAR(30) NOT NULL DEFAULT 'DISABLED',
    consent_version VARCHAR(20) NOT NULL DEFAULT '1.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, profile_id)
);

-- Canonical, immutable source records for the main formation categories.
CREATE TABLE IF NOT EXISTS formation_twin_identity_statements (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    content TEXT NOT NULL, source_kind VARCHAR(30) NOT NULL, statement_type VARCHAR(60) NOT NULL,
    scope VARCHAR(30) NOT NULL, user_review_status VARCHAR(30) NOT NULL, life_event_id UUID REFERENCES formation_twin_life_events(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS formation_twin_interpretations (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    content TEXT NOT NULL, source_kind VARCHAR(30) NOT NULL, statement_type VARCHAR(60) NOT NULL,
    scope VARCHAR(30) NOT NULL, user_review_status VARCHAR(30) NOT NULL, life_event_id UUID REFERENCES formation_twin_life_events(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS formation_twin_belief_statements (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    content TEXT NOT NULL, source_kind VARCHAR(30) NOT NULL, statement_type VARCHAR(60) NOT NULL,
    scope VARCHAR(30) NOT NULL, user_review_status VARCHAR(30) NOT NULL, life_event_id UUID REFERENCES formation_twin_life_events(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS formation_twin_desire_observations (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    content TEXT NOT NULL, source_kind VARCHAR(30) NOT NULL, statement_type VARCHAR(60) NOT NULL,
    scope VARCHAR(30) NOT NULL, user_review_status VARCHAR(30) NOT NULL, life_event_id UUID REFERENCES formation_twin_life_events(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS formation_twin_fear_observations (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    content TEXT NOT NULL, source_kind VARCHAR(30) NOT NULL, statement_type VARCHAR(60) NOT NULL,
    scope VARCHAR(30) NOT NULL, user_review_status VARCHAR(30) NOT NULL, life_event_id UUID REFERENCES formation_twin_life_events(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS formation_twin_temptation_observations (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    content TEXT NOT NULL, source_kind VARCHAR(30) NOT NULL, statement_type VARCHAR(60) NOT NULL,
    scope VARCHAR(30) NOT NULL, user_review_status VARCHAR(30) NOT NULL, life_event_id UUID REFERENCES formation_twin_life_events(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS formation_twin_behavior_observations (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    content TEXT NOT NULL, behavior_kind VARCHAR(40), source_kind VARCHAR(30) NOT NULL, statement_type VARCHAR(60) NOT NULL,
    scope VARCHAR(30) NOT NULL, user_review_status VARCHAR(30) NOT NULL, life_event_id UUID REFERENCES formation_twin_life_events(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS formation_twin_outcome_observations (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    content TEXT NOT NULL, source_kind VARCHAR(30) NOT NULL, statement_type VARCHAR(60) NOT NULL,
    scope VARCHAR(30) NOT NULL, user_review_status VARCHAR(30) NOT NULL, life_event_id UUID REFERENCES formation_twin_life_events(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS formation_twin_formation_nodes (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    node_type VARCHAR(40) NOT NULL, content TEXT NOT NULL, canonical_record_type VARCHAR(60), canonical_record_id UUID,
    life_event_id UUID REFERENCES formation_twin_life_events(id),
    emotion_observation_id UUID REFERENCES formation_twin_emotion_observations(id),
    source_kind VARCHAR(30) NOT NULL, statement_type VARCHAR(60) NOT NULL, scope VARCHAR(30) NOT NULL DEFAULT 'THIS_EVENT_ONLY',
    confidence NUMERIC CHECK (confidence BETWEEN 0 AND 1), alternatives_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence_json JSONB NOT NULL DEFAULT '[]'::jsonb, user_review_status VARCHAR(30) NOT NULL,
    processing_status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE', model_version VARCHAR(120), prompt_version VARCHAR(60),
    schema_version VARCHAR(40), rule_version VARCHAR(60), revision INTEGER NOT NULL DEFAULT 1,
    supersedes_id UUID REFERENCES formation_twin_formation_nodes(id), expires_at TIMESTAMPTZ,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(), created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    CHECK (NOT (source_kind='USER_REPORT' AND confidence IS NOT NULL)),
    CHECK (NOT (source_kind='MODEL' AND statement_type NOT IN ('MODEL_EXTRACTED_EXPLICIT_EXPRESSION','MODEL_FORMATION_HYPOTHESIS')))
);
CREATE INDEX IF NOT EXISTS idx_ft_formation_nodes_owner_type ON formation_twin_formation_nodes(email,node_type,created_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_ft_formation_nodes_event ON formation_twin_formation_nodes(email,life_event_id) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_formation_evidence (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    node_id UUID NOT NULL REFERENCES formation_twin_formation_nodes(id) ON DELETE CASCADE,
    life_event_id UUID REFERENCES formation_twin_life_events(id), content_reference_id UUID REFERENCES formation_twin_sensitive_contents(id),
    evidence_type VARCHAR(30) NOT NULL, start_offset INTEGER, end_offset INTEGER, evidence_hash VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), CHECK (start_offset IS NULL OR end_offset > start_offset)
);

CREATE TABLE IF NOT EXISTS formation_twin_formation_edges (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    source_node_id UUID NOT NULL REFERENCES formation_twin_formation_nodes(id),
    target_node_id UUID NOT NULL REFERENCES formation_twin_formation_nodes(id),
    relation_type VARCHAR(50) NOT NULL, source_kind VARCHAR(30) NOT NULL, statement_type VARCHAR(60) NOT NULL,
    confidence NUMERIC CHECK (confidence BETWEEN 0 AND 1), evidence_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    alternatives_json JSONB NOT NULL DEFAULT '[]'::jsonb, user_review_status VARCHAR(30) NOT NULL,
    processing_status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE', rule_version VARCHAR(60),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    CHECK (source_node_id<>target_node_id), CHECK (relation_type NOT IN ('CAUSED','PROVED','DETERMINED'))
);

CREATE TABLE IF NOT EXISTS formation_twin_formation_chains (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    title VARCHAR(160) NOT NULL DEFAULT '', life_event_id UUID REFERENCES formation_twin_life_events(id),
    creation_method VARCHAR(30) NOT NULL, scope VARCHAR(30) NOT NULL DEFAULT 'THIS_EVENT_ONLY',
    completeness NUMERIC NOT NULL DEFAULT 0 CHECK (completeness BETWEEN 0 AND 1),
    user_review_status VARCHAR(30) NOT NULL, processing_status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    limitations_json JSONB NOT NULL DEFAULT '[]'::jsonb, alternative_of_chain_id UUID REFERENCES formation_twin_formation_chains(id),
    excluded_from_context BOOLEAN NOT NULL DEFAULT FALSE, version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_ft_formation_chains_owner ON formation_twin_formation_chains(email,created_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_chain_nodes (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    chain_id UUID NOT NULL REFERENCES formation_twin_formation_chains(id) ON DELETE CASCADE,
    node_id UUID NOT NULL REFERENCES formation_twin_formation_nodes(id), sequence_order INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(chain_id,node_id), UNIQUE(chain_id,sequence_order)
);
CREATE TABLE IF NOT EXISTS formation_twin_chain_edges (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    chain_id UUID NOT NULL REFERENCES formation_twin_formation_chains(id) ON DELETE CASCADE,
    edge_id UUID NOT NULL REFERENCES formation_twin_formation_edges(id), sequence_order INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(chain_id,edge_id)
);

CREATE TABLE IF NOT EXISTS formation_twin_formation_snapshots (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    snapshot_type VARCHAR(40) NOT NULL, window_start TIMESTAMPTZ NOT NULL, window_end TIMESTAMPTZ NOT NULL,
    data_status VARCHAR(30) NOT NULL, user_reported_json JSONB NOT NULL, observed_relations_json JSONB NOT NULL,
    confirmed_patterns_json JSONB NOT NULL, pending_hypotheses_json JSONB NOT NULL, grace_recovery_json JSONB NOT NULL,
    directions_json JSONB NOT NULL, tensions_json JSONB NOT NULL, reflective_questions_json JSONB NOT NULL,
    limitations_json JSONB NOT NULL, coverage_json JSONB NOT NULL, version INTEGER NOT NULL,
    engine_version VARCHAR(60) NOT NULL, input_hash VARCHAR(64) NOT NULL,
    supersedes_snapshot_id UUID REFERENCES formation_twin_formation_snapshots(id), superseded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(email,snapshot_type,input_hash), CHECK (window_end>=window_start)
);

CREATE TABLE IF NOT EXISTS formation_twin_formation_reviews (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    node_id UUID REFERENCES formation_twin_formation_nodes(id), edge_id UUID REFERENCES formation_twin_formation_edges(id),
    chain_id UUID REFERENCES formation_twin_formation_chains(id), review_action VARCHAR(30) NOT NULL,
    scope VARCHAR(30), replacement_content TEXT, user_comment TEXT, created_by TEXT NOT NULL,
    confirmed_record_id UUID, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), revoked_at TIMESTAMPTZ,
    CHECK (num_nonnulls(node_id,edge_id,chain_id)=1)
);

CREATE TABLE IF NOT EXISTS formation_twin_formation_model_runs (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    request_id UUID NOT NULL, provider VARCHAR(40), model_name VARCHAR(120), prompt_version VARCHAR(60), schema_version VARCHAR(40),
    result_status VARCHAR(40) NOT NULL, candidate_count INTEGER NOT NULL DEFAULT 0, redacted_error_code VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS formation_twin_graph_syncs (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    chain_id UUID REFERENCES formation_twin_formation_chains(id), sync_status VARCHAR(30) NOT NULL,
    node_count INTEGER NOT NULL DEFAULT 0, edge_count INTEGER NOT NULL DEFAULT 0, error_code VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$
DECLARE table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'formation_twin_formation_settings','formation_twin_identity_statements','formation_twin_interpretations',
    'formation_twin_belief_statements','formation_twin_desire_observations','formation_twin_fear_observations',
    'formation_twin_temptation_observations','formation_twin_behavior_observations','formation_twin_outcome_observations',
    'formation_twin_formation_nodes','formation_twin_formation_evidence','formation_twin_formation_edges',
    'formation_twin_formation_chains','formation_twin_chain_nodes','formation_twin_chain_edges',
    'formation_twin_formation_snapshots','formation_twin_formation_reviews','formation_twin_formation_model_runs',
    'formation_twin_graph_syncs'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS ft_owner_policy ON %I', table_name);
    EXECUTE format('CREATE POLICY ft_owner_policy ON %I USING (email=current_setting(''app.current_user_email'',true)) WITH CHECK (email=current_setting(''app.current_user_email'',true))', table_name);
  END LOOP;
END $$;

COMMENT ON TABLE formation_twin_formation_nodes IS 'Reviewable formation observations; hypotheses stay separate from user-confirmed records.';
COMMENT ON TABLE formation_twin_graph_syncs IS 'Metadata-only graph projection receipts; never full diary, prayer, confession, temptation, transcript, or crisis text.';

-- Rollback (repository convention; destructive and operator-controlled):
-- DROP TABLE formation_twin_graph_syncs, formation_twin_formation_model_runs, formation_twin_formation_reviews,
-- formation_twin_formation_snapshots, formation_twin_chain_edges, formation_twin_chain_nodes,
-- formation_twin_formation_chains, formation_twin_formation_edges, formation_twin_formation_evidence,
-- formation_twin_formation_nodes, formation_twin_outcome_observations, formation_twin_behavior_observations,
-- formation_twin_temptation_observations, formation_twin_fear_observations, formation_twin_desire_observations,
-- formation_twin_belief_statements, formation_twin_interpretations, formation_twin_identity_statements,
-- formation_twin_formation_settings;
