-- MissionBridge Skill 02: tenant RBAC, explicit collaboration and RLS.
CREATE TABLE IF NOT EXISTS mission_bridge_roles (
  key TEXT PRIMARY KEY, title TEXT NOT NULL, sensitive_access BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE TABLE IF NOT EXISTS mission_bridge_permissions (
  key TEXT PRIMARY KEY, description TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mission_bridge_role_permissions (
  role_key TEXT NOT NULL REFERENCES mission_bridge_roles(key),
  permission_key TEXT NOT NULL REFERENCES mission_bridge_permissions(key),
  PRIMARY KEY(role_key,permission_key)
);
CREATE TABLE IF NOT EXISTS mission_bridge_tenant_memberships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id TEXT NOT NULL,
  user_id TEXT NOT NULL, role_key TEXT NOT NULL REFERENCES mission_bridge_roles(key),
  status TEXT NOT NULL DEFAULT 'active', created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(tenant_id,user_id,role_key)
);
CREATE TABLE IF NOT EXISTS mission_bridge_program_memberships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id TEXT NOT NULL,
  program_id TEXT NOT NULL, user_id TEXT NOT NULL, role_key TEXT NOT NULL REFERENCES mission_bridge_roles(key),
  status TEXT NOT NULL DEFAULT 'active', created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(tenant_id,program_id,user_id,role_key)
);
CREATE TABLE IF NOT EXISTS mission_bridge_guardian_relationships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id TEXT NOT NULL,
  guardian_user_id TEXT NOT NULL, participant_user_id TEXT NOT NULL,
  verification_status TEXT NOT NULL DEFAULT 'pending', permissions JSONB NOT NULL DEFAULT '[]'::jsonb,
  expires_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(tenant_id,guardian_user_id,participant_user_id)
);
CREATE TABLE IF NOT EXISTS mission_bridge_cross_tenant_grants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), owner_tenant_id TEXT NOT NULL,
  grantee_tenant_id TEXT NOT NULL, program_id TEXT NOT NULL, permission TEXT NOT NULL,
  granted_by TEXT NOT NULL, expires_at TIMESTAMPTZ NOT NULL, revoked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO mission_bridge_roles(key,title,sensitive_access) VALUES
('platform_admin','Platform administrator',TRUE),('tenant_admin','Tenant administrator',TRUE),
('program_manager','Program manager',FALSE),('safeguarding_officer','Safeguarding officer',TRUE),
('child_protection_officer','Child protection officer',TRUE),('professional_referral_partner','Professional referral partner',TRUE),
('pastor','Pastor',FALSE),('facilitator','Facilitator',FALSE),('mentor','Mentor',FALSE),
('volunteer','Volunteer',FALSE),('participant','Participant',FALSE),('guardian','Guardian',TRUE),
('auditor','Auditor',TRUE),('content_editor','Content editor',FALSE)
ON CONFLICT(key) DO NOTHING;
INSERT INTO mission_bridge_permissions(key,description) VALUES
('program.read','Read program'),('program.manage','Manage program'),('participant.self','Read own participant data'),
('participant.list_masked','Read masked participant list'),('incident.report','Report incident'),
('incident.manage','Manage safeguarding incidents'),('incident.child.read','Read child-safety incidents'),
('referral.manage','Manage professional referrals'),('content.manage','Manage reviewed content'),
('audit.read_masked','Read masked audit events'),('tenant.manage','Manage tenant membership')
ON CONFLICT(key) DO NOTHING;
INSERT INTO mission_bridge_role_permissions(role_key,permission_key)
SELECT role_key,permission_key FROM (VALUES
('participant','program.read'),('participant','participant.self'),('participant','incident.report'),
('mentor','program.read'),('mentor','participant.list_masked'),('mentor','incident.report'),
('facilitator','program.read'),('facilitator','participant.list_masked'),('facilitator','incident.report'),
('program_manager','program.read'),('program_manager','program.manage'),('program_manager','participant.list_masked'),
('safeguarding_officer','incident.manage'),('safeguarding_officer','referral.manage'),
('child_protection_officer','incident.manage'),('child_protection_officer','incident.child.read'),
('professional_referral_partner','referral.manage'),('content_editor','content.manage'),
('auditor','audit.read_masked'),('tenant_admin','tenant.manage'),('tenant_admin','program.manage'),
('platform_admin','tenant.manage'),('platform_admin','program.manage'),('platform_admin','incident.manage'),
('platform_admin','incident.child.read'),('platform_admin','referral.manage'),('platform_admin','content.manage'),('platform_admin','audit.read_masked')
) AS rp(role_key,permission_key) ON CONFLICT DO NOTHING;

-- RLS uses a transaction-local tenant set by the API. Table owners retain migration access.
DO $$ DECLARE table_name TEXT; BEGIN
  FOREACH table_name IN ARRAY ARRAY['mission_bridge_consents','mission_bridge_enrollments','incident_reports','mission_bridge_audit_log','safeguarding_acknowledgements','mission_bridge_data_access_grants','mission_bridge_tenant_memberships','mission_bridge_program_memberships','mission_bridge_guardian_relationships'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY',table_name);
    EXECUTE format('DROP POLICY IF EXISTS mission_bridge_tenant_isolation ON %I',table_name);
    EXECUTE format('CREATE POLICY mission_bridge_tenant_isolation ON %I USING (tenant_id = current_setting(''app.tenant_id'',true)) WITH CHECK (tenant_id = current_setting(''app.tenant_id'',true))',table_name);
  END LOOP;
END $$;
