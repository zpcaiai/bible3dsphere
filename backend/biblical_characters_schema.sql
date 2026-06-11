-- ============================================================================
-- Biblical Characters Schema (镜鉴人物数据库)
-- 存储镜鉴tab中的205+圣经人物及其完整字段
-- ============================================================================

-- 依赖表：用户表 (简化版，用于外键约束)
CREATE TABLE IF NOT EXISTS sfds_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    nickname VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- 1. 主表: 圣经人物基础信息
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS biblical_characters (
    id SERIAL PRIMARY KEY,
    -- 基础标识
    name VARCHAR(100) NOT NULL,           -- 中文名 (如: "亚伯拉罕")
    name_en VARCHAR(100) NOT NULL,        -- 英文名 (如: "Abraham")

    -- 分类信息
    era VARCHAR(50) NOT NULL,             -- 时代 (族长时代/出埃及时代/士师时代/王国时代/被掳归回时代)
    role VARCHAR(50) NOT NULL,            -- 角色 (女性/族长/先知/君王/祭司/其他)
    kingdom VARCHAR(50),                    -- 王国 (统一王国/北国以色列/南国犹大) - 仅君王适用
    character_type VARCHAR(20) NOT NULL CHECK (character_type IN ('正面', '警戒', '混合')),

    -- 核心内容
    lesson VARCHAR(200) NOT NULL,         -- 核心教训
    summary TEXT NOT NULL,                -- 人物简介
    witness TEXT NOT NULL,                -- 见证/解读

    -- 圣经参考
    scripture_ref VARCHAR(200) NOT NULL,  -- 主要经文参考 (如: "创12-25")

    -- 祷告词
    prayer TEXT NOT NULL,                 -- 祷告词

    -- 元数据
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,         -- 排序权重
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_characters_era ON biblical_characters(era);
CREATE INDEX IF NOT EXISTS idx_characters_role ON biblical_characters(role);
CREATE INDEX IF NOT EXISTS idx_characters_type ON biblical_characters(character_type);
CREATE INDEX IF NOT EXISTS idx_characters_kingdom ON biblical_characters(kingdom) WHERE kingdom IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_characters_active ON biblical_characters(is_active) WHERE is_active = true;

-- ----------------------------------------------------------------------------
-- 2. 人物标签表 (多对多关联)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS character_tags (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES biblical_characters(id) ON DELETE CASCADE,
    tag VARCHAR(50) NOT NULL,              -- 标签 (如: "正面榜样", "警戒为主", "混合型", "族长")
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(character_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_tags_character_id ON character_tags(character_id);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON character_tags(tag);

-- ----------------------------------------------------------------------------
-- 3. 效法要点表 (Follow - 值得效法的点)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS character_follow_points (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES biblical_characters(id) ON DELETE CASCADE,
    content TEXT NOT NULL,                 -- 具体内容
    sort_order INTEGER DEFAULT 0,        -- 排序
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_follow_character_id ON character_follow_points(character_id);

-- ----------------------------------------------------------------------------
-- 4. 警戒要点表 (Caution - 需要警戒的点)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS character_caution_points (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES biblical_characters(id) ON DELETE CASCADE,
    content TEXT NOT NULL,                 -- 具体内容
    sort_order INTEGER DEFAULT 0,        -- 排序
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_caution_character_id ON character_caution_points(character_id);

-- ----------------------------------------------------------------------------
-- 5. 实际应用表 (Applications - 可操作建议)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS character_applications (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES biblical_characters(id) ON DELETE CASCADE,
    content TEXT NOT NULL,                 -- 具体应用建议
    sort_order INTEGER DEFAULT 0,        -- 排序
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_applications_character_id ON character_applications(character_id);

-- ----------------------------------------------------------------------------
-- 6. 相关经文表 (Scriptures)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS character_scriptures (
    id SERIAL PRIMARY KEY,
    character_id INTEGER NOT NULL REFERENCES biblical_characters(id) ON DELETE CASCADE,
    reference VARCHAR(100) NOT NULL,       -- 经文引用 (如: "创12:1-4", "罗4:3")
    book VARCHAR(50),                    -- 书卷名 (可选,便于筛选)
    chapter INTEGER,                     -- 章 (可选)
    sort_order INTEGER DEFAULT 0,        -- 排序
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scriptures_character_id ON character_scriptures(character_id);
CREATE INDEX IF NOT EXISTS idx_scriptures_book ON character_scriptures(book) WHERE book IS NOT NULL;

-- ----------------------------------------------------------------------------
-- 7. 主题合集表 (Themes)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS character_themes (
    id VARCHAR(50) PRIMARY KEY,            -- 主题标识 (如: "faith-obedience")
    name VARCHAR(100) NOT NULL,          -- 主题名 (如: "小人物大信心篇")
    name_en VARCHAR(100),                -- 英文名
    description TEXT,                    -- 主题描述
    icon VARCHAR(50),                    -- 图标标识
    emoji VARCHAR(20),                   -- 表情符号
    scripture TEXT,                      -- 主题经文
    intro TEXT,                          -- 主题介绍
    summary TEXT,                        -- 主题摘要
    how_to_apply TEXT[],                 -- 应用建议数组
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 人物-主题关联表
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

-- ----------------------------------------------------------------------------
-- 8. 人物关系图谱表 (Biblical Character Knowledge Graph)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS biblical_character_relationships (
    id SERIAL PRIMARY KEY,
    source_character_id INTEGER NOT NULL REFERENCES biblical_characters(id) ON DELETE CASCADE,
    target_character_id INTEGER NOT NULL REFERENCES biblical_characters(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL, -- father_of / spouse / mentor_of / betrayed 等
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

-- ----------------------------------------------------------------------------
-- 9. 用户收藏/互动表 (可选 - 用户与人物的互动)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_character_interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES sfds_users(id) ON DELETE CASCADE,
    character_id INTEGER NOT NULL REFERENCES biblical_characters(id) ON DELETE CASCADE,
    is_favorite BOOLEAN DEFAULT false,     -- 是否收藏
    is_reflected BOOLEAN DEFAULT false,    -- 是否反思过
    personal_notes TEXT,                   -- 个人笔记
    last_viewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, character_id)
);

CREATE INDEX IF NOT EXISTS idx_user_char_interactions_user_id ON user_character_interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_char_interactions_character_id ON user_character_interactions(character_id);

-- ----------------------------------------------------------------------------
-- 10. 自动更新时间戳触发器
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_biblical_characters_updated_at ON biblical_characters;
CREATE TRIGGER update_biblical_characters_updated_at
    BEFORE UPDATE ON biblical_characters
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_character_interactions_updated_at ON user_character_interactions;
CREATE TRIGGER update_user_character_interactions_updated_at
    BEFORE UPDATE ON user_character_interactions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_biblical_character_relationships_updated_at ON biblical_character_relationships;
CREATE TRIGGER update_biblical_character_relationships_updated_at
    BEFORE UPDATE ON biblical_character_relationships
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------------------
-- 11. 常用查询视图
-- ----------------------------------------------------------------------------

-- 人物完整信息视图 (包含所有关联数组聚合)
CREATE OR REPLACE VIEW v_character_full AS
SELECT
    c.*,
    COALESCE((
        SELECT array_agg(ct.tag ORDER BY ct.tag)
        FROM character_tags ct
        WHERE ct.character_id = c.id
    ), '{}') as tags,
    COALESCE((
        SELECT array_agg(cf.content ORDER BY cf.sort_order, cf.id)
        FROM character_follow_points cf
        WHERE cf.character_id = c.id
    ), '{}') as follow_points,
    COALESCE((
        SELECT array_agg(cc.content ORDER BY cc.sort_order, cc.id)
        FROM character_caution_points cc
        WHERE cc.character_id = c.id
    ), '{}') as caution_points,
    COALESCE((
        SELECT array_agg(ca.content ORDER BY ca.sort_order, ca.id)
        FROM character_applications ca
        WHERE ca.character_id = c.id
    ), '{}') as applications,
    COALESCE((
        SELECT array_agg(cs.reference ORDER BY cs.sort_order, cs.id)
        FROM character_scriptures cs
        WHERE cs.character_id = c.id
    ), '{}') as scriptures,
    COALESCE((
        SELECT array_agg(t.name ORDER BY ctm.sort_order)
        FROM character_theme_mappings ctm
        JOIN character_themes t ON ctm.theme_id = t.id
        WHERE ctm.character_id = c.id AND t.is_active = true
    ), '{}') as themes
FROM biblical_characters c
WHERE c.is_active = true;

-- 按时代统计视图
CREATE OR REPLACE VIEW v_characters_by_era AS
SELECT
    era,
    COUNT(*) as total_count,
    COUNT(*) FILTER (WHERE character_type = '正面') as positive_count,
    COUNT(*) FILTER (WHERE character_type = '警戒') as warning_count,
    COUNT(*) FILTER (WHERE character_type = '混合') as mixed_count
FROM biblical_characters
WHERE is_active = true
GROUP BY era
ORDER BY MIN(sort_order), era;

-- 按角色统计视图
CREATE OR REPLACE VIEW v_characters_by_role AS
SELECT
    role,
    COUNT(*) as total_count
FROM biblical_characters
WHERE is_active = true
GROUP BY role
ORDER BY COUNT(*) DESC;

-- 人物关系图谱边视图
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

-- 人物关系图谱节点视图
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

-- ----------------------------------------------------------------------------
-- 数据导入说明:
-- ----------------------------------------------------------------------------
-- 1. 将 mirrorData.js 的 JSON 数据转换为 SQL INSERT 语句
-- 2. 数组字段需要拆分到对应的关联表中
-- 3. 示例 INSERT:
--
-- INSERT INTO biblical_characters (id, name, name_en, era, role, character_type, lesson, summary, witness, scripture_ref, prayer)
-- VALUES (1, '亚当', 'Adam', '族长时代', '其他', '警戒', '顺服的重要性', '...', '...', '创2-3', '...');
--
-- INSERT INTO character_tags (character_id, tag) VALUES (1, '其他'), (1, '警戒为主');
-- INSERT INTO character_follow_points (character_id, content, sort_order) VALUES (1, '被委托管理受造世界...', 1), ...;
-- INSERT INTO character_caution_points (character_id, content, sort_order) VALUES (1, '在试探面前沉默不说话', 1), ...;
-- INSERT INTO character_applications (character_id, content, sort_order) VALUES (1, '面对诱惑时，先停下来问...', 1), ...;
-- INSERT INTO character_scriptures (character_id, reference, book, chapter, sort_order) VALUES (1, '创2:16-17', '创世记', 2, 1), ...;
--
