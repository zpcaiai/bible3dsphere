-- EMD-OS Batch 1: emotional maturity diagnostic governance inside Formation Twin.
-- Stores consent per scope, safety triage results, normalized evidence, per-dimension
-- snapshots, profiles, growth routes, user corrections and reassessment plans.
-- No raw narrative, no total maturity score, no spiritual verdict may be stored here.

CREATE TABLE IF NOT EXISTS formation_twin_emd_consents (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    consent_scope VARCHAR(60) NOT NULL,
    policy_version VARCHAR(32) NOT NULL DEFAULT 'emd-consent-1.0',
    status VARCHAR(20) NOT NULL DEFAULT 'GRANTED',
    limits_acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(), withdrawn_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(email, consent_scope, policy_version),
    CHECK(status IN ('GRANTED','WITHDRAWN','BLOCKED'))
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_consent_owner ON formation_twin_emd_consents(email,status,granted_at DESC);

CREATE TABLE IF NOT EXISTS formation_twin_emd_sessions (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    state VARCHAR(40) NOT NULL DEFAULT 'CONSENT_REQUESTED',
    granted_scopes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    safety_level VARCHAR(20) NOT NULL DEFAULT 'NONE',
    relationship_safety VARCHAR(20) NOT NULL DEFAULT 'STANDARD',
    triage_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    intake_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    validity_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    answered_count INTEGER NOT NULL DEFAULT 0 CHECK(answered_count >= 0),
    engine_version VARCHAR(60) NOT NULL, rule_version VARCHAR(60) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CHECK(safety_level IN ('NONE','CONCERN','ELEVATED','IMMINENT'))
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_session_owner ON formation_twin_emd_sessions(email,state,updated_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_emd_evidence_items (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    session_id UUID REFERENCES formation_twin_emd_sessions(id) ON DELETE CASCADE,
    evidence_id VARCHAR(160) NOT NULL,
    dimension_code VARCHAR(8) NOT NULL, evidence_kind VARCHAR(40) NOT NULL,
    context VARCHAR(40) NOT NULL DEFAULT 'OTHER', stage_signal VARCHAR(4) NOT NULL,
    statement_type VARCHAR(50) NOT NULL DEFAULT 'USER_REPORTED_FACT',
    user_confirmed BOOLEAN NOT NULL DEFAULT TRUE, self_rated BOOLEAN NOT NULL DEFAULT FALSE,
    independence_group VARCHAR(160),
    behavior_summary VARCHAR(240) NOT NULL DEFAULT '',
    references_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL, recorded_at TIMESTAMPTZ NOT NULL,
    excluded BOOLEAN NOT NULL DEFAULT FALSE, exclusion_reason VARCHAR(120),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, evidence_id),
    CHECK(stage_signal IN ('E0','E1','E2','E3','E4','E5')),
    CHECK(recorded_at >= occurred_at)
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_evidence_owner ON formation_twin_emd_evidence_items(email,dimension_code,occurred_at DESC) WHERE deleted_at IS NULL AND excluded = FALSE;

CREATE TABLE IF NOT EXISTS formation_twin_emd_dimension_snapshots (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    session_id UUID REFERENCES formation_twin_emd_sessions(id) ON DELETE CASCADE,
    dimension_code VARCHAR(8) NOT NULL, stage VARCHAR(4) NOT NULL,
    confidence VARCHAR(20) NOT NULL,
    evidence_count INTEGER NOT NULL DEFAULT 0 CHECK(evidence_count >= 0),
    evidence_weight NUMERIC NOT NULL DEFAULT 0 CHECK(evidence_weight >= 0),
    evidence_kinds_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    contexts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    context_differences_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    caps_applied_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    uncertainty_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    user_review_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    supersedes_snapshot_id UUID REFERENCES formation_twin_emd_dimension_snapshots(id) ON DELETE SET NULL,
    rule_version VARCHAR(60) NOT NULL, model_version VARCHAR(60) NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CHECK(stage IN ('E0','E1','E2','E3','E4','E5')),
    CHECK(confidence IN ('INSUFFICIENT','PROVISIONAL','MODERATE','HIGHER')),
    CHECK(user_review_status IN ('PENDING','USER_CONFIRMED','USER_DISPUTED','USER_CORRECTED')),
    -- A stage may never be asserted without supporting evidence.
    CHECK(confidence <> 'INSUFFICIENT' OR stage = 'E0')
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_snapshot_owner ON formation_twin_emd_dimension_snapshots(email,dimension_code,computed_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_emd_profiles (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    session_id UUID REFERENCES formation_twin_emd_sessions(id) ON DELETE CASCADE,
    model_version VARCHAR(60) NOT NULL, engine_version VARCHAR(60) NOT NULL,
    dimensions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    strengths_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    growth_invitations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    insufficient_dimensions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    validity_flags_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    limitations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    safety_level VARCHAR(20) NOT NULL DEFAULT 'NONE',
    relationship_safety VARCHAR(20) NOT NULL DEFAULT 'STANDARD',
    user_review_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    twin_update_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    input_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_profile_owner ON formation_twin_emd_profiles(email,created_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_emd_growth_routes (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    emd_profile_id UUID NOT NULL REFERENCES formation_twin_emd_profiles(id) ON DELETE CASCADE,
    route_type VARCHAR(30) NOT NULL DEFAULT 'TRAINING',
    schema_version VARCHAR(40) NOT NULL,
    assignments_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    checkpoints_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    limitations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    user_response VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    CHECK(route_type IN ('TRAINING','CARE_FIRST')),
    CHECK(user_response IN ('PENDING','ACCEPTED','DECLINED','PARTIAL'))
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_route_owner ON formation_twin_emd_growth_routes(email,created_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_emd_corrections (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    snapshot_id UUID REFERENCES formation_twin_emd_dimension_snapshots(id) ON DELETE SET NULL,
    dimension_code VARCHAR(8) NOT NULL, correction_type VARCHAR(40) NOT NULL,
    target_evidence_id VARCHAR(160),
    user_note TEXT,
    resulting_snapshot_id UUID REFERENCES formation_twin_emd_dimension_snapshots(id) ON DELETE SET NULL,
    twin_update_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    CHECK(correction_type IN ('DISPUTE_STAGE','EXCLUDE_EVIDENCE','CORRECT_CONTEXT','ADD_EVIDENCE','DECLINE_DIMENSION'))
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_correction_owner ON formation_twin_emd_corrections(email,created_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_emd_reassessment_plans (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    emd_profile_id UUID NOT NULL REFERENCES formation_twin_emd_profiles(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'SCHEDULED',
    dimensions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    checkpoints_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    rubric_version VARCHAR(60) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CHECK(status IN ('SCHEDULED','NOT_SCHEDULED','PAUSED','COMPLETED','CANCELLED'))
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_plan_owner ON formation_twin_emd_reassessment_plans(email,status,created_at DESC) WHERE deleted_at IS NULL;

-- Owner RLS is defense in depth; application queries also retain email predicates.
DO $$
DECLARE table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'formation_twin_emd_consents','formation_twin_emd_sessions',
    'formation_twin_emd_evidence_items','formation_twin_emd_dimension_snapshots',
    'formation_twin_emd_profiles','formation_twin_emd_growth_routes',
    'formation_twin_emd_corrections','formation_twin_emd_reassessment_plans'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS ft_owner_policy ON %I', table_name);
    EXECUTE format(
      'CREATE POLICY ft_owner_policy ON %I USING (email=current_setting(''app.current_user_email'',true)) '
      'WITH CHECK (email=current_setting(''app.current_user_email'',true))', table_name
    );
  END LOOP;
END $$;
