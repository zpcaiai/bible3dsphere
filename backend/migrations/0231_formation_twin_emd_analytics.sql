-- EMD-OS Batch 9: metric catalog, adaptive reassessment, comparability, trajectories,
-- generalization analytics, attribution/regression calibration and user-controlled reports.
-- No table in this batch may ever store a total score, a life index or a cross-user ranking.

CREATE TABLE IF NOT EXISTS formation_twin_emd_metric_catalog (
    id UUID PRIMARY KEY,
    metric_code VARCHAR(60) NOT NULL,
    version VARCHAR(12) NOT NULL DEFAULT 'v1',
    display_name VARCHAR(60) NOT NULL,
    domain VARCHAR(20) NOT NULL,
    description VARCHAR(240) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    numerator_definition VARCHAR(240) NOT NULL DEFAULT '',
    denominator_definition VARCHAR(240) NOT NULL DEFAULT '',
    eligible_evidence_types_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    forbidden_interpretations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(10) NOT NULL DEFAULT 'DRAFT',
    frozen_at TIMESTAMPTZ, retired_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- one definition per (code, version); changing semantics requires a new version
    UNIQUE(metric_code, version),
    CHECK(domain IN ('BEHAVIOR','RECOVERY','REPAIR','TRANSFER','PRACTICE','SAFETY','EXPERIENCE')),
    CHECK(unit IN ('RATE','COUNT','DURATION_SECONDS','STAGE','LEVEL')),
    CHECK(status IN ('DRAFT','ACTIVE','FROZEN','RETIRED')),
    CHECK(unit <> 'RATE' OR (numerator_definition <> '' AND denominator_definition <> '')),
    CHECK(jsonb_array_length(eligible_evidence_types_json) > 0)
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_metric_observations (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    metric_code VARCHAR(60) NOT NULL, metric_version VARCHAR(12) NOT NULL,
    value NUMERIC,
    evidence_type VARCHAR(32) NOT NULL,
    source_event_id VARCHAR(80),
    observed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_metric_obs_owner ON formation_twin_emd_metric_observations(email,metric_code,observed_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_emd_reassessment_compositions (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    composition_id VARCHAR(80) NOT NULL,
    day INTEGER NOT NULL CHECK(day IN (14,30,90)),
    selected_items_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    excluded_skipped_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    item_budget INTEGER NOT NULL DEFAULT 12 CHECK(item_budget > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, composition_id)
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_comparability_checks (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    reconciliation_id VARCHAR(80) NOT NULL,
    comparable BOOLEAN NOT NULL DEFAULT FALSE,
    verdict VARCHAR(24) NOT NULL,
    changed_components_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    stage_change INTEGER NOT NULL DEFAULT 0,
    measurement_error INTEGER NOT NULL DEFAULT 1 CHECK(measurement_error >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, reconciliation_id),
    CHECK(verdict IN ('NOT_COMPARABLE','CHANGE_NOT_CONFIRMED','COMPARABLE_CHANGE')),
    -- a comparable change is only claimed when nothing versioned changed
    CHECK(verdict <> 'COMPARABLE_CHANGE' OR comparable = TRUE)
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_trajectories (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    trajectory_id VARCHAR(80) NOT NULL,
    domain VARCHAR(20) NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'ANALYSED',
    direction VARCHAR(12),
    early_median NUMERIC, late_median NUMERIC, delta NUMERIC,
    point_count INTEGER NOT NULL DEFAULT 0 CHECK(point_count >= 0),
    change_point_json JSONB,
    -- trajectories describe data, never causes
    causal_claim BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, trajectory_id),
    CHECK(direction IS NULL OR direction IN ('IMPROVING','STABLE','WORSENING')),
    CHECK(causal_claim = FALSE)
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_generalizations (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    generalization_id VARCHAR(80) NOT NULL,
    level VARCHAR(2) NOT NULL DEFAULT 'G0',
    contexts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    per_context_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    high_pressure_events INTEGER NOT NULL DEFAULT 0 CHECK(high_pressure_events >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, generalization_id),
    CHECK(level IN ('G0','G1','G2','G3','G4'))
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_attributions (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    attribution_id VARCHAR(80) NOT NULL,
    observed_change VARCHAR(240) NOT NULL,
    attribution_claim VARCHAR(20) NOT NULL DEFAULT 'CORRELATION_ONLY',
    alternative_explanations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    regression_signals_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    regression_severity VARCHAR(16) NOT NULL DEFAULT 'NONE',
    evidence_sufficiency VARCHAR(12) NOT NULL DEFAULT 'LIMITED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, attribution_id),
    CHECK(attribution_claim = 'CORRELATION_ONLY'),
    CHECK(regression_severity IN ('NONE','WATCH','ELEVATED','SAFETY_FIRST')),
    -- an attribution always ships with at least one alternative explanation
    CHECK(jsonb_array_length(alternative_explanations_json) > 0)
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_growth_reports (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    report_id VARCHAR(80) NOT NULL,
    view VARCHAR(12) NOT NULL DEFAULT 'PRIVATE',
    status VARCHAR(32) NOT NULL DEFAULT 'DRAFT_AWAITING_USER_APPROVAL',
    sections_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    user_approved BOOLEAN NOT NULL DEFAULT FALSE,
    -- reports never carry a score, an index or a ranking
    total_score NUMERIC, ranking INTEGER,
    auto_shared BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ, revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, report_id),
    CHECK(view IN ('PRIVATE','PASTORAL','GROUP')),
    CHECK(status IN ('DRAFT_AWAITING_USER_APPROVAL','PUBLISHED','BLOCKED_NO_CONSENT','REVOKED','EXPIRED','DISCARDED')),
    CHECK(total_score IS NULL),
    CHECK(ranking IS NULL),
    CHECK(auto_shared = FALSE),
    CHECK(status <> 'PUBLISHED' OR user_approved = TRUE),
    -- any shared view must expire
    CHECK(view = 'PRIVATE' OR status <> 'PUBLISHED' OR expires_at IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_report_owner ON formation_twin_emd_growth_reports(email,view,created_at DESC) WHERE deleted_at IS NULL;

-- Owner RLS is defense in depth; the metric catalog itself carries no user data.
DO $$
DECLARE table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'formation_twin_emd_metric_observations','formation_twin_emd_reassessment_compositions',
    'formation_twin_emd_comparability_checks','formation_twin_emd_trajectories',
    'formation_twin_emd_generalizations','formation_twin_emd_attributions',
    'formation_twin_emd_growth_reports'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS ft_owner_policy ON %I', table_name);
    EXECUTE format(
      'CREATE POLICY ft_owner_policy ON %I USING (email=current_setting(''app.current_user_email'',true)) '
      'WITH CHECK (email=current_setting(''app.current_user_email'',true))', table_name
    );
  END LOOP;
END $$;
