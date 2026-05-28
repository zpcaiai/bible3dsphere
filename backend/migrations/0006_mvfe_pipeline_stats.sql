-- Migration 0006: MVFE pipeline run statistics
-- Stores per-run metrics from the 13-step MVFE pipeline for longitudinal analysis,
-- governance audit rate reporting, and ablation benchmarking.

CREATE TABLE IF NOT EXISTS mvfe_pipeline_stats (
    id                      BIGSERIAL PRIMARY KEY,
    user_id                 TEXT        NOT NULL,
    event_id                TEXT        NOT NULL UNIQUE,   -- matches orchestrator event_id

    -- Timing
    pipeline_latency_ms     REAL        NOT NULL DEFAULT 0,

    -- Formation metrics (snapshot)
    formation_score         REAL        NOT NULL DEFAULT 0,
    drift_score             REAL        NOT NULL DEFAULT 0,
    stability_score         REAL        NOT NULL DEFAULT 0,
    formation_score_ema     REAL        NOT NULL DEFAULT 0,

    -- Critic metrics
    coherence_score         REAL        NOT NULL DEFAULT 0,
    overfit_risk            REAL        NOT NULL DEFAULT 0,
    confidence_adjustment   REAL        NOT NULL DEFAULT 0,

    -- Governance metrics
    governance_passed       BOOLEAN     NOT NULL DEFAULT TRUE,
    governance_violations   INTEGER     NOT NULL DEFAULT 0,
    governance_risk_level   TEXT        NOT NULL DEFAULT 'low',

    -- Emotion extraction
    primary_emotion         TEXT        NOT NULL DEFAULT '',
    emotion_intensity       REAL        NOT NULL DEFAULT 0,
    emotion_uncertainty     REAL        NOT NULL DEFAULT 0,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mvfe_stats_user
    ON mvfe_pipeline_stats (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_mvfe_stats_created
    ON mvfe_pipeline_stats (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_mvfe_stats_governance
    ON mvfe_pipeline_stats (governance_passed, governance_risk_level)
    WHERE governance_passed = FALSE;
