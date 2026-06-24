-- 0077_care_dashboard.sql
-- Advanced Batch · Module 3 — Group Leader Care Dashboard
-- Idempotent. "Group" maps to the existing church model (churches / church_members).
-- Care signals are CARE prompts, never private journal text or "spiritual scores".
-- A signal is only leader/pastor-visible when the member consented OR a crisis
-- escalation explicitly authorised it.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS care_signals (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT NOT NULL,                  -- member the signal is about
    church_id     INTEGER,                        -- group/church scope (churches.id)
    signal_type   TEXT NOT NULL,                  -- prayer_request|needs_encouragement|
                                                  -- isolation|inactivity|risk_trend_up|
                                                  -- needs_1on1|crisis_linked
    signal_level  TEXT NOT NULL DEFAULT 'low',    -- low|medium|high|critical
    title         TEXT NOT NULL,
    summary       TEXT NOT NULL,                  -- authorised summary ONLY (no raw logs)
    suggested_action TEXT,
    source_type   TEXT,                           -- prayer_request|crisis_event|inactivity|...
    source_id     TEXT,
    consent_share BOOLEAN DEFAULT FALSE,          -- member authorised sharing this summary
    visible_to_group_leader BOOLEAN DEFAULT FALSE,
    visible_to_pastor       BOOLEAN DEFAULT FALSE,
    requires_followup BOOLEAN DEFAULT FALSE,
    resolved      BOOLEAN DEFAULT FALSE,
    resolved_at   TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_care_signals_church ON care_signals(church_id, resolved, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_care_signals_email ON care_signals(email, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_care_signals_level ON care_signals(signal_level) WHERE resolved = FALSE;

CREATE TABLE IF NOT EXISTS care_actions (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    care_signal_id UUID NOT NULL REFERENCES care_signals(id) ON DELETE CASCADE,
    actor_email    TEXT NOT NULL,                 -- leader/pastor taking the action
    target_email   TEXT NOT NULL,                 -- member being cared for
    church_id      INTEGER,
    action_type    TEXT NOT NULL,                 -- pray|message|meet_1on1|refer_to_pastor|follow_up
    action_note    TEXT,
    followup_date  DATE,
    completed      BOOLEAN DEFAULT FALSE,
    completed_at   TIMESTAMPTZ,
    created_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_care_actions_signal ON care_actions(care_signal_id);
CREATE INDEX IF NOT EXISTS idx_care_actions_actor ON care_actions(actor_email, created_at DESC);
