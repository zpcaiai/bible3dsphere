-- EMD-OS Batch 2: ten-dimension item bank, responses, extracted behavior evidence,
-- behaviorally anchored rubric results, consistency calibrations and sufficiency runs.
-- Item text is versioned and immutable: editing an item requires a new item_id or bank_version.

CREATE TABLE IF NOT EXISTS formation_twin_emd_item_banks (
    id UUID PRIMARY KEY,
    bank_version VARCHAR(60) NOT NULL,
    locale VARCHAR(16) NOT NULL DEFAULT 'zh-CN',
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    rubric_bundle_version VARCHAR(60) NOT NULL,
    coverage_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    registered_item_count INTEGER NOT NULL DEFAULT 0 CHECK(registered_item_count >= 0),
    calibration_status VARCHAR(24) NOT NULL DEFAULT 'estimated',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), retired_at TIMESTAMPTZ,
    UNIQUE(bank_version, locale),
    CHECK(status IN ('draft','reviewed','pilot','active','retired')),
    CHECK(calibration_status IN ('estimated','pilot_calibrated'))
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_items (
    id UUID PRIMARY KEY,
    item_id VARCHAR(40) NOT NULL,
    bank_version VARCHAR(60) NOT NULL,
    locale VARCHAR(16) NOT NULL DEFAULT 'zh-CN',
    dimension_code VARCHAR(8) NOT NULL,
    item_type VARCHAR(4) NOT NULL,
    canonical_text VARCHAR(400) NOT NULL,
    contexts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    response_mode VARCHAR(20) NOT NULL,
    estimated_difficulty NUMERIC NOT NULL DEFAULT 0.5 CHECK(estimated_difficulty BETWEEN 0 AND 1),
    estimated_discrimination NUMERIC NOT NULL DEFAULT 0.5 CHECK(estimated_discrimination BETWEEN 0 AND 1),
    calibration_status VARCHAR(24) NOT NULL DEFAULT 'estimated',
    reverse_keyed BOOLEAN NOT NULL DEFAULT FALSE,
    social_desirability_risk VARCHAR(10) NOT NULL DEFAULT 'medium',
    rubric_id VARCHAR(60) NOT NULL,
    safety_level VARCHAR(12) NOT NULL DEFAULT 'normal',
    requires_safety_gate BOOLEAN NOT NULL DEFAULT FALSE,
    burden VARCHAR(10) NOT NULL DEFAULT 'medium',
    status VARCHAR(12) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), retired_at TIMESTAMPTZ,
    -- immutability: one row per (item_id, bank_version, locale), never updated in place
    UNIQUE(item_id, bank_version, locale),
    CHECK(item_type IN ('SR','BE','SF','CF','RV')),
    CHECK(response_mode IN ('likert','frequency','open_text','forced_choice','ordered_options')),
    CHECK(safety_level IN ('normal','sensitive','restricted')),
    CHECK(status IN ('draft','reviewed','pilot','active','retired')),
    CHECK(item_type <> 'RV' OR reverse_keyed = TRUE),
    CHECK(item_type NOT IN ('BE','SF','CF') OR response_mode = 'open_text')
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_item_lookup ON formation_twin_emd_items(bank_version,dimension_code,item_type) WHERE retired_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_emd_responses (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    session_id UUID REFERENCES formation_twin_emd_sessions(id) ON DELETE CASCADE,
    response_id VARCHAR(80) NOT NULL,
    item_id VARCHAR(40) NOT NULL, bank_version VARCHAR(60) NOT NULL,
    dimension_code VARCHAR(8) NOT NULL,
    -- raw open text is deliberately NOT stored; only structured metadata and extracted spans
    response_length INTEGER NOT NULL DEFAULT 0 CHECK(response_length >= 0),
    response_choice VARCHAR(40),
    response_time_ms INTEGER CHECK(response_time_ms IS NULL OR response_time_ms >= 0),
    skipped BOOLEAN NOT NULL DEFAULT FALSE,
    user_confidence SMALLINT CHECK(user_confidence IS NULL OR user_confidence BETWEEN 1 AND 5),
    context_tags_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    occurred_in_real_life BOOLEAN NOT NULL DEFAULT FALSE,
    event_recency_days INTEGER CHECK(event_recency_days IS NULL OR event_recency_days >= 0),
    submitted_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, response_id)
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_response_owner ON formation_twin_emd_responses(email,dimension_code,submitted_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_emd_behavior_evidence (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    evidence_id VARCHAR(80) NOT NULL, response_id VARCHAR(80) NOT NULL,
    dimension_code VARCHAR(8) NOT NULL, source_type VARCHAR(30) NOT NULL,
    evidence_level VARCHAR(4) NOT NULL,
    extracted_features_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    unsupported_fields_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    context VARCHAR(40) NOT NULL DEFAULT 'OTHER', scenario_context VARCHAR(40),
    behavior_specificity NUMERIC NOT NULL DEFAULT 0 CHECK(behavior_specificity BETWEEN 0 AND 1),
    evidence_reliability NUMERIC NOT NULL DEFAULT 0 CHECK(evidence_reliability BETWEEN 0 AND 1),
    fact_inference_separated BOOLEAN NOT NULL DEFAULT TRUE,
    requires_user_confirmation BOOLEAN NOT NULL DEFAULT FALSE,
    user_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
    extractor_version VARCHAR(60) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, evidence_id),
    CHECK(evidence_level IN ('L1','L2','L3','L4','L5'))
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_behavior_evidence_owner ON formation_twin_emd_behavior_evidence(email,dimension_code,created_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_emd_rubric_results (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    rubric_result_id VARCHAR(80) NOT NULL, evidence_id VARCHAR(80) NOT NULL,
    dimension_code VARCHAR(8) NOT NULL,
    rubric_version VARCHAR(60) NOT NULL, rubric_bundle_version VARCHAR(60) NOT NULL,
    provisional_stage VARCHAR(4) NOT NULL,
    supported_anchors_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    missing_anchors_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    harmful_markers_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    caps_applied_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    source_type VARCHAR(30) NOT NULL, source_confidence VARCHAR(10) NOT NULL,
    source_weight NUMERIC NOT NULL CHECK(source_weight BETWEEN 0 AND 1),
    context VARCHAR(40) NOT NULL DEFAULT 'OTHER',
    is_stable_capacity BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, rubric_result_id),
    CHECK(provisional_stage IN ('E0','E1','E2','E3','E4','E5')),
    CHECK(source_confidence IN ('low','medium','high')),
    -- intention-only evidence can never claim a stable capacity
    CHECK(is_stable_capacity = FALSE OR source_type IN ('escalated_behavior','post_repair'))
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_rubric_owner ON formation_twin_emd_rubric_results(email,dimension_code,created_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_emd_scenarios (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    session_id UUID REFERENCES formation_twin_emd_sessions(id) ON DELETE CASCADE,
    scenario_id VARCHAR(80) NOT NULL, target_dimension VARCHAR(8) NOT NULL,
    axes_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    changed_axes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    stages_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    restrictions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(24) NOT NULL DEFAULT 'READY',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, scenario_id),
    CHECK(status IN ('READY','BLOCKED_BY_SAFETY','COMPLETED','ABANDONED'))
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_counterfactual_probes (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    probe_id VARCHAR(80) NOT NULL, base_item_id VARCHAR(40) NOT NULL,
    target_dimension VARCHAR(8) NOT NULL, changed_variable VARCHAR(40) NOT NULL,
    from_condition VARCHAR(40) NOT NULL, to_condition VARCHAR(40) NOT NULL,
    probe_text VARCHAR(400) NOT NULL,
    answered BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, probe_id)
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_probe_base ON formation_twin_emd_counterfactual_probes(email,base_item_id) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_emd_calibrations (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    calibration_id VARCHAR(80) NOT NULL, dimension_code VARCHAR(8) NOT NULL,
    consistency_status VARCHAR(24) NOT NULL,
    patterns_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    confidence_adjustment NUMERIC NOT NULL DEFAULT 0,
    clarification_needed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, calibration_id),
    CHECK(consistency_status IN ('consistent','context_dependent','needs_clarification'))
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_sufficiency_runs (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    session_id UUID REFERENCES formation_twin_emd_sessions(id) ON DELETE CASCADE,
    evidence_bundle_id VARCHAR(80) NOT NULL,
    decision VARCHAR(30) NOT NULL, assessment_status VARCHAR(40) NOT NULL,
    dimension_readiness_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    remaining_unknowns_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    items_asked INTEGER NOT NULL DEFAULT 0 CHECK(items_asked >= 0),
    fatigue NUMERIC NOT NULL DEFAULT 0 CHECK(fatigue BETWEEN 0 AND 1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, evidence_bundle_id),
    CHECK(decision IN ('continue_assessment','complete_assessment','pause_and_save','stop_assessment','stop_for_safety'))
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_sufficiency_owner ON formation_twin_emd_sufficiency_runs(email,created_at DESC) WHERE deleted_at IS NULL;

-- Owner RLS is defense in depth; the shared item bank itself carries no user data.
DO $$
DECLARE table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'formation_twin_emd_responses','formation_twin_emd_behavior_evidence',
    'formation_twin_emd_rubric_results','formation_twin_emd_scenarios',
    'formation_twin_emd_counterfactual_probes','formation_twin_emd_calibrations',
    'formation_twin_emd_sufficiency_runs'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS ft_owner_policy ON %I', table_name);
    EXECUTE format(
      'CREATE POLICY ft_owner_policy ON %I USING (email=current_setting(''app.current_user_email'',true)) '
      'WITH CHECK (email=current_setting(''app.current_user_email'',true))', table_name
    );
  END LOOP;
END $$;
