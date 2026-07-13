-- Mission OS encrypted Vault: ciphertext-only secrets/files with key versioning and audited grants.
ALTER TABLE mission_secure_sessions DROP CONSTRAINT IF EXISTS mission_secure_sessions_purpose_check;
ALTER TABLE mission_secure_sessions ADD CONSTRAINT mission_secure_sessions_purpose_check
 CHECK(purpose IN('sensitive_export','break_glass','admin_settings','bulk_download','credential_download','medical_record_access'));

CREATE TABLE IF NOT EXISTS mission_vault_secrets (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id TEXT NOT NULL,
 resource_type TEXT NOT NULL, resource_id TEXT NOT NULL, field_name TEXT NOT NULL,
 key_version TEXT NOT NULL, nonce BYTEA NOT NULL, ciphertext BYTEA NOT NULL,
 content_sha256 TEXT NOT NULL, created_by TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), rotated_at TIMESTAMPTZ,
 UNIQUE(tenant_id,resource_type,resource_id,field_name));
CREATE TABLE IF NOT EXISTS mission_vault_files (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id TEXT NOT NULL,
 resource_type TEXT NOT NULL, resource_id TEXT NOT NULL, file_name TEXT NOT NULL,
 media_type TEXT NOT NULL DEFAULT 'application/octet-stream', byte_size BIGINT NOT NULL CHECK(byte_size BETWEEN 1 AND 10485760),
 key_version TEXT NOT NULL, nonce BYTEA NOT NULL, ciphertext BYTEA NOT NULL,
 content_sha256 TEXT NOT NULL, created_by TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), deleted_at TIMESTAMPTZ);
CREATE TABLE IF NOT EXISTS mission_vault_access_grants (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id TEXT NOT NULL,
 user_id TEXT NOT NULL, resource_type TEXT NOT NULL, resource_id TEXT NOT NULL,
 purpose TEXT NOT NULL, secure_session_id UUID NOT NULL REFERENCES mission_secure_sessions(id),
 expires_at TIMESTAMPTZ NOT NULL, max_uses INTEGER NOT NULL DEFAULT 1 CHECK(max_uses BETWEEN 1 AND 10),
 uses INTEGER NOT NULL DEFAULT 0, revoked_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
ALTER TABLE mission_vault_secrets ENABLE ROW LEVEL SECURITY;
ALTER TABLE mission_vault_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE mission_vault_access_grants ENABLE ROW LEVEL SECURITY;
DO $$DECLARE t TEXT;BEGIN FOREACH t IN ARRAY ARRAY['mission_vault_secrets','mission_vault_files','mission_vault_access_grants'] LOOP
 EXECUTE format('CREATE POLICY mission_tenant_isolation ON %I USING(tenant_id=current_setting(''app.tenant_id'',true)) WITH CHECK(tenant_id=current_setting(''app.tenant_id'',true))',t);
END LOOP;END$$;
CREATE INDEX IF NOT EXISTS idx_mission_vault_secret_resource ON mission_vault_secrets(tenant_id,resource_type,resource_id);
CREATE INDEX IF NOT EXISTS idx_mission_vault_file_resource ON mission_vault_files(tenant_id,resource_type,resource_id,deleted_at);
CREATE INDEX IF NOT EXISTS idx_mission_vault_grant_user ON mission_vault_access_grants(tenant_id,user_id,expires_at,revoked_at);
-- Rollback: drop access_grants, files, secrets; restore secure-session purpose constraint if required.
