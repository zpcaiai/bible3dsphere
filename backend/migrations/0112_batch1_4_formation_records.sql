-- Batch 1, 3, 4 completion layer.
-- Generic durable store for Scripture Formation, Virtue/Vice, and Holy Habit
-- frontend records that previously only lived in localStorage or scattered APIs.

CREATE TABLE IF NOT EXISTS formation_batch1_4_records (
    id          TEXT NOT NULL,
    email       TEXT NOT NULL,
    batch       INT NOT NULL,
    domain      TEXT NOT NULL,
    record_type TEXT NOT NULL,
    payload     JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_on DATE,
    status      TEXT DEFAULT 'active',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (email, id)
);

CREATE INDEX IF NOT EXISTS idx_formation_batch1_4_email_domain
    ON formation_batch1_4_records (email, domain, record_type, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_formation_batch1_4_email_status
    ON formation_batch1_4_records (email, status, updated_at DESC);
