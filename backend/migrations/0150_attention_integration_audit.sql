-- 0150_attention_integration_audit.sql — Attention Stewardship Batch 7
-- Release integration indexes and privacy-preserving admin audit metadata.

CREATE INDEX IF NOT EXISTS idx_attention_entries_date_category
ON attention_entries(entry_date DESC, category);

CREATE INDEX IF NOT EXISTS idx_attention_focus_sessions_started
ON attention_focus_sessions(started_at DESC);

CREATE INDEX IF NOT EXISTS idx_attention_reviews_date
ON attention_reviews(review_date DESC);

CREATE INDEX IF NOT EXISTS idx_attention_ai_diagnoses_date_safety
ON attention_ai_diagnoses(diagnosis_date DESC, safety_level);

CREATE INDEX IF NOT EXISTS idx_attention_weekly_reports_week_status
ON attention_weekly_reports(week_start DESC, week_end DESC, status);

CREATE INDEX IF NOT EXISTS idx_attention_prayer_requests_status
ON attention_prayer_requests(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_attention_share_revoked_target_user
ON attention_share_snapshots(target_user_id, revoked_at, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_attention_challenge_checkins_user_today
ON attention_challenge_checkins(user_id, checkin_date DESC);

CREATE TABLE IF NOT EXISTS attention_admin_audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL DEFAULT 'attention',
    target_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_attention_admin_audit_events_created
ON attention_admin_audit_events(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_attention_admin_audit_events_admin
ON attention_admin_audit_events(admin_user_id, created_at DESC);
