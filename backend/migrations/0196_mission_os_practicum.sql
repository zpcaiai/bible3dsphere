-- Skill 46/47: local cross-cultural practicum and short-term exposure.
CREATE TABLE IF NOT EXISTS mission_practicums (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,title TEXT NOT NULL,practicum_type TEXT NOT NULL,
 host_organization_id TEXT NOT NULL,field_id TEXT,description TEXT,duration_weeks INTEGER,expected_hours_per_week INTEGER,cohort_size_limit INTEGER,
 risk_level TEXT NOT NULL DEFAULT 'low',required_training_modules JSONB NOT NULL DEFAULT '[]'::jsonb,
 status TEXT NOT NULL DEFAULT 'draft',created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_practicum_placements (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,practicum_id UUID NOT NULL REFERENCES mission_practicums(id),
 worker_profile_id TEXT NOT NULL,supervisor_id TEXT,placement_status TEXT NOT NULL DEFAULT 'applied' CHECK(placement_status IN('applied','screening','accepted','preparation_required','ready','active','paused','completed','withdrawn','terminated','failed_to_start')),
 starts_at TIMESTAMPTZ,expected_end_at TIMESTAMPTZ,actual_end_at TIMESTAMPTZ,role_description TEXT,
 allowed_activities JSONB NOT NULL DEFAULT '[]'::jsonb,prohibited_activities JSONB NOT NULL DEFAULT '[]'::jsonb,
 safeguarding_current BOOLEAN NOT NULL DEFAULT FALSE,consent_status TEXT NOT NULL DEFAULT 'pending',created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_practicum_observations (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,placement_id UUID NOT NULL REFERENCES mission_practicum_placements(id),
 observer_id TEXT NOT NULL,competency_key TEXT NOT NULL,observation_context TEXT,observed_behavior TEXT NOT NULL,development_note TEXT,evidence_level TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_exposure_programs (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,program_type TEXT NOT NULL CHECK(program_type IN('virtual_field_orientation','local_exposure_day','short_observation_trip','guided_exploration_trip','cross_cultural_internship','language_immersion','professional_service_internship','team_life_internship')),
 field_id TEXT,host_organization_id TEXT NOT NULL,title TEXT NOT NULL,description TEXT,duration_days INTEGER,
 objectives JSONB NOT NULL DEFAULT '[]'::jsonb,non_objectives JSONB NOT NULL DEFAULT '[]'::jsonb,risk_profile TEXT NOT NULL DEFAULT 'low',
 status TEXT NOT NULL DEFAULT 'draft',created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK(jsonb_array_length(non_objectives)>0));
CREATE TABLE IF NOT EXISTS mission_exposure_enrollments (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,program_id UUID NOT NULL REFERENCES mission_exposure_programs(id),
 worker_profile_id TEXT NOT NULL,enrollment_status TEXT NOT NULL DEFAULT 'applied',evidence_weight TEXT NOT NULL DEFAULT 'exposure' CHECK(evidence_weight IN('exposure','long_term_experience')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
ALTER TABLE mission_practicums ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_practicum_placements ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_practicum_observations ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_exposure_programs ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_exposure_enrollments ENABLE ROW LEVEL SECURITY;
DO $$DECLARE t TEXT;BEGIN FOREACH t IN ARRAY ARRAY['mission_practicums','mission_practicum_placements','mission_practicum_observations','mission_exposure_programs','mission_exposure_enrollments'] LOOP EXECUTE format('CREATE POLICY mission_tenant_isolation ON %I USING(tenant_id=current_setting(''app.tenant_id'',true)) WITH CHECK(tenant_id=current_setting(''app.tenant_id'',true))',t);END LOOP;END$$;
CREATE INDEX IF NOT EXISTS idx_mission_practicum_placement ON mission_practicum_placements(tenant_id,practicum_id,placement_status);
CREATE INDEX IF NOT EXISTS idx_mission_exposure_enroll ON mission_exposure_enrollments(tenant_id,program_id,worker_profile_id);
-- Rollback: drop exposure_enrollments, exposure_programs, practicum_observations, practicum_placements, then practicums.
