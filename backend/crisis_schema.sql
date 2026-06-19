-- Crisis Care (危机守护) persistence tables.
-- Names follow the Crisis Care subsystem spec. id/user_id are TEXT to match this
-- app's current email/session identity model and frontend-generated local IDs.
--
-- Privacy/compliance notes:
--   * triggering_message is nullable and may be redacted; never store more
--     sensitive content than needed. Users can delete their crisis records.
--   * Guardian notifications require explicit, revocable consent (consent_enabled)
--     and every notify action is recorded in crisis_events.escalation_actions.

-- ── Crisis audit/event log ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crisis_events (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  risk_level TEXT NOT NULL,                          -- green | yellow | orange | red
  risk_types JSONB NOT NULL DEFAULT '[]'::jsonb,
  evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
  triggering_message TEXT,                           -- nullable / redactable
  system_response TEXT DEFAULT '',
  workflow_started TEXT,                             -- normal_care | yellow_support | orange_safety_plan | red_emergency
  region_code TEXT,
  escalation_actions JSONB NOT NULL DEFAULT '[]'::jsonb,
  guardian_notified BOOLEAN DEFAULT FALSE,
  user_acknowledged BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crisis_events_user_time
  ON crisis_events (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_crisis_events_user_level
  ON crisis_events (user_id, risk_level, created_at DESC);

-- ── Personal safety plan (one active per user; history kept) ────────────────
CREATE TABLE IF NOT EXISTS crisis_safety_plans (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  warning_signs JSONB NOT NULL DEFAULT '[]'::jsonb,
  internal_coping_strategies JSONB NOT NULL DEFAULT '[]'::jsonb,
  safe_people JSONB NOT NULL DEFAULT '[]'::jsonb,
  safe_places JSONB NOT NULL DEFAULT '[]'::jsonb,
  professional_resources JSONB NOT NULL DEFAULT '[]'::jsonb,
  means_restriction_steps JSONB NOT NULL DEFAULT '[]'::jsonb,
  spiritual_anchors JSONB NOT NULL DEFAULT '[]'::jsonb,
  emergency_message_template TEXT DEFAULT '',
  region_code TEXT,
  status TEXT NOT NULL DEFAULT 'active',             -- active | archived
  last_reviewed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crisis_safety_plans_user
  ON crisis_safety_plans (user_id, status, updated_at DESC);

-- ── Guardian network (human emergency / spiritual / clinical contacts) ──────
CREATE TABLE IF NOT EXISTS crisis_guardian_contacts (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  name TEXT NOT NULL,
  relationship TEXT DEFAULT '',
  role TEXT NOT NULL DEFAULT 'friend'
    CHECK (role IN ('family','friend','pastor','small_group_leader',
                    'counselor','doctor','peer_companion')),
  phone TEXT DEFAULT '',
  email TEXT DEFAULT '',
  notify_methods JSONB NOT NULL DEFAULT '[]'::jsonb, -- ['sms','email','wechat','app_push']
  permission_level TEXT NOT NULL DEFAULT 'orange'
    CHECK (permission_level IN ('yellow','orange','red')),
  consent_enabled BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crisis_guardians_user
  ON crisis_guardian_contacts (user_id, created_at DESC);

-- ── Post-crisis follow-up timeline (24h / 72h / 7d / 30d) ───────────────────
CREATE TABLE IF NOT EXISTS crisis_followups (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  event_id TEXT,                                     -- references crisis_events.id (soft)
  phase TEXT NOT NULL CHECK (phase IN ('24h','72h','7d','30d')),
  tasks JSONB NOT NULL DEFAULT '[]'::jsonb,
  completed_task_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  due_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'pending',            -- pending | done | skipped
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crisis_followups_user_phase
  ON crisis_followups (user_id, status, due_at);

-- ── Caregiver collaboration: consent-based read-only sharing ────────────────
-- A user (user_id = sharer email) explicitly grants a pastor/counselor
-- (caregiver_email, matched against their login email) read access to a
-- limited scope of crisis data. Revocable; every caregiver view is timestamped.
CREATE TABLE IF NOT EXISTS crisis_care_shares (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  caregiver_email TEXT NOT NULL,
  caregiver_name TEXT DEFAULT '',
  caregiver_role TEXT NOT NULL DEFAULT 'pastor'
    CHECK (caregiver_role IN ('pastor','counselor','small_group_leader')),
  scope JSONB NOT NULL DEFAULT '["status","safety_plan","events"]'::jsonb,
  status TEXT NOT NULL DEFAULT 'active',
  last_viewed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_crisis_shares_user
  ON crisis_care_shares (user_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_crisis_shares_caregiver
  ON crisis_care_shares (caregiver_email, status);


-- ── Caregiver view audit (who viewed a share, and when) ─────────────────────
CREATE TABLE IF NOT EXISTS crisis_share_views (
  id TEXT PRIMARY KEY,
  share_id TEXT NOT NULL,
  user_id TEXT NOT NULL,            -- sharer
  caregiver_email TEXT NOT NULL,
  viewed_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_crisis_share_views_share ON crisis_share_views (share_id, viewed_at DESC);
CREATE INDEX IF NOT EXISTS idx_crisis_share_views_user ON crisis_share_views (user_id, viewed_at DESC);

ALTER TABLE crisis_care_shares ADD COLUMN IF NOT EXISTS contact_phone TEXT DEFAULT '';

ALTER TABLE crisis_care_shares ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
