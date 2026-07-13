-- Skill 31/32/33/34: worker profile, roles, matches and 15-dimension readiness.
CREATE TABLE IF NOT EXISTS mission_worker_profiles (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,user_id TEXT NOT NULL,
 profile_status TEXT NOT NULL DEFAULT 'draft',public_summary TEXT,internal_summary TEXT,
 preferred_service_modes JSONB NOT NULL DEFAULT '[]'::jsonb,availability_profile JSONB NOT NULL DEFAULT '{}'::jsonb,
 mobility_profile JSONB NOT NULL DEFAULT '{}'::jsonb,family_stage_summary TEXT,last_reviewed_at TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(tenant_id,user_id));
CREATE TABLE IF NOT EXISTS mission_worker_role_definitions (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT,role_key TEXT NOT NULL,display_name TEXT NOT NULL,description TEXT,
 role_family TEXT NOT NULL CHECK(role_family IN('frontline_ministry','church_equipping','translation_and_language','professional_service','care_and_safeguarding','technology_and_media','research_and_strategy','operations_and_support','sending_and_mobilization')),
 version INTEGER NOT NULL DEFAULT 1,requires_hard_qualification BOOLEAN NOT NULL DEFAULT FALSE,public_visibility BOOLEAN NOT NULL DEFAULT TRUE,
 status TEXT NOT NULL DEFAULT 'active' CHECK(status IN('draft','active','retired')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(tenant_id,role_key,version));
CREATE TABLE IF NOT EXISTS mission_worker_matches (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,worker_profile_id UUID NOT NULL REFERENCES mission_worker_profiles(id),
 match_layer TEXT NOT NULL CHECK(match_layer IN('role_match','field_match','deployment')),role_definition_id UUID REFERENCES mission_worker_role_definitions(id),
 field_id TEXT,match_status TEXT NOT NULL DEFAULT 'draft',recommendation TEXT,evidence_level TEXT NOT NULL DEFAULT 'unknown',
 generated_by_type TEXT NOT NULL DEFAULT 'system' CHECK(generated_by_type IN('human','ai','system')),reviewed_by TEXT,reviewed_at TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_readiness_assessments (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,worker_profile_id UUID NOT NULL REFERENCES mission_worker_profiles(id),
 calling_journey_id UUID,framework_version INTEGER NOT NULL DEFAULT 1,assessment_status TEXT NOT NULL DEFAULT 'draft' CHECK(assessment_status IN('draft','self_assessment','evidence_collection','mentor_review','church_review','panel_review','completed','paused','expired','superseded')),
 target_role_id UUID,target_field_id TEXT,readiness_level TEXT CHECK(readiness_level IS NULL OR readiness_level IN('exploration','foundational_development','local_practice_ready','cross_cultural_internship_ready','team_discernment_ready','deployment_candidate','pause_and_restore','not_enough_evidence')),
 evidence_quality TEXT,overall_summary TEXT,hard_blocks JSONB NOT NULL DEFAULT '[]'::jsonb,
 generated_by_type TEXT NOT NULL DEFAULT 'system' CHECK(generated_by_type IN('human','ai','system')),reviewed_by TEXT,reviewed_at TIMESTAMPTZ,next_review_due_at TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_readiness_dimensions (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,assessment_id UUID NOT NULL REFERENCES mission_readiness_assessments(id),
 dimension_key TEXT NOT NULL,self_assessment_level TEXT,reviewer_level TEXT,final_level TEXT,
 evidence_references JSONB NOT NULL DEFAULT '[]'::jsonb,evidence_quality TEXT,development_priority TEXT,blocking BOOLEAN NOT NULL DEFAULT FALSE,
 explanation TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(tenant_id,assessment_id,dimension_key));
CREATE TABLE IF NOT EXISTS mission_readiness_decisions (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,assessment_id UUID NOT NULL REFERENCES mission_readiness_assessments(id),
 decision_type TEXT NOT NULL,readiness_level TEXT,rationale TEXT,conditions JSONB NOT NULL DEFAULT '[]'::jsonb,
 decided_by TEXT NOT NULL,second_reviewer_id TEXT,is_panel BOOLEAN NOT NULL DEFAULT FALSE,
 effective_at TIMESTAMPTZ NOT NULL DEFAULT now(),expires_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK(decided_by IS NOT NULL AND decided_by<>''));
ALTER TABLE mission_worker_profiles ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_worker_role_definitions ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_worker_matches ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_readiness_assessments ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_readiness_dimensions ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_readiness_decisions ENABLE ROW LEVEL SECURITY;
DO $$DECLARE t TEXT;BEGIN FOREACH t IN ARRAY ARRAY['mission_worker_profiles','mission_worker_role_definitions','mission_worker_matches','mission_readiness_assessments','mission_readiness_dimensions','mission_readiness_decisions'] LOOP EXECUTE format('DROP POLICY IF EXISTS mission_tenant_isolation ON %I',t);EXECUTE format('CREATE POLICY mission_tenant_isolation ON %I USING(tenant_id=current_setting(''app.tenant_id'',true) OR tenant_id IS NULL) WITH CHECK(tenant_id=current_setting(''app.tenant_id'',true))',t);END LOOP;END$$;
CREATE INDEX IF NOT EXISTS idx_mission_worker_profile_user ON mission_worker_profiles(tenant_id,user_id);
CREATE INDEX IF NOT EXISTS idx_mission_readiness_worker ON mission_readiness_assessments(tenant_id,worker_profile_id,assessment_status);
CREATE INDEX IF NOT EXISTS idx_mission_worker_match_layer ON mission_worker_matches(tenant_id,worker_profile_id,match_layer);
-- Rollback: drop decisions, dimensions, assessments, matches, role_definitions, then worker_profiles.
