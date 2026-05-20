-- Neon PostgreSQL 兼容迁移脚本
-- 适用于标准 PostgreSQL (无 TimescaleDB)

-- 1. 创建 sfds_behavior_history 表 (标准 PostgreSQL 版本)
CREATE TABLE IF NOT EXISTS sfds_behavior_history (
    id                   BIGSERIAL    PRIMARY KEY,
    user_id              TEXT         NOT NULL,
    session_id           TEXT         NOT NULL,
    executed_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    -- Task info
    task                 TEXT         NOT NULL,
    original_task        TEXT,

    -- Energy and motivation levels (1-5, 1-10)
    energy_level         INTEGER      CHECK (energy_level BETWEEN 1 AND 5) DEFAULT 3,
    motivation           INTEGER      CHECK (motivation BETWEEN 1 AND 10) DEFAULT 5,

    -- Tier executed (Green/Yellow/Red)
    tier_executed        VARCHAR(20)  NOT NULL DEFAULT 'Yellow',

    -- Regulation result
    min_executable_action TEXT,
    task_downgrade        TEXT,
    emotional_compensation TEXT,
    continuity_advice     TEXT,

    -- Execution outcome
    was_completed       BOOLEAN      NOT NULL DEFAULT FALSE,
    completion_percentage INTEGER      CHECK (completion_percentage BETWEEN 0 AND 100) DEFAULT 0,
    resistance_at_start   INTEGER      CHECK (resistance_at_start BETWEEN 1 AND 10),

    -- System state
    system_energy_state   VARCHAR(20)  DEFAULT 'normal',
    shame_prevented       BOOLEAN      NOT NULL DEFAULT FALSE
);

-- 标准索引 (替代 hypertable)
CREATE INDEX IF NOT EXISTS idx_sfds_behavior_user_time
    ON sfds_behavior_history (user_id, executed_at DESC);

CREATE INDEX IF NOT EXISTS idx_sfds_behavior_tier
    ON sfds_behavior_history (user_id, tier_executed);

-- 2. 确保 sfds_formation_metrics 表存在 (简化版本)
CREATE TABLE IF NOT EXISTS sfds_formation_metrics (
    user_id              TEXT         NOT NULL,
    session_id           TEXT         NOT NULL,
    recorded_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    decision_category    VARCHAR(60)  DEFAULT 'other',
    loop_broken          BOOLEAN      NOT NULL DEFAULT FALSE,
    pattern_categories   TEXT[]       DEFAULT '{}',
    
    -- 8-dimension FormationStateVector deltas
    humility_delta            REAL    DEFAULT 0.0,
    fear_tendency_delta       REAL    DEFAULT 0.0,
    pride_tendency_delta      REAL    DEFAULT 0.0,
    emotional_stability_delta REAL    DEFAULT 0.0,
    truth_alignment_delta     REAL    DEFAULT 0.0,
    relational_health_delta   REAL    DEFAULT 0.0,
    resilience_delta          REAL    DEFAULT 0.0,
    spiritual_clarity_delta   REAL    DEFAULT 0.0,
    
    -- Trajectory classification
    trajectory_direction  VARCHAR(40)  DEFAULT 'unknown',
    dominant_loop         VARCHAR(60)  DEFAULT 'unknown',
    emotional_intensity   REAL         DEFAULT 5.0,
    reflection_active     BOOLEAN      NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_sfds_formation_user_time
    ON sfds_formation_metrics (user_id, recorded_at DESC);
