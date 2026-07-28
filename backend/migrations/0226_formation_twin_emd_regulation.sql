-- EMD-OS Batch 4: emotion awareness and regulation training sessions.
-- Stores activation bands, confirmed emotions, body signals, trigger profiles,
-- pause protocols, impulse guards, co-regulation requests, recovery plans and rehearsals.
-- Candidate emotions are never stored as confirmed; medical red flags never become diagnoses.

CREATE TABLE IF NOT EXISTS formation_twin_emd_regulation_sessions (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    regulation_session_id VARCHAR(80) NOT NULL,
    source_event_id VARCHAR(80),
    mode VARCHAR(16) NOT NULL DEFAULT 'REAL_TIME',
    safety_status VARCHAR(16) NOT NULL DEFAULT 'UNKNOWN',
    activation_level SMALLINT CHECK(activation_level IS NULL OR activation_level BETWEEN 0 AND 10),
    activation_band VARCHAR(10) NOT NULL DEFAULT 'UNKNOWN',
    confirmed_emotions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    emotion_candidates_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    body_signals_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    action_urges_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    medical_red_flag BOOLEAN NOT NULL DEFAULT FALSE,
    deep_dive_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    current_node VARCHAR(48) NOT NULL DEFAULT 'SESSION_STARTED',
    next_action VARCHAR(48),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    UNIQUE(email, regulation_session_id),
    CHECK(mode IN ('REAL_TIME','RETROSPECTIVE','REHEARSAL')),
    CHECK(safety_status IN ('UNKNOWN','SAFE','NEEDS_CAUTION','HIGH_RISK','CRISIS_ROUTED')),
    CHECK(activation_band IN ('GREEN','AMBER','RED','CRISIS','UNKNOWN')),
    -- deep emotional dives are only allowed in the lower activation bands
    CHECK(deep_dive_allowed = FALSE OR activation_band IN ('GREEN','AMBER'))
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_reg_session_owner ON formation_twin_emd_regulation_sessions(email,updated_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_emd_trigger_profiles (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    trigger_profile_id VARCHAR(80) NOT NULL,
    event_count INTEGER NOT NULL DEFAULT 0 CHECK(event_count >= 0),
    trigger_signature_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    contexts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    earliest_body_signals_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    typical_urges_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    median_escalation_minutes NUMERIC,
    user_review_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, trigger_profile_id),
    CHECK(user_review_status IN ('PENDING','USER_CONFIRMED','USER_DISPUTED','USER_CORRECTED')),
    CHECK(median_escalation_minutes IS NULL OR median_escalation_minutes >= 0)
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_pause_protocols (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    protocol_id VARCHAR(80) NOT NULL, regulation_session_id VARCHAR(80),
    pause_level VARCHAR(4) NOT NULL,
    steps_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    duration_seconds_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    return_commitment_required BOOLEAN NOT NULL DEFAULT FALSE,
    returned_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'READY',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, protocol_id),
    CHECK(pause_level IN ('P1','P2','P3')),
    CHECK(status IN ('READY','ACTIVE','RETURNED','ABANDONED','ROUTED_TO_CRISIS'))
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_impulse_guards (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    guard_id VARCHAR(80) NOT NULL, regulation_session_id VARCHAR(80),
    urge_type VARCHAR(48) NOT NULL,
    urgency SMALLINT NOT NULL DEFAULT 0 CHECK(urgency BETWEEN 0 AND 10),
    reversibility VARCHAR(32) NOT NULL,
    strategies_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    delay_seconds INTEGER NOT NULL DEFAULT 0 CHECK(delay_seconds >= 0),
    substitute_action VARCHAR(200),
    -- drafts are stored, sending is never performed by the system
    draft_saved BOOLEAN NOT NULL DEFAULT TRUE,
    send_blocked BOOLEAN NOT NULL DEFAULT TRUE,
    user_overrode BOOLEAN NOT NULL DEFAULT FALSE,
    outcome VARCHAR(24) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, guard_id),
    CHECK(reversibility IN ('REVERSIBLE_LOW_IMPACT','REVERSIBLE_HIGH_IMPACT','IRREVERSIBLE_HIGH_IMPACT','SAFETY_CRITICAL')),
    CHECK(outcome IN ('PENDING','DELAYED','SUBSTITUTED','SENT_BY_USER','ABANDONED','ROUTED_TO_CRISIS'))
);
CREATE INDEX IF NOT EXISTS idx_ft_emd_guard_owner ON formation_twin_emd_impulse_guards(email,created_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS formation_twin_emd_support_persons (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    support_person_id VARCHAR(80) NOT NULL,
    relationship_role VARCHAR(40) NOT NULL,
    allowed_support_types_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    availability_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    content_sharing_scope VARCHAR(64) NOT NULL DEFAULT 'activation_level_and_support_request_only',
    -- both sides must consent; a contact is never added to an emergency list by default
    person_has_consented BOOLEAN NOT NULL DEFAULT FALSE,
    user_has_consented BOOLEAN NOT NULL DEFAULT FALSE,
    is_conflict_party BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), revoked_at TIMESTAMPTZ, deleted_at TIMESTAMPTZ,
    UNIQUE(email, support_person_id)
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_coregulation_requests (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    plan_id VARCHAR(80) NOT NULL, regulation_session_id VARCHAR(80),
    requested_support_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    eligible_contacts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    excluded_contacts_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    activation_level SMALLINT CHECK(activation_level IS NULL OR activation_level BETWEEN 0 AND 10),
    message_auto_sent BOOLEAN NOT NULL DEFAULT FALSE,
    event_details_shared BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(24) NOT NULL DEFAULT 'READY',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, plan_id),
    CHECK(status IN ('READY','NO_ELIGIBLE_CONTACT','SENT_BY_USER','DECLINED')),
    -- the system never sends on the user's behalf and never shares event bodies
    CHECK(message_auto_sent = FALSE),
    CHECK(event_details_shared = FALSE)
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_recovery_plans (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    recovery_plan_id VARCHAR(80) NOT NULL, regulation_session_id VARCHAR(80),
    source_event_id VARCHAR(80),
    activation_peak SMALLINT CHECK(activation_peak IS NULL OR activation_peak BETWEEN 0 AND 10),
    activation_current SMALLINT CHECK(activation_current IS NULL OR activation_current BETWEEN 0 AND 10),
    horizons_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    recovery_kinds_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    optional_spiritual_support_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    harmful_action_occurred BOOLEAN NOT NULL DEFAULT FALSE,
    relationship_repair_needed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, recovery_plan_id)
);

CREATE TABLE IF NOT EXISTS formation_twin_emd_rehearsals (
    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, profile_id TEXT NOT NULL, email TEXT NOT NULL,
    rehearsal_id VARCHAR(80) NOT NULL, regulation_session_id VARCHAR(80),
    level SMALLINT NOT NULL CHECK(level IN (1,2,3)),
    changed_variable VARCHAR(48),
    cards_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(28) NOT NULL DEFAULT 'READY',
    used_in_real_life BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ,
    UNIQUE(email, rehearsal_id),
    CHECK(status IN ('READY','PRACTISED','NOT_APPLICABLE_SAFETY','RETIRED'))
);

-- Owner RLS is defense in depth; application queries also retain email predicates.
DO $$
DECLARE table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'formation_twin_emd_regulation_sessions','formation_twin_emd_trigger_profiles',
    'formation_twin_emd_pause_protocols','formation_twin_emd_impulse_guards',
    'formation_twin_emd_support_persons','formation_twin_emd_coregulation_requests',
    'formation_twin_emd_recovery_plans','formation_twin_emd_rehearsals'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS ft_owner_policy ON %I', table_name);
    EXECUTE format(
      'CREATE POLICY ft_owner_policy ON %I USING (email=current_setting(''app.current_user_email'',true)) '
      'WITH CHECK (email=current_setting(''app.current_user_email'',true))', table_name
    );
  END LOOP;
END $$;
