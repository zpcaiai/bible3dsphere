-- 见证墙：生命改变故事（教会隔离，可选跨教会公开）
CREATE TABLE IF NOT EXISTS testimonies (
    id            SERIAL PRIMARY KEY,
    email         TEXT NOT NULL,
    nickname      TEXT NOT NULL DEFAULT '弟兄姐妹',
    title         TEXT NOT NULL DEFAULT '',
    before_story  TEXT NOT NULL DEFAULT '',
    how_story     TEXT NOT NULL DEFAULT '',
    after_story   TEXT NOT NULL DEFAULT '',
    is_anonymous  BOOLEAN NOT NULL DEFAULT FALSE,
    is_public     BOOLEAN NOT NULL DEFAULT FALSE,
    amen_count    INTEGER NOT NULL DEFAULT 0,
    church_id     INTEGER,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_testimonies_church ON testimonies (church_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_testimonies_email ON testimonies (email);
