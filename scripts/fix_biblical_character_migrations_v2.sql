-- 修复剩余的 biblical_character migration 警告 (0053, 0055)
-- 执行: psql $DATABASE_URL -f scripts/fix_biblical_character_migrations_v2.sql

-- 1. 给 biblical_character_relationships 添加缺失的列（0055 需要 confidence）
DO $$
BEGIN
    -- confidence 列
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'biblical_character_relationships' AND column_name = 'confidence'
    ) THEN
        ALTER TABLE biblical_character_relationships ADD COLUMN confidence NUMERIC(4,2) NOT NULL DEFAULT 1.0;
    END IF;
    
    -- is_active 列
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'biblical_character_relationships' AND column_name = 'is_active'
    ) THEN
        ALTER TABLE biblical_character_relationships ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
    END IF;
    
    -- updated_at 列
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'biblical_character_relationships' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE biblical_character_relationships ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
    END IF;
END $$;

-- 2. 添加 updated_at 触发器（如果 0053 的触发器未创建）
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

DROP TRIGGER IF EXISTS update_biblical_character_relationships_updated_at ON biblical_character_relationships;
CREATE TRIGGER update_biblical_character_relationships_updated_at
    BEFORE UPDATE ON biblical_character_relationships
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 3. 删除 biblical_characters 表多余的列，恢复 c.* 原始结构
-- is_mixed_type 会改变 c.* 的列数，导致 CREATE OR REPLACE VIEW 列位置冲突
DO $$
BEGIN
    -- 删除 tags（如果存在）
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'biblical_characters' AND column_name = 'tags'
    ) THEN
        ALTER TABLE biblical_characters DROP COLUMN tags;
    END IF;
    
    -- 删除 is_mixed_type（如果存在）
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'biblical_characters' AND column_name = 'is_mixed_type'
    ) THEN
        ALTER TABLE biblical_characters DROP COLUMN is_mixed_type;
    END IF;
END $$;

-- 4. 删除 0053 的跳过记录，让服务器重启时真正执行它
-- 0055 已经成功应用，保留其记录
DELETE FROM schema_migrations WHERE version = '0053_biblical_characters_graph';

-- 验证
SELECT 'columns fixed' as status,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'biblical_character_relationships' AND column_name IN ('confidence','is_active','updated_at')) as fixed_cols;
