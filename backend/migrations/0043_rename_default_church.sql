-- 0043_rename_default_church.sql — 品牌更名：默认教会「情感星球大家庭」→「属灵星球大家庭」
-- 注：0041 已应用不可修改，名称变更走新迁移（幂等：仅当仍为旧名时更新）
UPDATE churches SET name = '属灵星球大家庭'
WHERE is_default = TRUE AND name = '情感星球大家庭';
