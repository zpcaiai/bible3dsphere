-- Skill 08: Mission-specific organization profiles over existing organizations.
CREATE TABLE IF NOT EXISTS mission_organization_profiles (
 organization_id VARCHAR(64) PRIMARY KEY REFERENCES organizations(id),tenant_id TEXT NOT NULL,
 organization_kind TEXT NOT NULL CHECK(organization_kind IN('church','mission_agency','receiving_church','team','training_provider','care_provider','professional_partner','funding_partner')),
 legal_name TEXT,country_code TEXT CHECK(country_code IS NULL OR length(country_code)=2),
 safeguarding_contact_user_id TEXT,data_residency_region TEXT,status TEXT NOT NULL DEFAULT 'active' CHECK(status IN('active','suspended','closed')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(tenant_id,organization_id));
CREATE TABLE IF NOT EXISTS mission_organization_relationships (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,source_organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id),
 target_organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id),relationship_type TEXT NOT NULL CHECK(relationship_type IN('sending','receiving','partner','training','member_care','professional_referral','funding')),
 status TEXT NOT NULL DEFAULT 'proposed' CHECK(status IN('proposed','active','paused','ended','rejected')),
 decision_rights JSONB NOT NULL DEFAULT '{}'::jsonb,starts_at TIMESTAMPTZ,ends_at TIMESTAMPTZ,created_by TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),CHECK(source_organization_id<>target_organization_id),UNIQUE(tenant_id,source_organization_id,target_organization_id,relationship_type));
CREATE TABLE IF NOT EXISTS mission_organization_invitations (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id),
 invited_email TEXT NOT NULL,role_key TEXT NOT NULL,token_hash TEXT NOT NULL UNIQUE,status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN('pending','accepted','expired','revoked')),
 expires_at TIMESTAMPTZ NOT NULL,invited_by TEXT NOT NULL,accepted_at TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
ALTER TABLE mission_organization_profiles ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_organization_relationships ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_organization_invitations ENABLE ROW LEVEL SECURITY;
DO $$DECLARE t TEXT;BEGIN FOREACH t IN ARRAY ARRAY['mission_organization_profiles','mission_organization_relationships','mission_organization_invitations'] LOOP EXECUTE format('CREATE POLICY mission_tenant_isolation ON %I USING(tenant_id=current_setting(''app.tenant_id'',true)) WITH CHECK(tenant_id=current_setting(''app.tenant_id'',true))',t);END LOOP;END$$;
CREATE INDEX IF NOT EXISTS idx_mission_org_relation_target ON mission_organization_relationships(tenant_id,target_organization_id,status);
CREATE INDEX IF NOT EXISTS idx_mission_org_invite_email ON mission_organization_invitations(tenant_id,invited_email,status);
-- Rollback: drop invitations, relationships and profiles; existing organizations remain owned by Identity/Productization.
