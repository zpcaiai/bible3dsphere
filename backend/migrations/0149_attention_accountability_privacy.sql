-- 0149_attention_accountability_privacy.sql — Attention Stewardship Batch 6
-- Email-keyed TEXT ids match the existing attention_* tables.

CREATE TABLE IF NOT EXISTS attention_privacy_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL UNIQUE,
    default_partner_visibility TEXT NOT NULL DEFAULT 'status_only',
    default_group_visibility TEXT NOT NULL DEFAULT 'status_only',
    default_challenge_visibility TEXT NOT NULL DEFAULT 'status_only',
    share_scores_with_partners BOOLEAN NOT NULL DEFAULT false,
    share_scores_with_groups BOOLEAN NOT NULL DEFAULT false,
    share_weekly_report_summary BOOLEAN NOT NULL DEFAULT false,
    share_warfare_plan_progress BOOLEAN NOT NULL DEFAULT false,
    share_prayer_requests BOOLEAN NOT NULL DEFAULT true,
    hide_sensitive_categories TEXT[] NOT NULL DEFAULT ARRAY[
        'lust','financial_anxiety','family_conflict','mental_health',
        'trauma','addiction','work_conflict','identity_shame'
    ],
    allow_partner_reminders BOOLEAN NOT NULL DEFAULT true,
    allow_group_challenge_reminders BOOLEAN NOT NULL DEFAULT true,
    require_preview_before_sharing BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS attention_accountability_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requester_user_id TEXT NOT NULL,
    partner_user_id TEXT NOT NULL,
    pair_key TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    direction_label TEXT,
    requester_message TEXT,
    requester_permissions JSONB NOT NULL DEFAULT '{}'::jsonb,
    partner_permissions JSONB NOT NULL DEFAULT '{}'::jsonb,
    accepted_at TIMESTAMPTZ,
    declined_at TIMESTAMPTZ,
    paused_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (requester_user_id <> partner_user_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uniq_attention_accountability_pair_active
ON attention_accountability_relationships(pair_key)
WHERE status IN ('pending', 'active', 'paused');

CREATE INDEX IF NOT EXISTS idx_attention_accountability_requester
ON attention_accountability_relationships(requester_user_id, status);

CREATE INDEX IF NOT EXISTS idx_attention_accountability_partner
ON attention_accountability_relationships(partner_user_id, status);

CREATE TABLE IF NOT EXISTS attention_share_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    target_user_id TEXT,
    target_group_id UUID,
    source_type TEXT NOT NULL,
    source_id TEXT,
    title TEXT NOT NULL,
    summary TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    visibility_level TEXT NOT NULL DEFAULT 'summary',
    sensitive_redactions TEXT[] NOT NULL DEFAULT '{}',
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_attention_share_owner
ON attention_share_snapshots(owner_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_attention_share_target_user
ON attention_share_snapshots(target_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_attention_share_target_group
ON attention_share_snapshots(target_group_id, created_at DESC);

CREATE TABLE IF NOT EXISTS attention_prayer_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id TEXT NOT NULL,
    target_user_id TEXT,
    target_group_id UUID,
    title TEXT NOT NULL,
    body TEXT,
    category TEXT,
    visibility_level TEXT NOT NULL DEFAULT 'summary',
    is_sensitive BOOLEAN NOT NULL DEFAULT false,
    status TEXT NOT NULL DEFAULT 'open',
    answered_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_attention_prayer_owner
ON attention_prayer_requests(owner_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_attention_prayer_target_user
ON attention_prayer_requests(target_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_attention_prayer_target_group
ON attention_prayer_requests(target_group_id, created_at DESC);

CREATE TABLE IF NOT EXISTS attention_prayer_marks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prayer_request_id UUID NOT NULL REFERENCES attention_prayer_requests(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(prayer_request_id, user_id)
);

CREATE TABLE IF NOT EXISTS attention_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    group_type TEXT NOT NULL DEFAULT 'private',
    invite_code TEXT UNIQUE,
    invite_enabled BOOLEAN NOT NULL DEFAULT true,
    default_member_visibility TEXT NOT NULL DEFAULT 'status_only',
    guidelines TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_attention_groups_owner
ON attention_groups(owner_user_id, status);

CREATE TABLE IF NOT EXISTS attention_group_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES attention_groups(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    status TEXT NOT NULL DEFAULT 'active',
    visibility_level TEXT NOT NULL DEFAULT 'status_only',
    permissions JSONB NOT NULL DEFAULT '{}'::jsonb,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    left_at TIMESTAMPTZ,
    removed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(group_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_attention_group_members_group
ON attention_group_members(group_id, status);
CREATE INDEX IF NOT EXISTS idx_attention_group_members_user
ON attention_group_members(user_id, status);

CREATE TABLE IF NOT EXISTS attention_group_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES attention_groups(id) ON DELETE CASCADE,
    invited_by_user_id TEXT NOT NULL,
    invited_user_id TEXT,
    invited_email TEXT,
    invite_code TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    message TEXT,
    expires_at TIMESTAMPTZ,
    accepted_at TIMESTAMPTZ,
    declined_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_attention_group_invitations_group
ON attention_group_invitations(group_id, status);
CREATE INDEX IF NOT EXISTS idx_attention_group_invitations_user
ON attention_group_invitations(invited_user_id, status);

CREATE TABLE IF NOT EXISTS attention_group_challenges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES attention_groups(id) ON DELETE CASCADE,
    created_by_user_id TEXT NOT NULL,
    template_key TEXT,
    title TEXT NOT NULL,
    description TEXT,
    challenge_type TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    target_days INTEGER,
    target_minutes INTEGER,
    checkin_prompt TEXT,
    privacy_mode TEXT NOT NULL DEFAULT 'status_only',
    allow_comments BOOLEAN NOT NULL DEFAULT false,
    allow_prayer_requests BOOLEAN NOT NULL DEFAULT true,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_attention_group_challenges_group
ON attention_group_challenges(group_id, status, start_date DESC);

CREATE TABLE IF NOT EXISTS attention_challenge_participations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    challenge_id UUID NOT NULL REFERENCES attention_group_challenges(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    left_at TIMESTAMPTZ,
    personal_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(challenge_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_attention_challenge_participations_challenge
ON attention_challenge_participations(challenge_id, status);
CREATE INDEX IF NOT EXISTS idx_attention_challenge_participations_user
ON attention_challenge_participations(user_id, status);

CREATE TABLE IF NOT EXISTS attention_challenge_checkins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    challenge_id UUID NOT NULL REFERENCES attention_group_challenges(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    checkin_date DATE NOT NULL,
    completed BOOLEAN NOT NULL DEFAULT false,
    value_minutes INTEGER,
    value_count INTEGER,
    reflection TEXT,
    prayer_request_id UUID REFERENCES attention_prayer_requests(id) ON DELETE SET NULL,
    visibility_level TEXT NOT NULL DEFAULT 'status_only',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(challenge_id, user_id, checkin_date)
);

CREATE INDEX IF NOT EXISTS idx_attention_challenge_checkins_challenge_date
ON attention_challenge_checkins(challenge_id, checkin_date DESC);
CREATE INDEX IF NOT EXISTS idx_attention_challenge_checkins_user_date
ON attention_challenge_checkins(user_id, checkin_date DESC);

DROP TRIGGER IF EXISTS trg_attention_privacy_settings_updated_at ON attention_privacy_settings;
CREATE TRIGGER trg_attention_privacy_settings_updated_at
BEFORE UPDATE ON attention_privacy_settings
FOR EACH ROW EXECUTE FUNCTION set_attention_updated_at();

DROP TRIGGER IF EXISTS trg_attention_accountability_relationships_updated_at ON attention_accountability_relationships;
CREATE TRIGGER trg_attention_accountability_relationships_updated_at
BEFORE UPDATE ON attention_accountability_relationships
FOR EACH ROW EXECUTE FUNCTION set_attention_updated_at();

DROP TRIGGER IF EXISTS trg_attention_share_snapshots_updated_at ON attention_share_snapshots;
CREATE TRIGGER trg_attention_share_snapshots_updated_at
BEFORE UPDATE ON attention_share_snapshots
FOR EACH ROW EXECUTE FUNCTION set_attention_updated_at();

DROP TRIGGER IF EXISTS trg_attention_prayer_requests_updated_at ON attention_prayer_requests;
CREATE TRIGGER trg_attention_prayer_requests_updated_at
BEFORE UPDATE ON attention_prayer_requests
FOR EACH ROW EXECUTE FUNCTION set_attention_updated_at();

DROP TRIGGER IF EXISTS trg_attention_groups_updated_at ON attention_groups;
CREATE TRIGGER trg_attention_groups_updated_at
BEFORE UPDATE ON attention_groups
FOR EACH ROW EXECUTE FUNCTION set_attention_updated_at();

DROP TRIGGER IF EXISTS trg_attention_group_members_updated_at ON attention_group_members;
CREATE TRIGGER trg_attention_group_members_updated_at
BEFORE UPDATE ON attention_group_members
FOR EACH ROW EXECUTE FUNCTION set_attention_updated_at();

DROP TRIGGER IF EXISTS trg_attention_group_challenges_updated_at ON attention_group_challenges;
CREATE TRIGGER trg_attention_group_challenges_updated_at
BEFORE UPDATE ON attention_group_challenges
FOR EACH ROW EXECUTE FUNCTION set_attention_updated_at();

DROP TRIGGER IF EXISTS trg_attention_challenge_participations_updated_at ON attention_challenge_participations;
CREATE TRIGGER trg_attention_challenge_participations_updated_at
BEFORE UPDATE ON attention_challenge_participations
FOR EACH ROW EXECUTE FUNCTION set_attention_updated_at();

DROP TRIGGER IF EXISTS trg_attention_challenge_checkins_updated_at ON attention_challenge_checkins;
CREATE TRIGGER trg_attention_challenge_checkins_updated_at
BEFORE UPDATE ON attention_challenge_checkins
FOR EACH ROW EXECUTE FUNCTION set_attention_updated_at();
