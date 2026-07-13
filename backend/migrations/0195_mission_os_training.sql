-- Skill 37/44/45: training plans, language plans and professional verification.
CREATE TABLE IF NOT EXISTS mission_training_plans (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,worker_profile_id TEXT NOT NULL,calling_journey_id TEXT,readiness_assessment_id TEXT,
 target_role_id TEXT,target_field_id TEXT,plan_type TEXT NOT NULL DEFAULT 'foundational_formation',plan_version INTEGER NOT NULL DEFAULT 1,
 plan_status TEXT NOT NULL DEFAULT 'draft' CHECK(plan_status IN('draft','awaiting_worker_review','awaiting_mentor_review','approved','active','paused','revision_required','completed','cancelled','superseded')),
 duration_months INTEGER,expected_weekly_hours INTEGER,generated_by_type TEXT NOT NULL DEFAULT 'system' CHECK(generated_by_type IN('human','ai','system')),
 approved_by TEXT,approved_at TIMESTAMPTZ,next_review_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_training_plan_modules (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,training_plan_id UUID NOT NULL REFERENCES mission_training_plans(id),
 module_type TEXT NOT NULL,module_reference_id TEXT,title TEXT NOT NULL,requirement_level TEXT NOT NULL DEFAULT 'required',sequence_order INTEGER NOT NULL DEFAULT 0,
 expected_hours INTEGER,status TEXT NOT NULL DEFAULT 'planned',completion_evidence_requirement TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_training_plan_gaps (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,training_plan_id UUID NOT NULL REFERENCES mission_training_plans(id),
 readiness_dimension TEXT NOT NULL,gap_type TEXT,current_level TEXT,target_level TEXT,remediation_strategy TEXT,blocking BOOLEAN NOT NULL DEFAULT FALSE,
 status TEXT NOT NULL DEFAULT 'open',created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_language_plans (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,worker_profile_id TEXT NOT NULL,language_id TEXT NOT NULL,language_variety_id TEXT,
 target_role_id TEXT,current_level TEXT NOT NULL DEFAULT 'L0' CHECK(current_level IN('L0','L1','L2','L3','L4','L5')),target_level TEXT NOT NULL DEFAULT 'L2' CHECK(target_level IN('L0','L1','L2','L3','L4','L5')),
 weekly_hours INTEGER,plan_status TEXT NOT NULL DEFAULT 'active',mentor_id TEXT,starts_at TIMESTAMPTZ,target_review_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_language_assessments (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,plan_id UUID NOT NULL REFERENCES mission_language_plans(id),
 assessment_type TEXT NOT NULL,assessor_type TEXT NOT NULL CHECK(assessor_type IN('self','ai','native_speaker','authorized_assessor')),assessor_id TEXT,
 listening_level TEXT,speaking_level TEXT,reading_level TEXT,writing_level TEXT,relational_level TEXT,ministry_level TEXT,
 verified BOOLEAN NOT NULL DEFAULT FALSE,assessed_at TIMESTAMPTZ NOT NULL DEFAULT now(),expires_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK(NOT verified OR assessor_type IN('native_speaker','authorized_assessor')));
CREATE TABLE IF NOT EXISTS mission_cultural_observations (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,worker_profile_id TEXT NOT NULL,field_id TEXT,observation_date DATE,
 context_type TEXT,observation_description TEXT NOT NULL,initial_interpretation TEXT,local_explanation TEXT,revised_interpretation TEXT,
 cultural_guide_id TEXT,sensitivity_level TEXT NOT NULL DEFAULT 'P2',confidence TEXT NOT NULL DEFAULT 'low',created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK(confidence<>'high' OR local_explanation IS NOT NULL));
CREATE TABLE IF NOT EXISTS mission_professional_verifications (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,worker_profile_id TEXT NOT NULL,profession_key TEXT NOT NULL,country_code TEXT,
 verification_type TEXT,issuing_or_verifying_body TEXT,verification_status TEXT NOT NULL DEFAULT 'unverified' CHECK(verification_status IN('unverified','submitted','verified','expired','rejected')),
 valid_from DATE,expires_at DATE,evidence_reference TEXT,verified_by TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT now());
ALTER TABLE mission_training_plans ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_training_plan_modules ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_training_plan_gaps ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_language_plans ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_language_assessments ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_cultural_observations ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_professional_verifications ENABLE ROW LEVEL SECURITY;
DO $$DECLARE t TEXT;BEGIN FOREACH t IN ARRAY ARRAY['mission_training_plans','mission_training_plan_modules','mission_training_plan_gaps','mission_language_plans','mission_language_assessments','mission_cultural_observations','mission_professional_verifications'] LOOP EXECUTE format('CREATE POLICY mission_tenant_isolation ON %I USING(tenant_id=current_setting(''app.tenant_id'',true)) WITH CHECK(tenant_id=current_setting(''app.tenant_id'',true))',t);END LOOP;END$$;
CREATE INDEX IF NOT EXISTS idx_mission_training_plan_worker ON mission_training_plans(tenant_id,worker_profile_id,plan_status);
CREATE INDEX IF NOT EXISTS idx_mission_language_plan_worker ON mission_language_plans(tenant_id,worker_profile_id);
CREATE INDEX IF NOT EXISTS idx_mission_prof_verif_worker ON mission_professional_verifications(tenant_id,worker_profile_id,profession_key);
-- Rollback: drop professional_verifications, cultural_observations, language_assessments, language_plans, plan_gaps, plan_modules, then training_plans.
