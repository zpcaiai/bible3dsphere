-- EMD-OS Batch 6: empathy, boundaries, clean conflict, apology, forgiveness and repair.
-- Boundaries record what the user will do; the other party's response is stored for the
-- user's own reflection and never changes a stage or a trust level.

CREATE TABLE IF NOT EXISTS formation_twin_emd_boundaries (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    boundary_id VARCHAR(80) NOT NULL,
    boundary_object VARCHAR(32) NOT NULL,
    boundary_kind VARCHAR(10) NOT NULL,
    boundary_statement VARCHAR(240) NOT NULL,
    responsibility_map_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    action_if_violated VARCHAR(240) NOT NULL,
    relationship_context VARCHAR(32),
    relationship_safety VARCHAR(10) NOT NULL DEFAULT 'UNKNOWN',
    power_asymmetry VARCHAR(10) NOT NULL DEFAULT 'LOW',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, boundary_id),
    CHECK(boundary_kind IN ('REQUEST','LIMIT')),
    CHECK(relationship_safety IN ('SAFE','CAUTION','UNSAFE','UNKNOWN'))
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_boundary_owner ON formation_twin_emd_boundaries(email,created_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_emd_boundary_enforcements (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    plan_id VARCHAR(80) NOT NULL, boundary_id VARCHAR(80),
    recommended_level VARCHAR(4) NOT NULL,
    violation_count INTEGER NOT NULL DEFAULT 0 CHECK(violation_count >= 0),
    previous_actions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    retaliation_risk VARCHAR(10) NOT NULL DEFAULT 'LOW',
    available_support_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    executed_level VARCHAR(4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, plan_id),
    CHECK(recommended_level IN ('L0','L1','L2','L3','L4','L5')),
    CHECK(executed_level IS NULL OR executed_level IN ('L0','L1','L2','L3','L4','L5')),
    CHECK(retaliation_risk IN ('LOW','MEDIUM','HIGH'))
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_conflict_issues (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    issue_id VARCHAR(80) NOT NULL,
    status VARCHAR(12) NOT NULL DEFAULT 'READY',
    single_issue VARCHAR(240),
    dirty_components_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    cleaned_structure_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    blocks_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    activation_level SMALLINT CHECK(activation_level IS NULL OR activation_level BETWEEN 0 AND 10),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, issue_id),
    CHECK(status IN ('READY','NOT_READY')),
    -- a ready conflict issue always names exactly one issue
    CHECK(status <> 'READY' OR single_issue IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_dialogues (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    dialogue_id VARCHAR(80) NOT NULL, issue_id VARCHAR(80),
    mode VARCHAR(20) NOT NULL DEFAULT 'SOLO_REHEARSAL',
    status VARCHAR(28) NOT NULL DEFAULT 'READY',
    both_parties_consented BOOLEAN NOT NULL DEFAULT FALSE,
    protocol_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    pause_contract_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, dialogue_id),
    CHECK(mode IN ('SOLO_REHEARSAL','MUTUAL_WORKSPACE')),
    CHECK(status IN ('READY','BLOCKED_CONSENT','NOT_GENERATED_UNSAFE','COMPLETED','PAUSED')),
    -- a shared workspace requires both parties to have consented
    CHECK(mode <> 'MUTUAL_WORKSPACE' OR status <> 'READY' OR both_parties_consented = TRUE)
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_apologies (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    apology_id VARCHAR(80) NOT NULL, event_id VARCHAR(80),
    status VARCHAR(20) NOT NULL DEFAULT 'READY',
    specific_behavior VARCHAR(240) NOT NULL,
    impact VARCHAR(240) NOT NULL,
    amends VARCHAR(240), change_plan VARCHAR(240),
    missing_parts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    invalid_patterns_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    composed_draft TEXT NOT NULL,
    -- the system never sends an apology on the user's behalf
    auto_sent BOOLEAN NOT NULL DEFAULT FALSE,
    delivered_by_user BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, apology_id),
    CHECK(status IN ('READY','NEEDS_REVISION','DELIVERED','WITHDRAWN')),
    CHECK(auto_sent = FALSE)
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_forgiveness_maps (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    differentiation_id VARCHAR(80) NOT NULL, event_id VARCHAR(80),
    harm_type VARCHAR(160) NOT NULL,
    framework_source VARCHAR(40) NOT NULL,
    separation_model_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    observed_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- the engine never concludes whether the user has forgiven
    system_conclusion VARCHAR(1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, differentiation_id),
    CHECK(framework_source IN ('USER_SELECTED_THEOLOGY','CHURCH_CONFIGURED_PRINCIPLES','GENERAL_RELATIONAL_PRINCIPLES')),
    CHECK(system_conclusion IS NULL)
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_restitution_plans (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    plan_id VARCHAR(80) NOT NULL, event_id VARCHAR(80),
    mode VARCHAR(12) NOT NULL DEFAULT 'UNILATERAL',
    status VARCHAR(32) NOT NULL DEFAULT 'READY',
    items_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    verification_window_days INTEGER NOT NULL DEFAULT 3 CHECK(verification_window_days >= 0),
    completed_items INTEGER NOT NULL DEFAULT 0 CHECK(completed_items >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, plan_id),
    CHECK(mode IN ('UNILATERAL','MUTUAL')),
    CHECK(status IN ('READY','DOWNGRADED_TO_UNILATERAL','NOT_GENERATED_UNSAFE','COMPLETED','ABANDONED'))
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_trust_assessments (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    routing_id VARCHAR(80) NOT NULL,
    domain VARCHAR(32) NOT NULL,
    trust_level VARCHAR(4) NOT NULL,
    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    options_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    user_decision VARCHAR(24),
    -- the system offers evidence-based options; it never records a decision of its own
    system_decides BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, routing_id),
    CHECK(trust_level IN ('TR0','TR1','TR2','TR3','TR4','TR5')),
    CHECK(user_decision IS NULL OR user_decision IN
        ('CONTINUE_REBUILDING','LIMIT_CONTACT','REQUEST_MEDIATION','PAUSE_RELATIONSHIP','EXIT_RELATIONSHIP')),
    CHECK(system_decides = FALSE)
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_trust_owner ON formation_twin_emd_trust_assessments(email,domain,created_at DESC) WHERE deleted_at IS NULL;

-- Owner RLS is defense in depth; application queries also retain email predicates.
DO $$
DECLARE table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'formation_twin_emd_boundaries','formation_twin_emd_boundary_enforcements',
    'formation_twin_emd_conflict_issues','formation_twin_emd_dialogues',
    'formation_twin_emd_apologies','formation_twin_emd_forgiveness_maps',
    'formation_twin_emd_restitution_plans','formation_twin_emd_trust_assessments'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS ft_owner_policy ON %I', table_name);
    EXECUTE format(
      'CREATE POLICY ft_owner_policy ON %I USING (email=current_setting(''app.current_user_email'',true)) '
      'WITH CHECK (email=current_setting(''app.current_user_email'',true))', table_name
    );
  END LOOP;
END $$;
