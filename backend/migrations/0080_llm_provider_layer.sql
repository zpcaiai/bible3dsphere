-- 0076_llm_provider_layer.sql
-- Advanced Batch · Module 1 — Real LLM Provider Layer (+ shared audit_logs)
-- (renumbered to 0080 to avoid a concurrent-session collision at 0076/0077;
--  theological_review_logs is owned by 0075 and reused, not redefined.)
-- Idempotent. Keyed by email like the rest of the repo. agent_runs (0037) and
-- review_logs (0069) already exist and are reused; this migration only adds the
-- provider/prompt/safety/audit tables they reference.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Versioned, swappable prompt templates per (agent, skill) -------------------
CREATE TABLE IF NOT EXISTS llm_prompt_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name      TEXT NOT NULL,
    skill_name      TEXT NOT NULL,
    version         TEXT NOT NULL,
    system_prompt   TEXT NOT NULL,
    developer_prompt TEXT,
    output_schema   JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE (agent_name, skill_name, version)
);
CREATE INDEX IF NOT EXISTS idx_llm_prompt_templates_active
    ON llm_prompt_templates(agent_name, skill_name) WHERE is_active = TRUE;

-- Provider observability (model / latency / tokens / error) is recorded on
-- agent_runs by the concurrent migration 0074_agent_runs_observability.sql
-- (columns model_name / latency_ms / token_usage / error_message / skill_name /
-- prompt_version). We REUSE those per-run columns instead of a separate
-- llm_provider_events table. (Reconciled onto the concurrent design.)

-- Theological safety gate: theological_review_logs is created by migration
-- 0075_theological_review_logs.sql (concurrent line of work). We REUSE that
-- table (columns: content_type / content_excerpt / review_status /
-- detected_issues / reviewer ...) instead of defining a divergent one here.

-- Generic, append-only audit trail (shared by Care Dashboard + future RLS) ---
CREATE TABLE IF NOT EXISTS audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_email     TEXT,                          -- who performed the action
    subject_email   TEXT,                          -- whose data was touched (nullable)
    action          TEXT NOT NULL,                 -- e.g. care_dashboard.view
    resource_type   TEXT,
    resource_id     TEXT,
    church_id       INTEGER,
    detail          JSONB DEFAULT '{}'::jsonb,
    ip              TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor ON audit_logs(actor_email, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_subject ON audit_logs(subject_email, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action, created_at DESC);
