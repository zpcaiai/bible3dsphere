-- ============================================================================
-- SFDS TimescaleDB Schema (V2) — Temporal Formation Tracking
-- Requires: TimescaleDB extension + existing sfds_users table
-- Apply after sfds_schema_core.sql
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ──────────────────────────────────────────────────────────────────────────────
-- 1. user_spiritual_timeline
--    Core per-user spiritual formation time-series.
-- ──────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sfds_user_spiritual_timeline (
    user_id              UUID        NOT NULL REFERENCES sfds_users(id) ON DELETE CASCADE,
    recorded_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Emotional metrics (0-10)
    anxiety_level        SMALLINT    CHECK (anxiety_level        BETWEEN 0 AND 10),
    peace_level          SMALLINT    CHECK (peace_level          BETWEEN 0 AND 10),
    clarity_level        SMALLINT    CHECK (clarity_level        BETWEEN 0 AND 10),
    spiritual_dryness    SMALLINT    CHECK (spiritual_dryness    BETWEEN 0 AND 10),
    emotional_stability  SMALLINT    CHECK (emotional_stability  BETWEEN 0 AND 10),
    decision_confidence  SMALLINT    CHECK (decision_confidence  BETWEEN 0 AND 10),

    -- Source of the record
    source_type          VARCHAR(30) DEFAULT 'checkin'
                             CHECK (source_type IN ('checkin','journal','decision','review','manual')),
    source_id            UUID,           -- FK to the source record (optional)

    -- Free-form notes
    notes                TEXT,

    -- Derived computed column (populated by application)
    wellbeing_composite  DECIMAL(4,2),   -- weighted average of metrics above

    PRIMARY KEY (user_id, recorded_at)
);

