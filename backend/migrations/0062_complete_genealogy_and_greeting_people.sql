-- Complete two high-value but previously broken networks in the knowledge graph:
--   1. The Adam -> Noah -> Abraham genealogy chain (intermediate patriarchs were referenced
--      in 0060 edges but did not exist in biblical_characters, so those FATHER_OF edges were skipped).
--   2. Romans 16 / epistle greeting people and Paul's named coworkers, so the
--      event-paul-greetings container and the Paul mission subgraph are actually populated.
--
-- Strategy:
--   A. Insert the missing biblical people into biblical_characters (guarded by NOT EXISTS on name).
--   B. Create graph nodes for every active non-教会时代 character that still lacks one (0059-style, generic).
--   C. Insert family + membership edges via the name-resolution pattern; unmatched rows are skipped.
-- The migration is idempotent: NOT EXISTS guards, ON CONFLICT DO NOTHING.

-- Reset the primary key sequence so that auto-generated character IDs start after the current max ID
SELECT setval(
    pg_get_serial_sequence('biblical_characters', 'id'),
    COALESCE((SELECT MAX(id) FROM biblical_characters), 0)
);

-- ============================================================
-- PART A. Missing biblical people (graph-relevant minor figures)
-- name|name_en|era|role|type|scripture_ref|summary
-- ============================================================
WITH raw(line) AS (
    SELECT * FROM regexp_split_to_table($people$
以挪士|Enosh|族长时代|其他|混合|创5:6-11|塞特之子，那时候人开始求告耶和华的名。
该南|Kenan|族长时代|其他|混合|创5:9-14|以挪士之子，亚当敬虔家谱第四代。
玛勒列|Mahalalel|族长时代|其他|混合|创5:12-17|该南之子，亚当家谱一代。
雅列|Jared|族长时代|其他|混合|创5:15-20|玛勒列之子，以诺之父。
以诺|Enoch|族长时代|其他|正面|创5:21-24|与神同行三百年，神将他取去，他就不在世了。
拉麦|Lamech|族长时代|其他|混合|创5:25-31|玛土撒拉之子，挪亚之父。
闪|Shem|族长时代|其他|正面|创9:26,11:10|挪亚之子，闪族与亚伯拉罕谱系之源。
含|Ham|族长时代|其他|混合|创9:18-25|挪亚之子，迦南之父。
雅弗|Japheth|族长时代|其他|混合|创9:27,10:2|挪亚之子，列邦分布之祖之一。
迦南（含之子）|Canaan|族长时代|其他|警戒|创9:25,10:6|含之子，受咒诅，迦南诸族之祖。
他拉|Terah|族长时代|其他|混合|创11:24-32|亚伯拉罕之父，从吾珥迁往哈兰。
拿鹤|Nahor|族长时代|其他|混合|创11:26-29|亚伯拉罕兄弟，利百加家族之祖。
哈兰|Haran|族长时代|其他|混合|创11:27-28|亚伯拉罕兄弟，罗得之父，死于吾珥。
以拜尼土|Epaenetus|新约时代|其他|正面|罗16:5|亚西亚初结果子归基督的人，保罗所亲爱的。
安多尼古|Andronicus|新约时代|其他|正面|罗16:7|与保罗一同坐监的亲属，在使徒中有名望。
犹尼亚|Junia|新约时代|女性|正面|罗16:7|与安多尼古一同被保罗称许的信徒。
暗伯利|Ampliatus|新约时代|其他|正面|罗16:8|保罗在主里所亲爱的。
耳巴奴|Urbanus|新约时代|其他|正面|罗16:9|在基督里与保罗同工的。
士大古|Stachys|新约时代|其他|正面|罗16:9|保罗所亲爱的同伴。
亚比利|Apelles|新约时代|其他|正面|罗16:10|在基督里经过试验、蒙称许的。
希罗天|Herodion|新约时代|其他|正面|罗16:11|保罗的亲属。
土非拿|Tryphena|新约时代|女性|正面|罗16:12|为主劳苦的姊妹。
土富撒|Tryphosa|新约时代|女性|正面|罗16:12|与土非拿一同为主劳苦的姊妹。
彼息|Persis|新约时代|女性|正面|罗16:12|所亲爱、为主多多劳苦的姊妹。
鲁孚|Rufus|新约时代|其他|正面|罗16:13|在主蒙拣选的，其母亲待保罗如同母亲。
亚逊其土|Asyncritus|新约时代|其他|混合|罗16:14|保罗在罗马书所问安的弟兄之一。
弗勒干|Phlegon|新约时代|其他|混合|罗16:14|保罗在罗马书所问安的弟兄之一。
黑米|Hermes|新约时代|其他|混合|罗16:14|保罗在罗马书所问安的弟兄之一。
八罗巴|Patrobas|新约时代|其他|混合|罗16:14|保罗在罗马书所问安的弟兄之一。
黑马|Hermas|新约时代|其他|混合|罗16:14|保罗在罗马书所问安的弟兄之一。
非罗罗古|Philologus|新约时代|其他|混合|罗16:15|保罗在罗马书所问安的圣徒之一。
犹利亚|Julia|新约时代|女性|混合|罗16:15|保罗在罗马书所问安的姊妹。
尼利亚|Nereus|新约时代|其他|混合|罗16:15|保罗在罗马书所问安的圣徒之一。
阿林巴|Olympas|新约时代|其他|混合|罗16:15|保罗在罗马书所问安的圣徒之一。
该犹|Gaius|新约时代|其他|正面|罗16:23|接待保罗与全教会的人。
以拉都|Erastus|新约时代|其他|正面|罗16:23|哥林多城管银库的信徒。
所西巴德|Sosipater|新约时代|其他|正面|罗16:21|保罗的亲属与同工。
耶孙|Jason|新约时代|其他|正面|罗16:21,徒17:5-9|接待保罗、在帖撒罗尼迦受牵连的信徒。
路求|Lucius|新约时代|其他|正面|罗16:21|保罗的亲属与同工。
推基古|Tychicus|新约时代|其他|正面|弗6:21,西4:7|保罗所差派传递书信的亲爱弟兄。
阿尼色弗|Onesiphorus|新约时代|其他|正面|提后1:16|多次使保罗畅快、不以锁链为耻的人。
以巴弗|Epaphras|新约时代|其他|正面|西1:7,4:12|歌罗西教会忠心的执事，常为信徒竭力祷告。
以巴弗提|Epaphroditus|新约时代|其他|正面|腓2:25|腓立比教会差遣供应保罗、几乎至死的同工。
亚基布|Archippus|新约时代|其他|正面|西4:17,门2|被嘱咐要谨慎尽职的同工。
$people$, E'\n')
), parsed AS (
    SELECT string_to_array(line, '|') AS parts
    FROM raw
    WHERE line <> ''
), person AS (
    SELECT
        parts[1] AS name,
        parts[2] AS name_en,
        parts[3] AS era,
        parts[4] AS role,
        parts[5] AS character_type,
        parts[6] AS scripture_ref,
        parts[7] AS summary
    FROM parsed
)
INSERT INTO biblical_characters (
    name, name_en, era, role, character_type, lesson, summary, witness, scripture_ref, prayer, is_active, sort_order
)
SELECT
    p.name,
    p.name_en,
    p.era,
    p.role,
    p.character_type,
    p.name || '在圣经救赎历史中的位置与见证。',
    p.summary,
    p.summary,
    p.scripture_ref,
    '愿我从' || p.name || '的记载中认识神在历史与群体中的作为。',
    true,
    6000
