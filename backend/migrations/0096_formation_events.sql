-- 0096_formation_events.sql
-- 统一成长事件流（整合层 Phase 0）：所有模块的诊断/重写/操练/复盘/危机/恩赐等产出，
-- best-effort 汇入这一张表，构成「一个人」的纵向成长时间轴。growth_state 由它聚合（读时计算）。
CREATE TABLE IF NOT EXISTS formation_events (
    id          BIGSERIAL PRIMARY KEY,
    email       TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source      VARCHAR(40) NOT NULL,   -- worldview / gift / spiritual_formation / weekly_review / crisis ...
    event_type  VARCHAR(40) NOT NULL,   -- diagnosis / reframe / practice / review / crisis / gift / checkin ...
    domain      VARCHAR(60),            -- 偶像类别 / 世界观领域 / 主题
    title       TEXT,
    summary     TEXT,
    severity    VARCHAR(10),            -- green/amber/red 或 low/medium/high
    refs        JSONB NOT NULL DEFAULT '[]',
    payload     JSONB NOT NULL DEFAULT '{}',
    ref_id      TEXT,                   -- 来源行 id（用于幂等去重）
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_formation_events_email_time ON formation_events(email, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_formation_events_email_src  ON formation_events(email, source);
-- 有来源 id 的事件按 (email,source,type,ref_id) 幂等去重
CREATE UNIQUE INDEX IF NOT EXISTS idx_formation_events_dedupe
    ON formation_events(email, source, event_type, ref_id) WHERE ref_id IS NOT NULL;
