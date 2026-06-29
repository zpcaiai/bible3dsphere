-- Spiritual Formation persistence tables.
-- Names follow the Skills Pack. id/user_id are TEXT to match this app's current
-- email/session identity model and frontend-generated local IDs.

CREATE TABLE IF NOT EXISTS spiritual_daily_examens (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  date DATE NOT NULL,
  strongest_emotion TEXT NOT NULL,
  triggers JSONB NOT NULL DEFAULT '[]'::jsonb,
  behavior_description TEXT DEFAULT '',
  detected_sin_patterns JSONB NOT NULL DEFAULT '[]'::jsonb,
  selected_primary_sin_pattern TEXT,
  core_lie TEXT DEFAULT '',
  gospel_truth TEXT DEFAULT '',
  confession TEXT DEFAULT '',
  repentance_action TEXT DEFAULT '',
  obedience_action TEXT DEFAULT '',
  fruit_practiced JSONB NOT NULL DEFAULT '[]'::jsonb,
  virtues_practiced JSONB NOT NULL DEFAULT '[]'::jsonb,
  prayer TEXT DEFAULT '',
  grace_recovery_needed BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_spiritual_daily_user_date
  ON spiritual_daily_examens (user_id, date DESC);

CREATE TABLE IF NOT EXISTS spiritual_thought_captive_entries (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  date DATE NOT NULL,
  catch_thought TEXT NOT NULL,
  named_sin_pattern TEXT NOT NULL,
  exposed_lie TEXT NOT NULL,
  replacement_truth TEXT NOT NULL,
  obedience_action TEXT NOT NULL,
  scripture JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_spiritual_thought_user_date
  ON spiritual_thought_captive_entries (user_id, date DESC);

CREATE TABLE IF NOT EXISTS spiritual_grace_recovery_entries (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  date DATE NOT NULL,
  sin_pattern TEXT,
  what_happened TEXT NOT NULL,
  confession TEXT NOT NULL,
  received_grace_statement TEXT NOT NULL,
  repair_action TEXT DEFAULT '',
  boundary_action TEXT DEFAULT '',
  accountability_action TEXT DEFAULT '',
  next_obedience_step TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_spiritual_recovery_user_date
  ON spiritual_grace_recovery_entries (user_id, date DESC);

CREATE TABLE IF NOT EXISTS spiritual_transformation_plans (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  title TEXT NOT NULL,
  duration TEXT NOT NULL,
  intensity TEXT NOT NULL,
  primary_sin_pattern TEXT NOT NULL,
  secondary_sin_pattern TEXT,
  target_fruits JSONB NOT NULL DEFAULT '[]'::jsonb,
  target_virtues JSONB NOT NULL DEFAULT '[]'::jsonb,
  daily_practices JSONB NOT NULL DEFAULT '[]'::jsonb,
  weekly_practices JSONB NOT NULL DEFAULT '[]'::jsonb,
  review_questions JSONB NOT NULL DEFAULT '[]'::jsonb,
  progress_summary TEXT DEFAULT '',
  recommended_next_step TEXT DEFAULT '',
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  completed_practice_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_spiritual_plans_user_status
  ON spiritual_transformation_plans (user_id, status, start_date DESC);

CREATE TABLE IF NOT EXISTS spiritual_holy_life_day_logs (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  date DATE NOT NULL,
  intention TEXT DEFAULT '',
  entries JSONB NOT NULL DEFAULT '[]'::jsonb,
  presence_logs JSONB NOT NULL DEFAULT '[]'::jsonb,
  rule_of_life JSONB NOT NULL DEFAULT '{}'::jsonb,
  purpose_review JSONB NOT NULL DEFAULT '{}'::jsonb,
  decision_sanctification_logs JSONB NOT NULL DEFAULT '[]'::jsonb,
  daily_report TEXT DEFAULT '',
  tomorrow_formation TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (user_id, date)
);

CREATE INDEX IF NOT EXISTS idx_spiritual_holy_life_user_date
  ON spiritual_holy_life_day_logs (user_id, date DESC);
