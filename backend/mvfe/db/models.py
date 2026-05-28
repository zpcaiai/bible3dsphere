"""
MVFE Database Models / Schema SQL
"""

MVFE_TABLES_SQL = """
-- MVFE Events Table (TimescaleDB hypertable)
CREATE TABLE IF NOT EXISTS mvfe_events (
    id UUID DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    type TEXT NOT NULL,
    payload JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
);

-- Convert to TimescaleDB hypertable (ignore error if already exists)
DO $$
BEGIN
    PERFORM create_hypertable('mvfe_events', 'created_at',
        chunk_time_interval => INTERVAL '7 days',
        if_not_exists => TRUE);
EXCEPTION WHEN OTHERS THEN
    NULL; -- TimescaleDB not available or already hypertable
END $$;

-- MVFE Formation State (upsert target)
CREATE TABLE IF NOT EXISTS mvfe_formation_state (
    user_id TEXT PRIMARY KEY,
    emotion JSONB,
    attention JSONB,
    decision JSONB,
    context JSONB,
    formation_score REAL DEFAULT 0.0,
    drift_score REAL DEFAULT 0.0,
    stability_score REAL DEFAULT 0.0,
    trajectory_vector JSONB,
    loop_detected BOOLEAN DEFAULT FALSE,
    loop_type TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- MVFE Memories (pgvector with HNSW index)
CREATE TABLE IF NOT EXISTS mvfe_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- HNSW index for fast ANN search
CREATE INDEX IF NOT EXISTS idx_mvfe_memories_embedding
    ON mvfe_memories USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Loop Detection History (TimescaleDB hypertable for trend analysis)
CREATE TABLE IF NOT EXISTS mvfe_loop_history (
    id UUID DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    loop_detected BOOLEAN NOT NULL,
    loop_type TEXT,
    loop_strength REAL DEFAULT 0.0,
    emotion_primary TEXT,
    emotion_intensity REAL,
    decision_type TEXT,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (id, recorded_at)
);

DO $$
BEGIN
    PERFORM create_hypertable('mvfe_loop_history', 'recorded_at',
        chunk_time_interval => INTERVAL '30 days',
        if_not_exists => TRUE);
EXCEPTION WHEN OTHERS THEN
    NULL;
END $$;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_mvfe_events_user_id ON mvfe_events(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_mvfe_memories_user_id ON mvfe_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_mvfe_loop_history_user ON mvfe_loop_history(user_id, recorded_at DESC);

-- Prompt Registry Table
CREATE TABLE IF NOT EXISTS mvfe_prompt_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt_name TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    content TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    performance_score REAL DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(prompt_name, version)
);

-- Drift Events Log (TimescaleDB hypertable)
CREATE TABLE IF NOT EXISTS mvfe_drift_events (
    id UUID DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    epsilon_pred REAL DEFAULT 0.0,
    epsilon_attr REAL DEFAULT 0.0,
    epsilon_loop REAL DEFAULT 0.0,
    total_error REAL DEFAULT 0.0,
    triggered_update BOOLEAN DEFAULT FALSE,
    prompt_version INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (id, timestamp)
);

DO $$
BEGIN
    PERFORM create_hypertable('mvfe_drift_events', 'timestamp',
        chunk_time_interval => INTERVAL '30 days',
        if_not_exists => TRUE);
EXCEPTION WHEN OTHERS THEN
    NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_mvfe_drift_user_id ON mvfe_drift_events(user_id, timestamp DESC);
"""


MVFE_TABLES_SQL_NO_VECTOR = """
-- MVFE Events Table
CREATE TABLE IF NOT EXISTS mvfe_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    type TEXT NOT NULL,
    payload JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- MVFE Formation State (upsert target)
CREATE TABLE IF NOT EXISTS mvfe_formation_state (
    user_id TEXT PRIMARY KEY,
    emotion JSONB,
    attention JSONB,
    decision JSONB,
    context JSONB,
    formation_score REAL DEFAULT 0.0,
    drift_score REAL DEFAULT 0.0,
    stability_score REAL DEFAULT 0.0,
    trajectory_vector JSONB,
    loop_detected BOOLEAN DEFAULT FALSE,
    loop_type TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- MVFE Memories (no vector - fallback)
CREATE TABLE IF NOT EXISTS mvfe_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_mvfe_events_user_id ON mvfe_events(user_id);
CREATE INDEX IF NOT EXISTS idx_mvfe_events_created_at ON mvfe_events(created_at);
CREATE INDEX IF NOT EXISTS idx_mvfe_memories_user_id ON mvfe_memories(user_id);

-- Prompt Registry Table
CREATE TABLE IF NOT EXISTS mvfe_prompt_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt_name TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    content TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    performance_score REAL DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(prompt_name, version)
);

-- Drift Events Log (system memory for error tracking)
CREATE TABLE IF NOT EXISTS mvfe_drift_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    epsilon_pred REAL DEFAULT 0.0,
    epsilon_attr REAL DEFAULT 0.0,
    epsilon_loop REAL DEFAULT 0.0,
    total_error REAL DEFAULT 0.0,
    triggered_update BOOLEAN DEFAULT FALSE,
    prompt_version INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mvfe_drift_user_id ON mvfe_drift_events(user_id);
CREATE INDEX IF NOT EXISTS idx_mvfe_drift_timestamp ON mvfe_drift_events(timestamp);
"""
