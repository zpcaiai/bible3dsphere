-- EMD-OS Batch 7: losses, grief companionship, control/limit calibration, ambiguous loss,
-- spiritual-bypassing checks, optional rituals, rest rhythms and integration evaluation.
-- Integration levels describe living with loss — they never describe "finished" grief.

CREATE TABLE IF NOT EXISTS formation_twin_emd_losses (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    loss_id VARCHAR(80) NOT NULL,
    loss_type VARCHAR(32) NOT NULL,
    what_was_lost VARCHAR(240) NOT NULL,
    secondary_losses_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    concrete_impacts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_ambiguous BOOLEAN NOT NULL DEFAULT FALSE,
    integration_level VARCHAR(4) NOT NULL DEFAULT 'GI0',
    occurred_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, loss_id),
    CHECK(integration_level IN ('GI0','GI1','GI2','GI3','GI4','GI5','GI6'))
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_loss_owner ON formation_twin_emd_losses(email,created_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_emd_grief_sessions (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    companion_id VARCHAR(80) NOT NULL, loss_id VARCHAR(80),
    named_emotions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    lament_used BOOLEAN NOT NULL DEFAULT FALSE,
    lament_ended_unresolved BOOLEAN NOT NULL DEFAULT TRUE,
    days_since_loss INTEGER CHECK(days_since_loss IS NULL OR days_since_loss >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, companion_id)
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_control_calibrations (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    calibration_id VARCHAR(80) NOT NULL, loss_id VARCHAR(80),
    buckets_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    outstanding_responsibilities_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    integration_level VARCHAR(4) NOT NULL DEFAULT 'GI0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, calibration_id),
    CHECK(integration_level IN ('GI0','GI1','GI2','GI3','GI4','GI5','GI6'))
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_ambiguous_losses (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    process_id VARCHAR(80) NOT NULL, loss_id VARCHAR(80),
    kind VARCHAR(48) NOT NULL,
    what_is_unresolved VARCHAR(240) NOT NULL,
    options_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    -- ambiguous loss never records a "closure" state
    closure_claimed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, process_id),
    CHECK(closure_claimed = FALSE)
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_bypassing_checks (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    discernment_id VARCHAR(80) NOT NULL,
    flags_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    reframes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    source VARCHAR(24) NOT NULL DEFAULT 'USER_TEXT',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, discernment_id),
    CHECK(source IN ('USER_TEXT','SYSTEM_OUTPUT','THIRD_PARTY_QUOTE'))
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_rituals (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    ritual_id VARCHAR(80) NOT NULL, loss_id VARCHAR(80),
    kind VARCHAR(24) NOT NULL,
    what_it_marks VARCHAR(240) NOT NULL,
    elements_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    with_others BOOLEAN NOT NULL DEFAULT FALSE,
    performed_at TIMESTAMPTZ,
    -- a ritual never claims supernatural efficacy or a transaction with God
    claims_efficacy BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, ritual_id),
    CHECK(kind IN ('RELEASE','MEMORIAL','FAREWELL','GRATITUDE','BOUNDARY_MARKER')),
    CHECK(claims_efficacy = FALSE)
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_rest_rhythms (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    rhythm_id VARCHAR(80) NOT NULL,
    plan_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    weekly_sabbath_hours INTEGER NOT NULL DEFAULT 4 CHECK(weekly_sabbath_hours >= 0),
    rest_measures_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    stopping_is_not_recovery BOOLEAN NOT NULL DEFAULT FALSE,
    rest_guilt_level SMALLINT CHECK(rest_guilt_level IS NULL OR rest_guilt_level BETWEEN 0 AND 10),
    slots_kept_last_week INTEGER NOT NULL DEFAULT 0 CHECK(slots_kept_last_week >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    UNIQUE(email, rhythm_id)
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_grief_integrations (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    evaluation_id VARCHAR(80) NOT NULL, loss_id VARCHAR(80),
    day INTEGER NOT NULL CHECK(day IN (14,30,90)),
    integration_level VARCHAR(4) NOT NULL,
    concerns_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    attribution_limits_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    anniversary_reaction BOOLEAN NOT NULL DEFAULT FALSE,
    -- grief completion is never asserted
    grief_completed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, evaluation_id),
    CHECK(integration_level IN ('GI0','GI1','GI2','GI3','GI4','GI5','GI6')),
    CHECK(grief_completed = FALSE)
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_grief_integration_owner ON formation_twin_emd_grief_integrations(email,day,created_at DESC) WHERE deleted_at IS NULL;

-- Owner RLS is defense in depth; application queries also retain email predicates.
DO $$
DECLARE table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'formation_twin_emd_losses','formation_twin_emd_grief_sessions',
    'formation_twin_emd_control_calibrations','formation_twin_emd_ambiguous_losses',
    'formation_twin_emd_bypassing_checks','formation_twin_emd_rituals',
    'formation_twin_emd_rest_rhythms','formation_twin_emd_grief_integrations'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS ft_owner_policy ON %I', table_name);
    EXECUTE format(
      'CREATE POLICY ft_owner_policy ON %I USING (email=current_setting(''app.current_user_email'',true)) '
      'WITH CHECK (email=current_setting(''app.current_user_email'',true))', table_name
    );
  END LOOP;
END $$;
