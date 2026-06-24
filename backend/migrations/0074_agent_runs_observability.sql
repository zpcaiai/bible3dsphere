-- 0074_agent_runs_observability.sql
-- AI 运行可观测性：为 agent_runs 增补 skill / prompt / model / 延迟 / token / 错误 字段。
-- 幂等；向后兼容（全部可空或带默认）。email 仍为用户键，沿用既有 BIGSERIAL 主键。

ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS skill_name     VARCHAR(80)  DEFAULT '';
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS prompt_version VARCHAR(40)  DEFAULT '';
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS model_name     VARCHAR(80)  DEFAULT '';
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS latency_ms     INTEGER;
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS token_usage    JSONB        DEFAULT '{}'::jsonb;
ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS error_message  TEXT;

-- 便于按 skill 维度查询运行历史与失败率
CREATE INDEX IF NOT EXISTS idx_agent_runs_skill ON agent_runs(skill_name, created_at DESC);
