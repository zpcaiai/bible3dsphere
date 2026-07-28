-- EMD-OS Batch 5: three-generation genograms, family scripts and triangles,
-- attachment activation cycles, differentiation, early survival oaths, false-self masks,
-- the true-self compass and graded vulnerability experiments.
-- Family members are recorded as observable behaviour only; no third party is ever diagnosed.

CREATE TABLE IF NOT EXISTS formation_twin_emd_genograms (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    genogram_id VARCHAR(80) NOT NULL,
    member_count INTEGER NOT NULL DEFAULT 0 CHECK(member_count >= 0),
    generations_covered_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    members_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    relationships_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    memory_sources_used_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(28) NOT NULL DEFAULT 'DRAFT_USER_CONTROLLED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    UNIQUE(email, genogram_id),
    CHECK(status IN ('DRAFT_USER_CONTROLLED','USER_CONFIRMED','ARCHIVED'))
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_family_patterns (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    analysis_id VARCHAR(80) NOT NULL, genogram_id VARCHAR(80),
    pattern_kind VARCHAR(12) NOT NULL,
    pattern_code VARCHAR(48) NOT NULL, pattern_text VARCHAR(200),
    evidence_level VARCHAR(4) NOT NULL DEFAULT 'FP0',
    may_write_to_twin BOOLEAN NOT NULL DEFAULT FALSE,
    detail_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    user_review_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    CHECK(pattern_kind IN ('SCRIPT','ROLE','TRIANGLE')),
    CHECK(evidence_level IN ('FP0','FP1','FP2','FP3','FP4','FP5')),
    CHECK(user_review_status IN ('PENDING','USER_CONFIRMED','USER_DISPUTED','USER_CORRECTED')),
    -- only FP4+ patterns may ever be promoted into the long-term twin
    CHECK(may_write_to_twin = FALSE OR evidence_level IN ('FP4','FP5'))
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_family_pattern_owner ON formation_twin_emd_family_patterns(email,pattern_kind,created_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_emd_attachment_cycles (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    cycle_id VARCHAR(80) NOT NULL,
    relationship_context VARCHAR(32) NOT NULL,
    trigger_condition VARCHAR(160) NOT NULL,
    pressure_level VARCHAR(12) NOT NULL DEFAULT 'medium',
    timeframe_days INTEGER NOT NULL DEFAULT 90 CHECK(timeframe_days > 0),
    dominant_protective_action VARCHAR(16) NOT NULL DEFAULT 'UNKNOWN',
    event_count INTEGER NOT NULL DEFAULT 0 CHECK(event_count >= 0),
    repair_count INTEGER NOT NULL DEFAULT 0 CHECK(repair_count >= 0),
    other_contexts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence_level VARCHAR(4) NOT NULL DEFAULT 'FP0',
    may_write_to_twin BOOLEAN NOT NULL DEFAULT FALSE,
    -- an attachment "type" is never stored; the column exists only to stay NULL
    attachment_type_assigned VARCHAR(1),
    user_review_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, cycle_id),
    CHECK(dominant_protective_action IN ('PURSUE','WITHDRAW','CONTROL','MIXED','UNKNOWN')),
    CHECK(evidence_level IN ('FP0','FP1','FP2','FP3','FP4','FP5')),
    CHECK(attachment_type_assigned IS NULL)
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_differentiation_assessments (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    assessment_id VARCHAR(80) NOT NULL,
    stage VARCHAR(4) NOT NULL,
    event_count INTEGER NOT NULL DEFAULT 0 CHECK(event_count >= 0),
    practice_blocked_while_activated BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, assessment_id),
    CHECK(stage IN ('SD0','SD1','SD2','SD3','SD4','SD5'))
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_survival_oaths (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    oath_id VARCHAR(80) NOT NULL,
    oath_text VARCHAR(200) NOT NULL,
    memory_source VARCHAR(24) NOT NULL,
    language_used VARCHAR(32) NOT NULL DEFAULT 'PAST_SELF',
    current_cost VARCHAR(240),
    adult_commitment VARCHAR(240),
    spiritual_integration_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(20) NOT NULL DEFAULT 'REFRAMED_DRAFT',
    user_review_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, oath_id),
    -- system hypotheses and vague impressions may never become stored family material
    CHECK(memory_source IN ('direct_memory','family_account','record_or_photo')),
    CHECK(language_used IN ('PAST_SELF','INNER_CHILD','EARLY_SURVIVAL_RESPONSE','OLD_CORE_BELIEF')),
    CHECK(status IN ('REFRAMED_DRAFT','USER_CONFIRMED','DECLINED','RETIRED'))
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_mask_profiles (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    mask_profile_id VARCHAR(80) NOT NULL,
    mask_code VARCHAR(40) NOT NULL,
    contexts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence_level VARCHAR(4) NOT NULL DEFAULT 'FP0',
    may_write_to_twin BOOLEAN NOT NULL DEFAULT FALSE,
    user_review_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    CHECK(evidence_level IN ('FP0','FP1','FP2','FP3','FP4','FP5')),
    CHECK(may_write_to_twin = FALSE OR evidence_level IN ('FP4','FP5'))
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_true_self_compasses (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    compass_id VARCHAR(80) NOT NULL,
    parts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    missing_parts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    completeness NUMERIC NOT NULL DEFAULT 0 CHECK(completeness BETWEEN 0 AND 1),
    adult_commitment VARCHAR(240) NOT NULL,
    masks_replaced_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    UNIQUE(email, compass_id)
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_vulnerability_experiments (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    experiment_id VARCHAR(80) NOT NULL, compass_id VARCHAR(80),
    target_relationship_type VARCHAR(32) NOT NULL,
    safety_status VARCHAR(10) NOT NULL,
    depth VARCHAR(2),
    depth_caps_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    target_issue VARCHAR(240) NOT NULL,
    expression_structure_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(28) NOT NULL DEFAULT 'READY',
    outcome VARCHAR(24) NOT NULL DEFAULT 'PENDING',
    linked_event_id VARCHAR(80),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, experiment_id),
    CHECK(safety_status IN ('SAFE','CAUTION','UNSAFE','UNKNOWN')),
    CHECK(depth IS NULL OR depth IN ('V1','V2','V3','V4','V5')),
    CHECK(status IN ('READY','NOT_GENERATED_UNSAFE','DEFERRED_HIGH_ACTIVATION','COMPLETED','ABANDONED')),
    CHECK(outcome IN ('PENDING','EXPRESSED','PARTIALLY_EXPRESSED','NOT_ATTEMPTED')),
    -- unsafe relationships never carry a disclosure depth
    CHECK(safety_status <> 'UNSAFE' OR depth IS NULL),
    -- caution and unknown safety cap disclosure at V2
    CHECK(safety_status NOT IN ('CAUTION','UNKNOWN') OR depth IS NULL OR depth IN ('V1','V2'))
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_vex_owner ON formation_twin_emd_vulnerability_experiments(email,created_at DESC) WHERE deleted_at IS NULL;

-- Owner RLS is defense in depth; application queries also retain email predicates.
DO $$
DECLARE table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'formation_twin_emd_genograms','formation_twin_emd_family_patterns',
    'formation_twin_emd_attachment_cycles','formation_twin_emd_differentiation_assessments',
    'formation_twin_emd_survival_oaths','formation_twin_emd_mask_profiles',
    'formation_twin_emd_true_self_compasses','formation_twin_emd_vulnerability_experiments'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS ft_owner_policy ON %I', table_name);
    EXECUTE format(
      'CREATE POLICY ft_owner_policy ON %I USING (email=current_setting(''app.current_user_email'',true)) '
      'WITH CHECK (email=current_setting(''app.current_user_email'',true))', table_name
    );
  END LOOP;
END $$;
