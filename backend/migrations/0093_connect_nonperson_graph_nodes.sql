-- 0093_connect_nonperson_graph_nodes.sql
-- 关系图谱：把「非人物」节点（时代/主题/事件）连到引用它们的人物，解决
-- 「按主题/事件聚焦时只有一个孤立节点、展不开」的问题（例如「新约时代」）。
-- 数据来源：biblical_graph_nodes 上人物节点已有的 era / theological_themes / key_events 字段，
-- 不引入新数据，只把已存在的引用关系「物化」成图谱的边。
-- 幂等：每条边用 NOT EXISTS 去重，可安全重复执行（迁移可能因 checksum 变化被重跑）。
--
-- 说明：地点/邦国/群体（place/nation/group）缺少可派生的人物关联字段，本迁移不处理，
--       它们若要可展开，需要单独的关系种子数据。

-- A. 人物 → 所属时代/同名非人物节点（如「新约时代」「旧约时代」「士师时代」）。
INSERT INTO biblical_graph_edges
  (source_node_id, target_node_id, relationship_type, relationship_category,
   label_zh, label_en, description, weight, confidence, is_directed, is_active, sort_order)
SELECT DISTINCT cn.id, tn.id, 'IN_ERA', 'other',
       '所属时代', 'in era', cn.name || ' 属于 ' || tn.name, 1.0, 0.80, false, true, 93000
FROM biblical_graph_nodes cn
JOIN biblical_graph_nodes tn
  ON tn.is_active = true
 AND tn.node_type <> 'character'
 AND cn.era IS NOT NULL AND cn.era <> ''
 AND tn.name = cn.era
WHERE cn.is_active = true
  AND cn.node_type = 'character'
  AND cn.id <> tn.id
  AND NOT EXISTS (
    SELECT 1 FROM biblical_graph_edges e
    WHERE e.source_node_id = cn.id AND e.target_node_id = tn.id AND e.relationship_type = 'IN_ERA'
  );

-- B. 人物 → 相关神学主题（theme 节点，按名称匹配 theological_themes 数组）。
INSERT INTO biblical_graph_edges
  (source_node_id, target_node_id, relationship_type, relationship_category,
   label_zh, label_en, description, weight, confidence, is_directed, is_active, sort_order)
SELECT DISTINCT cn.id, tn.id, 'RELATED_TO_THEME', 'spiritual',
       '相关主题', 'related theme', cn.name || ' 关联主题 ' || tn.name, 1.0, 0.70, false, true, 93100
FROM biblical_graph_nodes cn
JOIN biblical_graph_nodes tn
  ON tn.is_active = true
 AND tn.node_type = 'theme'
 AND tn.name = ANY(cn.theological_themes)
WHERE cn.is_active = true
  AND cn.node_type = 'character'
  AND cn.id <> tn.id
  AND NOT EXISTS (
    SELECT 1 FROM biblical_graph_edges e
    WHERE e.source_node_id = cn.id AND e.target_node_id = tn.id AND e.relationship_type = 'RELATED_TO_THEME'
  );

-- C. 人物 → 参与的事件（event 节点，按名称匹配 key_events 数组）。
INSERT INTO biblical_graph_edges
  (source_node_id, target_node_id, relationship_type, relationship_category,
   label_zh, label_en, description, weight, confidence, is_directed, is_active, sort_order)
SELECT DISTINCT cn.id, tn.id, 'PARTICIPATED_IN', 'event',
       '参与事件', 'participated in', cn.name || ' 参与 ' || tn.name, 1.0, 0.70, true, true, 93200
FROM biblical_graph_nodes cn
JOIN biblical_graph_nodes tn
  ON tn.is_active = true
 AND tn.node_type = 'event'
 AND tn.name = ANY(cn.key_events)
WHERE cn.is_active = true
  AND cn.node_type = 'character'
  AND cn.id <> tn.id
  AND NOT EXISTS (
    SELECT 1 FROM biblical_graph_edges e
    WHERE e.source_node_id = cn.id AND e.target_node_id = tn.id AND e.relationship_type = 'PARTICIPATED_IN'
  );
