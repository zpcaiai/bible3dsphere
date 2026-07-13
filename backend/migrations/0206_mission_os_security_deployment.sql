-- Skill 70/71: digital security, emergency/evacuation and the Deployment Readiness Gate.
CREATE TABLE IF NOT EXISTS mission_digital_security_profiles (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,worker_profile_id TEXT,team_id TEXT,deployment_case_id TEXT,
 security_tier TEXT NOT NULL DEFAULT 'standard' CHECK(security_tier IN('standard','elevated','high','restricted')),profile_status TEXT NOT NULL DEFAULT 'draft',
 assessed_by TEXT,assessed_at TIMESTAMPTZ,expires_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_device_inventory (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,security_profile_id UUID NOT NULL REFERENCES mission_digital_security_profiles(id),
 device_type TEXT,device_alias TEXT,ownership_type TEXT,managed BOOLEAN NOT NULL DEFAULT FALSE,encryption_status TEXT,screen_lock_status TEXT,remote_wipe_status TEXT,
 compliance_status TEXT NOT NULL DEFAULT 'unknown',last_checked_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_security_exceptions (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,security_profile_id UUID NOT NULL REFERENCES mission_digital_security_profiles(id),
 control_key TEXT NOT NULL,exception_reason TEXT,compensating_controls TEXT,approved_by TEXT,starts_at TIMESTAMPTZ,expires_at TIMESTAMPTZ NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_emergency_response_plans (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,deployment_case_id TEXT,team_id TEXT NOT NULL,field_id TEXT,plan_version INTEGER NOT NULL DEFAULT 1,
 plan_status TEXT NOT NULL DEFAULT 'draft' CHECK(plan_status IN('draft','review','approved','active','exercise_due','revision_required','suspended','expired','superseded')),
 risk_scope TEXT,incident_command_structure JSONB NOT NULL DEFAULT '{}'::jsonb,activation_authority TEXT,review_at TIMESTAMPTZ,approved_by TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_evacuation_plans (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,emergency_plan_id UUID NOT NULL REFERENCES mission_emergency_response_plans(id),
 evacuation_type TEXT NOT NULL CHECK(evacuation_type IN('shelter_in_place','relocation','temporary_evacuation','permanent_exit','medical_evacuation')),
 trigger_summary TEXT,primary_destination_summary TEXT,alternate_destination_summary TEXT,family_and_dependent_plan TEXT,local_partner_continuity_plan TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_emergency_drills (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,emergency_plan_id UUID NOT NULL REFERENCES mission_emergency_response_plans(id),
 drill_type TEXT NOT NULL,scheduled_at TIMESTAMPTZ,completed_at TIMESTAMPTZ,drill_status TEXT NOT NULL DEFAULT 'scheduled',findings TEXT,corrective_actions TEXT,critical_finding_open BOOLEAN NOT NULL DEFAULT FALSE,created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_deployment_readiness_gates (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,sending_journey_id TEXT NOT NULL,gate_version INTEGER NOT NULL DEFAULT 1,
 gate_status TEXT NOT NULL DEFAULT 'not_started' CHECK(gate_status IN('not_started','data_collection','review_required','blocked','conditionally_ready','ready_for_deployment_planning','expired','revoked')),
 financial_status TEXT,legal_status TEXT,credential_status TEXT,compliance_status TEXT,medical_status TEXT,insurance_status TEXT,family_status TEXT,digital_security_status TEXT,emergency_status TEXT,
 blocking_findings JSONB NOT NULL DEFAULT '[]'::jsonb,conditional_requirements JSONB NOT NULL DEFAULT '[]'::jsonb,unlocks TEXT NOT NULL DEFAULT 'none',
 decided_by_panel_id TEXT,decided_at TIMESTAMPTZ,expires_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
ALTER TABLE mission_digital_security_profiles ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_device_inventory ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_security_exceptions ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_emergency_response_plans ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_evacuation_plans ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_emergency_drills ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_deployment_readiness_gates ENABLE ROW LEVEL SECURITY;
DO $$DECLARE t TEXT;BEGIN FOREACH t IN ARRAY ARRAY['mission_digital_security_profiles','mission_device_inventory','mission_security_exceptions','mission_emergency_response_plans','mission_evacuation_plans','mission_emergency_drills','mission_deployment_readiness_gates'] LOOP EXECUTE format('CREATE POLICY mission_tenant_isolation ON %I USING(tenant_id=current_setting(''app.tenant_id'',true)) WITH CHECK(tenant_id=current_setting(''app.tenant_id'',true))',t);END LOOP;END$$;
CREATE INDEX IF NOT EXISTS idx_mission_device_profile ON mission_device_inventory(tenant_id,security_profile_id,compliance_status);
CREATE INDEX IF NOT EXISTS idx_mission_emergency_team ON mission_emergency_response_plans(tenant_id,team_id,plan_status);
CREATE INDEX IF NOT EXISTS idx_mission_deployment_gate ON mission_deployment_readiness_gates(tenant_id,sending_journey_id,gate_status);
-- Rollback: drop deployment_readiness_gates, emergency_drills, evacuation_plans, emergency_response_plans, security_exceptions, device_inventory, then digital_security_profiles.
