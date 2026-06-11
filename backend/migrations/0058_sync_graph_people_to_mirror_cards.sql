-- Ensure every person node in the canonical knowledge graph has a mirror card.
-- Current seeded migrations already align graph people with biblical_characters;
-- this keeps production data safe if extra graph-only person nodes are added.

UPDATE biblical_graph_nodes n
SET character_id = c.id
FROM biblical_characters c
WHERE n.node_type = 'character'
  AND n.character_id IS NULL
  AND c.is_active = true
  AND (
      c.name = COALESCE(n.chinese_name, n.name)
      OR c.name_en = COALESCE(n.english_name, n.name_en)
      OR c.name = ANY(n.aliases)
      OR c.name_en = ANY(n.aliases)
  );

SELECT setval(
    pg_get_serial_sequence('biblical_characters', 'id'),
    GREATEST((SELECT COALESCE(MAX(id), 0) FROM biblical_characters), 1),
    true
);

WITH missing_people AS (
    SELECT
        n.id AS graph_node_id,
        COALESCE(NULLIF(n.chinese_name, ''), n.name) AS name,
        COALESCE(NULLIF(n.english_name, ''), NULLIF(n.name_en, ''), NULLIF(n.chinese_name, ''), n.name) AS name_en,
        COALESCE(NULLIF(n.era, ''), CASE WHEN n.testament = 'New Testament' THEN '新约时代' ELSE '族长时代' END) AS era,
        CASE
            WHEN array_length(n.role_labels, 1) >= 1 AND NULLIF(n.role_labels[1], '') IS NOT NULL THEN n.role_labels[1]
            WHEN n.category IN ('族长', '先知', '君王', '祭司', '使徒', '女性', '天使') THEN n.category
            WHEN n.gender = 'female' THEN '女性'
            ELSE '其他'
        END AS role,
        CASE n.moral_evaluation
            WHEN 'positive' THEN '正面'
            WHEN 'negative' THEN '警戒'
            WHEN 'mixed' THEN '混合'
            ELSE '混合'
        END AS character_type,
        LEFT(
            COALESCE(
                NULLIF(n.key_events[1], ''),
                NULLIF(n.theological_themes[1], ''),
                NULLIF(n.summary, ''),
                NULLIF(n.description, ''),
                '在圣经人物关系图谱中补足救赎历史脉络'
            ),
            200
        ) AS lesson,
        COALESCE(
            NULLIF(n.summary, ''),
            NULLIF(n.description, ''),
            COALESCE(NULLIF(n.chinese_name, ''), n.name) || '是圣经知识图谱补充人物，用于连接家族、事件、地点、职分与神学主题。'
        ) AS summary,
        COALESCE(
            NULLIF(n.description, ''),
            NULLIF(n.summary, ''),
            '此人物由知识图谱同步到镜鉴卡片，用于补全人物—家族—地点—事件—经文—主题的多层关系。'
        ) AS witness,
        COALESCE(NULLIF(n.first_appearance, ''), NULLIF(n.related_books[1], ''), '待补充经文') AS scripture_ref
    FROM biblical_graph_nodes n
    WHERE n.node_type = 'character'
      AND n.is_active = true
      AND n.character_id IS NULL
      AND NOT EXISTS (
          SELECT 1
          FROM biblical_characters c
          WHERE c.is_active = true
            AND (
                c.name = COALESCE(NULLIF(n.chinese_name, ''), n.name)
                OR c.name_en = COALESCE(NULLIF(n.english_name, ''), NULLIF(n.name_en, ''), NULLIF(n.chinese_name, ''), n.name)
                OR c.name = ANY(n.aliases)
                OR c.name_en = ANY(n.aliases)
            )
      )
), inserted AS (
    INSERT INTO biblical_characters (
        name,
        name_en,
        era,
        role,
        kingdom,
        character_type,
        lesson,
        summary,
        witness,
        scripture_ref,
        prayer,
        is_active,
        sort_order
    )
    SELECT
        name,
        name_en,
        era,
        role,
        NULL,
        character_type,
        lesson,
        summary,
        witness,
        scripture_ref,
        '主，借着' || name || '的故事帮助我看见你在历史、关系和救恩中的工作，并把这份提醒落实在今天的顺服里。阿们。',
        true,
        3000 + ROW_NUMBER() OVER (ORDER BY graph_node_id)
    FROM missing_people
    RETURNING id, name, era, role, character_type, scripture_ref
)
INSERT INTO character_tags (character_id, tag)
SELECT id, tag
FROM inserted
CROSS JOIN LATERAL (
    VALUES (era), (role), (character_type), ('知识图谱补充'), ('镜鉴补全')
) AS tags(tag)
WHERE tag IS NOT NULL AND tag <> ''
ON CONFLICT (character_id, tag) DO NOTHING;

UPDATE biblical_graph_nodes n
SET character_id = c.id
FROM biblical_characters c
WHERE n.node_type = 'character'
  AND n.character_id IS NULL
  AND c.is_active = true
  AND (
      c.name = COALESCE(n.chinese_name, n.name)
      OR c.name_en = COALESCE(n.english_name, n.name_en)
      OR c.name = ANY(n.aliases)
      OR c.name_en = ANY(n.aliases)
  );

INSERT INTO character_scriptures (character_id, reference, sort_order)
SELECT c.id, c.scripture_ref, 1
FROM biblical_characters c
JOIN biblical_graph_nodes n ON n.character_id = c.id
WHERE n.node_type = 'character'
  AND c.scripture_ref IS NOT NULL
  AND c.scripture_ref <> ''
  AND NOT EXISTS (
      SELECT 1
      FROM character_scriptures cs
      WHERE cs.character_id = c.id
        AND cs.reference = c.scripture_ref
  );
