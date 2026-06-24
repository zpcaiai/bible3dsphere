-- 0076_weekly_reviews.sql
-- 每周复盘（Skill 5）：按 (email, week_start) 聚合一周打卡 / 操练 / 反思，给出趋势与福音提醒。
-- 幂等；UUID 主键；email 为用户键。趋势取值：improving/stable/fluctuating/worsening/needs_attention。
-- 注：不存"属灵分数"，只存趋势、聚合证据与温柔的下一步建议。

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS weekly_reviews (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email                     TEXT NOT NULL,
    week_start                DATE NOT NULL,
    week_end                  DATE NOT NULL,
    main_theme                TEXT,
    progress_summary          TEXT,
    struggle_summary          TEXT,
    repentance_summary        TEXT,
    encouragement_summary     TEXT,
    trend_anxiety             TEXT,
    trend_prayer              TEXT,
    trend_scripture           TEXT,
    trend_community           TEXT,
    overall_trend             TEXT,
    metrics                   JSONB DEFAULT '{}',    -- 原始聚合：打卡数 / 完成率 / 均值 等
    recommended_next_steps    JSONB DEFAULT '[]',
    suggested_prayer_requests JSONB DEFAULT '[]',
    generated_by_agent        TEXT DEFAULT 'WeeklyReviewAgent',
    created_at                TIMESTAMPTZ DEFAULT now(),
    updated_at                TIMESTAMPTZ DEFAULT now(),
    UNIQUE(email, week_start)
);

CREATE INDEX IF NOT EXISTS idx_weekly_reviews_email ON weekly_reviews(email, week_start DESC);
