-- 0077_semantic_index.sql
-- 语义检索索引：对用户的反思日志 / 长期生命记忆等文本做语义检索（规格 reflection_logs /
-- formation_memory_events 的检索能力）。附加表，不改任何既有写路径。
--
-- 设计沿用本仓库既有约定（guardian_memories / stronghold_rag）：embedding 存 JSONB，
-- 余弦相似度在 Python 计算；未配置嵌入服务时走 16 维确定性 mock（offline 可用）。
-- 严格按 email 隔离，绝不跨用户检索。

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS semantic_index (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT NOT NULL,
    source_type TEXT NOT NULL,          -- reflection / formation_memory / examen / journal / ...
    source_id   TEXT NOT NULL,          -- 源记录键（文本，兼容 uuid/serial/varchar；缺省取内容哈希）
    content     TEXT NOT NULL,
    embedding   JSONB,                  -- list[float]；未配置嵌入时为 NULL
    model       TEXT DEFAULT '',
    dim         INT  DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE(email, source_type, source_id)
);

CREATE INDEX IF NOT EXISTS idx_semantic_index_email
    ON semantic_index(email, source_type, created_at DESC);
