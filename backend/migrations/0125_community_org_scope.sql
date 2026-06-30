-- Migration 0125: 社区数据 org 作用域 Community Org Scope（B12 多租户隔离）
-- 仅"社区/组织"数据加 org_id(可空,渐进回填);
-- 个人成长数据(省察/认罪/危机/祷告/记忆/灵修日志/灵魂一问/偶像/试探)保持 email 私有,绝不加 org_id。
-- 危机/安全永远豁免租户限制。org_id 可空:历史行与个人自建记录 org_id=NULL,按 email 归属本人。

ALTER TABLE accountability_groups          ADD COLUMN IF NOT EXISTS org_id VARCHAR(64);
ALTER TABLE accountability_group_checkins  ADD COLUMN IF NOT EXISTS org_id VARCHAR(64);
ALTER TABLE church_profiles                ADD COLUMN IF NOT EXISTS org_id VARCHAR(64);
ALTER TABLE church_life_checkins           ADD COLUMN IF NOT EXISTS org_id VARCHAR(64);
ALTER TABLE mentor_relationships           ADD COLUMN IF NOT EXISTS org_id VARCHAR(64);
ALTER TABLE mentor_sessions                ADD COLUMN IF NOT EXISTS org_id VARCHAR(64);
ALTER TABLE discipleship_stages            ADD COLUMN IF NOT EXISTS org_id VARCHAR(64);
ALTER TABLE user_discipleship_paths        ADD COLUMN IF NOT EXISTS org_id VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_acct_groups_org     ON accountability_groups(org_id);
CREATE INDEX IF NOT EXISTS idx_acct_checkins_org   ON accountability_group_checkins(org_id);
CREATE INDEX IF NOT EXISTS idx_church_profiles_org ON church_profiles(org_id);
CREATE INDEX IF NOT EXISTS idx_church_checkins_org ON church_life_checkins(org_id);
CREATE INDEX IF NOT EXISTS idx_mentor_rel_org      ON mentor_relationships(org_id);
CREATE INDEX IF NOT EXISTS idx_mentor_sessions_org ON mentor_sessions(org_id);
CREATE INDEX IF NOT EXISTS idx_disc_stages_org     ON discipleship_stages(org_id);
CREATE INDEX IF NOT EXISTS idx_user_disc_paths_org ON user_discipleship_paths(org_id);
