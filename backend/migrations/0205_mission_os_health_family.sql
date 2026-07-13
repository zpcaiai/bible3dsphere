-- Skill 68/69: minimal medical readiness, insurance and family readiness.
CREATE TABLE IF NOT EXISTS mission_medical_readiness_profiles (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,worker_profile_id TEXT NOT NULL,household_member_reference TEXT,assessment_version INTEGER NOT NULL DEFAULT 1,
 medical_status TEXT NOT NULL DEFAULT 'assessment_pending' CHECK(medical_status IN('assessment_pending','additional_review_required','cleared','cleared_with_conditions','not_cleared_currently','expired','superseded')),
 target_field_id TEXT,target_role_id TEXT,assessed_by_professional_reference TEXT,assessment_date DATE,expires_at DATE,restriction_summary TEXT,accommodation_requirements TEXT,
 follow_up_requirements TEXT,emergency_requirements TEXT,secure_document_reference TEXT,sensitivity_level TEXT NOT NULL DEFAULT 'P4',created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_medication_continuity_plans (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,medical_profile_id UUID NOT NULL REFERENCES mission_medical_readiness_profiles(id),
 medication_category TEXT,ongoing_required BOOLEAN NOT NULL DEFAULT FALSE,supply_duration_target TEXT,local_availability_status TEXT,backup_plan TEXT,review_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_insurance_policies (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,policy_holder_reference TEXT NOT NULL,insurer_reference TEXT,policy_type TEXT NOT NULL,coverage_regions JSONB NOT NULL DEFAULT '[]'::jsonb,
 effective_at DATE,expires_at DATE,coverage_status TEXT NOT NULL DEFAULT 'active',emergency_coverage BOOLEAN NOT NULL DEFAULT FALSE,evacuation_coverage BOOLEAN NOT NULL DEFAULT FALSE,repatriation_coverage BOOLEAN NOT NULL DEFAULT FALSE,
 exclusion_summary TEXT,secure_document_reference TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_insurance_gap_assessments (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,policy_id UUID REFERENCES mission_insurance_policies(id),financial_plan_id TEXT,
 gap_type TEXT NOT NULL CHECK(gap_type IN('region_not_covered','preexisting_condition_excluded','mental_health_excluded','maternity_excluded','evacuation_missing','repatriation_missing','deductible_too_high','coverage_limit_low','provider_network_inadequate','professional_liability_missing','dependent_missing','policy_expiring')),
 severity TEXT NOT NULL DEFAULT 'medium',gap_summary TEXT,remediation_required BOOLEAN NOT NULL DEFAULT TRUE,status TEXT NOT NULL DEFAULT 'open',reviewed_by TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_households (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,worker_profile_id TEXT NOT NULL,household_type TEXT,household_status TEXT NOT NULL DEFAULT 'active',primary_country TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_family_readiness_plans (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,household_id UUID NOT NULL REFERENCES mission_households(id),sending_journey_id TEXT,plan_version INTEGER NOT NULL DEFAULT 1,
 plan_status TEXT NOT NULL DEFAULT 'draft',target_field_id TEXT,intended_move_date DATE,assessed_by TEXT,approved_by TEXT,review_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_spouse_readiness_reviews (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,family_plan_id UUID NOT NULL REFERENCES mission_family_readiness_plans(id),spouse_user_id TEXT NOT NULL,submitted_by TEXT NOT NULL,
 consent_status TEXT,willingness_status TEXT NOT NULL DEFAULT 'not_asked' CHECK(willingness_status IN('not_asked','considering','supportive','supportive_with_conditions','not_ready','does_not_consent','withdrawn','review_required')),
 concern_summary TEXT,privacy_level TEXT NOT NULL DEFAULT 'P3',submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),review_due_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK(submitted_by=spouse_user_id));
CREATE TABLE IF NOT EXISTS mission_child_education_plans (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,family_plan_id UUID NOT NULL REFERENCES mission_family_readiness_plans(id),child_reference TEXT NOT NULL,
 education_model TEXT NOT NULL CHECK(education_model IN('local_public_school','local_private_school','international_school','boarding_school','homeschool_where_legal','online_school','hybrid','return_home_for_schooling','undetermined')),
 legal_in_region BOOLEAN NOT NULL DEFAULT TRUE,special_education_support TEXT,safeguarding_status TEXT,cost_summary TEXT,transition_plan TEXT,review_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK(education_model<>'homeschool_where_legal' OR legal_in_region));
ALTER TABLE mission_medical_readiness_profiles ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_medication_continuity_plans ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_insurance_policies ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_insurance_gap_assessments ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_households ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_family_readiness_plans ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_spouse_readiness_reviews ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_child_education_plans ENABLE ROW LEVEL SECURITY;
DO $$DECLARE t TEXT;BEGIN FOREACH t IN ARRAY ARRAY['mission_medical_readiness_profiles','mission_medication_continuity_plans','mission_insurance_policies','mission_insurance_gap_assessments','mission_households','mission_family_readiness_plans','mission_spouse_readiness_reviews','mission_child_education_plans'] LOOP EXECUTE format('DROP POLICY IF EXISTS mission_tenant_isolation ON %I',t);EXECUTE format('CREATE POLICY mission_tenant_isolation ON %I USING(tenant_id=current_setting(''app.tenant_id'',true)) WITH CHECK(tenant_id=current_setting(''app.tenant_id'',true))',t);END LOOP;END$$;
CREATE INDEX IF NOT EXISTS idx_mission_medical_worker ON mission_medical_readiness_profiles(tenant_id,worker_profile_id,medical_status);
CREATE INDEX IF NOT EXISTS idx_mission_family_plan ON mission_family_readiness_plans(tenant_id,household_id,plan_status);
CREATE INDEX IF NOT EXISTS idx_mission_insurance_gap ON mission_insurance_gap_assessments(tenant_id,status,severity);
-- Rollback: drop child_education_plans, spouse_reviews, family_readiness_plans, households, insurance_gap_assessments, insurance_policies, medication_continuity_plans, then medical_readiness_profiles.
