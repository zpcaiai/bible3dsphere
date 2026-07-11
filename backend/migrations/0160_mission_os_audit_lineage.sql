CREATE TABLE IF NOT EXISTS mission_audit_logs (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,actor_id TEXT NOT NULL,actor_role TEXT NOT NULL,
 action TEXT NOT NULL,resource_type TEXT NOT NULL,resource_id TEXT NOT NULL,field_names_changed TEXT[] NOT NULL DEFAULT '{}',
 reason TEXT,request_id TEXT,trace_id TEXT,ip_hash TEXT,user_agent_summary TEXT,result TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS idx_mission_audit_lookup ON mission_audit_logs(tenant_id,resource_type,resource_id,created_at DESC);
CREATE TABLE IF NOT EXISTS mission_break_glass_access (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,actor_id TEXT NOT NULL,target_type TEXT NOT NULL,target_id TEXT NOT NULL,
 reason TEXT NOT NULL CHECK(length(reason)>=12),status TEXT NOT NULL DEFAULT 'active' CHECK(status IN('active','expired','revoked')),
 expires_at TIMESTAMPTZ NOT NULL,review_status TEXT NOT NULL DEFAULT 'pending',reviewed_by TEXT,reviewed_at TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_data_lineage (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,
 derived_resource_type TEXT NOT NULL,derived_resource_id TEXT NOT NULL,source_resource_type TEXT NOT NULL,source_resource_id TEXT NOT NULL,
 transformation_type TEXT NOT NULL,model_run_id TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE(tenant_id,derived_resource_type,derived_resource_id,source_resource_type,source_resource_id,transformation_type));
CREATE INDEX IF NOT EXISTS idx_mission_lineage_derived ON mission_data_lineage(tenant_id,derived_resource_type,derived_resource_id);
CREATE TABLE IF NOT EXISTS mission_post_access_reviews (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,break_glass_id UUID NOT NULL REFERENCES mission_break_glass_access(id),
 assigned_role TEXT NOT NULL DEFAULT 'safeguarding_officer',status TEXT NOT NULL DEFAULT 'open' CHECK(status IN('open','completed')),
 findings TEXT,completed_by TEXT,completed_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE(break_glass_id));
ALTER TABLE mission_audit_logs ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_break_glass_access ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_data_lineage ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_post_access_reviews ENABLE ROW LEVEL SECURITY;
DO $$ DECLARE t TEXT;BEGIN FOREACH t IN ARRAY ARRAY['mission_audit_logs','mission_break_glass_access','mission_data_lineage','mission_post_access_reviews'] LOOP EXECUTE format('CREATE POLICY mission_tenant_isolation ON %I USING(tenant_id=current_setting(''app.tenant_id'',true)) WITH CHECK(tenant_id=current_setting(''app.tenant_id'',true))',t);END LOOP;END $$;
CREATE OR REPLACE FUNCTION prevent_mission_audit_mutation() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN RAISE EXCEPTION 'mission audit logs are immutable';END$$;
DROP TRIGGER IF EXISTS mission_audit_immutable ON mission_audit_logs;
CREATE TRIGGER mission_audit_immutable BEFORE UPDATE OR DELETE ON mission_audit_logs FOR EACH ROW EXECUTE FUNCTION prevent_mission_audit_mutation();
-- Rollback: drop trigger/function, then mission_data_lineage, mission_break_glass_access, mission_audit_logs.
