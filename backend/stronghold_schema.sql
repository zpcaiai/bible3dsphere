-- 自高之事 (Stronghold) cloud persistence.
-- Mirrors the frontend StrongholdScanRecord so local "self-discernment" history
-- can sync to the cloud. id/user_id are TEXT to match this app's email/session
-- identity model and frontend-generated local IDs.

CREATE TABLE IF NOT EXISTS stronghold_scans (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  scanned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  text TEXT DEFAULT '',
  emotions JSONB NOT NULL DEFAULT '[]'::jsonb,
  primary_code TEXT,
  detected_codes JSONB NOT NULL DEFAULT '[]'::jsonb,
  archetype_code TEXT,
  blocked_doctrine_code TEXT,
  trigger_type TEXT,
  confidence NUMERIC(4,3) DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stronghold_scans_user_time
  ON stronghold_scans (user_id, scanned_at DESC);
