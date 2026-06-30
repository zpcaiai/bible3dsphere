-- Migration 0124: AI 属灵导师对话(多轮线程) AI Tutor Threads（B10 LLM 导师对话）
-- 线程 + 消息。危机消息先走安全门、路由到 /api/crisis,绝不进入 LLM。
-- 注:既有 0117 的 ai_tutor_conversations 是「单轮问答」表(formation_advanced 用);
--     本表是多轮线程模型,名称独立,互不冲突。

CREATE TABLE IF NOT EXISTS tutor_threads (
    id            VARCHAR(64)  PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    title         VARCHAR(200) DEFAULT '新的对话',
    topic         VARCHAR(60)  DEFAULT 'general',
    status        VARCHAR(20)  DEFAULT 'active',      -- active|archived
    risk_level    VARCHAR(20)  DEFAULT 'none',        -- none|elevated|high
    message_count INTEGER      DEFAULT 0,
    created_at    TIMESTAMPTZ  DEFAULT now(),
    updated_at    TIMESTAMPTZ  DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_tutor_threads_email ON tutor_threads(email, status);

CREATE TABLE IF NOT EXISTS tutor_messages (
    id           VARCHAR(64)  PRIMARY KEY,
    thread_id    VARCHAR(64)  NOT NULL,
    email        VARCHAR(255) NOT NULL,
    role         VARCHAR(16)  NOT NULL,               -- user|assistant
    content      TEXT         NOT NULL,
    message_type VARCHAR(20)  DEFAULT 'chat',          -- chat|safety|system
    route_module VARCHAR(40)  DEFAULT '',
    used_memory  BOOLEAN      DEFAULT FALSE,
    created_at   TIMESTAMPTZ  DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_tutor_messages_thread ON tutor_messages(thread_id, created_at);
