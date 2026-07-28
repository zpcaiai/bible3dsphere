-- Extend the existing anonymous dating-priority survey without exposing
-- authenticated account identifiers or deleting legacy responses.
CREATE TABLE IF NOT EXISTS dating_priority_submissions (
    id SERIAL PRIMARY KEY,
    visitor_id VARCHAR(255) NOT NULL,
    perspective VARCHAR(32) NOT NULL,
    focus_order JSONB NOT NULL DEFAULT '[]'::jsonb,
    block_order JSONB NOT NULL DEFAULT '[]'::jsonb,
    response_version INTEGER NOT NULL DEFAULT 1,
    response_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE dating_priority_submissions
    ADD COLUMN IF NOT EXISTS response_version INTEGER NOT NULL DEFAULT 1;

ALTER TABLE dating_priority_submissions
    ALTER COLUMN perspective TYPE VARCHAR(32);

ALTER TABLE dating_priority_submissions
    ADD COLUMN IF NOT EXISTS response_json JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_dating_priority_perspective_created
    ON dating_priority_submissions (perspective, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_dating_priority_visitor
    ON dating_priority_submissions (visitor_id);
