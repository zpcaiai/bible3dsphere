-- Skill 65/66: legal identity paths and credential lifecycle (masked identifiers).
CREATE TABLE IF NOT EXISTS mission_legal_identity_paths (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,sending_journey_id TEXT,worker_profile_id TEXT NOT NULL,target_field_id TEXT,
 identity_type TEXT NOT NULL CHECK(identity_type IN('employment','self_employment','business_owner','student','researcher','dependent','family_reunification','volunteer_where_legal','religious_worker_where_legal','retirement','digital_nomad_where_legal','professional_secondment','humanitarian_worker','local_citizen_or_permanent_resident')),
 path_version INTEGER NOT NULL DEFAULT 1,proposed_role TEXT,declared_activity_summary TEXT,actual_activity_summary TEXT,consistency_status TEXT NOT NULL DEFAULT 'unreviewed',
 sponsoring_organization_id TEXT,dependent_family_count INTEGER NOT NULL DEFAULT 0,path_status TEXT NOT NULL DEFAULT 'idea' CHECK(path_status IN('idea','research','professional_review','application_ready','application_submitted','approved','active','renewal_due','expired','revoked','not_viable','superseded')),
 legal_review_status TEXT NOT NULL DEFAULT 'not_started',created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_identity_path_requirements (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,identity_path_id UUID NOT NULL REFERENCES mission_legal_identity_paths(id),
 requirement_key TEXT NOT NULL,requirement_type TEXT,description TEXT,requirement_status TEXT NOT NULL DEFAULT 'open',blocking BOOLEAN NOT NULL DEFAULT FALSE,expires_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_credential_portfolios (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,worker_profile_id TEXT NOT NULL,household_id TEXT,portfolio_status TEXT NOT NULL DEFAULT 'active',created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_credentials (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,credential_portfolio_id UUID NOT NULL REFERENCES mission_credential_portfolios(id),subject_user_id TEXT,dependent_reference TEXT,
 credential_type TEXT NOT NULL,issuing_country TEXT,issuing_authority TEXT,encrypted_identifier_reference TEXT,masked_identifier TEXT,issued_at DATE,expires_at DATE,
 credential_status TEXT NOT NULL DEFAULT 'planned' CHECK(credential_status IN('planned','collecting','submitted','issued','active','renewal_due','expired','revoked','lost','replaced','not_required')),
 verification_status TEXT NOT NULL DEFAULT 'unverified',secure_file_reference TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK(masked_identifier IS NULL OR masked_identifier LIKE '****%'));
CREATE TABLE IF NOT EXISTS mission_credential_tasks (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,credential_id UUID REFERENCES mission_credentials(id),task_type TEXT NOT NULL,title TEXT NOT NULL,owner_id TEXT,
 due_at TIMESTAMPTZ,task_status TEXT NOT NULL DEFAULT 'open',evidence_reference TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
ALTER TABLE mission_legal_identity_paths ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_identity_path_requirements ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_credential_portfolios ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_credentials ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_credential_tasks ENABLE ROW LEVEL SECURITY;
DO $$DECLARE t TEXT;BEGIN FOREACH t IN ARRAY ARRAY['mission_legal_identity_paths','mission_identity_path_requirements','mission_credential_portfolios','mission_credentials','mission_credential_tasks'] LOOP EXECUTE format('CREATE POLICY mission_tenant_isolation ON %I USING(tenant_id=current_setting(''app.tenant_id'',true)) WITH CHECK(tenant_id=current_setting(''app.tenant_id'',true))',t);END LOOP;END$$;
CREATE INDEX IF NOT EXISTS idx_mission_identity_worker ON mission_legal_identity_paths(tenant_id,worker_profile_id,path_status);
CREATE INDEX IF NOT EXISTS idx_mission_credential_expiry ON mission_credentials(tenant_id,expires_at,credential_status);
CREATE INDEX IF NOT EXISTS idx_mission_credential_task_due ON mission_credential_tasks(tenant_id,due_at,task_status);
-- Rollback: drop credential_tasks, credentials, credential_portfolios, identity_path_requirements, then legal_identity_paths.
