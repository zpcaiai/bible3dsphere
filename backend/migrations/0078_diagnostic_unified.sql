-- 0078_diagnostic_unified.sql
-- 统一诊断读层（适配器模式）：既有 checkup/gospel/disciple/worldview 引擎在产出后，
-- 额外写入统一的 diagnostic_sessions + diagnostic_findings，提供一个可查询的诊断历史 / 发现面。
-- 不替换任何既有表与引擎；email 为用户键；UUID 主键。

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS diagnostic_sessions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT NOT NULL,
    source_engine TEXT NOT NULL,          -- gospel / checkup / disciple / worldview / ...
    source_id     TEXT,                   -- 对应领域记录主键（文本兼容）
    session_type  TEXT DEFAULT 'diagnosis',
    primary_theme TEXT,
    risk_level    TEXT DEFAULT 'low',     -- low / medium / high / critical
    summary       TEXT,
    raw           JSONB DEFAULT '{}',
    created_at    TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_diag_sessions_email  ON diagnostic_sessions(email, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_diag_sessions_engine ON diagnostic_sessions(email, source_engine, created_at DESC);

CREATE TABLE IF NOT EXISTS diagnostic_findings (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id        UUID NOT NULL REFERENCES diagnostic_sessions(id) ON DELETE CASCADE,
    email             TEXT NOT NULL,
    category          TEXT NOT NULL,        -- identity / trust / relationship_with_god / ...
    finding_type      TEXT,                 -- false_belief / sin_pattern / spiritual_dryness / ...
    title             TEXT NOT NULL,
    description       TEXT,
    possible_root     TEXT,
    gospel_truth      TEXT,
    scripture_anchors JSONB DEFAULT '[]',
    severity          INT CHECK (severity BETWEEN 1 AND 5),
    confidence        NUMERIC(5,4),
    risk_level        TEXT DEFAULT 'low',
    created_at        TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_diag_findings_email    ON diagnostic_findings(email, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_diag_findings_session  ON diagnostic_findings(session_id);
CREATE INDEX IF NOT EXISTS idx_diag_findings_category ON diagnostic_findings(email, category);
