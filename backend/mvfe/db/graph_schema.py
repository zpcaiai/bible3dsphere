"""
MVFE Graph Schema (PostgreSQL, replaces Neo4j)
Two tables: mvfe_graph_nodes + mvfe_graph_edges
Loop detection via Recursive CTE.
"""

MVFE_GRAPH_SCHEMA_SQL = """
-- ── Node table ─────────────────────────────────────────────────
-- Stores all causal nodes: Emotion, Desire, Belief, Behavior, Outcome, Attention, Decision
CREATE TABLE IF NOT EXISTS mvfe_graph_nodes (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     TEXT        NOT NULL,
    node_type   TEXT        NOT NULL,   -- Emotion | Desire | Belief | Behavior | Outcome | Attention | Decision
    node_name   TEXT        NOT NULL,   -- e.g. "anxiety", "safety", "avoidance_prevents_harm"
    properties  JSONB       NOT NULL DEFAULT '{}',
    strength    REAL        NOT NULL DEFAULT 1.0,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, node_type, node_name)
);

CREATE INDEX IF NOT EXISTS idx_graph_nodes_user ON mvfe_graph_nodes(user_id);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_type ON mvfe_graph_nodes(user_id, node_type);

-- ── Edge table ─────────────────────────────────────────────────
-- Stores causal relationships: CAUSES | DRIVES | LEADS_TO | REINFORCES | AMPLIFIES
CREATE TABLE IF NOT EXISTS mvfe_graph_edges (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         TEXT        NOT NULL,
    source_id       UUID        NOT NULL REFERENCES mvfe_graph_nodes(id) ON DELETE CASCADE,
    target_id       UUID        NOT NULL REFERENCES mvfe_graph_nodes(id) ON DELETE CASCADE,
    edge_type       TEXT        NOT NULL,   -- CAUSES | DRIVES | LEADS_TO | REINFORCES | AMPLIFIES | DRIVES_TO
    weight          REAL        NOT NULL DEFAULT 1.0,
    traversal_count INT         NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, source_id, target_id, edge_type)
);

CREATE INDEX IF NOT EXISTS idx_graph_edges_user    ON mvfe_graph_edges(user_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_source  ON mvfe_graph_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_target  ON mvfe_graph_edges(target_id);
"""

# ── Recursive CTE: detect HIDOS formation loops (up to 6 hops) ──────────────────
#
# HIDOS loop:
#   Emotion -[CAUSES]-> Desire -[DRIVES]-> Behavior -[LEADS_TO]-> Outcome
#           -[REINFORCES]-> Belief -[AMPLIFIES]-> Emotion  (5 hops = 1 full loop)
#
# We search paths starting at Emotion nodes and detect when a path
# returns to the same Emotion node within ≤6 hops.
LOOP_DETECTION_CTE = """
WITH RECURSIVE graph_path AS (
    -- ── Anchor: start from every Emotion node for this user ──
    SELECT
        n.id            AS origin_id,
        n.node_name     AS origin_name,
        n.strength      AS origin_strength,
        n.id            AS current_id,
        n.node_type     AS current_type,
        n.node_name     AS current_name,
        ARRAY[n.id]     AS visited_ids,
        ARRAY[n.node_type || ':' || n.node_name] AS path_labels,
        1               AS depth
    FROM mvfe_graph_nodes n
    WHERE n.user_id = %(user_id)s
      AND n.node_type = 'Emotion'

    UNION ALL

    -- ── Recursive: follow edges, avoid revisiting nodes ──
    SELECT
        gp.origin_id,
        gp.origin_name,
        gp.origin_strength,
        e.target_id                                             AS current_id,
        n2.node_type                                            AS current_type,
        n2.node_name                                            AS current_name,
        gp.visited_ids || e.target_id                          AS visited_ids,
        gp.path_labels || (n2.node_type || ':' || n2.node_name) AS path_labels,
        gp.depth + 1                                            AS depth
    FROM graph_path gp
    JOIN mvfe_graph_edges e  ON e.source_id = gp.current_id AND e.user_id = %(user_id)s
    JOIN mvfe_graph_nodes n2 ON n2.id = e.target_id
    WHERE gp.depth < 6                              -- hard limit: max 6 hops
      AND NOT (e.target_id = ANY(gp.visited_ids))  -- no revisit (cycle guard)
)
-- ── Find paths whose current node connects back to the origin Emotion ──
SELECT
    gp.origin_name                              AS loop_anchor,
    gp.origin_strength                          AS anchor_strength,
    gp.depth                                    AS loop_depth,
    gp.path_labels                              AS path,
    e_back.weight                               AS closing_edge_weight,
    COUNT(*) OVER (PARTITION BY gp.origin_id)   AS loop_count
FROM graph_path gp
JOIN mvfe_graph_edges e_back
    ON e_back.source_id = gp.current_id
   AND e_back.target_id = gp.origin_id
   AND e_back.user_id = %(user_id)s
WHERE gp.depth >= 3   -- minimum meaningful loop: at least 3 intermediate nodes
ORDER BY gp.origin_strength DESC, gp.depth ASC
LIMIT 10;
"""

# ── 3-hop neighbourhood query (for future social/contextual features) ──────────
NEIGHBOURHOOD_CTE = """
WITH RECURSIVE graph_path AS (
    SELECT source_id, target_id, 1 AS depth, edge_type
    FROM mvfe_graph_edges
    WHERE user_id = %(user_id)s AND source_id = %(start_id)s

    UNION

    SELECT c.source_id, c.target_id, p.depth + 1, c.edge_type
    FROM mvfe_graph_edges c
    JOIN graph_path p ON c.source_id = p.target_id AND c.user_id = %(user_id)s
    WHERE p.depth < %(max_depth)s
)
SELECT gp.*, n.node_name, n.node_type
FROM graph_path gp
JOIN mvfe_graph_nodes n ON n.id = gp.target_id
ORDER BY depth, edge_type;
"""
