-- Migration 0004: add formation_score_ema column for cross-session EMA tracking
-- EMA smooths instantaneous formation_score over time so transient spikes
-- don't dominate the long-term formation signal.

ALTER TABLE mvfe_formation_state
    ADD COLUMN IF NOT EXISTS formation_score_ema REAL DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS session_count       INTEGER DEFAULT 0;

-- Back-fill: seed EMA from existing instantaneous score
UPDATE mvfe_formation_state
SET formation_score_ema = formation_score
WHERE formation_score_ema = 0.0 AND formation_score > 0.0;
