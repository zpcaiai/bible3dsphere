DROP INDEX IF EXISTS idx_dating_priority_perspective_created;

ALTER TABLE dating_priority_submissions
    DROP COLUMN IF EXISTS response_json;

ALTER TABLE dating_priority_submissions
    DROP COLUMN IF EXISTS response_version;
