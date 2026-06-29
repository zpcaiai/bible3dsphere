ALTER TABLE spiritual_holy_life_day_logs
  ADD COLUMN IF NOT EXISTS rule_of_life JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS purpose_review JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS decision_sanctification_logs JSONB NOT NULL DEFAULT '[]'::jsonb;
