-- Migration 0221: Unify graph storage on PostgreSQL
-- Adds 3D position columns to mvfe_graph_nodes for 3D visualization support
-- Part of the Neo4j → PostgreSQL graph unification

ALTER TABLE mvfe_graph_nodes ADD COLUMN IF NOT EXISTS position_x REAL;
ALTER TABLE mvfe_graph_nodes ADD COLUMN IF NOT EXISTS position_y REAL;
ALTER TABLE mvfe_graph_nodes ADD COLUMN IF NOT EXISTS position_z REAL;

-- Formation Twin temporal/review projections attach provenance to edges.
ALTER TABLE mvfe_graph_edges ADD COLUMN IF NOT EXISTS properties JSONB NOT NULL DEFAULT '{}';

CREATE TABLE IF NOT EXISTS mvfe_graph_events (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          TEXT        NOT NULL,
    event_id         TEXT        NOT NULL,
    emotion_name     TEXT,
    desire_name      TEXT,
    behavior_name    TEXT,
    outcome_name     TEXT,
    belief_name      TEXT,
    status           TEXT        NOT NULL DEFAULT 'OBSERVED',
    matched_patterns JSONB       NOT NULL DEFAULT '[]',
    properties       JSONB       NOT NULL DEFAULT '{}',
    observed_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at      TIMESTAMPTZ,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, event_id)
);
CREATE INDEX IF NOT EXISTS idx_graph_events_user_time
    ON mvfe_graph_events(user_id, observed_at DESC);

-- Index for efficient subgraph queries
CREATE INDEX IF NOT EXISTS idx_graph_nodes_id_user ON mvfe_graph_nodes(id, user_id);

-- Composite index for edge traversal in both directions
CREATE INDEX IF NOT EXISTS idx_graph_edges_both_ends ON mvfe_graph_edges(source_id, target_id, user_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_target_source ON mvfe_graph_edges(target_id, source_id, user_id);

-- Index for pattern seeding queries
CREATE INDEX IF NOT EXISTS idx_graph_nodes_system ON mvfe_graph_nodes(user_id, node_type) WHERE user_id = '__system__';
CREATE INDEX IF NOT EXISTS idx_graph_nodes_updated ON mvfe_graph_nodes(user_id, updated_at DESC);

-- Operational view used by health checks without returning personal node content.
CREATE OR REPLACE VIEW mvfe_graph_health_summary AS
SELECT users.user_id,
       users.node_count,
       COALESCE(edges.edge_count, 0) AS edge_count,
       users.isolated_node_count,
       users.positioned_node_count,
       users.last_node_update
FROM (
    SELECT n.user_id,
           COUNT(*) AS node_count,
           COUNT(*) FILTER (
               WHERE NOT EXISTS (
                   SELECT 1 FROM mvfe_graph_edges e
                   WHERE e.source_id = n.id OR e.target_id = n.id
               )
           ) AS isolated_node_count,
           COUNT(*) FILTER (
               WHERE n.position_x IS NOT NULL
                 AND n.position_y IS NOT NULL
                 AND n.position_z IS NOT NULL
           ) AS positioned_node_count,
           MAX(n.updated_at) AS last_node_update
    FROM mvfe_graph_nodes n
    GROUP BY n.user_id
) users
LEFT JOIN (
    SELECT user_id, COUNT(*) AS edge_count
    FROM mvfe_graph_edges
    GROUP BY user_id
) edges USING (user_id);
