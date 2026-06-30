-- Migration 0120: 个人成长 Agent / 统一编排层 (B10 核心)
-- 跨模块统一 dashboard + 意图路由(安全优先) + 每日计划。把 13 batch 串起来的闭环层。
-- email 标识用户。

CREATE TABLE IF NOT EXISTS daily_formation_plans (
    id              VARCHAR(64)  PRIMARY KEY,
    email           VARCHAR(255) NOT NULL,
    plan_date       DATE         NOT NULL,
    plan_title      VARCHAR(160) DEFAULT '今日的忠心一小步',
    primary_focus   VARCHAR(120) DEFAULT '',
    practices       JSONB        DEFAULT '[]'::jsonb,
    guardrails      JSONB        DEFAULT '[]'::jsonb,
    status          VARCHAR(12)  DEFAULT 'active',
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (email, plan_date)
);
CREATE INDEX IF NOT EXISTS idx_daily_plans_email ON daily_formation_plans (email, plan_date DESC);

CREATE TABLE IF NOT EXISTS formation_agent_sessions (
    id             VARCHAR(64)  PRIMARY KEY,
    email          VARCHAR(255) NOT NULL,
    session_date   DATE         DEFAULT CURRENT_DATE,
    intent_text    TEXT         DEFAULT '',
    detected_intent VARCHAR(24) DEFAULT '',
    risk_level     VARCHAR(12)  DEFAULT 'none',
    routed_module  VARCHAR(40)  DEFAULT '',
    created_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_agent_sessions_email ON formation_agent_sessions (email, created_at DESC);
