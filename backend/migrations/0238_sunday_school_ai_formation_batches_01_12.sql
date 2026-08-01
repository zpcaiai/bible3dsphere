-- Sunday School AI-era formation Batches 01-12.
-- Feature flag defaults off; generated and age-sensitive content begins in review.

CREATE TABLE IF NOT EXISTS sunday_school_ai_formation_records (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    record_type TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    payload_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN('active','paused','completed','archived','deleted')),
    idempotency_key TEXT NOT NULL,
    retention_until TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    UNIQUE(tenant_id,email,idempotency_key)
);
CREATE INDEX IF NOT EXISTS idx_ai_formation_records_owner
    ON sunday_school_ai_formation_records(tenant_id,email,record_type,created_at DESC)
    WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS sunday_school_ai_formation_content (
    id TEXT NOT NULL,
    batch_id TEXT NOT NULL CHECK(batch_id ~ '^(0[1-9]|1[0-2])$'),
    content_kind TEXT NOT NULL,
    version TEXT NOT NULL,
    authority_level TEXT NOT NULL CHECK(authority_level IN('SCRIPTURE_EXPLICIT','THEOLOGICAL_INFERENCE','PASTORAL_WISDOM','PRODUCT_DEFAULT')),
    review_status TEXT NOT NULL CHECK(review_status IN('draft','theology_review','pastoral_review','approved','rejected')),
    age_bands_json JSONB NOT NULL,
    content_json JSONB NOT NULL,
    source_provenance_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ,
    retired_at TIMESTAMPTZ,
    PRIMARY KEY(id,version),
    CHECK(review_status='approved' OR published_at IS NULL)
);
CREATE INDEX IF NOT EXISTS idx_ai_formation_content_review
    ON sunday_school_ai_formation_content(batch_id,review_status,updated_at DESC);

CREATE TABLE IF NOT EXISTS sunday_school_ai_formation_content_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id TEXT NOT NULL,
    content_version TEXT NOT NULL,
    reviewer_email TEXT NOT NULL,
    reviewer_role TEXT NOT NULL CHECK(reviewer_role IN('theology_reviewer','pastoral_reviewer','child_safety_reviewer','rights_reviewer','release_reviewer')),
    decision TEXT NOT NULL CHECK(decision IN('approve','request_changes','reject')),
    reason_codes_json JSONB NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY(content_id,content_version)
        REFERENCES sunday_school_ai_formation_content(id,version) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sunday_school_ai_formation_audit (
    id BIGSERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    email TEXT NOT NULL,
    actor_email TEXT NOT NULL,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    reason_codes_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ai_formation_audit_owner
    ON sunday_school_ai_formation_audit(tenant_id,email,created_at DESC);

CREATE TABLE IF NOT EXISTS sunday_school_ai_formation_release_evidence (
    id UUID PRIMARY KEY,
    artifact_id TEXT NOT NULL,
    artifact_version TEXT NOT NULL,
    environment TEXT NOT NULL CHECK(environment IN('local','ci','staging','production')),
    artifact_sha256 TEXT NOT NULL CHECK(artifact_sha256 ~ '^[a-f0-9]{64}$'),
    gate TEXT NOT NULL CHECK(gate IN(
        'theology','pastoral_safety','child_safety','privacy_security','tenant_isolation',
        'accessibility_automated','accessibility_manual','content_quality','skill_evals','rollback_rehearsal'
    )),
    result TEXT NOT NULL CHECK(result IN('passed','failed','not_run','blocked')),
    command TEXT NOT NULL,
    exit_code INTEGER,
    executed_at TIMESTAMPTZ NOT NULL,
    human_reviewer TEXT,
    recorded_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(artifact_id,artifact_version,environment,artifact_sha256,gate,executed_at)
);

CREATE TABLE IF NOT EXISTS sunday_school_ai_formation_release_decisions (
    id UUID PRIMARY KEY,
    artifact_id TEXT NOT NULL,
    artifact_sha256 TEXT NOT NULL CHECK(artifact_sha256 ~ '^[a-f0-9]{64}$'),
    decision TEXT NOT NULL CHECK(decision IN('blocked','limited_rollout','approved','rolled_back')),
    authorized_by TEXT NOT NULL,
    rollback_owner TEXT NOT NULL,
    incident_owner TEXT NOT NULL,
    blocker_snapshot_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
DECLARE table_name TEXT;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'sunday_school_ai_formation_records',
    'sunday_school_ai_formation_audit'
  ] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS ai_formation_owner_policy ON %I', table_name);
    EXECUTE format(
      'CREATE POLICY ai_formation_owner_policy ON %I USING (LOWER(email)=LOWER(COALESCE(current_setting(''app.current_user_email'',true),''''))) WITH CHECK (LOWER(email)=LOWER(COALESCE(current_setting(''app.current_user_email'',true),'''')))',
      table_name
    );
  END LOOP;
END $$;

-- Rollback rehearsal (manual, reviewed): disable SUNDAY_SCHOOL_AI_FORMATION_ENABLED,
-- export/delete owner records under the data-rights procedure, then drop the six
-- sunday_school_ai_formation_* tables in reverse dependency order.
