-- 0095_fix_united_kingdom_and_dedupe_edges.sql
-- 修正关系图谱数据质量问题：
--  1. 「统一王国」节点被 0060 的通用规则 (role='君王' -> nation-united-kingdom) 错误地连上了
--     所有君王（含分裂王国、外邦、甚至耶稣基督）。只应保留统一王国三王：扫罗 / 大卫 / 所罗门。
--  2. 同一对节点之间的重复边（0060/0066/0094 因经文出处不同未被唯一索引去重）需合并为一条。
-- 幂等：DELETE 可安全重复执行。

-- A. 移除错误挂到「统一王国」的人物边（仅保留扫罗/大卫/所罗门；非人物节点不动）。
DELETE FROM biblical_graph_edges e
USING biblical_graph_nodes n
WHERE 'nation-united-kingdom' IN (e.source_node_id, e.target_node_id)
  AND n.id = CASE WHEN e.source_node_id = 'nation-united-kingdom'
                  THEN e.target_node_id ELSE e.source_node_id END
  AND n.node_type = 'character'
  AND NOT EXISTS (
    SELECT 1 FROM biblical_characters c
    WHERE c.id = n.character_id AND c.name IN ('扫罗', '大卫', '所罗门')
  );

-- B. 全图：去掉「同源同目标同关系类型」的重复边（仅因经文出处不同而重复），每组保留权重最高(并列取最小 id)。
DELETE FROM biblical_graph_edges e
USING biblical_graph_edges keep
WHERE e.source_node_id = keep.source_node_id
  AND e.target_node_id = keep.target_node_id
  AND e.relationship_type = keep.relationship_type
  AND (e.weight < keep.weight OR (e.weight = keep.weight AND e.id > keep.id));

-- C. 「统一王国」相关：进一步把同一人物的多条边合并为一条（如所罗门的 统治/君王/国势鼎盛 → 一条），
--    每个有向节点对只保留权重最高的一条，避免同名在关系列表里重复出现。
DELETE FROM biblical_graph_edges e
USING biblical_graph_edges keep
WHERE 'nation-united-kingdom' IN (e.source_node_id, e.target_node_id)
  AND keep.source_node_id = e.source_node_id
  AND keep.target_node_id = e.target_node_id
  AND (e.weight < keep.weight OR (e.weight = keep.weight AND e.id > keep.id));

-- End of 0095.
