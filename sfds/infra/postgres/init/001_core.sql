-- ============================================================
-- SFDS v3 — PostgreSQL Core Schema
-- Includes pgvector extension + spiritual_principles table
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Spiritual Principles (pgvector semantic store) ────────────
CREATE TABLE IF NOT EXISTS spiritual_principles (
    id              UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    principle_en    TEXT         NOT NULL,
    principle_zh    TEXT         DEFAULT '',
    category        VARCHAR(60)  DEFAULT 'general',
    source_ref      VARCHAR(120) DEFAULT '',
    tags            TEXT[]       DEFAULT '{}',
    embedding       vector(1536),
    created_at      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_principles_embedding
    ON spiritual_principles USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_principles_category
    ON spiritual_principles (category);

-- ── User Decisions ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_decisions (
    id                  UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             TEXT         NOT NULL,
    title               TEXT         DEFAULT '',
    description         TEXT         DEFAULT '',
    category            VARCHAR(60)  DEFAULT 'other',
    urgency             SMALLINT     DEFAULT 3,
    importance          SMALLINT     DEFAULT 3,
    anxiety_level       SMALLINT     DEFAULT 5,
    peace_level         SMALLINT     DEFAULT 5,
    clarity_level       SMALLINT     DEFAULT 5,
    reflection_notes    TEXT         DEFAULT '',
    analysis_result     JSONB        DEFAULT '{}',
    confirmed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_decisions_user ON user_decisions (user_id, created_at DESC);

-- ── User Profiles ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id     TEXT        PRIMARY KEY,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
