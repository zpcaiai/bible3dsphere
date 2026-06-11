-- Product-facing graph metadata and curated subgraph definitions.

ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS chinese_name VARCHAR(120);
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS english_name VARCHAR(120);
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS hebrew_name VARCHAR(120);
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS greek_name VARCHAR(120);
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS aliases TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS gender VARCHAR(20)
    CHECK (gender IS NULL OR gender IN ('male', 'female', 'unknown'));
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS testament VARCHAR(30)
    CHECK (testament IS NULL OR testament IN ('Old Testament', 'New Testament', 'Intertestamental'));
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS era VARCHAR(80);
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS tribe VARCHAR(80);
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS nation VARCHAR(80);
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS role_labels TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS family_line VARCHAR(120);
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS importance_level VARCHAR(1) NOT NULL DEFAULT 'C'
    CHECK (importance_level IN ('S', 'A', 'B', 'C'));
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS first_appearance VARCHAR(120);
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS last_appearance VARCHAR(120);
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS related_books TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS key_events TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS theological_themes TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS christ_typology TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS moral_evaluation VARCHAR(20)
    CHECK (moral_evaluation IS NULL OR moral_evaluation IN ('positive', 'negative', 'mixed', 'neutral'));
ALTER TABLE biblical_graph_nodes ADD COLUMN IF NOT EXISTS summary TEXT;

ALTER TABLE biblical_graph_edges ADD COLUMN IF NOT EXISTS scripture_refs TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE biblical_graph_edges ADD COLUMN IF NOT EXISTS confidence_level VARCHAR(10) NOT NULL DEFAULT 'high'
    CHECK (confidence_level IN ('high', 'medium', 'low'));

UPDATE biblical_graph_nodes n
SET
    chinese_name = COALESCE(n.chinese_name, c.name, n.name),
    english_name = COALESCE(n.english_name, c.name_en, n.name_en),
    aliases = CASE
        WHEN n.aliases = '{}' THEN ARRAY_REMOVE(ARRAY[c.name, c.name_en], NULL)
        ELSE n.aliases
    END,
    gender = COALESCE(
        n.gender,
        CASE
            WHEN c.role = '女性' OR c.name LIKE '%妻%' OR c.name LIKE '%女儿%' OR c.name LIKE '%妇人%' THEN 'female'
            WHEN c.role IS NULL THEN 'unknown'
            ELSE 'male'
        END
    ),
    testament = COALESCE(
        n.testament,
        CASE WHEN c.era = '新约时代' THEN 'New Testament' ELSE 'Old Testament' END
    ),
    era = COALESCE(n.era, c.era),
    role_labels = CASE WHEN n.role_labels = '{}' THEN ARRAY[c.role] ELSE n.role_labels END,
    family_line = COALESCE(
        n.family_line,
        CASE
            WHEN c.name IN ('亚当', '塞特', '挪亚', '闪', '亚伯拉罕', '以撒', '雅各', '犹大（雅各之子）', '大卫', '耶稣基督')
                THEN '弥赛亚家谱'
            WHEN c.name LIKE '%雅各之子%' OR c.name IN ('流便（雅各长子）', '利亚', '拉结')
                THEN '雅各家族/十二支派'
            WHEN c.kingdom IS NOT NULL THEN c.kingdom
            ELSE NULL
        END
    ),
    importance_level = CASE
        WHEN c.name = '耶稣基督' THEN 'S'
        WHEN c.name IN ('亚当', '挪亚', '亚伯拉罕', '以撒', '雅各', '约瑟', '摩西', '亚伦', '约书亚', '撒母耳', '大卫', '所罗门', '以利亚', '以利沙', '以赛亚', '耶利米', '但以理', '马利亚', '彼得', '约翰', '保罗')
            THEN 'A'
        WHEN c.role IN ('族长', '先知', '君王', '祭司', '使徒') OR c.character_type = '正面'
            THEN 'B'
        ELSE COALESCE(n.importance_level, 'C')
    END,
    first_appearance = COALESCE(n.first_appearance, c.scripture_ref),
    related_books = CASE
        WHEN n.related_books = '{}' THEN ARRAY[c.scripture_ref]
        ELSE n.related_books
    END,
    key_events = CASE
        WHEN n.key_events = '{}' THEN ARRAY_REMOVE(ARRAY[c.lesson], NULL)
        ELSE n.key_events
    END,
    theological_themes = CASE
        WHEN n.theological_themes = '{}' THEN ARRAY_REMOVE(ARRAY[c.lesson, c.character_type], NULL)
        ELSE n.theological_themes
    END,
    christ_typology = CASE
        WHEN n.christ_typology = '{}' AND c.name IN ('亚当', '亚伯拉罕', '以撒', '约瑟', '摩西', '大卫', '约拿（先知）', '麦基洗德')
            THEN ARRAY['基督预表/弥赛亚线索']
        ELSE n.christ_typology
    END,
    moral_evaluation = COALESCE(
        n.moral_evaluation,
        CASE c.character_type
            WHEN '正面' THEN 'positive'
            WHEN '警戒' THEN 'negative'
            WHEN '混合' THEN 'mixed'
            ELSE 'neutral'
        END
    ),
    summary = COALESCE(n.summary, c.summary, n.description)
