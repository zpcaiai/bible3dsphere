-- Spiritual Planet discernment Batches 07-10.
-- Encrypted Formation Twin, purpose-bound collaboration, theology evidence and release certification.

CREATE TABLE IF NOT EXISTS spiritual_planet_formation_events (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    case_id UUID REFERENCES spiritual_planet_discernment_cases(id) ON DELETE CASCADE,
    occurred_at TIMESTAMPTZ NOT NULL,
    source_type TEXT NOT NULL,
    evidence_quality TEXT NOT NULL CHECK(evidence_quality IN('E0','E1','E2','E3','E4')),
    data_level TEXT NOT NULL CHECK(data_level IN('L0','L1','L2','L3')),
    consent_json JSONB NOT NULL,
    encryption_key_version TEXT NOT NULL,
    nonce BYTEA NOT NULL,
    encrypted_payload BYTEA NOT NULL,
    payload_hash TEXT NOT NULL,
    chain_summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN('ACTIVE','CORRECTED','WITHDRAWN')),
    correction_of UUID REFERENCES spiritual_planet_formation_events(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_sp_formation_events_owner
    ON spiritual_planet_formation_events(tenant_id,email,occurred_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS spiritual_planet_formation_artifacts (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    artifact_type TEXT NOT NULL CHECK(artifact_type IN('SNAPSHOT','WINDOW_REVIEW','RELAPSE','RELATIONSHIP_REPAIR','IDENTITY_MIGRATION')),
    window_days INTEGER,
    source_event_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    encryption_key_version TEXT NOT NULL,
    nonce BYTEA NOT NULL,
    encrypted_payload BYTEA NOT NULL,
    payload_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_sp_formation_artifacts_owner
    ON spiritual_planet_formation_artifacts(tenant_id,email,artifact_type,created_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS spiritual_planet_collaboration_consents (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    recipient_email TEXT NOT NULL,
    recipient_role TEXT NOT NULL,
    purpose TEXT NOT NULL,
    allowed_categories_json JSONB NOT NULL,
    allowed_actions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    expires_at TIMESTAMPTZ NOT NULL,
    reshare_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN('ACTIVE','REVOKED','EXPIRED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_sp_collaboration_consents_owner
    ON spiritual_planet_collaboration_consents(tenant_id,email,created_at DESC);

CREATE TABLE IF NOT EXISTS spiritual_planet_collaboration_disclosures (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    recipient_email TEXT NOT NULL,
    recipient_role TEXT NOT NULL,
    consent_id UUID NOT NULL REFERENCES spiritual_planet_collaboration_consents(id) ON DELETE CASCADE,
    case_id UUID REFERENCES spiritual_planet_discernment_cases(id) ON DELETE CASCADE,
    purpose TEXT NOT NULL,
    data_level TEXT NOT NULL CHECK(data_level IN('L0','L1','L2','L3')),
    selected_fields_json JSONB NOT NULL,
    redacted_fields_json JSONB NOT NULL,
    basis TEXT NOT NULL,
    reshare_policy TEXT NOT NULL DEFAULT 'forbidden',
    expires_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN('ACTIVE','REVOKED','EXPIRED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_sp_disclosures_participants
    ON spiritual_planet_collaboration_disclosures(tenant_id,email,recipient_email,created_at DESC);

CREATE TABLE IF NOT EXISTS spiritual_planet_collaboration_meeting_preps (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    recipient_email TEXT NOT NULL,
    disclosure_id UUID NOT NULL REFERENCES spiritual_planet_collaboration_disclosures(id) ON DELETE CASCADE,
    case_id UUID NOT NULL REFERENCES spiritual_planet_discernment_cases(id) ON DELETE CASCADE,
    encryption_key_version TEXT NOT NULL,
    nonce BYTEA NOT NULL,
    encrypted_payload BYTEA NOT NULL,
    payload_hash TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS spiritual_planet_collaboration_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    recipient_email TEXT,
    actor_email TEXT NOT NULL,
    action TEXT NOT NULL,
    purpose TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id UUID,
    reason TEXT NOT NULL,
    outcome TEXT NOT NULL,
    details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sp_collaboration_audit_owner
    ON spiritual_planet_collaboration_audit(tenant_id,email,created_at DESC);

CREATE TABLE IF NOT EXISTS spiritual_planet_theology_sources (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    title TEXT NOT NULL,
    source_type TEXT NOT NULL,
    rights_status TEXT NOT NULL,
    quality_tier TEXT NOT NULL,
    source_json JSONB NOT NULL,
    user_confirms_rights BOOLEAN NOT NULL DEFAULT FALSE,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN('ACTIVE','WITHDRAWN','BLOCKED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_sp_theology_sources_owner
    ON spiritual_planet_theology_sources(tenant_id,email,created_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS spiritual_planet_theology_queries (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    query_hash TEXT NOT NULL,
    intent TEXT NOT NULL,
    review_status TEXT NOT NULL,
    encryption_key_version TEXT NOT NULL,
    nonce BYTEA NOT NULL,
    encrypted_query BYTEA NOT NULL,
    result_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_sp_theology_queries_owner
    ON spiritual_planet_theology_queries(tenant_id,email,created_at DESC) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS spiritual_planet_certification_evaluations (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    build_hash TEXT NOT NULL,
    target_scope TEXT NOT NULL CHECK(target_scope IN('pilot','production')),
    status TEXT NOT NULL,
    result_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sp_certification_evaluations
    ON spiritual_planet_certification_evaluations(build_hash,created_at DESC);

CREATE TABLE IF NOT EXISTS spiritual_planet_release_certificates (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    release_id UUID NOT NULL REFERENCES spiritual_planet_certification_evaluations(id) ON DELETE CASCADE,
    build_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    certificate_json JSONB NOT NULL,
    signature_hash TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS spiritual_planet_recertification_events (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    required_domains_json JSONB NOT NULL,
    details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'RECERTIFICATION_REQUIRED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
DECLARE table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'spiritual_planet_formation_events',
    'spiritual_planet_formation_artifacts',
    'spiritual_planet_collaboration_consents',
    'spiritual_planet_collaboration_meeting_preps',
    'spiritual_planet_theology_sources',
    'spiritual_planet_theology_queries',
    'spiritual_planet_certification_evaluations',
    'spiritual_planet_release_certificates',
    'spiritual_planet_recertification_events'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS spiritual_planet_owner_policy ON %I', table_name);
    EXECUTE format(
      'CREATE POLICY spiritual_planet_owner_policy ON %I USING (LOWER(email)=LOWER(COALESCE(current_setting(''app.current_user_email'',true),''''))) WITH CHECK (LOWER(email)=LOWER(COALESCE(current_setting(''app.current_user_email'',true),'''')))',
      table_name
    );
  END LOOP;
END $$;

ALTER TABLE spiritual_planet_collaboration_disclosures ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS spiritual_planet_disclosure_participant_policy ON spiritual_planet_collaboration_disclosures;
CREATE POLICY spiritual_planet_disclosure_participant_policy ON spiritual_planet_collaboration_disclosures
  USING (
    LOWER(email)=LOWER(COALESCE(current_setting('app.current_user_email',true),''))
    OR LOWER(recipient_email)=LOWER(COALESCE(current_setting('app.current_user_email',true),''))
  )
  WITH CHECK (LOWER(email)=LOWER(COALESCE(current_setting('app.current_user_email',true),'')));

ALTER TABLE spiritual_planet_collaboration_audit ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS spiritual_planet_audit_participant_policy ON spiritual_planet_collaboration_audit;
CREATE POLICY spiritual_planet_audit_participant_policy ON spiritual_planet_collaboration_audit
  USING (
    LOWER(email)=LOWER(COALESCE(current_setting('app.current_user_email',true),''))
    OR LOWER(COALESCE(recipient_email,''))=LOWER(COALESCE(current_setting('app.current_user_email',true),''))
  )
  WITH CHECK (LOWER(email)=LOWER(COALESCE(current_setting('app.current_user_email',true),'')));

ALTER TABLE spiritual_planet_collaboration_meeting_preps ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS spiritual_planet_meeting_prep_participant_policy ON spiritual_planet_collaboration_meeting_preps;
DROP POLICY IF EXISTS spiritual_planet_owner_policy ON spiritual_planet_collaboration_meeting_preps;
CREATE POLICY spiritual_planet_meeting_prep_participant_policy ON spiritual_planet_collaboration_meeting_preps
  USING (
    LOWER(email)=LOWER(COALESCE(current_setting('app.current_user_email',true),''))
    OR LOWER(recipient_email)=LOWER(COALESCE(current_setting('app.current_user_email',true),''))
  )
  WITH CHECK (LOWER(email)=LOWER(COALESCE(current_setting('app.current_user_email',true),'')));
