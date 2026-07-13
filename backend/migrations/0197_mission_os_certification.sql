-- Skill 43/49: safeguarding certification and multi-evidence stage certification.
CREATE TABLE IF NOT EXISTS mission_competency_definitions (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT,competency_key TEXT NOT NULL,name TEXT NOT NULL,description TEXT,category TEXT,
 version INTEGER NOT NULL DEFAULT 1,high_risk BOOLEAN NOT NULL DEFAULT FALSE,evidence_requirements JSONB NOT NULL DEFAULT '[]'::jsonb,
 status TEXT NOT NULL DEFAULT 'active' CHECK(status IN('draft','active','retired')),created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(tenant_id,competency_key,version));
CREATE TABLE IF NOT EXISTS mission_competency_evidence (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,worker_profile_id TEXT NOT NULL,competency_definition_id UUID NOT NULL REFERENCES mission_competency_definitions(id),
 evidence_type TEXT NOT NULL,source_type TEXT,source_id TEXT,evidence_summary TEXT,evidence_level TEXT NOT NULL DEFAULT 'submitted',
 verified BOOLEAN NOT NULL DEFAULT FALSE,verified_by TEXT,verified_at TIMESTAMPTZ,expires_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_observation_rubrics (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT,rubric_key TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,competency_id TEXT,
 context_type TEXT,criteria_json JSONB NOT NULL DEFAULT '[]'::jsonb,status TEXT NOT NULL DEFAULT 'active',created_at TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(tenant_id,rubric_key,version));
CREATE TABLE IF NOT EXISTS mission_stage_certifications (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,worker_profile_id TEXT NOT NULL,training_plan_id TEXT,
 certification_type TEXT NOT NULL CHECK(certification_type IN('foundational_training_completed','local_practicum_ready','local_practicum_completed','cross_cultural_internship_ready','team_discernment_ready','role_training_requirement_satisfied','safeguarding_contact_ready','language_stage_verified','professional_requirement_verified')),
 certification_version INTEGER NOT NULL DEFAULT 1,certification_status TEXT NOT NULL DEFAULT 'evidence_collection',high_risk BOOLEAN NOT NULL DEFAULT FALSE,
 evidence_summary TEXT,required_conditions JSONB NOT NULL DEFAULT '[]'::jsonb,decided_by TEXT,second_reviewer_id TEXT,
 issued_at TIMESTAMPTZ,expires_at TIMESTAMPTZ,revoked_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK(NOT high_risk OR second_reviewer_id IS NULL OR second_reviewer_id<>decided_by));
CREATE TABLE IF NOT EXISTS mission_safeguarding_training_records (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,worker_profile_id TEXT NOT NULL,course_version TEXT,
 completion_status TEXT NOT NULL DEFAULT 'in_progress',human_scenario_assessment_passed BOOLEAN NOT NULL DEFAULT FALSE,
 certification_level TEXT CHECK(certification_level IS NULL OR certification_level IN('awareness_completed','contact_ready','supervised_response_ready','incident_role_ready')),
 certified_by TEXT,certified_at TIMESTAMPTZ,expires_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK(certification_level IS NULL OR certification_level='awareness_completed' OR human_scenario_assessment_passed));
ALTER TABLE mission_competency_definitions ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_competency_evidence ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_observation_rubrics ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_stage_certifications ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_safeguarding_training_records ENABLE ROW LEVEL SECURITY;
DO $$DECLARE t TEXT;BEGIN FOREACH t IN ARRAY ARRAY['mission_competency_definitions','mission_competency_evidence','mission_observation_rubrics','mission_stage_certifications','mission_safeguarding_training_records'] LOOP EXECUTE format('CREATE POLICY mission_tenant_isolation ON %I USING(tenant_id=current_setting(''app.tenant_id'',true) OR tenant_id IS NULL) WITH CHECK(tenant_id=current_setting(''app.tenant_id'',true) OR tenant_id IS NULL)',t);END LOOP;END$$;
CREATE INDEX IF NOT EXISTS idx_mission_competency_evidence_worker ON mission_competency_evidence(tenant_id,worker_profile_id,competency_definition_id);
CREATE INDEX IF NOT EXISTS idx_mission_stage_cert_worker ON mission_stage_certifications(tenant_id,worker_profile_id,certification_type);
CREATE INDEX IF NOT EXISTS idx_mission_safeguarding_worker ON mission_safeguarding_training_records(tenant_id,worker_profile_id,expires_at);
-- Rollback: drop safeguarding_training_records, stage_certifications, observation_rubrics, competency_evidence, then competency_definitions.