FROM person p
WHERE NOT EXISTS (
    SELECT 1 FROM biblical_characters c WHERE c.name = p.name
);

-- ============================================================
-- PART B. Create graph nodes for any active non-教会时代 character that lacks one
-- ============================================================
INSERT INTO biblical_graph_nodes (
    id, node_type, name, name_en, category, description, character_id,
    chinese_name, english_name, aliases, testament, era, role_labels,
    importance_level, first_appearance, related_books, key_events,
    theological_themes, moral_evaluation, summary
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
    'C',
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
  AND NOT EXISTS (
      SELECT 1 FROM biblical_graph_nodes n WHERE n.character_id = c.id
  )
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- PART C. Family chain + membership edges
-- Format: source_kind|source_ref|target_kind|target_ref|rel|cat|label|scripture|desc|weight
-- ============================================================
WITH raw(line) AS (
    SELECT * FROM regexp_split_to_table($edges$
-- ---- Genesis genealogy chain (Adam -> Noah -> Abraham) ----
character|塞特|character|以挪士|FATHER_OF|family|父亲|创5:6|塞特生以挪士。|2.4
character|以挪士|character|该南|FATHER_OF|family|父亲|创5:9|以挪士生该南。|2.2
character|该南|character|玛勒列|FATHER_OF|family|父亲|创5:12|该南生玛勒列。|2.2
character|玛勒列|character|雅列|FATHER_OF|family|父亲|创5:15|玛勒列生雅列。|2.2
character|雅列|character|以诺|FATHER_OF|family|父亲|创5:18|雅列生以诺。|2.4
character|以诺|character|玛土撒拉|FATHER_OF|family|父亲|创5:21|以诺生玛土撒拉。|2.4
character|玛土撒拉|character|拉麦|FATHER_OF|family|父亲|创5:25|玛土撒拉生拉麦。|2.2
character|拉麦|character|挪亚|FATHER_OF|family|父亲|创5:28-29|拉麦生挪亚。|2.6
character|挪亚|character|闪|FATHER_OF|family|父亲|创5:32|闪是挪亚之子。|2.6
character|挪亚|character|含|FATHER_OF|family|父亲|创5:32|含是挪亚之子。|2.4
character|挪亚|character|雅弗|FATHER_OF|family|父亲|创5:32|雅弗是挪亚之子。|2.4
character|含|character|迦南（含之子）|FATHER_OF|family|父亲|创10:6|迦南是含之子。|2.2
character|闪|character|亚伯拉罕|ANCESTOR_OF|family|祖先|创11:10-26|亚伯拉罕是闪的后裔。|2.6
character|他拉|character|亚伯拉罕|FATHER_OF|family|父亲|创11:27|他拉生亚伯兰。|2.8
character|他拉|character|拿鹤|FATHER_OF|family|父亲|创11:26|拿鹤是他拉之子。|2.0
character|他拉|character|哈兰|FATHER_OF|family|父亲|创11:26|哈兰是他拉之子。|2.0
character|哈兰|character|罗得|FATHER_OF|family|父亲|创11:27|哈兰生罗得。|2.2
-- ---- Genesis genealogy membership ----
character|以挪士|event|genesis-genealogies|MEMBER_OF|other|创世记族谱|创5|以挪士属亚当至挪亚的家谱。|1.8
character|该南|event|genesis-genealogies|MEMBER_OF|other|创世记族谱|创5|该南属亚当至挪亚的家谱。|1.8
character|玛勒列|event|genesis-genealogies|MEMBER_OF|other|创世记族谱|创5|玛勒列属亚当至挪亚的家谱。|1.8
character|雅列|event|genesis-genealogies|MEMBER_OF|other|创世记族谱|创5|雅列属亚当至挪亚的家谱。|1.8
character|以诺|event|genesis-genealogies|MEMBER_OF|other|创世记族谱|创5|以诺属亚当至挪亚的家谱。|2.0
character|拉麦|event|genesis-genealogies|MEMBER_OF|other|创世记族谱|创5|拉麦属亚当至挪亚的家谱。|1.8
character|闪|event|genesis-genealogies|MEMBER_OF|other|创世记族谱|创10-11|闪属挪亚至亚伯拉罕的家谱。|2.0
character|含|event|genesis-genealogies|MEMBER_OF|other|创世记族谱|创10|含属挪亚后裔列邦家谱。|1.8
character|雅弗|event|genesis-genealogies|MEMBER_OF|other|创世记族谱|创10|雅弗属挪亚后裔列邦家谱。|1.8
character|他拉|event|genesis-genealogies|MEMBER_OF|other|创世记族谱|创11|他拉属挪亚至亚伯拉罕的家谱。|2.0
-- ---- Romans 16 / epistle greeting people (event-paul-greetings) ----
character|以拜尼土|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:5|亚西亚初结果子归基督的人。|1.8
character|安多尼古|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:7|与保罗同坐监的亲属，在使徒中有名望。|2.0
character|犹尼亚|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:7|与安多尼古一同被保罗称许。|2.0
character|暗伯利|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:8|保罗在主里所亲爱的。|1.8
character|耳巴奴|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:9|在基督里与保罗同工的。|1.8
character|士大古|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:9|保罗所亲爱的同伴。|1.8
character|亚比利|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:10|经试验蒙称许的信徒。|1.8
character|希罗天|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:11|保罗的亲属。|1.8
character|土非拿|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:12|为主劳苦的姊妹。|1.8
character|土富撒|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:12|为主劳苦的姊妹。|1.8
character|彼息|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:12|为主多多劳苦的姊妹。|1.8
character|鲁孚|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:13|在主蒙拣选的信徒。|2.0
character|亚逊其土|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:14|保罗问安的弟兄之一。|1.6
character|弗勒干|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:14|保罗问安的弟兄之一。|1.6
character|黑米|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:14|保罗问安的弟兄之一。|1.6
character|八罗巴|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:14|保罗问安的弟兄之一。|1.6
character|黑马|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:14|保罗问安的弟兄之一。|1.6
character|非罗罗古|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:15|保罗问安的圣徒之一。|1.6
character|犹利亚|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:15|保罗问安的姊妹。|1.6
character|尼利亚|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:15|保罗问安的圣徒之一。|1.6
character|阿林巴|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:15|保罗问安的圣徒之一。|1.6
character|该犹|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:23|接待保罗与全教会的人。|2.0
character|以拉都|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:23|哥林多城管银库的信徒。|1.8
character|所西巴德|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:21|保罗的亲属与同工。|1.8
character|耶孙|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:21|接待保罗的信徒。|1.8
character|路求|event|paul-greetings|MEMBER_OF|other|问安人物|罗16:21|保罗的亲属与同工。|1.8
character|推基古|event|paul-greetings|MEMBER_OF|other|问安人物|弗6:21|保罗差派传书信的亲爱弟兄。|2.0
character|阿尼色弗|event|paul-greetings|MEMBER_OF|other|问安人物|提后1:16|多次使保罗畅快的人。|2.0
character|以巴弗|event|paul-greetings|MEMBER_OF|other|问安人物|西4:12|歌罗西教会忠心的执事。|2.0
character|以巴弗提|event|paul-greetings|MEMBER_OF|other|问安人物|腓2:25|腓立比教会差遣供应保罗的同工。|2.0
character|亚基布|event|paul-greetings|MEMBER_OF|other|问安人物|西4:17|被嘱咐谨慎尽职的同工。|1.8
-- ---- A few epistle coworkers tied to their ministry place ----
character|以巴弗|place|colossae|MINISTERED_IN|location|服事于|西1:7|以巴弗在歌罗西忠心服事。|2.0
character|以巴弗提|place|philippi|MINISTERED_IN|location|服事于|腓2:25|以巴弗提出自腓立比教会。|1.8
character|以拉都|place|corinth|LIVED_IN|location|居住/任职于|罗16:23|以拉都是哥林多城管银库者。|1.8
$edges$, E'\n')
), edge_seed AS (
    SELECT
        row_number() OVER () AS ord,
        parts[1] AS source_kind,
        parts[2] AS source_ref,
        parts[3] AS target_kind,
        parts[4] AS target_ref,
        parts[5] AS relationship_type,
        parts[6] AS relationship_category,
        parts[7] AS label_zh,
        parts[8] AS scripture_ref,
        parts[9] AS description,
        parts[10]::numeric AS weight
    FROM raw
    CROSS JOIN LATERAL (SELECT string_to_array(line, '|') AS parts) parsed
    WHERE line <> '' AND line NOT LIKE '--%'
), resolved AS (
    SELECT
        edge_seed.*,
        CASE
            WHEN source_kind = 'character' THEN source_char_node.id
            ELSE source_kind || '-' || source_ref
        END AS source_node_id,
        CASE
            WHEN target_kind = 'character' THEN target_char_node.id
            ELSE target_kind || '-' || target_ref
        END AS target_node_id
    FROM edge_seed
    LEFT JOIN biblical_characters source_char
        ON source_kind = 'character' AND source_char.name = source_ref AND source_char.is_active = true
    LEFT JOIN biblical_graph_nodes source_char_node
        ON source_char_node.character_id = source_char.id AND source_char_node.is_active = true
    LEFT JOIN biblical_characters target_char
        ON target_kind = 'character' AND target_char.name = target_ref AND target_char.is_active = true
    LEFT JOIN biblical_graph_nodes target_char_node
        ON target_char_node.character_id = target_char.id AND target_char_node.is_active = true
)
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
    source_node_id,
    target_node_id,
    relationship_type,
    relationship_category,
    label_zh,
    relationship_type,
    scripture_ref,
    description,
    weight,
    0.9,
    relationship_type NOT IN ('SPOUSE_OF', 'SIBLING_OF', 'ALLIED_WITH'),
    50000 + ord,
    ARRAY_REMOVE(ARRAY[scripture_ref], NULL),
    'high'
FROM resolved
WHERE source_node_id IS NOT NULL
  AND target_node_id IS NOT NULL
  AND source_node_id <> target_node_id
  AND EXISTS (SELECT 1 FROM biblical_graph_nodes n WHERE n.id = source_node_id)
  AND EXISTS (SELECT 1 FROM biblical_graph_nodes n WHERE n.id = target_node_id)
ON CONFLICT DO NOTHING;

-- Inverse edges for the newly added family + membership relationships (sort_order 50000-59999).
WITH new_edges AS (
    SELECT *
    FROM biblical_graph_edges
    WHERE is_active = true
      AND sort_order BETWEEN 50000 AND 59999
), inverse_rows AS (
    SELECT
        target_node_id AS source_node_id,
        source_node_id AS target_node_id,
        CASE relationship_type
            WHEN 'FATHER_OF' THEN 'CHILD_OF'
            WHEN 'ANCESTOR_OF' THEN 'DESCENDANT_OF'
            WHEN 'MEMBER_OF' THEN 'CONTAINS_MEMBER'
        END AS relationship_type,
        relationship_category,
        CASE relationship_type
            WHEN 'FATHER_OF' THEN '儿子/女儿'
            WHEN 'ANCESTOR_OF' THEN '后裔'
            WHEN 'MEMBER_OF' THEN '包含成员'
        END AS label_zh,
        CASE relationship_type
            WHEN 'FATHER_OF' THEN 'child of'
            WHEN 'ANCESTOR_OF' THEN 'descendant of'
            WHEN 'MEMBER_OF' THEN 'contains member'
        END AS label_en,
        scripture_ref,
        '由 0062 关系自动生成的反向关系：' || description AS description,
        GREATEST(weight - 0.2, 0.1) AS weight,
        confidence,
        true AS is_directed,
        sort_order + 5000 AS sort_order,
        scripture_refs,
        confidence_level
    FROM new_edges
    WHERE relationship_type IN ('FATHER_OF', 'ANCESTOR_OF', 'MEMBER_OF')
)
INSERT INTO biblical_graph_edges (
    source_node_id, target_node_id, relationship_type, relationship_category,
    label_zh, label_en, scripture_ref, description, weight, confidence,
    is_directed, sort_order, scripture_refs, confidence_level
)
SELECT
    source_node_id, target_node_id, relationship_type, relationship_category,
    label_zh, label_en, scripture_ref, description, weight, confidence,
    is_directed, sort_order, scripture_refs, confidence_level
FROM inverse_rows
WHERE source_node_id <> target_node_id
ON CONFLICT DO NOTHING;
