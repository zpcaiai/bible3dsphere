-- Migration 0037: 门徒塑造整合层 — Agent 运行记录 (event consumer 的产物)
-- domain_events(0036) 是"写"，这张表是"消费"：事件消费者(process_user_events)
-- 对每条未处理事件跑规则 Agent(StateTransition/IdolWatch/Cadence)，把结论与 nudge 落此表。
-- 幂等：IF NOT EXISTS。

CREATE TABLE IF NOT EXISTS agent_runs (
    id             BIGSERIAL PRIMARY KEY,
    email          VARCHAR(255) NOT NULL,
    agent_name     VARCHAR(60)  NOT NULL,           -- StateTransitionAgent | IdolWatchAgent | CadenceAgent
    event_type     VARCHAR(80)  DEFAULT '',         -- 触发它的领域事件
    input_payload  JSONB        DEFAULT '{}'::jsonb,
    output_payload JSONB        DEFAULT '{}'::jsonb, -- {kind, title, body, ...}
    status         VARCHAR(20)  NOT NULL DEFAULT 'DONE', -- DONE | FAILED
    notified       BOOLEAN      DEFAULT FALSE,        -- 是否已 Web Push 通知
    created_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_agent_runs_email
    ON agent_runs(email, created_at DESC);