FROM biblical_characters c
WHERE n.character_id = c.id;

UPDATE biblical_graph_nodes
SET
    chinese_name = COALESCE(chinese_name, name),
    english_name = COALESCE(english_name, name_en),
    testament = COALESCE(testament, 'Old Testament'),
    gender = COALESCE(gender, 'unknown'),
    moral_evaluation = COALESCE(moral_evaluation, 'neutral'),
    summary = COALESCE(summary, description)
WHERE node_type <> 'character';

UPDATE biblical_graph_edges
SET
    scripture_refs = CASE
        WHEN scripture_refs = '{}' AND scripture_ref IS NOT NULL AND scripture_ref <> '' THEN ARRAY[scripture_ref]
        ELSE scripture_refs
    END,
    confidence_level = CASE
        WHEN confidence >= 0.9 THEN 'high'
        WHEN confidence >= 0.7 THEN 'medium'
        ELSE 'low'
    END;

CREATE TABLE IF NOT EXISTS biblical_graph_subgraphs (
    slug VARCHAR(80) PRIMARY KEY,
    title VARCHAR(120) NOT NULL,
    title_en VARCHAR(160),
    description TEXT,
    focus_nodes TEXT[] NOT NULL DEFAULT '{}',
    node_types TEXT[] NOT NULL DEFAULT '{}',
    relationship_categories TEXT[] NOT NULL DEFAULT '{}',
    relationship_types TEXT[] NOT NULL DEFAULT '{}',
    depth INTEGER NOT NULL DEFAULT 2 CHECK (depth BETWEEN 1 AND 4),
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

DROP TRIGGER IF EXISTS update_biblical_graph_subgraphs_updated_at ON biblical_graph_subgraphs;
CREATE TRIGGER update_biblical_graph_subgraphs_updated_at
    BEFORE UPDATE ON biblical_graph_subgraphs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

INSERT INTO biblical_graph_subgraphs (
    slug, title, title_en, description, focus_nodes, node_types,
    relationship_categories, relationship_types, depth, sort_order
) VALUES
    (
        'adam-to-jesus-genealogy',
        '从亚当到耶稣的家谱图',
        'Adam to Jesus Genealogy',
        '弥赛亚家谱主线：亚当、塞特、挪亚、亚伯拉罕、以撒、雅各、犹大、大卫、耶稣。',
        ARRAY['亚当', '塞特', '挪亚', '闪', '亚伯拉罕', '以撒', '雅各', '犹大（雅各之子）', '大卫', '耶稣基督'],
        ARRAY['character'],
        ARRAY['family'],
        ARRAY['FATHER_OF', 'MOTHER_OF', 'SPOUSE_OF', 'SIBLING_OF', 'ANCESTOR_OF', 'DESCENDANT_OF'],
        2,
        10
    ),
    (
        'abraham-family',
        '亚伯拉罕家族图',
        'Abraham Family',
        '亚伯拉罕、撒拉、夏甲、以实玛利、以撒、基土拉、罗得、麦基洗德等关系。',
        ARRAY['亚伯拉罕', '撒拉', '夏甲', '以实玛利', '以撒', '基土拉', '罗得', '麦基洗德'],
        ARRAY['character', 'event', 'place'],
        ARRAY['family', 'spiritual', 'event', 'location'],
        ARRAY['FATHER_OF', 'MOTHER_OF', 'SPOUSE_OF', 'ANCESTOR_OF', 'PARTICIPATED_IN', 'TRAVELED_TO'],
        2,
        20
    ),
    (
        'jacob-twelve-tribes',
        '雅各十二支派图',
        'Jacob and the Twelve Tribes',
        '雅各、利亚、拉结、辟拉、悉帕和十二支派祖先。',
        ARRAY['雅各', '利亚', '拉结', '辟拉', '悉帕', '流便（雅各长子）', '西缅（雅各之子）', '利未（雅各之子）', '犹大（雅各之子）', '约瑟', '便雅悯（雅各之子）'],
        ARRAY['character'],
        ARRAY['family'],
        ARRAY['FATHER_OF', 'MOTHER_OF', 'SPOUSE_OF', 'SIBLING_OF', 'ANCESTOR_OF'],
        2,
        30
    ),
    (
        'exodus-leadership',
        '摩西—亚伦—约书亚出埃及领导网络',
        'Exodus Leadership Network',
        '摩西、亚伦、米利暗、约书亚、法老、叶忒罗和出埃及/西奈立约事件。',
        ARRAY['摩西', '亚伦', '米利暗', '约书亚', '法老', '叶忒罗/流珥', '出埃及', '西奈立约'],
        ARRAY['character', 'event', 'place', 'group'],
        ARRAY['family', 'spiritual', 'political', 'event', 'location'],
        ARRAY['SIBLING_OF', 'MENTOR_OF', 'LED', 'OPPOSED', 'PARTICIPATED_IN', 'MINISTERED_IN', 'LIVED_IN'],
        2,
        40
    ),
    (
        'judges-enemies',
        '士师时代人物与敌人网络',
        'Judges and Enemies',
        '士师、压迫者、拯救事件与士师时代循环。',
        ARRAY['底波拉', '巴拉', '雅亿', '基甸', '参孙', '耶弗他', '以笏', '西西拉', '大利拉', '士师循环'],
        ARRAY['character', 'event', 'place'],
        ARRAY['political', 'event', 'spiritual', 'conflict'],
        ARRAY['ATTACKED', 'DEFEATED', 'OPPOSED', 'PARTICIPATED_IN', 'CAUSED', 'LED'],
        2,
        50
    ),
    (
        'david-family-tragedy',
        '大卫家族悲剧网络',
        'David Family Tragedy',
        '大卫、扫罗、约拿单、拔示巴、乌利亚、暗嫩、他玛、押沙龙、亚多尼雅和拿单。',
        ARRAY['大卫', '扫罗', '约拿单', '拔示巴', '乌利亚', '暗嫩', '他玛，大卫女儿', '押沙龙', '亚多尼雅', '拿单先知'],
        ARRAY['character', 'event', 'place'],
        ARRAY['family', 'political', 'spiritual', 'event', 'location'],
        ARRAY['FATHER_OF', 'SPOUSE_OF', 'SIBLING_OF', 'ATTACKED', 'REBELLED_AGAINST', 'ANOINTED', 'DEFEATED', 'PARTICIPATED_IN'],
        2,
        60
    ),
    (
        'solomon-divided-kingdom',
        '所罗门与王国分裂网络',
        'Solomon and the Divided Kingdom',
        '所罗门晚年、罗波安、耶罗波安、亚希雅、示玛雅与王国分裂事件。',
        ARRAY['所罗门', '所罗门后期', '罗波安', '耶罗波安', '亚希雅', '示玛雅', '王国分裂'],
        ARRAY['character', 'event', 'place', 'nation'],
        ARRAY['family', 'political', 'spiritual', 'event'],
        ARRAY['FATHER_OF', 'OPPOSED', 'CAUSED', 'PARTICIPATED_IN', 'PROPHET_OF'],
        2,
        70
    ),
    (
        'kings-prophets',
        '南北国诸王与先知关系图',
        'Kings and Prophets',
        '南北国君王、先知责备、战争与被掳背景。',
        ARRAY['亚哈', '耶洗别', '以利亚', '以利沙', '希西家', '以赛亚', '约西亚', '耶利米', '何西阿', '阿摩司', '尼布甲尼撒'],
        ARRAY['character', 'event', 'place', 'nation'],
        ARRAY['spiritual', 'political', 'event', 'location'],
        ARRAY['MENTOR_OF', 'OPPOSED', 'ATTACKED', 'CONQUERED', 'PARTICIPATED_IN', 'EXILED_TO'],
        2,
        80
    ),
    (
        'return-from-exile',
        '被掳归回人物网络',
        'Return from Exile Network',
        '但以理、古列、所罗巴伯、以斯拉、尼希米、以斯帖、末底改与归回/重建。',
        ARRAY['但以理', '古列', '所罗巴伯', '以斯拉', '尼希米', '以斯帖', '末底改', '被掳归回', '巴比伦被掳'],
        ARRAY['character', 'event', 'place', 'nation', 'group'],
        ARRAY['political', 'spiritual', 'event', 'location'],
        ARRAY['EXILED_TO', 'ALLOWED_RETURN', 'INITIATED', 'PARTICIPATED_IN', 'MINISTERED_IN'],
        2,
        90
    ),
    (
        'jesus-gospels',
        '耶稣、十二门徒、福音书人物网络',
        'Jesus, the Twelve, and Gospel Figures',
        '耶稣、十二门徒、马利亚、施洗约翰、彼拉多、福音书神迹人物和受难复活事件。',
        ARRAY['耶稣基督', '马利亚', '约瑟（耶稣父亲）', '施洗约翰', '彼得', '约翰', '西庇太的雅各', '马太', '犹大', '彼拉多', '十字架受难', '复活'],
        ARRAY['character', 'event', 'place', 'group'],
        ARRAY['family', 'spiritual', 'political', 'event', 'location'],
        ARRAY['MOTHER_OF', 'SPOUSE_OF', 'CALLED', 'PREACHED_TO', 'SENTENCED', 'PARTICIPATED_IN', 'BORN_IN', 'CRUCIFIED_AT'],
        2,
        100
    ),
    (
        'paul-mission-network',
        '保罗宣教同工网络',
        'Paul Mission Network',
        '保罗、巴拿巴、西拉、提摩太、提多、路加、亚居拉、百基拉和宣教旅程地点。',
        ARRAY['保罗', '巴拿巴', '西拉', '提摩太', '提多', '路加', '亚居拉', '百基拉', '安提阿', '以弗所', '腓立比', '罗马', '保罗宣教旅程'],
        ARRAY['character', 'event', 'place', 'group'],
        ARRAY['spiritual', 'event', 'location'],
        ARRAY['MENTOR_OF', 'SENT_WITH', 'PREACHED_TO', 'PARTICIPATED_IN', 'SENT_FROM', 'MINISTERED_IN', 'IMPRISONED_IN'],
        2,
        110
    ),
    (
        'early-church',
        '初代教会人物网络',
        'Early Church Network',
        '彼得、司提反、腓力、哥尼流、亚拿尼亚、大比大、罗马书问安人物和初代教会事件。',
        ARRAY['彼得', '司提反', '腓力', '百夫长哥尼流', '亚拿尼亚（大马士革）', '多加', '腓比', '五旬节'],
        ARRAY['character', 'event', 'place', 'group'],
        ARRAY['spiritual', 'event', 'location', 'conflict'],
        ARRAY['PREACHED_TO', 'PREACHED_AT', 'PARTICIPATED_IN', 'MENTOR_OF', 'MINISTERED_IN'],
        2,
        120
    )
ON CONFLICT (slug) DO UPDATE SET
    title = EXCLUDED.title,
    title_en = EXCLUDED.title_en,
    description = EXCLUDED.description,
    focus_nodes = EXCLUDED.focus_nodes,
    node_types = EXCLUDED.node_types,
    relationship_categories = EXCLUDED.relationship_categories,
    relationship_types = EXCLUDED.relationship_types,
    depth = EXCLUDED.depth,
    sort_order = EXCLUDED.sort_order,
    is_active = true;
