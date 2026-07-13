-- Skill 67: multi-domain compliance cases, professional opinions, tax and data transfer.
CREATE TABLE IF NOT EXISTS mission_compliance_cases (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,sending_journey_id TEXT,target_field_id TEXT,compliance_case_version INTEGER NOT NULL DEFAULT 1,
 case_status TEXT NOT NULL DEFAULT 'draft' CHECK(case_status IN('draft','scoping','professional_review','requirements_pending','conditional','cleared_for_next_stage','review_required','blocked','expired','superseded')),
 activity_scope TEXT,organizations_involved JSONB NOT NULL DEFAULT '[]'::jsonb,reviewed_at TIMESTAMPTZ,next_review_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_compliance_domains (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,compliance_case_id UUID NOT NULL REFERENCES mission_compliance_cases(id),
 domain_key TEXT NOT NULL,applicability_status TEXT NOT NULL DEFAULT 'unknown',risk_level TEXT NOT NULL DEFAULT 'low',review_status TEXT NOT NULL DEFAULT 'not_started',
 responsible_reviewer_id TEXT,summary TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(tenant_id,compliance_case_id,domain_key));
CREATE TABLE IF NOT EXISTS mission_compliance_requirements (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,compliance_domain_id UUID NOT NULL REFERENCES mission_compliance_domains(id),
 requirement_key TEXT NOT NULL,description TEXT,requirement_status TEXT NOT NULL DEFAULT 'open',blocking BOOLEAN NOT NULL DEFAULT FALSE,valid_from DATE,expires_at DATE,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_professional_opinions (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,compliance_domain_id UUID NOT NULL REFERENCES mission_compliance_domains(id),
 professional_type TEXT NOT NULL,reviewer_reference TEXT,jurisdiction TEXT NOT NULL,opinion_summary TEXT,limitations TEXT,issued_at DATE NOT NULL,expires_at DATE NOT NULL,secure_document_reference TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK(expires_at>=issued_at));
CREATE TABLE IF NOT EXISTS mission_tax_profiles (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,worker_profile_id TEXT NOT NULL,relevant_countries JSONB NOT NULL DEFAULT '[]'::jsonb,
 tax_residency_status TEXT,filing_obligations_summary TEXT,payroll_status TEXT,self_employment_status TEXT,review_status TEXT NOT NULL DEFAULT 'not_started',
 reviewed_by TEXT,reviewed_at TIMESTAMPTZ,next_review_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(tenant_id,worker_profile_id));
CREATE TABLE IF NOT EXISTS mission_data_transfer_assessments (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,compliance_case_id UUID REFERENCES mission_compliance_cases(id),source_region TEXT,destination_region TEXT,
 data_categories JSONB NOT NULL DEFAULT '[]'::jsonb,transfer_basis TEXT,processor_or_provider TEXT,assessment_status TEXT NOT NULL DEFAULT 'draft',reviewed_at TIMESTAMPTZ,expires_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now());
ALTER TABLE mission_compliance_cases ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_compliance_domains ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_compliance_requirements ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_professional_opinions ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_tax_profiles ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_data_transfer_assessments ENABLE ROW LEVEL SECURITY;
DO $$DECLARE t TEXT;BEGIN FOREACH t IN ARRAY ARRAY['mission_compliance_cases','mission_compliance_domains','mission_compliance_requirements','mission_professional_opinions','mission_tax_profiles','mission_data_transfer_assessments'] LOOP EXECUTE format('CREATE POLICY mission_tenant_isolation ON %I USING(tenant_id=current_setting(''app.tenant_id'',true)) WITH CHECK(tenant_id=current_setting(''app.tenant_id'',true))',t);END LOOP;END$$;
CREATE INDEX IF NOT EXISTS idx_mission_compliance_case ON mission_compliance_cases(tenant_id,case_status);
CREATE INDEX IF NOT EXISTS idx_mission_prof_opinion_domain ON mission_professional_opinions(tenant_id,compliance_domain_id,expires_at);
-- Rollback: drop data_transfer_assessments, tax_profiles, professional_opinions, compliance_requirements, compliance_domains, then compliance_cases.
