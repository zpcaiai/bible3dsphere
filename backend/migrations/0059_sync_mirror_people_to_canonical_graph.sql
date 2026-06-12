-- Sync mirror character cards into the canonical multi-entity knowledge graph.
-- This keeps the 0055 supplemental people visible in both the mirror and graph APIs.

INSERT INTO biblical_graph_nodes (
    id,
    node_type,
    name,
    name_en,
    category,
    description,
    character_id,
    chinese_name,
    english_name,
    aliases,
    testament,
    era,
    role_labels,
    importance_level,
    first_appearance,
    related_books,
    key_events,
    theological_themes,
    moral_evaluation,
    summary
)
SELECT
    'char-' || c.id,
    'character',
    c.name,
    c.name_en,
    c.role,
    c.summary,
    c.id,
    c.name,
    c.name_en,
    ARRAY_REMOVE(ARRAY[c.name, c.name_en], NULL),
    CASE
        WHEN c.era ILIKE '%新约%' THEN 'New Testament'
        WHEN c.era ILIKE '%两约%' THEN 'Intertestamental'
        ELSE 'Old Testament'
    END,
    c.era,
    ARRAY_REMOVE(ARRAY[c.role], NULL),
    CASE
        WHEN c.character_type = '正面' AND c.role IN ('君王', '先知', '祭司', '使徒', '族长') THEN 'B'
        ELSE 'C'
    END,
    c.scripture_ref,
    ARRAY_REMOVE(ARRAY[c.scripture_ref], NULL),
    ARRAY_REMOVE(ARRAY[c.lesson], NULL),
    ARRAY_REMOVE(ARRAY[c.role, c.character_type], NULL),
    CASE c.character_type
        WHEN '正面' THEN 'positive'
        WHEN '警戒' THEN 'negative'
        ELSE 'mixed'
    END,
    c.summary
FROM biblical_characters c
WHERE c.is_active = true
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    name_en = EXCLUDED.name_en,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    character_id = EXCLUDED.character_id,
    chinese_name = EXCLUDED.chinese_name,
    english_name = EXCLUDED.english_name,
    aliases = EXCLUDED.aliases,
    testament = EXCLUDED.testament,
    era = EXCLUDED.era,
    role_labels = EXCLUDED.role_labels,
    first_appearance = EXCLUDED.first_appearance,
    related_books = EXCLUDED.related_books,
    key_events = EXCLUDED.key_events,
    theological_themes = EXCLUDED.theological_themes,
    moral_evaluation = EXCLUDED.moral_evaluation,
    summary = EXCLUDED.summary,
    is_active = true;

INSERT INTO biblical_graph_nodes (
    id,
    node_type,
    name,
    name_en,
    category,
    description,
    testament,
    era,
    importance_level,
    summary
)
SELECT DISTINCT
    'theme-era-' || SUBSTRING(md5(c.era), 1, 12),
    'theme',
    c.era,
    c.era,
    'era',
    c.era || '是圣经人物镜鉴与知识图谱的时代脉络节点。',
    CASE
        WHEN c.era ILIKE '%新约%' THEN 'New Testament'
        WHEN c.era ILIKE '%两约%' THEN 'Intertestamental'
        ELSE 'Old Testament'
    END,
    c.era,
    'C',
    c.era || '汇聚相关人物、事件和属灵主题。'
FROM biblical_characters c
WHERE c.is_active = true
  AND c.era IS NOT NULL
  AND c.era <> ''
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    name_en = EXCLUDED.name_en,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    testament = EXCLUDED.testament,
    era = EXCLUDED.era,
    summary = EXCLUDED.summary,
    is_active = true;

INSERT INTO biblical_graph_edges (
    source_node_id,
    target_node_id,
    relationship_type,
    relationship_category,
    label_zh,
    label_en,
    scripture_ref,
    description,
    weight,
    confidence,
    is_directed,
    sort_order,
    scripture_refs,
    confidence_level
)
SELECT
    'char-' || c.id,
    'theme-era-' || SUBSTRING(md5(c.era), 1, 12),
    'BELONGS_TO_ERA',
    'other',
    '所属时代',
    'belongs to era',
    c.scripture_ref,
    c.name || '属于' || c.era || '脉络，可由此进入同一时代的人物网络。',
    0.8,
    0.95,
    true,
    9000 + COALESCE(c.sort_order, c.id),
    ARRAY_REMOVE(ARRAY[c.scripture_ref], NULL),
    'high'
FROM biblical_characters c
WHERE c.is_active = true
  AND c.era IS NOT NULL
  AND c.era <> ''
ON CONFLICT DO NOTHING;

INSERT INTO biblical_graph_edges (
    source_node_id,
    target_node_id,
    relationship_type,
    relationship_category,
    label_zh,
    label_en,
    scripture_ref,
    description,
    weight,
    confidence,
    is_directed,
    sort_order,
    scripture_refs,
    confidence_level
)
SELECT
    'char-' || r.source_character_id,
    'char-' || r.target_character_id,
    UPPER(REGEXP_REPLACE(r.relationship_type, '[^[:alnum:]]+', '_', 'g')),
    CASE
        WHEN r.relationship_category IN ('family', 'marriage', 'lineage') THEN 'family'
        WHEN r.relationship_category IN ('ministry', 'spiritual') THEN 'spiritual'
        WHEN r.relationship_category IN ('political', 'conflict') THEN 'political'
        ELSE 'other'
    END,
    r.label_zh,
    COALESCE(r.label_en, r.relationship_type),
    r.scripture_ref,
    r.description,
    GREATEST(0.1, LEAST(COALESCE(r.weight, 1.0), 10.0)),
    GREATEST(0.1, LEAST(COALESCE(r.confidence, 0.75), 1.0)),
    r.is_directed,
    10000 + COALESCE(r.sort_order, r.id),
    ARRAY_REMOVE(ARRAY[r.scripture_ref], NULL),
    CASE
        WHEN COALESCE(r.confidence, 0.75) >= 0.85 THEN 'high'
        WHEN COALESCE(r.confidence, 0.75) >= 0.6 THEN 'medium'
        ELSE 'low'
    END