SELECT create_hypertable(
    'sfds_user_spiritual_timeline', 'recorded_at',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_ust_user_time
    ON sfds_user_spiritual_timeline (user_id, recorded_at DESC);


-- ──────────────────────────────────────────────────────────────────────────────
-- 2. decision_outcome_timeline
--    Tracks how a decision feels over time after being made.
-- ──────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sfds_decision_outcome_timeline (
    decision_id          UUID        NOT NULL REFERENCES sfds_decision_events(id) ON DELETE CASCADE,
    user_id              UUID        NOT NULL REFERENCES sfds_users(id) ON DELETE CASCADE,
    recorded_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    regret_level         SMALLINT    CHECK (regret_level            BETWEEN 0 AND 10),
    peace_after          SMALLINT    CHECK (peace_after             BETWEEN 0 AND 10),
    long_term_satisfaction SMALLINT  CHECK (long_term_satisfaction  BETWEEN 0 AND 10),
    alignment_score      SMALLINT    CHECK (alignment_score         BETWEEN 0 AND 10),

    notes                TEXT,

    PRIMARY KEY (decision_id, recorded_at)
);

SELECT create_hypertable(
    'sfds_decision_outcome_timeline', 'recorded_at',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_dot_decision_time
    ON sfds_decision_outcome_timeline (decision_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_dot_user_time
    ON sfds_decision_outcome_timeline (user_id, recorded_at DESC);


-- ──────────────────────────────────────────────────────────────────────────────
-- 3. emotional_cycle_series
--    High-resolution emotion intensity over time.
-- ──────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sfds_emotional_cycle_series (
    user_id              UUID        NOT NULL REFERENCES sfds_users(id) ON DELETE CASCADE,
    recorded_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    emotion_type         VARCHAR(50) NOT NULL,
    intensity            SMALLINT    NOT NULL CHECK (intensity BETWEEN 0 AND 10),

    -- Context
    trigger_description  TEXT,
    decision_context_id  UUID        REFERENCES sfds_decision_events(id) ON DELETE SET NULL,

    PRIMARY KEY (user_id, recorded_at, emotion_type)
);

SELECT create_hypertable(
    'sfds_emotional_cycle_series', 'recorded_at',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_ecs_user_emotion_time
    ON sfds_emotional_cycle_series (user_id, emotion_type, recorded_at DESC);


-- ──────────────────────────────────────────────────────────────────────────────
-- 4. Continuous aggregates — pre-computed weekly/monthly rollups
-- ──────────────────────────────────────────────────────────────────────────────

-- Weekly spiritual health aggregate
CREATE MATERIALIZED VIEW IF NOT EXISTS sfds_weekly_spiritual_health
WITH (timescaledb.continuous) AS
SELECT
    user_id,
    time_bucket('7 days', recorded_at)          AS week,
    AVG(anxiety_level)                           AS avg_anxiety,
    AVG(peace_level)                             AS avg_peace,
    AVG(clarity_level)                           AS avg_clarity,
    AVG(spiritual_dryness)                       AS avg_dryness,
    AVG(emotional_stability)                     AS avg_stability,
    AVG(decision_confidence)                     AS avg_confidence,
    COUNT(*)                                     AS data_points
FROM sfds_user_spiritual_timeline
GROUP BY user_id, week
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
    'sfds_weekly_spiritual_health',
    start_offset  => INTERVAL '3 months',
    end_offset    => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);


-- Weekly emotion intensity aggregate
CREATE MATERIALIZED VIEW IF NOT EXISTS sfds_weekly_emotion_intensity
WITH (timescaledb.continuous) AS
SELECT
    user_id,
    emotion_type,
    time_bucket('7 days', recorded_at)           AS week,
    AVG(intensity)                               AS avg_intensity,
    MAX(intensity)                               AS peak_intensity,
    COUNT(*)                                     AS occurrences
FROM sfds_emotional_cycle_series
GROUP BY user_id, emotion_type, week
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
    'sfds_weekly_emotion_intensity',
    start_offset  => INTERVAL '3 months',
    end_offset    => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);


-- ──────────────────────────────────────────────────────────────────────────────
-- 5. Retention policies — auto-drop raw data older than 2 years
-- ──────────────────────────────────────────────────────────────────────────────
SELECT add_retention_policy(
    'sfds_user_spiritual_timeline',
    INTERVAL '2 years',
    if_not_exists => TRUE
);

SELECT add_retention_policy(
    'sfds_emotional_cycle_series',
    INTERVAL '2 years',
    if_not_exists => TRUE
);


-- ──────────────────────────────────────────────────────────────────────────────
-- 6. Helper views for the temporal analytics engine
-- ──────────────────────────────────────────────────────────────────────────────

-- Last 30 days spiritual trend per user
CREATE OR REPLACE VIEW sfds_v_recent_spiritual_trend AS
SELECT
    user_id,
    DATE_TRUNC('day', recorded_at)  AS day,
    AVG(anxiety_level)              AS anxiety,
    AVG(peace_level)                AS peace,
    AVG(clarity_level)              AS clarity,
    AVG(spiritual_dryness)          AS dryness,
    AVG(emotional_stability)        AS stability
FROM sfds_user_spiritual_timeline
WHERE recorded_at > NOW() - INTERVAL '30 days'
GROUP BY user_id, day
ORDER BY user_id, day;


-- ──────────────────────────────────────────────────────────────────────────────
-- 4. sfds_formation_metrics  [v3 Formation Engine]
--    Tracks per-session character dimension deltas for long-term formation arcs.
--    Each row = one pipeline session's impact on the 7 character dimensions.
-- ──────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sfds_formation_metrics (
    user_id              TEXT         NOT NULL,
    session_id           TEXT         NOT NULL,
    recorded_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    decision_category    VARCHAR(60)  DEFAULT 'other',

    -- Was a behavioral loop broken in this session?
    loop_broken          BOOLEAN      NOT NULL DEFAULT FALSE,

    -- Which pattern categories were active? (e.g. '{"fear","shame"}')
    pattern_categories   TEXT[]       DEFAULT '{}',

    -- v3.1: 8-dimension FormationStateVector deltas (-1.0 to +1.0, clamped in application)
    humility_delta            REAL    DEFAULT 0.0,
    fear_tendency_delta       REAL    DEFAULT 0.0,
    pride_tendency_delta      REAL    DEFAULT 0.0,
    emotional_stability_delta REAL    DEFAULT 0.0,
    truth_alignment_delta     REAL    DEFAULT 0.0,
    relational_health_delta   REAL    DEFAULT 0.0,
    resilience_delta          REAL    DEFAULT 0.0,
    spiritual_clarity_delta   REAL    DEFAULT 0.0,

    -- Trajectory classification (v3.1)
    trajectory_direction  VARCHAR(40)  DEFAULT 'unknown',
    dominant_loop         VARCHAR(60)  DEFAULT 'unknown',
    emotional_intensity   REAL         DEFAULT 5.0,
    reflection_active     BOOLEAN      NOT NULL DEFAULT FALSE
);

SELECT create_hypertable(
    'sfds_formation_metrics', 'recorded_at',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_sfds_formation_user_time
    ON sfds_formation_metrics (user_id, recorded_at DESC);

-- Continuous aggregate: 30-day rolling dimension averages per user
CREATE MATERIALIZED VIEW IF NOT EXISTS sfds_formation_rolling_avg
WITH (timescaledb.continuous) AS
SELECT
    user_id,
    time_bucket('30 days', recorded_at)    AS bucket,
    AVG(humility_delta)                    AS avg_humility,
    AVG(fear_tendency_delta)               AS avg_fear_tendency,
    AVG(pride_tendency_delta)              AS avg_pride_tendency,
    AVG(emotional_stability_delta)         AS avg_emotional_stability,
    AVG(truth_alignment_delta)             AS avg_truth_alignment,
    AVG(relational_health_delta)           AS avg_relational_health,
    AVG(resilience_delta)                  AS avg_resilience,
    AVG(spiritual_clarity_delta)           AS avg_spiritual_clarity,
    COUNT(*)                               AS sessions,
    SUM(loop_broken::int)                  AS loop_breaks
FROM sfds_formation_metrics
GROUP BY user_id, bucket
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
    'sfds_formation_rolling_avg',
    start_offset  => INTERVAL '6 months',
    end_offset    => INTERVAL '1 day',
    schedule_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Retention: keep raw formation events for 2 years
SELECT add_retention_policy(
    'sfds_formation_metrics',
    INTERVAL '2 years',
    if_not_exists => TRUE
);


-- ──────────────────────────────────────────────────────────────────────────────
-- Emotion recurrence — weekly pattern for cycle detection
CREATE OR REPLACE VIEW sfds_v_emotion_recurrence AS
SELECT
    user_id,
    emotion_type,
    EXTRACT(DOW FROM recorded_at)   AS day_of_week,   -- 0=Sun ... 6=Sat
    EXTRACT(HOUR FROM recorded_at)  AS hour_of_day,
    AVG(intensity)                  AS avg_intensity,
    COUNT(*)                        AS occurrences
FROM sfds_emotional_cycle_series
WHERE recorded_at > NOW() - INTERVAL '90 days'
GROUP BY user_id, emotion_type, day_of_week, hour_of_day
ORDER BY user_id, occurrences DESC;
