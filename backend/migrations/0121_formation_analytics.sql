-- Migration 0121: 成长分析 Formation Analytics（B11）
-- 把跨模块活动聚合成谦卑、恩典优先、不排名的成长指示;恩典证据、过载信号、月度报告。
-- 指标是反思镜子,不是属灵成绩。email 标识用户。

CREATE TABLE IF NOT EXISTS formation_metric_snapshots (
    id            VARCHAR(64)  PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    snapshot_date DATE         DEFAULT CURRENT_DATE,
    period_type   VARCHAR(12)  DEFAULT 'weekly',
    summary       TEXT         DEFAULT '',
    metrics       JSONB        DEFAULT '{}'::jsonb,
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE formation_metric_snapshots
    ADD COLUMN IF NOT EXISTS id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS email VARCHAR(255),
    ADD COLUMN IF NOT EXISTS snapshot_date DATE DEFAULT CURRENT_DATE,
    ADD COLUMN IF NOT EXISTS period_type VARCHAR(12) DEFAULT 'weekly',
    ADD COLUMN IF NOT EXISTS summary TEXT DEFAULT '',
    ADD COLUMN IF NOT EXISTS metrics JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX IF NOT EXISTS idx_metric_snapshots_email ON formation_metric_snapshots (email, snapshot_date DESC);

CREATE TABLE IF NOT EXISTS formation_grace_evidence (
    id            VARCHAR(64)  PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    evidence_date DATE         DEFAULT CURRENT_DATE,
    evidence_type VARCHAR(30)  DEFAULT 'other',
    title         VARCHAR(200) NOT NULL,
    description   TEXT         DEFAULT '',
    source_module VARCHAR(40)  DEFAULT '',
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE formation_grace_evidence
    ADD COLUMN IF NOT EXISTS id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS email VARCHAR(255),
    ADD COLUMN IF NOT EXISTS evidence_date DATE DEFAULT CURRENT_DATE,
    ADD COLUMN IF NOT EXISTS evidence_type VARCHAR(30) DEFAULT 'other',
    ADD COLUMN IF NOT EXISTS title VARCHAR(200),
    ADD COLUMN IF NOT EXISTS description TEXT DEFAULT '',
    ADD COLUMN IF NOT EXISTS source_module VARCHAR(40) DEFAULT '',
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX IF NOT EXISTS idx_grace_evidence_email ON formation_grace_evidence (email, evidence_date DESC);

CREATE TABLE IF NOT EXISTS formation_overload_signals (
    id            VARCHAR(64)  PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    signal_date   DATE         DEFAULT CURRENT_DATE,
    signal_type   VARCHAR(30)  DEFAULT 'other',
    severity      VARCHAR(12)  DEFAULT 'low',
    evidence      JSONB        DEFAULT '[]'::jsonb,
    recommended_response TEXT  DEFAULT '',
    status        VARCHAR(12)  DEFAULT 'active',
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE formation_overload_signals
    ADD COLUMN IF NOT EXISTS id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS email VARCHAR(255),
    ADD COLUMN IF NOT EXISTS signal_date DATE DEFAULT CURRENT_DATE,
    ADD COLUMN IF NOT EXISTS signal_type VARCHAR(30) DEFAULT 'other',
    ADD COLUMN IF NOT EXISTS severity VARCHAR(12) DEFAULT 'low',
    ADD COLUMN IF NOT EXISTS evidence JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS recommended_response TEXT DEFAULT '',
    ADD COLUMN IF NOT EXISTS status VARCHAR(12) DEFAULT 'active',
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX IF NOT EXISTS idx_overload_email ON formation_overload_signals (email, status);

CREATE TABLE IF NOT EXISTS formation_reports (
    id            VARCHAR(64)  PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    report_type   VARCHAR(16)  DEFAULT 'monthly',
    period_start  DATE,
    period_end    DATE,
    title         VARCHAR(160) DEFAULT '',
    summary       TEXT         DEFAULT '',
    sections      JSONB        DEFAULT '[]'::jsonb,
    recommendations JSONB      DEFAULT '[]'::jsonb,
    visibility_scope VARCHAR(16) DEFAULT 'private',
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE formation_reports
    ADD COLUMN IF NOT EXISTS id VARCHAR(64),
    ADD COLUMN IF NOT EXISTS email VARCHAR(255),
    ADD COLUMN IF NOT EXISTS report_type VARCHAR(16) DEFAULT 'monthly',
    ADD COLUMN IF NOT EXISTS period_start DATE,
    ADD COLUMN IF NOT EXISTS period_end DATE,
    ADD COLUMN IF NOT EXISTS title VARCHAR(160) DEFAULT '',
    ADD COLUMN IF NOT EXISTS summary TEXT DEFAULT '',
    ADD COLUMN IF NOT EXISTS sections JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS recommendations JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS visibility_scope VARCHAR(16) DEFAULT 'private',
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX IF NOT EXISTS idx_formation_reports_email ON formation_reports (email, created_at DESC);
