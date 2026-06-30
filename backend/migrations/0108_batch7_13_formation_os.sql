-- Batch 7-13 backend support: flexible persisted records and event log.
-- This complements existing specialized tables without conflicting with them.

CREATE TABLE IF NOT EXISTS formation_os_records (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL,
  batch INTEGER NOT NULL CHECK (batch BETWEEN 7 AND 13),
  module_key TEXT NOT NULL,
  record_type TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_formation_os_records_email_batch
  ON formation_os_records (email, batch, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_formation_os_records_type
  ON formation_os_records (record_type);

CREATE INDEX IF NOT EXISTS idx_formation_os_records_payload
  ON formation_os_records USING GIN (payload);

CREATE TABLE IF NOT EXISTS formation_os_events (
  id BIGSERIAL PRIMARY KEY,
  email TEXT NOT NULL,
  batch INTEGER NOT NULL CHECK (batch BETWEEN 7 AND 13),
  module_key TEXT NOT NULL,
  event_type TEXT NOT NULL,
  source_record_id TEXT NULL REFERENCES formation_os_records(id) ON DELETE SET NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_formation_os_events_email_batch
  ON formation_os_events (email, batch, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_formation_os_events_type
  ON formation_os_events (event_type);
