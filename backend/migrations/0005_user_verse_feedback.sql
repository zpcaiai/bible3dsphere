-- Migration 0005: user verse feedback for personalized retrieval
-- Stores implicit feedback (saved, prayed, shared) on individual verses.
-- The embedding column holds the BGE-M3 vector for that verse text so we can
-- compute a user preference vector without re-embedding at query time.

CREATE TABLE IF NOT EXISTS user_verse_feedback (
    id            BIGSERIAL PRIMARY KEY,
    user_id       TEXT        NOT NULL,
    verse_pk_id   TEXT,                          -- optional: pk_id from verse index
    verse_ref     TEXT        NOT NULL DEFAULT '', -- e.g. "John 3:16"
    verse_text    TEXT        NOT NULL DEFAULT '', -- raw verse text
    feedback_type TEXT        NOT NULL DEFAULT 'saved', -- saved | prayed | shared
    embedding     REAL[],                         -- BGE-M3 vector (1024 dims), nullable
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_verse_feedback_user
    ON user_verse_feedback (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_verse_feedback_type
    ON user_verse_feedback (user_id, feedback_type);

-- Deduplicate: one feedback record per (user, verse_pk_id, feedback_type)
CREATE UNIQUE INDEX IF NOT EXISTS idx_verse_feedback_unique
    ON user_verse_feedback (user_id, verse_pk_id, feedback_type)
    WHERE verse_pk_id IS NOT NULL;
