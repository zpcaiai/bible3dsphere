-- Spiritual Planet discernment Batches 01-06.
-- Evidence-governed cases, dialogue checkpoints, corrections and human review.

CREATE TABLE IF NOT EXISTS spiritual_planet_discernment_cases (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    title TEXT NOT NULL,
    subject_type TEXT NOT NULL CHECK(subject_type IN('idea','person','event','product','media','self_reflection','mixed')),
    user_goal TEXT NOT NULL,
    faith_context TEXT NOT NULL CHECK(faith_context IN('christian','seeker','unknown','other')),
    sensitivity TEXT NOT NULL,
    consent_scope_json JSONB NOT NULL,
    input_json JSONB NOT NULL,
    report_json JSONB NOT NULL,
    gospel_path_json JSONB,
    engine_versions_json JSONB NOT NULL,
    workflow_state TEXT NOT NULL,
    review_status TEXT NOT NULL CHECK(review_status IN('ready','human_review_required','blocked','withdrawn')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_sp_discernment_cases_owner
    ON spiritual_planet_discernment_cases(tenant_id,email,created_at DESC)
    WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS spiritual_planet_discernment_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    case_id UUID NOT NULL REFERENCES spiritual_planet_discernment_cases(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,
    locator TEXT NOT NULL,
    excerpt TEXT,
    evidence_level TEXT NOT NULL,
    independence_group TEXT,
    limitations_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sp_discernment_evidence_case
    ON spiritual_planet_discernment_evidence(tenant_id,email,case_id,created_at);

CREATE TABLE IF NOT EXISTS spiritual_planet_discernment_dialogue_sessions (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    case_id UUID NOT NULL REFERENCES spiritual_planet_discernment_cases(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    stage TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    gospel_consent TEXT NOT NULL DEFAULT 'not_asked',
    state_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_sp_discernment_dialogue_owner
    ON spiritual_planet_discernment_dialogue_sessions(tenant_id,email,case_id,created_at DESC)
    WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS spiritual_planet_discernment_dialogue_turns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    session_id UUID NOT NULL REFERENCES spiritual_planet_discernment_dialogue_sessions(id) ON DELETE CASCADE,
    turn_index INTEGER NOT NULL,
    speaker TEXT NOT NULL CHECK(speaker IN('user','assistant','system')),
    content TEXT NOT NULL,
    stage TEXT,
    difficulty TEXT,
    hypothesis_impact_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    safety_event_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(session_id,turn_index)
);

CREATE TABLE IF NOT EXISTS spiritual_planet_discernment_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    case_id UUID NOT NULL REFERENCES spiritual_planet_discernment_cases(id) ON DELETE CASCADE,
    actor_type TEXT NOT NULL CHECK(actor_type IN('USER','ADMIN_REVIEWER')),
    actor_id TEXT NOT NULL,
    action TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    correction_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sp_discernment_reviews_case
    ON spiritual_planet_discernment_reviews(tenant_id,email,case_id,created_at DESC);

DO $$
DECLARE table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'spiritual_planet_discernment_cases',
    'spiritual_planet_discernment_evidence',
    'spiritual_planet_discernment_dialogue_sessions',
    'spiritual_planet_discernment_dialogue_turns',
    'spiritual_planet_discernment_reviews'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS spiritual_planet_discernment_owner_policy ON %I', table_name);
    EXECUTE format(
      'CREATE POLICY spiritual_planet_discernment_owner_policy ON %I USING (LOWER(email)=LOWER(COALESCE(current_setting(''app.current_user_email'',true),''''))) WITH CHECK (LOWER(email)=LOWER(COALESCE(current_setting(''app.current_user_email'',true),'''')))',
      table_name
    );
  END LOOP;
END $$;
