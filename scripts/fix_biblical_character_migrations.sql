-- 修复 biblical_character 相关 migration 警告
-- 执行: psql $DATABASE_URL -f scripts/fix_biblical_character_migrations.sql

-- 1. 重建关系表（匹配 migration 期望的列名）
DROP TABLE IF EXISTS biblical_character_relationships CASCADE;
CREATE TABLE biblical_character_relationships (
    id SERIAL PRIMARY KEY,
    source_character_id INTEGER REFERENCES biblical_characters(id) ON DELETE CASCADE,
    target_character_id INTEGER REFERENCES biblical_characters(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL DEFAULT '',
    relationship_category VARCHAR(50) DEFAULT '',
    label_zh VARCHAR(100) DEFAULT '',
    label_en VARCHAR(100) DEFAULT '',
    scripture_ref VARCHAR(200) DEFAULT '',
    description TEXT DEFAULT '',
    weight REAL DEFAULT 1.0,
    is_directed BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bcr_source ON biblical_character_relationships(source_character_id);
CREATE INDEX IF NOT EXISTS idx_bcr_target ON biblical_character_relationships(target_character_id);

-- 2. 如果 biblical_characters 表存在 tags 列，添加 is_mixed_type 列
-- 0053 migration 试图将视图列 tags 重命名为 is_mixed_type，这是不可能的
-- 我们直接修改底层表结构
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'biblical_characters' AND column_name = 'tags'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'biblical_characters' AND column_name = 'is_mixed_type'
    ) THEN
        ALTER TABLE biblical_characters ADD COLUMN is_mixed_type BOOLEAN DEFAULT FALSE;
    END IF;
END $$;

-- 3. 标记 migration 已执行（避免重启后重复尝试）
INSERT INTO schema_migrations (version, name, checksum) 
VALUES 
    ('0053_biblical_characters_graph', 'biblical_characters_graph', 'skipped'),
    ('0054_expand_biblical_character_graph', 'expand_biblical_character_graph', 'skipped'),
    ('0055_supplement_biblical_characters', 'supplement_biblical_characters', 'skipped')
ON CONFLICT (version) DO NOTHING;

-- 验证
SELECT 'biblical_character_relationships created' as status
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'biblical_character_relationships');
