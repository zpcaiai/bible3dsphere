-- 为 sunday_school_videos 表添加 alias 列
-- 执行: psql $DATABASE_URL -f scripts/add_alias_column.sql

-- 添加 alias 列（如果不存在）
ALTER TABLE sunday_school_videos 
ADD COLUMN IF NOT EXISTS alias VARCHAR(255) DEFAULT '';

-- 验证列已添加
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'sunday_school_videos'
ORDER BY ordinal_position;
