-- Skill 54/55/56/57: mission teams, capability, covenant and health/complaints.
CREATE TABLE IF NOT EXISTS mission_teams (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,team_type TEXT NOT NULL,name TEXT NOT NULL,public_alias TEXT,
 field_id TEXT,lead_organization_id TEXT NOT NULL,receiving_organization_id TEXT,team_status TEXT NOT NULL DEFAULT 'forming' CHECK(team_status IN('forming','recruiting','discernment','active','paused','restructuring','closing','closed')),
 sensitivity_level TEXT NOT NULL DEFAULT 'P2',purpose TEXT,capacity INTEGER,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_team_memberships (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,team_id UUID NOT NULL REFERENCES mission_teams(id),worker_profile_id TEXT NOT NULL,
 team_role_id TEXT,membership_status TEXT NOT NULL DEFAULT 'invited',membership_stage TEXT NOT NULL DEFAULT 'invited' CHECK(membership_stage IN('invited','discernment','provisional','probation','active','on_leave','transitioning_out','ended')),
 is_spouse BOOLEAN NOT NULL DEFAULT FALSE,starts_at TIMESTAMPTZ,probation_ends_at TIMESTAMPTZ,ends_at TIMESTAMPTZ,approved_by TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE(tenant_id,team_id,worker_profile_id));
CREATE TABLE IF NOT EXISTS mission_team_role_slots (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,team_id UUID NOT NULL REFERENCES mission_teams(id),role_definition_id TEXT,
 capability_key TEXT NOT NULL,criticality TEXT NOT NULL DEFAULT 'required' CHECK(criticality IN('optional','helpful','required','mission_critical','safety_critical')),
 required_count INTEGER NOT NULL DEFAULT 1,filled_count INTEGER NOT NULL DEFAULT 0,single_point_of_failure BOOLEAN NOT NULL DEFAULT FALSE,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_team_covenants (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,team_id UUID NOT NULL REFERENCES mission_teams(id),covenant_version INTEGER NOT NULL DEFAULT 1,
 covenant_status TEXT NOT NULL DEFAULT 'draft',sections JSONB NOT NULL DEFAULT '[]'::jsonb,clauses JSONB NOT NULL DEFAULT '[]'::jsonb,
 effective_at TIMESTAMPTZ,review_due_at TIMESTAMPTZ,approved_by TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_team_health_assessments (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,team_id UUID NOT NULL REFERENCES mission_teams(id),assessment_type TEXT NOT NULL DEFAULT 'quarterly',
 assessment_status TEXT NOT NULL DEFAULT 'open',aggregate_level TEXT CHECK(aggregate_level IS NULL OR aggregate_level IN('green','attention','significant_concern','critical')),
 response_count INTEGER NOT NULL DEFAULT 0,privacy_threshold_met BOOLEAN NOT NULL DEFAULT FALSE,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),completed_at TIMESTAMPTZ);
CREATE TABLE IF NOT EXISTS mission_team_complaints (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,team_id UUID NOT NULL REFERENCES mission_teams(id),complainant_user_id TEXT NOT NULL,
 complaint_type TEXT NOT NULL,confidentiality_level TEXT NOT NULL DEFAULT 'P3',accused_user_id TEXT,risk_level TEXT NOT NULL DEFAULT 'medium',
 status TEXT NOT NULL DEFAULT 'submitted',assigned_independent_reviewer_id TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),resolved_at TIMESTAMPTZ,
 CHECK(assigned_independent_reviewer_id IS NULL OR accused_user_id IS NULL OR assigned_independent_reviewer_id<>accused_user_id));
ALTER TABLE mission_teams ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_team_memberships ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_team_role_slots ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_team_covenants ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_team_health_assessments ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_team_complaints ENABLE ROW LEVEL SECURITY;
DO $$DECLARE t TEXT;BEGIN FOREACH t IN ARRAY ARRAY['mission_teams','mission_team_memberships','mission_team_role_slots','mission_team_covenants','mission_team_health_assessments','mission_team_complaints'] LOOP EXECUTE format('CREATE POLICY mission_tenant_isolation ON %I USING(tenant_id=current_setting(''app.tenant_id'',true)) WITH CHECK(tenant_id=current_setting(''app.tenant_id'',true))',t);END LOOP;END$$;
CREATE INDEX IF NOT EXISTS idx_mission_team_membership ON mission_team_memberships(tenant_id,team_id,membership_stage);
CREATE INDEX IF NOT EXISTS idx_mission_team_role_slot ON mission_team_role_slots(tenant_id,team_id,criticality);
CREATE INDEX IF NOT EXISTS idx_mission_team_complaint ON mission_team_complaints(tenant_id,team_id,status);
-- Rollback: drop complaints, health_assessments, covenants, role_slots, memberships, then teams.
