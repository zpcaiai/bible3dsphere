-- Migration 0036: 门徒塑造整合层 — 领域事件流 (Domain Events)
-- 记录 ReflectionAssessed / SpiritualStateChanged / IdolDetected 等领域事件，
-- 为后续事件驱动编排（周/月复盘触发、状态迁移确认）打底。
-- 幂等：IF NOT EXISTS。

CREATE TABLE IF NOT EXISTS domain_events (
    id             BIGSERIAL PRIMARY KEY,
    aggregate_type VARCHAR(60)  NOT NULL,            -- disciple_profile | disciple_assessment ...
    aggregate_id   VARCHAR(255) NOT NULL,            -- 通常是 email
    event_type     VARCHAR(80)  NOT NULL,            -- ReflectionAssessed | SpiritualStateChanged ...
    payload        JSONB        NOT NULL DEFAULT '{}'::jsonb,
    processed      BOOLEAN      DEFAULT FALSE,
    processed_at   TIMESTAMP,
    created_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_domain_events_unprocessed
    ON domain_events(processed, created_at) WHERE processed = FALSE;
CREATE INDEX IF NOT EXISTS idx_domain_events_aggregate
    ON domain_events(aggregate_type, aggregate_id, created_at DESC);