FROM biblical_character_relationships r
JOIN biblical_graph_nodes source_node ON source_node.id = 'char-' || r.source_character_id
JOIN biblical_graph_nodes target_node ON target_node.id = 'char-' || r.target_character_id
WHERE r.is_active = true
  AND r.source_character_id <> r.target_character_id
  AND source_node.node_type = 'character'
  AND target_node.node_type = 'character'
ON CONFLICT DO NOTHING;

-- Handle composite/split characters: create group nodes for combined names
-- that were split into individual characters in 0055
INSERT INTO biblical_graph_nodes (
    id,
    node_type,
    name,
    name_en,
    category,
    description,
    testament,
    era,
    importance_level,
    summary,
    is_active
)
SELECT DISTINCT
    'group-' || SUBSTRING(md5(r.target_name), 1, 12),
    'group',
    r.target_name,
    r.target_name,
    'composite',
    r.target_name || '是复合人物节点，包含多个相关人物，用于承接与原组合人物的关系连接。',
    'Old Testament',
    '复合人物',
    'C',
    r.target_name || '作为群组节点，连接其包含的独立人物成员。',
    true
FROM biblical_character_relationships r
WHERE r.target_name LIKE '%与%' 
   OR r.target_name LIKE '%和%'
   OR r.target_name LIKE '%、%'
   OR r.target_name LIKE '%们%'
   OR r.target_name LIKE '%群体%'
   OR r.target_name LIKE '%家里%'
   OR r.target_name LIKE '%家%'
   OR r.target_name LIKE '%三百人%'
   OR r.target_name LIKE '%儿子%'
   OR r.target_name LIKE '%女儿%'
   OR r.target_name SIMILAR TO '%(士师记|列王纪|创世记|出埃及记)%'
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    is_active = true;

-- Create edges from individual characters to their composite group node
-- This preserves the relationship structure when composite characters were split
INSERT INTO biblical_graph_edges (
    source_node_id,
    target_node_id,
    relationship_type,
    relationship_category,
    label_zh,
    label_en,
    scripture_ref,
    description,
    weight,
    confidence,
    is_directed,
    sort_order,
    scripture_refs,
    confidence_level
)
SELECT
    'char-' || c.id,
    'group-' || SUBSTRING(md5(rel.target_name), 1, 12),
    'BELONGS_TO_GROUP',
    'other',
    '属于群组',
    'belongs to group',
    c.scripture_ref,
    c.name || '属于' || rel.target_name || '群组。',
    0.7,
    0.8,
    true,
    12000 + c.id,
    ARRAY_REMOVE(ARRAY[c.scripture_ref], NULL),
    'medium'
FROM biblical_characters c
JOIN biblical_character_relationships rel ON (
    -- Match characters that reference composite names in their description or relationships
    (rel.target_name LIKE '%' || c.name || '%' AND rel.target_name LIKE '%与%')
    OR c.summary LIKE '%' || rel.target_name || '%'
)
WHERE c.is_active = true
  AND rel.target_name IS NOT NULL
  AND EXISTS (
      SELECT 1 FROM biblical_graph_nodes g 
      WHERE g.id = 'group-' || SUBSTRING(md5(rel.target_name), 1, 12)
  )
ON CONFLICT DO NOTHING;

-- Also create edges where composite group is the source
INSERT INTO biblical_graph_edges (
    source_node_id,
    target_node_id,
    relationship_type,
    relationship_category,
    label_zh,
    label_en,
    scripture_ref,
    description,
    weight,
    confidence,
    is_directed,
    sort_order,
    scripture_refs,
    confidence_level
)
SELECT
    'group-' || SUBSTRING(md5(r.source_name), 1, 12),
    'char-' || c.id,
    'CONTAINS_MEMBER',
    'other',
    '包含成员',
    'contains member',
    c.scripture_ref,
    r.source_name || '群组包含' || c.name || '。',
    0.7,
    0.8,
    true,
    12500 + c.id,
    ARRAY_REMOVE(ARRAY[c.scripture_ref], NULL),
    'medium'
FROM biblical_character_relationships r
JOIN biblical_characters c ON c.name = r.target_name
WHERE r.is_active = true
  AND (r.source_name LIKE '%与%' 
       OR r.source_name LIKE '%和%'
       OR r.source_name LIKE '%们%'
       OR r.source_name LIKE '%群体%')
  AND EXISTS (
      SELECT 1 FROM biblical_graph_nodes g 
      WHERE g.id = 'group-' || SUBSTRING(md5(r.source_name), 1, 12)
  )
ON CONFLICT DO NOTHING;

INSERT INTO character_scriptures (character_id, reference, sort_order)
SELECT c.id, c.scripture_ref, 1
FROM biblical_characters c
WHERE c.is_active = true
  AND c.scripture_ref IS NOT NULL
  AND c.scripture_ref <> ''
  AND NOT EXISTS (
      SELECT 1
      FROM character_scriptures cs
      WHERE cs.character_id = c.id
        AND cs.reference = c.scripture_ref
  );
