-- Exclude mirror-only church-era figures from the biblical knowledge graph.
--
-- mirrorData may intentionally keep church-history cards for devotional use,
-- but the canonical biblical graph must only expose biblical-era entities.
-- This cleanup handles databases that already applied older graph syncs before
-- the 0059/0062 non-教会时代 filters were added.

WITH church_era_nodes AS (
    SELECT n.id
    FROM biblical_graph_nodes n
    LEFT JOIN biblical_characters c ON c.id = n.character_id
    WHERE n.is_active = true
      AND (
          (n.node_type = 'character' AND c.era = '教会时代')
          OR n.era = '教会时代'
          OR n.id = 'theme-era-' || SUBSTRING(md5('教会时代'), 1, 12)
      )
)
UPDATE biblical_graph_edges e
SET is_active = false
WHERE e.is_active = true
  AND (
      e.source_node_id IN (SELECT id FROM church_era_nodes)
      OR e.target_node_id IN (SELECT id FROM church_era_nodes)
  );

UPDATE biblical_graph_nodes n
SET is_active = false
FROM biblical_characters c
WHERE n.character_id = c.id
  AND c.era = '教会时代'
  AND n.is_active = true;

UPDATE biblical_graph_nodes
SET is_active = false
WHERE is_active = true
  AND (
      era = '教会时代'
      OR id = 'theme-era-' || SUBSTRING(md5('教会时代'), 1, 12)
  );

DROP VIEW IF EXISTS v_biblical_knowledge_graph_edges;
DROP VIEW IF EXISTS v_biblical_knowledge_graph_nodes;

CREATE VIEW v_biblical_knowledge_graph_edges AS
SELECT
    e.id,
    e.source_node_id AS source,
    source.name AS source_name,
    source.node_type AS source_type,
    e.target_node_id AS target,
    target.name AS target_name,
    target.node_type AS target_type,
    e.relationship_type,
    e.relationship_category,
    e.label_zh,
    e.label_en,
    e.scripture_ref,
    e.description,
    e.weight,
    e.confidence,
    e.is_directed
FROM biblical_graph_edges e
JOIN biblical_graph_nodes source ON source.id = e.source_node_id
JOIN biblical_graph_nodes target ON target.id = e.target_node_id
LEFT JOIN biblical_characters source_char ON source_char.id = source.character_id
LEFT JOIN biblical_characters target_char ON target_char.id = target.character_id
WHERE e.is_active = true
  AND source.is_active = true
  AND target.is_active = true
  AND COALESCE(source_char.era, source.era, '') <> '教会时代'
  AND COALESCE(target_char.era, target.era, '') <> '教会时代';

CREATE VIEW v_biblical_knowledge_graph_nodes AS
SELECT
    n.*,
    COALESCE(deg.degree, 0) AS degree,
    COALESCE(deg.out_degree, 0) AS out_degree,
    COALESCE(deg.in_degree, 0) AS in_degree
FROM biblical_graph_nodes n
LEFT JOIN biblical_characters c ON c.id = n.character_id
LEFT JOIN (
    SELECT
         node_id,
         COUNT(*) AS degree,
         COUNT(*) FILTER (WHERE direction = 'out') AS out_degree,
         COUNT(*) FILTER (WHERE direction = 'in') AS in_degree
    FROM (
         SELECT e.source_node_id AS node_id, 'out' AS direction
         FROM biblical_graph_edges e
         JOIN biblical_graph_nodes source ON source.id = e.source_node_id
         JOIN biblical_graph_nodes target ON target.id = e.target_node_id
         LEFT JOIN biblical_characters source_char ON source_char.id = source.character_id
         LEFT JOIN biblical_characters target_char ON target_char.id = target.character_id
         WHERE e.is_active = true
           AND source.is_active = true
           AND target.is_active = true
           AND COALESCE(source_char.era, source.era, '') <> '教会时代'
           AND COALESCE(target_char.era, target.era, '') <> '教会时代'
         UNION ALL
         SELECT e.target_node_id AS node_id, 'in' AS direction
         FROM biblical_graph_edges e
         JOIN biblical_graph_nodes source ON source.id = e.source_node_id
         JOIN biblical_graph_nodes target ON target.id = e.target_node_id
         LEFT JOIN biblical_characters source_char ON source_char.id = source.character_id
         LEFT JOIN biblical_characters target_char ON target_char.id = target.character_id
         WHERE e.is_active = true
           AND source.is_active = true
           AND target.is_active = true
           AND COALESCE(source_char.era, source.era, '') <> '教会时代'
           AND COALESCE(target_char.era, target.era, '') <> '教会时代'
    ) rels
    GROUP BY node_id
) deg ON deg.node_id = n.id
WHERE n.is_active = true
  AND COALESCE(c.era, n.era, '') <> '教会时代';
