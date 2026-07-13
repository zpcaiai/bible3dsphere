-- Skill 15: step-up authentication, sensitive-export approval and secure sessions.
CREATE TABLE IF NOT EXISTS mission_secure_sessions (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,user_id TEXT NOT NULL,
 purpose TEXT NOT NULL CHECK(purpose IN('sensitive_export','break_glass','admin_settings','bulk_download')),
 step_up_method TEXT NOT NULL CHECK(step_up_method IN('totp','webauthn','email_code','sms_code')),
 verified_at TIMESTAMPTZ NOT NULL DEFAULT now(),expires_at TIMESTAMPTZ NOT NULL,revoked_at TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_sensitive_export_requests (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,requester_id TEXT NOT NULL,
 resource_type TEXT NOT NULL,scope JSONB NOT NULL DEFAULT '{}'::jsonb,
 sensitivity_level TEXT NOT NULL CHECK(sensitivity_level IN('P0','P1','P2','P3','P4')),
 justification TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'requested' CHECK(status IN('requested','step_up_pending','approved','denied','ready','downloaded','expired','revoked')),
 step_up_session_id UUID REFERENCES mission_secure_sessions(id),step_up_verified_at TIMESTAMPTZ,
 approver_id TEXT,approved_at TIMESTAMPTZ,denied_reason TEXT,
 token_hash TEXT UNIQUE,watermark_label TEXT,
 downloads INTEGER NOT NULL DEFAULT 0,max_downloads INTEGER NOT NULL DEFAULT 1 CHECK(max_downloads BETWEEN 1 AND 10),
 expires_at TIMESTAMPTZ,revoked_at TIMESTAMPTZ,deleted_at TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK(approver_id IS NULL OR approver_id<>requester_id));
ALTER TABLE mission_secure_sessions ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_sensitive_export_requests ENABLE ROW LEVEL SECURITY;
DO $$DECLARE t TEXT;BEGIN FOREACH t IN ARRAY ARRAY['mission_secure_sessions','mission_sensitive_export_requests'] LOOP EXECUTE format('CREATE POLICY mission_tenant_isolation ON %I USING(tenant_id=current_setting(''app.tenant_id'',true)) WITH CHECK(tenant_id=current_setting(''app.tenant_id'',true))',t);END LOOP;END$$;
CREATE INDEX IF NOT EXISTS idx_mission_secure_session_user ON mission_secure_sessions(tenant_id,user_id,purpose,expires_at);
CREATE INDEX IF NOT EXISTS idx_mission_sensitive_export_status ON mission_sensitive_export_requests(tenant_id,status,expires_at);
-- Rollback: drop mission_sensitive_export_requests, then mission_secure_sessions. No other Mission OS data depends on these tables.
