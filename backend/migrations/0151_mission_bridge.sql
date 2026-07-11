-- MissionBridge MVP: safeguarding, consent, versioned programs and participant journey.
CREATE TABLE IF NOT EXISTS safeguarding_policy_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), version TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL, policy JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL DEFAULT 'active', published_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mission_bridge_consents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id TEXT NOT NULL DEFAULT 'public',
  user_id TEXT NOT NULL, consent_type TEXT NOT NULL,
  granted BOOLEAN NOT NULL DEFAULT FALSE, policy_version TEXT NOT NULL,
  granted_at TIMESTAMPTZ, withdrawn_at TIMESTAMPTZ, updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, user_id, consent_type)
);

CREATE TABLE IF NOT EXISTS safeguarding_acknowledgements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id TEXT NOT NULL DEFAULT 'public',
  user_id TEXT NOT NULL, policy_version_id UUID NOT NULL REFERENCES safeguarding_policy_versions(id),
  acknowledged_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(tenant_id,user_id,policy_version_id)
);

CREATE TABLE IF NOT EXISTS mission_bridge_data_access_grants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id TEXT NOT NULL,
  grantee_user_id TEXT NOT NULL, participant_id TEXT NOT NULL,
  permission TEXT NOT NULL, purpose TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active',
  granted_by TEXT NOT NULL, expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mission_bridge_program_definitions (
  id TEXT PRIMARY KEY, group_type TEXT NOT NULL, title TEXT NOT NULL,
  description TEXT NOT NULL, active_version TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'published',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mission_bridge_program_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), program_id TEXT NOT NULL REFERENCES mission_bridge_program_definitions(id),
  version TEXT NOT NULL, definition JSONB NOT NULL, safeguarding_profile JSONB NOT NULL,
  published_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(program_id, version)
);

CREATE TABLE IF NOT EXISTS mission_bridge_enrollments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id TEXT NOT NULL DEFAULT 'public',
  user_id TEXT NOT NULL, program_id TEXT NOT NULL, program_version TEXT NOT NULL,
  pathway TEXT NOT NULL DEFAULT 'standard', status TEXT NOT NULL DEFAULT 'active',
  current_step INTEGER NOT NULL DEFAULT 0, participant_goal TEXT,
  enrolled_at TIMESTAMPTZ NOT NULL DEFAULT now(), exited_at TIMESTAMPTZ,
  UNIQUE(tenant_id, user_id, program_id)
);

CREATE TABLE IF NOT EXISTS mission_bridge_checkins (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), enrollment_id UUID NOT NULL REFERENCES mission_bridge_enrollments(id),
  user_id TEXT NOT NULL, wellbeing SMALLINT NOT NULL CHECK (wellbeing BETWEEN 1 AND 5),
  reflection TEXT, needs_support BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mission_bridge_content_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), program_id TEXT NOT NULL,
  title TEXT NOT NULL, content_type TEXT NOT NULL, language TEXT NOT NULL DEFAULT 'zh-CN',
  body JSONB NOT NULL DEFAULT '{}'::jsonb, theology_status TEXT NOT NULL DEFAULT 'approved',
  safeguarding_status TEXT NOT NULL DEFAULT 'approved', published BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS incident_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id TEXT NOT NULL DEFAULT 'public',
  participant_id TEXT, reporter_user_id TEXT NOT NULL, risk_level TEXT NOT NULL CHECK (risk_level IN ('L0','L1','L2','L3')),
  category TEXT NOT NULL, summary TEXT NOT NULL, immediate_danger BOOLEAN NOT NULL DEFAULT FALSE,
  location_scope TEXT NOT NULL DEFAULT 'undisclosed', status TEXT NOT NULL DEFAULT 'open',
  assigned_to TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS escalation_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), incident_id UUID NOT NULL REFERENCES incident_reports(id),
  from_level TEXT NOT NULL, to_level TEXT NOT NULL, reason TEXT NOT NULL,
  triggered_by_type TEXT NOT NULL, triggered_by_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mission_bridge_audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id TEXT NOT NULL DEFAULT 'public',
  actor_user_id TEXT NOT NULL, action TEXT NOT NULL, target_type TEXT NOT NULL,
  target_id TEXT, metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mb_enrollments_user ON mission_bridge_enrollments(tenant_id,user_id,status);
CREATE INDEX IF NOT EXISTS idx_mb_checkins_enrollment ON mission_bridge_checkins(enrollment_id,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_mb_incidents_tenant ON incident_reports(tenant_id,risk_level,status,created_at DESC);
CREATE INDEX IF NOT EXISTS idx_mb_ack_user ON safeguarding_acknowledgements(tenant_id,user_id,acknowledged_at DESC);
CREATE INDEX IF NOT EXISTS idx_mb_audit_actor ON mission_bridge_audit_log(tenant_id,actor_user_id,created_at DESC);

INSERT INTO safeguarding_policy_versions(version,title,policy) VALUES
('1.0.0','MissionBridge safeguarding baseline','{"levels":["L0","L1","L2","L3"],"ai_cannot_close":["L2","L3"],"voluntary":true}'::jsonb)
ON CONFLICT(version) DO NOTHING;

INSERT INTO mission_bridge_program_definitions(id,group_type,title,description,active_version) VALUES
('local-leader-90','local_leader','基层小组长 90 天装备','在真实服事处境中建立安全、带领、关怀与复制能力。','1.0.0'),
('attention-reset-30','christian_youth','青年注意力重建 30 天','以福音、节奏和同伴支持重建注意力，不以羞耻驱动。','1.0.0'),
('ai-faith-dialogue-8','technology_worker','AI 时代信仰探索 8 次讨论','面向科技从业者的自愿、透明、可退出信仰探索。','1.0.0')
ON CONFLICT(id) DO NOTHING;

INSERT INTO mission_bridge_program_versions(program_id,version,definition,safeguarding_profile)
SELECT id,'1.0.0',jsonb_build_object('durationWeeks',CASE id WHEN 'local-leader-90' THEN 13 WHEN 'attention-reset-30' THEN 4 ELSE 8 END,'sessionMode','hybrid','voluntary',true,'steps',CASE id WHEN 'local-leader-90' THEN 13 WHEN 'attention-reset-30' THEN 30 ELSE 8 END),
       '{"riskTriggers":["self_harm","violence","abuse","medical_emergency"],"professionalReferral":true,"noCoercion":true}'::jsonb
FROM mission_bridge_program_definitions ON CONFLICT(program_id,version) DO NOTHING;
