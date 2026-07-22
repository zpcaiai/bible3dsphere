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
    position_x  REAL,
    position_y  REAL,
    position_z  REAL,
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
    properties      JSONB       NOT NULL DEFAULT '{}',
    weight          REAL        NOT NULL DEFAULT 1.0,
    traversal_count INT         NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, source_id, target_id, edge_type)
);

CREATE INDEX IF NOT EXISTS idx_graph_edges_user    ON mvfe_graph_edges(user_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_source  ON mvfe_graph_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_target  ON mvfe_graph_edges(target_id);
CREATE INDEX IF NOT EXISTS idx_graph_nodes_updated ON mvfe_graph_nodes(user_id, updated_at DESC);

-- Existing installations may predate position/provenance columns; CREATE TABLE
-- IF NOT EXISTS does not evolve them, so keep these upgrades idempotent here.
ALTER TABLE mvfe_graph_nodes ADD COLUMN IF NOT EXISTS position_x REAL;
ALTER TABLE mvfe_graph_nodes ADD COLUMN IF NOT EXISTS position_y REAL;
ALTER TABLE mvfe_graph_nodes ADD COLUMN IF NOT EXISTS position_z REAL;
ALTER TABLE mvfe_graph_edges ADD COLUMN IF NOT EXISTS properties JSONB NOT NULL DEFAULT '{}';

-- Append/update one row per decision or reflection event so the aggregate node
-- graph never becomes the only source of historical truth.
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
      AND COALESCE(e.properties->>'evidence_status', 'observed') <> 'pending'
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
   AND COALESCE(e_back.properties->>'evidence_status', 'observed') <> 'pending'
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

# Position columns for 3D visualization
POSITION_COLUMNS_SQL = """
ALTER TABLE mvfe_graph_nodes ADD COLUMN IF NOT EXISTS position_x REAL;
ALTER TABLE mvfe_graph_nodes ADD COLUMN IF NOT EXISTS position_y REAL;
ALTER TABLE mvfe_graph_nodes ADD COLUMN IF NOT EXISTS position_z REAL;
"""

# Disciple chain depth CTE
DISCIPLE_CHAIN_CTE = """
WITH RECURSIVE disciple_chain AS (
    SELECT source_id, target_id, 1 AS depth, ARRAY[source_id] AS visited
    FROM mvfe_graph_edges
    WHERE user_id = %(user_id)s AND source_id = %(start_id)s AND edge_type = 'DISCIPLES'
    UNION ALL
    SELECT c.source_id, c.target_id, dc.depth + 1, dc.visited || c.source_id
    FROM mvfe_graph_edges c
    JOIN disciple_chain dc ON c.source_id = dc.target_id
    WHERE dc.depth < 10 AND NOT (c.source_id = ANY(dc.visited))
      AND c.edge_type = 'DISCIPLES' AND c.user_id = %(user_id)s
)
SELECT MAX(depth) AS max_depth, COUNT(DISTINCT target_id) AS reach
FROM disciple_chain;
"""

# Subgraph query for 3D visualization
SUBGRAPH_CTE = """
WITH RECURSIVE walk(id, depth) AS (
    SELECT n.id, 0 AS depth
    FROM mvfe_graph_nodes n
    WHERE n.id = %(focus_id)s AND n.user_id = %(user_id)s
    UNION
    SELECT neighbour.id, walk.depth + 1
    FROM walk
    JOIN mvfe_graph_edges e
      ON (e.source_id = walk.id OR e.target_id = walk.id)
     AND e.user_id = %(user_id)s
    JOIN mvfe_graph_nodes neighbour
      ON neighbour.id = CASE WHEN e.source_id = walk.id THEN e.target_id ELSE e.source_id END
     AND neighbour.user_id = %(user_id)s
    WHERE walk.depth < %(max_depth)s
), nearest AS (
    SELECT id, MIN(depth) AS depth
    FROM walk
    GROUP BY id
    ORDER BY MIN(depth), id
    LIMIT %(max_nodes)s
)
SELECT n.id, n.node_type, n.node_name, n.properties, n.strength,
       n.position_x, n.position_y, n.position_z, nearest.depth
FROM nearest
JOIN mvfe_graph_nodes n ON n.id = nearest.id
ORDER BY nearest.depth, n.strength DESC, n.id;
"""

# Graph health check queries
ISOLATED_NODES_SQL = """
SELECT n.id, n.node_type, n.node_name, n.user_id
FROM mvfe_graph_nodes n
LEFT JOIN mvfe_graph_edges e_out ON e_out.source_id = n.id
LEFT JOIN mvfe_graph_edges e_in  ON e_in.target_id = n.id
WHERE e_out.id IS NULL AND e_in.id IS NULL
  AND (%(user_id)s IS NULL OR n.user_id = %(user_id)s);
"""

DANGLING_EDGES_SQL = """
SELECT e.id, e.source_id, e.target_id, e.edge_type
FROM mvfe_graph_edges e
LEFT JOIN mvfe_graph_nodes ns ON ns.id = e.source_id
LEFT JOIN mvfe_graph_nodes nt ON nt.id = e.target_id
WHERE (ns.id IS NULL OR nt.id IS NULL)
  AND (%(user_id)s IS NULL OR e.user_id = %(user_id)s);
"""

CONNECTED_COMPONENTS_SQL = """
WITH RECURSIVE reach(root_id, node_id) AS (
    SELECT id, id
    FROM mvfe_graph_nodes
    WHERE (%(user_id)s IS NULL OR user_id = %(user_id)s)
    UNION
    SELECT reach.root_id,
           CASE WHEN e.source_id = reach.node_id THEN e.target_id ELSE e.source_id END
    FROM reach
    JOIN mvfe_graph_nodes current_node ON current_node.id = reach.node_id
    JOIN mvfe_graph_edges e
      ON (e.source_id = reach.node_id OR e.target_id = reach.node_id)
     AND e.user_id = current_node.user_id
    JOIN mvfe_graph_nodes neighbour
      ON neighbour.id = CASE WHEN e.source_id = reach.node_id THEN e.target_id ELSE e.source_id END
     AND neighbour.user_id = current_node.user_id
), assigned AS (
    SELECT node_id, MIN(root_id::text) AS component_id
    FROM reach
    GROUP BY node_id
)
SELECT COUNT(DISTINCT component_id) AS component_count
FROM assigned;
"""

# Shared write-back contract used by graph services that persist a pattern match.
PATTERN_WRITE_BACK_SQL = """
INSERT INTO mvfe_graph_nodes (user_id, node_type, node_name, properties, strength)
VALUES (%(user_id)s, %(node_type)s, %(node_name)s, %(properties)s, %(strength)s)
ON CONFLICT (user_id, node_type, node_name) DO UPDATE
SET properties = mvfe_graph_nodes.properties || EXCLUDED.properties,
    strength = GREATEST(mvfe_graph_nodes.strength, EXCLUDED.strength),
    updated_at = NOW()
RETURNING id;
"""

# Compact governance snapshot suitable for a health endpoint or scheduled job.
GRAPH_HEALTH_CHECK_SQL = """
SELECT
    (SELECT COUNT(*) FROM mvfe_graph_nodes
      WHERE (%(user_id)s IS NULL OR user_id = %(user_id)s)) AS total_nodes,
    (SELECT COUNT(*) FROM mvfe_graph_edges
      WHERE (%(user_id)s IS NULL OR user_id = %(user_id)s)) AS total_edges,
    (SELECT COUNT(*) FROM mvfe_graph_nodes n
      WHERE (%(user_id)s IS NULL OR n.user_id = %(user_id)s)
        AND NOT EXISTS (SELECT 1 FROM mvfe_graph_edges e
                        WHERE e.source_id = n.id OR e.target_id = n.id)) AS isolated_nodes;
"""
