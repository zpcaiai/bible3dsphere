-- Skill 11: field-level sensitivity classification (P0-P4) and field authorization.
CREATE TABLE IF NOT EXISTS mission_field_classifications (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,
 resource_type TEXT NOT NULL,field_name TEXT NOT NULL,
 sensitivity_level TEXT NOT NULL CHECK(sensitivity_level IN('P0','P1','P2','P3','P4')),
 rationale TEXT,reviewed_by TEXT,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE(tenant_id,resource_type,field_name));
CREATE TABLE IF NOT EXISTS mission_field_access_grants (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,
 subject_type TEXT NOT NULL CHECK(subject_type IN('user','role','service')),subject_id TEXT NOT NULL,
 resource_type TEXT NOT NULL,field_name TEXT NOT NULL,
 max_sensitivity TEXT NOT NULL CHECK(max_sensitivity IN('P0','P1','P2','P3','P4')),
 reason TEXT NOT NULL,granted_by TEXT NOT NULL,
 expires_at TIMESTAMPTZ,revoked_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now());
ALTER TABLE mission_field_classifications ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_field_access_grants ENABLE ROW LEVEL SECURITY;
DO $$DECLARE t TEXT;BEGIN FOREACH t IN ARRAY ARRAY['mission_field_classifications','mission_field_access_grants'] LOOP EXECUTE format('DROP POLICY IF EXISTS mission_tenant_isolation ON %I',t);EXECUTE format('CREATE POLICY mission_tenant_isolation ON %I USING(tenant_id=current_setting(''app.tenant_id'',true)) WITH CHECK(tenant_id=current_setting(''app.tenant_id'',true))',t);END LOOP;END$$;
CREATE INDEX IF NOT EXISTS idx_mission_field_class_resource ON mission_field_classifications(tenant_id,resource_type,field_name);
CREATE INDEX IF NOT EXISTS idx_mission_field_grant_subject ON mission_field_access_grants(tenant_id,subject_type,subject_id,resource_type);
-- Rollback: drop mission_field_access_grants, then mission_field_classifications. No other Mission OS data depends on these tables.
