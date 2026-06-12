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
  AND c.era <> '教会时代'
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
  AND c.era <> '教会时代'
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
  AND c.era <> '教会时代'
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
JOIN biblical_characters source_char ON source_char.id = r.source_character_id
JOIN biblical_characters target_char ON target_char.id = r.target_character_id
WHERE r.is_active = true
  AND r.source_character_id <> r.target_character_id
  AND source_node.node_type = 'character'
  AND target_node.node_type = 'character'
  AND source_char.era <> '教会时代'
  AND target_char.era <> '教会时代'
ON CONFLICT DO NOTHING;

-- Note: Composite/split character group nodes are intentionally not created here
-- because biblical_character_relationships stores IDs not names.
-- The main sync (character nodes + edges + era themes) handles the core functionality.

INSERT INTO character_scriptures (character_id, reference, sort_order)
SELECT c.id, c.scripture_ref, 1
FROM biblical_characters c
WHERE c.is_active = true
  AND c.era <> '教会时代'
  AND c.scripture_ref IS NOT NULL
  AND c.scripture_ref <> ''
  AND NOT EXISTS (
      SELECT 1
      FROM character_scriptures cs
      WHERE cs.character_id = c.id
        AND cs.reference = c.scripture_ref
  );
