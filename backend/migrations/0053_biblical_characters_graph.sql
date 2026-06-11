-- Biblical characters relationship graph.
-- The base character tables may already exist from backend/biblical_characters_seed.sql;
-- keep this migration idempotent so deploy-time migration can safely run first.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS sfds_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    nickname VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS biblical_characters (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    name_en VARCHAR(100) NOT NULL,
    era VARCHAR(50) NOT NULL,
    role VARCHAR(50) NOT NULL,
    kingdom VARCHAR(50),
    character_type VARCHAR(20) NOT NULL CHECK (character_type IN ('正面', '警戒', '混合')),
    lesson VARCHAR(200) NOT NULL,
    summary TEXT NOT NULL,
    witness TEXT NOT NULL,
    scripture_ref VARCHAR(200) NOT NULL,
    prayer TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_characters_era ON biblical_characters(era);
CREATE INDEX IF NOT EXISTS idx_characters_role ON biblical_characters(role);
CREATE INDEX IF NOT EXISTS idx_characters_type ON biblical_characters(character_type);
CREATE INDEX IF NOT EXISTS idx_characters_active ON biblical_characters(is_active) WHERE is_active = true;

CREATE TABLE IF NOT EXISTS character_tags (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES biblical_characters(id) ON DELETE CASCADE,
    tag VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(character_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_tags_character_id ON character_tags(character_id);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON character_tags(tag);

CREATE TABLE IF NOT EXISTS character_follow_points (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES biblical_characters(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_follow_character_id ON character_follow_points(character_id);

CREATE TABLE IF NOT EXISTS character_caution_points (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES biblical_characters(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_caution_character_id ON character_caution_points(character_id);

CREATE TABLE IF NOT EXISTS character_applications (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES biblical_characters(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_applications_character_id ON character_applications(character_id);

CREATE TABLE IF NOT EXISTS character_scriptures (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES biblical_characters(id) ON DELETE CASCADE,
    reference VARCHAR(100) NOT NULL,
    book VARCHAR(50),
    chapter INTEGER,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scriptures_character_id ON character_scriptures(character_id);
CREATE INDEX IF NOT EXISTS idx_scriptures_book ON character_scriptures(book) WHERE book IS NOT NULL;

CREATE TABLE IF NOT EXISTS character_themes (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    description TEXT,
    icon VARCHAR(50),
    emoji VARCHAR(20),
    scripture TEXT,
    intro TEXT,
    summary TEXT,
    how_to_apply TEXT[],
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS character_theme_mappings (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES biblical_characters(id) ON DELETE CASCADE,
    theme_id VARCHAR(50) NOT NULL REFERENCES character_themes(id) ON DELETE CASCADE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(character_id, theme_id)
);

CREATE INDEX IF NOT EXISTS idx_theme_mappings_theme_id ON character_theme_mappings(theme_id);
CREATE INDEX IF NOT EXISTS idx_theme_mappings_character_id ON character_theme_mappings(character_id);

CREATE OR REPLACE VIEW v_character_full AS
SELECT
    c.*,
    COALESCE((
        SELECT array_agg(ct.tag ORDER BY ct.tag)
        FROM character_tags ct
        WHERE ct.character_id = c.id
    ), '{}') AS tags,
    COALESCE((
        SELECT array_agg(cf.content ORDER BY cf.sort_order, cf.id)
        FROM character_follow_points cf
        WHERE cf.character_id = c.id
    ), '{}') AS follow_points,
    COALESCE((
        SELECT array_agg(cc.content ORDER BY cc.sort_order, cc.id)
        FROM character_caution_points cc
        WHERE cc.character_id = c.id
    ), '{}') AS caution_points,
    COALESCE((
        SELECT array_agg(ca.content ORDER BY ca.sort_order, ca.id)
        FROM character_applications ca
        WHERE ca.character_id = c.id
    ), '{}') AS applications,
    COALESCE((
        SELECT array_agg(cs.reference ORDER BY cs.sort_order, cs.id)
        FROM character_scriptures cs
        WHERE cs.character_id = c.id
    ), '{}') AS scriptures,
    COALESCE((
        SELECT array_agg(t.name ORDER BY ctm.sort_order)
        FROM character_theme_mappings ctm
        JOIN character_themes t ON ctm.theme_id = t.id
        WHERE ctm.character_id = c.id AND t.is_active = true
    ), '{}') AS themes
FROM biblical_characters c
WHERE c.is_active = true;

CREATE OR REPLACE VIEW v_characters_by_era AS
SELECT
    era,
    COUNT(*) AS total_count,
    COUNT(*) FILTER (WHERE character_type = '正面') AS positive_count,
    COUNT(*) FILTER (WHERE character_type = '警戒') AS warning_count,
    COUNT(*) FILTER (WHERE character_type = '混合') AS mixed_count
FROM biblical_characters
WHERE is_active = true
GROUP BY era
ORDER BY MIN(sort_order), era;

CREATE OR REPLACE VIEW v_characters_by_role AS
SELECT
    role,
    COUNT(*) AS total_count
FROM biblical_characters
WHERE is_active = true
GROUP BY role
ORDER BY COUNT(*) DESC;

CREATE TABLE IF NOT EXISTS biblical_character_relationships (
    id SERIAL PRIMARY KEY,
    source_character_id INTEGER NOT NULL REFERENCES biblical_characters(id) ON DELETE CASCADE,
    target_character_id INTEGER NOT NULL REFERENCES biblical_characters(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,
    relationship_category VARCHAR(30) NOT NULL DEFAULT 'other'
        CHECK (relationship_category IN ('family', 'marriage', 'ministry', 'conflict', 'political', 'spiritual', 'lineage', 'other')),
    label_zh VARCHAR(100) NOT NULL,
    label_en VARCHAR(100),
    scripture_ref VARCHAR(200),
    description TEXT,
    weight NUMERIC(4,2) NOT NULL DEFAULT 1.0 CHECK (weight >= 0 AND weight <= 10),
    confidence NUMERIC(4,2) NOT NULL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    is_directed BOOLEAN NOT NULL DEFAULT true,
    is_active BOOLEAN NOT NULL DEFAULT true,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CHECK (source_character_id <> target_character_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_character_relationship_unique
    ON biblical_character_relationships (
        source_character_id,
        target_character_id,
        relationship_type,
        COALESCE(scripture_ref, '')
    );
CREATE INDEX IF NOT EXISTS idx_character_relationship_source
    ON biblical_character_relationships(source_character_id) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_character_relationship_target
    ON biblical_character_relationships(target_character_id) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_character_relationship_type
    ON biblical_character_relationships(relationship_type) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_character_relationship_category
    ON biblical_character_relationships(relationship_category) WHERE is_active = true;

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

DROP TRIGGER IF EXISTS update_biblical_character_relationships_updated_at
    ON biblical_character_relationships;
CREATE TRIGGER update_biblical_character_relationships_updated_at
    BEFORE UPDATE ON biblical_character_relationships
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE VIEW v_biblical_character_graph_edges AS
SELECT
    r.id,
    r.source_character_id AS source_id,
    source.name AS source_name,
    source.name_en AS source_name_en,
    source.era AS source_era,
    source.role AS source_role,
    r.target_character_id AS target_id,
    target.name AS target_name,
    target.name_en AS target_name_en,
    target.era AS target_era,
    target.role AS target_role,
    r.relationship_type,
    r.relationship_category,
    r.label_zh,
    r.label_en,
    r.scripture_ref,
    r.description,
    r.weight,
    r.confidence,
    r.is_directed,
    r.sort_order
FROM biblical_character_relationships r
JOIN biblical_characters source ON source.id = r.source_character_id
JOIN biblical_characters target ON target.id = r.target_character_id
WHERE r.is_active = true
  AND source.is_active = true
  AND target.is_active = true;

CREATE OR REPLACE VIEW v_biblical_character_graph_nodes AS
SELECT
    c.id,
    c.name,
    c.name_en,
    c.era,
    c.role,
    c.kingdom,
    c.character_type,
    c.lesson,
    c.scripture_ref,
    c.sort_order,
    COALESCE(rel.degree, 0) AS degree,
    COALESCE(rel.out_degree, 0) AS out_degree,
    COALESCE(rel.in_degree, 0) AS in_degree
FROM biblical_characters c
LEFT JOIN (
    SELECT
        character_id,
        COUNT(*) AS degree,
        COUNT(*) FILTER (WHERE direction = 'out') AS out_degree,
        COUNT(*) FILTER (WHERE direction = 'in') AS in_degree
    FROM (
        SELECT source_character_id AS character_id, 'out' AS direction
        FROM biblical_character_relationships
        WHERE is_active = true
        UNION ALL
        SELECT target_character_id AS character_id, 'in' AS direction
        FROM biblical_character_relationships
        WHERE is_active = true
    ) rels
    GROUP BY character_id
) rel ON rel.character_id = c.id
WHERE c.is_active = true;

WITH rels(source_name, target_name, relationship_type, relationship_category, label_zh, label_en, scripture_ref, description, weight, is_directed, sort_order) AS (
    VALUES
    ('亚当', '夏娃', 'spouse', 'marriage', '夫妻', 'spouse', '创2-3', '人类第一对夫妻。', 3.0, false, 10),
    ('亚当', '该隐', 'father_of', 'family', '父亲', 'father of', '创4:1', '该隐是亚当和夏娃的儿子。', 2.5, true, 20),
    ('亚当', '亚伯', 'father_of', 'family', '父亲', 'father of', '创4:2', '亚伯是亚当和夏娃的儿子。', 2.5, true, 30),
    ('亚当', '塞特', 'father_of', 'family', '父亲', 'father of', '创4:25', '塞特被赐下代替亚伯，延续敬虔后裔。', 2.5, true, 40),
    ('该隐', '亚伯', 'murdered', 'conflict', '杀害', 'murdered', '创4:8', '该隐因嫉妒杀害亚伯。', 3.5, true, 50),
    ('亚伯拉罕', '撒拉', 'spouse', 'marriage', '夫妻', 'spouse', '创12-23', '亚伯拉罕与撒拉共同承受应许。', 3.0, false, 60),
    ('亚伯拉罕', '以撒', 'father_of', 'family', '父亲', 'father of', '创21', '以撒是应许之子。', 3.0, true, 70),
    ('亚伯拉罕', '罗得', 'uncle_of', 'family', '叔伯', 'uncle of', '创12-13', '罗得随亚伯拉罕离开本地，后来分开。', 2.0, true, 80),
    ('以撒', '利百加', 'spouse', 'marriage', '夫妻', 'spouse', '创24', '以撒与利百加的婚姻由神奇妙引导。', 3.0, false, 90),
    ('以撒', '以扫', 'father_of', 'family', '父亲', 'father of', '创25', '以扫是以撒的长子。', 2.5, true, 100),
    ('以撒', '雅各', 'father_of', 'family', '父亲', 'father of', '创25', '雅各是以撒的儿子，后来被改名为以色列。', 2.5, true, 110),
    ('雅各', '约瑟', 'father_of', 'family', '父亲', 'father of', '创30,37', '约瑟是雅各所爱的儿子。', 3.0, true, 120),
    ('雅各', '便雅悯（雅各之子）', 'father_of', 'family', '父亲', 'father of', '创35', '便雅悯是雅各最小的儿子。', 2.5, true, 130),
    ('约瑟', '玛拿西（约瑟长子）', 'father_of', 'family', '父亲', 'father of', '创41,48', '玛拿西是约瑟长子。', 2.0, true, 140),
    ('约瑟', '以法莲（约瑟次子）', 'father_of', 'family', '父亲', 'father of', '创41,48', '以法莲是约瑟次子。', 2.0, true, 150),
    ('摩西', '亚伦', 'sibling', 'family', '兄弟', 'sibling', '出4-民20', '摩西与亚伦同工带领以色列出埃及。', 3.0, false, 160),
    ('摩西', '米利暗', 'sibling', 'family', '姐弟', 'sibling', '出15,民12', '米利暗是摩西和亚伦的姊妹。', 2.5, false, 170),
    ('亚伦', '非尼哈', 'ancestor_of', 'lineage', '祖先', 'ancestor of', '民25', '非尼哈是亚伦家族的祭司后裔。', 2.0, true, 180),
    ('拿俄米', '路得', 'mother_in_law_of', 'family', '婆婆', 'mother-in-law of', '路得记1', '路得忠心跟随婆婆拿俄米。', 3.0, true, 190),
    ('路得', '波阿斯', 'spouse', 'marriage', '夫妻', 'spouse', '路得记4', '波阿斯作家业救赎主迎娶路得。', 3.5, false, 200),
    ('路得', '大卫', 'ancestor_of', 'lineage', '祖先', 'ancestor of', '得4:17-22', '路得进入大卫和弥赛亚家谱。', 2.5, true, 210),
    ('扫罗', '约拿单', 'father_of', 'family', '父亲', 'father of', '撒上14-31', '约拿单是扫罗的儿子。', 2.5, true, 220),
    ('约拿单', '大卫', 'covenant_friend', 'spiritual', '立约之友', 'covenant friend', '撒上18-20', '约拿单与大卫立约，保护大卫。', 3.5, false, 230),
    ('扫罗', '大卫', 'persecuted', 'conflict', '逼迫', 'persecuted', '撒上18-31', '扫罗因嫉妒多次追杀大卫。', 3.5, true, 240),
    ('大卫', '所罗门', 'father_of', 'family', '父亲', 'father of', '王上1-2', '所罗门继承大卫王位并建造圣殿。', 3.0, true, 250),
    ('大卫', '拔示巴', 'spouse', 'marriage', '夫妻', 'spouse', '撒下11-12', '大卫与拔示巴的关系包含严重犯罪、审判与恩典。', 2.5, false, 260),
    ('大卫', '押沙龙', 'father_of', 'family', '父亲', 'father of', '撒下13-18', '押沙龙是大卫的儿子，后来叛乱。', 3.0, true, 270),
    ('押沙龙', '大卫', 'rebelled_against', 'political', '叛乱', 'rebelled against', '撒下15-18', '押沙龙背叛大卫并夺取王位。', 3.0, true, 280),
    ('大卫', '米非波设', 'showed_covenant_kindness_to', 'spiritual', '守约施恩', 'showed covenant kindness to', '撒下9', '大卫因与约拿单的约恩待米非波设。', 2.5, true, 290),
    ('所罗门', '罗波安', 'father_of', 'family', '父亲', 'father of', '王上11-12', '罗波安是所罗门之子，其选择导致王国分裂。', 2.0, true, 300),
    ('以利亚', '以利沙', 'mentor_of', 'ministry', '师徒', 'mentor of', '王上19,王下2', '以利沙承接以利亚的先知职分。', 3.5, true, 310),
    ('耶稣基督', '马利亚', 'son_of', 'family', '儿子', 'son of', '路1-2', '耶稣由马利亚所生。', 3.5, true, 320),
    ('约瑟（耶稣父亲）', '马利亚', 'spouse', 'marriage', '夫妻', 'spouse', '太1-2', '约瑟顺服神，接纳并保护马利亚和耶稣。', 3.0, false, 330),
    ('施洗约翰', '耶稣基督', 'forerunner_of', 'spiritual', '先锋', 'forerunner of', '太3,约1', '施洗约翰为耶稣预备道路。', 3.5, true, 340),
    ('耶稣基督', '彼得', 'called_disciple', 'ministry', '呼召门徒', 'called disciple', '太4,约21', '耶稣呼召并恢复彼得。', 3.5, true, 350),
    ('耶稣基督', '约翰', 'called_disciple', 'ministry', '呼召门徒', 'called disciple', '太4,约13-21', '约翰是耶稣所爱的门徒。', 3.0, true, 360),
    ('犹大', '耶稣基督', 'betrayed', 'conflict', '出卖', 'betrayed', '太26-27', '犹大为三十块银子出卖耶稣。', 3.5, true, 370),
    ('巴拿巴', '保罗', 'sponsored', 'ministry', '接纳举荐', 'sponsored', '徒9,11', '巴拿巴接纳并举荐刚悔改的保罗。', 3.0, true, 380),
    ('保罗', '提摩太', 'mentor_of', 'ministry', '属灵父亲', 'mentor of', '徒16,提前,提后', '提摩太是保罗信任的属灵儿子和同工。', 3.5, true, 390),
    ('保罗', '巴拿巴', 'ministry_partner', 'ministry', '宣教同工', 'ministry partner', '徒13-15', '保罗与巴拿巴一同被差派宣教。', 3.0, false, 400)
)
INSERT INTO biblical_character_relationships (
    source_character_id,
    target_character_id,
    relationship_type,
    relationship_category,
    label_zh,
    label_en,
    scripture_ref,
    description,
    weight,
    is_directed,
    sort_order
)
SELECT
    source.id,
    target.id,
    rels.relationship_type,
    rels.relationship_category,
    rels.label_zh,
    rels.label_en,
    rels.scripture_ref,
    rels.description,
    rels.weight,
    rels.is_directed,
    rels.sort_order
FROM rels
JOIN biblical_characters source ON source.name = rels.source_name
JOIN biblical_characters target ON target.name = rels.target_name
ON CONFLICT DO NOTHING;
