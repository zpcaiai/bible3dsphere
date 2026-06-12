-- 修复 0060 migration 视图列名变更问题
-- 执行: psql $DATABASE_URL -f scripts/fix_0060_migration.sql

-- 1. 先删除旧视图（解除列名依赖）
DROP VIEW IF EXISTS v_biblical_knowledge_graph_nodes CASCADE;
DROP VIEW IF EXISTS v_biblical_knowledge_graph_edges CASCADE;

-- 2. 重新运行 0060 的视图定义（复制自 0060 migration）
CREATE OR REPLACE VIEW v_biblical_knowledge_graph_edges AS
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
    e.scripture_refs,
    e.confidence_level,
    e.description,
    e.weight,
    e.confidence,
    e.is_directed
FROM biblical_graph_edges e
JOIN biblical_graph_nodes source ON source.id = e.source_node_id
JOIN biblical_graph_nodes target ON target.id = e.target_node_id
WHERE e.is_active = true
  AND source.is_active = true
  AND target.is_active = true;

CREATE OR REPLACE VIEW v_biblical_knowledge_graph_nodes AS
SELECT
    n.*,
    COALESCE(deg.degree, 0) AS degree,
    COALESCE(deg.out_degree, 0) AS out_degree,
    COALESCE(deg.in_degree, 0) AS in_degree
FROM biblical_graph_nodes n
LEFT JOIN (
    SELECT
        node_id,
        COUNT(*) AS degree,
        COUNT(*) FILTER (WHERE direction = 'out') AS out_degree,
        COUNT(*) FILTER (WHERE direction = 'in') AS in_degree
    FROM (
        SELECT source_node_id AS node_id, 'out' AS direction
        FROM biblical_graph_edges WHERE is_active = true
        UNION ALL
        SELECT target_node_id AS node_id, 'in' AS direction
        FROM biblical_graph_edges WHERE is_active = true
    ) rels
    GROUP BY node_id
) deg ON deg.node_id = n.id
WHERE n.is_active = true;

-- 3. 标记 0060 为已执行
INSERT INTO schema_migrations (version, name, checksum)
VALUES ('0060_standardize_biblical_graph_relationships', 'standardize_biblical_graph_relationships', 'skipped_v2')
ON CONFLICT (version) DO UPDATE SET checksum = EXCLUDED.checksum;

-- 验证
SELECT '0060 views recreated' AS status,
       EXISTS(SELECT 1 FROM information_schema.views WHERE view_name = 'v_biblical_knowledge_graph_nodes') AS nodes_view_ok,
       EXISTS(SELECT 1 FROM information_schema.views WHERE view_name = 'v_biblical_knowledge_graph_edges') AS edges_view_ok;
