-- 0075_theological_review_logs.sql
-- 神学安全审查日志（Skill 9）：记录"展示给用户前"对 AI 输出做的福音中心审查结果。
-- 幂等；UUID 主键；email 为用户键（可空：系统级内容）。可挂接 agent_runs.id。
--
-- review_status: approved | needs_revision | blocked
-- detected_issues: [{dimension, severity(1-5), note}]
--   dimension ∈ legalism / prosperity_gospel / spiritual_shaming / ai_replaces_pastor /
--               crisis_without_human / scripture_misuse / over_psychologizing /
--               spiritual_scoring / mysticism_manipulation / disrespects_church

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS theological_review_logs (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email             TEXT,
    agent_run_id      BIGINT,                          -- 关联 agent_runs.id（可空）
    content_type      TEXT NOT NULL,                   -- diagnostic_finding/practice_plan/feedback_summary/weekly_review/shared_report/...
    content_id        UUID,
    content_excerpt   TEXT,                            -- 被审查内容摘要，便于审计回溯
    review_status     TEXT NOT NULL DEFAULT 'approved',
    detected_issues   JSONB DEFAULT '[]',
    corrected_content TEXT,
    reviewer_notes    TEXT,
    reviewer          TEXT NOT NULL DEFAULT 'agent',   -- agent | human
    created_at        TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_theo_review_email   ON theological_review_logs(email, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_theo_review_status  ON theological_review_logs(review_status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_theo_review_content ON theological_review_logs(content_type, content_id);
