CREATE TABLE IF NOT EXISTS spiritual_holy_life_day_logs (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  date DATE NOT NULL,
  intention TEXT DEFAULT '',
  entries JSONB NOT NULL DEFAULT '[]'::jsonb,
  presence_logs JSONB NOT NULL DEFAULT '[]'::jsonb,
  daily_report TEXT DEFAULT '',
  tomorrow_formation TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (user_id, date)
);

CREATE INDEX IF NOT EXISTS idx_spiritual_holy_life_user_date
  ON spiritual_holy_life_day_logs (user_id, date DESC);
