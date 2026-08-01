-- Production workflow columns for schema validation, concurrency, review and release.

ALTER TABLE sunday_school_ai_formation_records
    ADD COLUMN IF NOT EXISTS batch_id TEXT,
    ADD COLUMN IF NOT EXISTS schema_name TEXT,
    ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS paused_at TIMESTAMPTZ;

ALTER TABLE sunday_school_ai_formation_records
    DROP CONSTRAINT IF EXISTS sunday_school_ai_formation_records_status_check;
ALTER TABLE sunday_school_ai_formation_records
    ADD CONSTRAINT sunday_school_ai_formation_records_status_check
    CHECK(status IN('draft','active','paused','completed','archived','deleted'));
ALTER TABLE sunday_school_ai_formation_records
    DROP CONSTRAINT IF EXISTS sunday_school_ai_formation_records_batch_id_check;
ALTER TABLE sunday_school_ai_formation_records
    ADD CONSTRAINT sunday_school_ai_formation_records_batch_id_check
    CHECK(batch_id IS NULL OR batch_id ~ '^(0[1-9]|1[0-2])$');

CREATE INDEX IF NOT EXISTS idx_ai_formation_records_batch_owner
    ON sunday_school_ai_formation_records(tenant_id,email,batch_id,record_type,updated_at DESC)
    WHERE deleted_at IS NULL;

ALTER TABLE sunday_school_ai_formation_content
    ADD COLUMN IF NOT EXISTS content_sha256 TEXT,
    ADD COLUMN IF NOT EXISTS required_reviews_json JSONB NOT NULL DEFAULT '["theology_reviewer","pastoral_reviewer"]'::jsonb;

ALTER TABLE sunday_school_ai_formation_content
    DROP CONSTRAINT IF EXISTS sunday_school_ai_formation_content_sha256_check;
ALTER TABLE sunday_school_ai_formation_content
    ADD CONSTRAINT sunday_school_ai_formation_content_sha256_check
    CHECK(content_sha256 IS NULL OR content_sha256 ~ '^[a-f0-9]{64}$');

ALTER TABLE sunday_school_ai_formation_content_reviews
    ADD COLUMN IF NOT EXISTS content_sha256 TEXT;
ALTER TABLE sunday_school_ai_formation_content_reviews
    DROP CONSTRAINT IF EXISTS sunday_school_ai_formation_content_reviews_sha256_check;
ALTER TABLE sunday_school_ai_formation_content_reviews
    ADD CONSTRAINT sunday_school_ai_formation_content_reviews_sha256_check
    CHECK(content_sha256 IS NULL OR content_sha256 ~ '^[a-f0-9]{64}$');
ALTER TABLE sunday_school_ai_formation_content_reviews
    DROP CONSTRAINT IF EXISTS sunday_school_ai_formation_content_reviews_reviewer_role_check;
ALTER TABLE sunday_school_ai_formation_content_reviews
    ADD CONSTRAINT sunday_school_ai_formation_content_reviews_reviewer_role_check
    CHECK(reviewer_role IN(
        'theology_reviewer','pastoral_reviewer','child_safety_reviewer',
        'rights_reviewer','accessibility_reviewer','release_reviewer'
    ));

CREATE INDEX IF NOT EXISTS idx_ai_formation_reviews_exact_version
    ON sunday_school_ai_formation_content_reviews(content_id,content_version,content_sha256,reviewer_role,created_at DESC);

ALTER TABLE sunday_school_ai_formation_release_decisions
    ADD COLUMN IF NOT EXISTS rollout_percent INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS artifact_version TEXT,
    ADD COLUMN IF NOT EXISTS environment TEXT;
UPDATE sunday_school_ai_formation_release_decisions
SET artifact_version=COALESCE(artifact_version,'legacy'),
    environment=COALESCE(environment,'local');
ALTER TABLE sunday_school_ai_formation_release_decisions
    ALTER COLUMN artifact_version SET NOT NULL,
    ALTER COLUMN environment SET NOT NULL;
ALTER TABLE sunday_school_ai_formation_release_decisions
    DROP CONSTRAINT IF EXISTS sunday_school_ai_formation_release_decisions_rollout_check;
ALTER TABLE sunday_school_ai_formation_release_decisions
    ADD CONSTRAINT sunday_school_ai_formation_release_decisions_rollout_check
    CHECK(
        (decision='approved' AND rollout_percent=100) OR
        (decision='limited_rollout' AND rollout_percent BETWEEN 1 AND 99) OR
        (decision IN('blocked','rolled_back') AND rollout_percent=0)
    );
ALTER TABLE sunday_school_ai_formation_release_decisions
    DROP CONSTRAINT IF EXISTS sunday_school_ai_formation_release_decisions_environment_check;
ALTER TABLE sunday_school_ai_formation_release_decisions
    ADD CONSTRAINT sunday_school_ai_formation_release_decisions_environment_check
    CHECK(environment IN('staging','production'));

COMMENT ON COLUMN sunday_school_ai_formation_content.content_sha256 IS
    'Immutable canonical JSON hash; every review and publication action binds to this value.';
COMMENT ON COLUMN sunday_school_ai_formation_records.revision IS
    'Optimistic concurrency revision; stale PATCH and state transitions fail closed.';
