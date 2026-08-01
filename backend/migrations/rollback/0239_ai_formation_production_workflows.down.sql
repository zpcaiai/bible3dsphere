-- Review-only rollback. Disable the module and ensure 0240 seed rollback ran first.

DROP INDEX IF EXISTS idx_ai_formation_reviews_exact_version;
DROP INDEX IF EXISTS idx_ai_formation_records_batch_owner;

ALTER TABLE sunday_school_ai_formation_release_decisions
    DROP CONSTRAINT IF EXISTS sunday_school_ai_formation_release_decisions_rollout_check,
    DROP CONSTRAINT IF EXISTS sunday_school_ai_formation_release_decisions_environment_check,
    DROP COLUMN IF EXISTS rollout_percent,
    DROP COLUMN IF EXISTS artifact_version,
    DROP COLUMN IF EXISTS environment;

ALTER TABLE sunday_school_ai_formation_content_reviews
    DROP CONSTRAINT IF EXISTS sunday_school_ai_formation_content_reviews_sha256_check,
    DROP COLUMN IF EXISTS content_sha256;
ALTER TABLE sunday_school_ai_formation_content_reviews
    DROP CONSTRAINT IF EXISTS sunday_school_ai_formation_content_reviews_reviewer_role_check;
ALTER TABLE sunday_school_ai_formation_content_reviews
    ADD CONSTRAINT sunday_school_ai_formation_content_reviews_reviewer_role_check
    CHECK(reviewer_role IN(
        'theology_reviewer','pastoral_reviewer','child_safety_reviewer',
        'rights_reviewer','release_reviewer'
    ));

ALTER TABLE sunday_school_ai_formation_content
    DROP CONSTRAINT IF EXISTS sunday_school_ai_formation_content_sha256_check,
    DROP COLUMN IF EXISTS content_sha256,
    DROP COLUMN IF EXISTS required_reviews_json;

ALTER TABLE sunday_school_ai_formation_records
    DROP CONSTRAINT IF EXISTS sunday_school_ai_formation_records_batch_id_check,
    DROP COLUMN IF EXISTS paused_at,
    DROP COLUMN IF EXISTS revision,
    DROP COLUMN IF EXISTS schema_name,
    DROP COLUMN IF EXISTS batch_id;
