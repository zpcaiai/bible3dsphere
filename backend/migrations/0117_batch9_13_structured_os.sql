-- Migration 0117: Structured backend for B9-B13 formation modules.
-- Adds concrete psycopg2/raw-SQL persistence behind /api/formation-advanced.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'doctrine_learning_paths' AND column_name = 'path_key'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'doctrine_learning_paths' AND column_name = 'email'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'doctrine_path_templates'
    ) THEN
        ALTER TABLE doctrine_learning_paths RENAME TO doctrine_path_templates;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS doctrine_learning_paths (
    id                 VARCHAR(64) PRIMARY KEY,
    email              VARCHAR(255) NOT NULL,
    topic_key          VARCHAR(80) NOT NULL,
    tradition_context  VARCHAR(120) DEFAULT '',
    duration_days      INT DEFAULT 30,
    goals              JSONB DEFAULT '[]'::jsonb,
    lessons            JSONB DEFAULT '[]'::jsonb,
    status             VARCHAR(20) DEFAULT 'active',
    created_at         TIMESTAMPTZ DEFAULT now(),
    updated_at         TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_doctrine_paths_email ON doctrine_learning_paths (email, status, created_at DESC);

CREATE TABLE IF NOT EXISTS doctrine_lesson_progress (
    id          VARCHAR(64) PRIMARY KEY,
    path_id     VARCHAR(64) NOT NULL,
    email       VARCHAR(255) NOT NULL,
    lesson_key  VARCHAR(120) NOT NULL,
    status      VARCHAR(20) DEFAULT 'completed',
    reflection  TEXT DEFAULT '',
    created_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_doctrine_progress_path ON doctrine_lesson_progress (path_id, created_at DESC);

CREATE TABLE IF NOT EXISTS apologetics_dialogues (
    id               VARCHAR(64) PRIMARY KEY,
    email            VARCHAR(255) NOT NULL,
    topic_key        VARCHAR(80) DEFAULT 'general',
    question         TEXT NOT NULL,
    audience_context TEXT DEFAULT '',
    response         JSONB DEFAULT '{}'::jsonb,
    created_at       TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_apologetics_dialogues_email ON apologetics_dialogues (email, created_at DESC);

CREATE TABLE IF NOT EXISTS ai_formation_profiles (
    email                  VARCHAR(255) PRIMARY KEY,
    season                 VARCHAR(80) DEFAULT 'stable_growth',
    consent_ai_tutor       BOOLEAN DEFAULT TRUE,
    consent_mentor_summary BOOLEAN DEFAULT FALSE,
    formation_focuses      JSONB DEFAULT '[]'::jsonb,
    boundaries             JSONB DEFAULT '[]'::jsonb,
    created_at             TIMESTAMPTZ DEFAULT now(),
    updated_at             TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ai_formation_recommendations (
    id              VARCHAR(64) PRIMARY KEY,
    email           VARCHAR(255) NOT NULL,
    context_text    TEXT DEFAULT '',
    recommendations JSONB DEFAULT '[]'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ai_recommendations_email ON ai_formation_recommendations (email, created_at DESC);

CREATE TABLE IF NOT EXISTS ai_tutor_conversations (
    id                VARCHAR(64) PRIMARY KEY,
    email             VARCHAR(255) NOT NULL,
    conversation_type VARCHAR(40) DEFAULT 'formation',
    user_message      TEXT NOT NULL,
    assistant_reply   TEXT DEFAULT '',
    safety_flags      JSONB DEFAULT '{}'::jsonb,
    created_at        TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ai_tutor_conversations_email ON ai_tutor_conversations (email, created_at DESC);

CREATE TABLE IF NOT EXISTS formation_metric_snapshots (
    id             VARCHAR(64) PRIMARY KEY,
    email          VARCHAR(255) NOT NULL,
    period_key     VARCHAR(40) DEFAULT 'week',
    metrics        JSONB DEFAULT '{}'::jsonb,
    grace_evidence JSONB DEFAULT '[]'::jsonb,
    created_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_formation_metrics_email ON formation_metric_snapshots (email, created_at DESC);

CREATE TABLE IF NOT EXISTS formation_review_reports (
    id           VARCHAR(64) PRIMARY KEY,
    email        VARCHAR(255) NOT NULL,
    title        VARCHAR(200) DEFAULT 'Formation Review',
    report_scope VARCHAR(40) DEFAULT 'private',
    content      JSONB DEFAULT '{}'::jsonb,
    mentor_safe  BOOLEAN DEFAULT FALSE,
    created_at   TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_formation_reports_email ON formation_review_reports (email, created_at DESC);

CREATE TABLE IF NOT EXISTS formation_integrity_audits (
    id         VARCHAR(64) PRIMARY KEY,
    email      VARCHAR(255) NOT NULL,
    audit_type VARCHAR(40) DEFAULT 'privacy',
    status     VARCHAR(40) DEFAULT 'passed',
    findings   JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_formation_integrity_email ON formation_integrity_audits (email, created_at DESC);

CREATE TABLE IF NOT EXISTS formation_tenants (
    id          VARCHAR(64) PRIMARY KEY,
    name        VARCHAR(200) NOT NULL,
    tenant_type VARCHAR(40) DEFAULT 'church',
    owner_email VARCHAR(255) NOT NULL,
    status      VARCHAR(20) DEFAULT 'active',
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_formation_tenants_owner ON formation_tenants (owner_email, status);

CREATE TABLE IF NOT EXISTS formation_tenant_members (
    id         VARCHAR(64) PRIMARY KEY,
    tenant_id  VARCHAR(64) NOT NULL,
    email      VARCHAR(255) NOT NULL,
    role       VARCHAR(40) DEFAULT 'member',
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_formation_tenant_members_email ON formation_tenant_members (email, tenant_id);
CREATE INDEX IF NOT EXISTS idx_formation_tenant_members_tenant ON formation_tenant_members (tenant_id, role);

CREATE TABLE IF NOT EXISTS formation_subscriptions (
    id             VARCHAR(64) PRIMARY KEY,
    email          VARCHAR(255) NOT NULL,
    tenant_id      VARCHAR(64) DEFAULT '',
    plan_key       VARCHAR(40) DEFAULT 'personal',
    billing_status VARCHAR(40) DEFAULT 'trialing',
    created_at     TIMESTAMPTZ DEFAULT now(),
    updated_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_formation_subscriptions_email ON formation_subscriptions (email, created_at DESC);

CREATE TABLE IF NOT EXISTS formation_moderation_cases (
    id             VARCHAR(64) PRIMARY KEY,
    tenant_id      VARCHAR(64) DEFAULT '',
    reporter_email VARCHAR(255) NOT NULL,
    case_type      VARCHAR(40) DEFAULT 'content',
    severity       VARCHAR(20) DEFAULT 'low',
    summary        TEXT DEFAULT '',
    status         VARCHAR(40) DEFAULT 'open',
    created_at     TIMESTAMPTZ DEFAULT now(),
    updated_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_formation_moderation_tenant ON formation_moderation_cases (tenant_id, status, created_at DESC);

CREATE TABLE IF NOT EXISTS master_build_runs (
    id         VARCHAR(64) PRIMARY KEY,
    email      VARCHAR(255) NOT NULL,
    run_type   VARCHAR(80) DEFAULT 'full_stack_validation',
    status     VARCHAR(40) DEFAULT 'planned',
    evidence   JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_master_build_runs_email ON master_build_runs (email, created_at DESC);

CREATE TABLE IF NOT EXISTS master_acceptance_checks (
    id         VARCHAR(64) PRIMARY KEY,
    email      VARCHAR(255) NOT NULL,
    batch      INT NOT NULL CHECK (batch BETWEEN 1 AND 13),
    check_key  VARCHAR(120) NOT NULL,
    status     VARCHAR(40) DEFAULT 'passed',
    evidence   JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_master_acceptance_email ON master_acceptance_checks (email, batch, created_at DESC);
