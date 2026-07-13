-- Skill 58/59/60: local partners, agreements, decision rights and support networks.
CREATE TABLE IF NOT EXISTS mission_local_partner_profiles (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,organization_id TEXT,partner_type TEXT NOT NULL,public_name TEXT,internal_alias TEXT NOT NULL,
 field_id TEXT,profile_status TEXT NOT NULL DEFAULT 'candidate' CHECK(profile_status IN('candidate','researching','mutual_assessment','due_diligence','approved_for_limited_collaboration','approved','conditional','paused','suspended','ended','do_not_engage')),
 local_ownership_status TEXT,sensitivity_level TEXT NOT NULL DEFAULT 'P3',verified_at TIMESTAMPTZ,review_due_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_partner_due_diligence (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,partner_profile_id UUID NOT NULL REFERENCES mission_local_partner_profiles(id),
 due_diligence_version INTEGER NOT NULL DEFAULT 1,status TEXT NOT NULL DEFAULT 'in_progress',mutual_assessment_completed BOOLEAN NOT NULL DEFAULT FALSE,
 reviewed_by TEXT,completed_at TIMESTAMPTZ,next_review_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_partnership_agreements (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,partnership_id TEXT,agreement_type TEXT NOT NULL,agreement_version INTEGER NOT NULL DEFAULT 1,
 agreement_status TEXT NOT NULL DEFAULT 'draft',sections JSONB NOT NULL DEFAULT '[]'::jsonb,decision_rights JSONB NOT NULL DEFAULT '{}'::jsonb,
 has_exit_plan BOOLEAN NOT NULL DEFAULT FALSE,has_local_decision_rights BOOLEAN NOT NULL DEFAULT FALSE,
 effective_at TIMESTAMPTZ,expires_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_agreement_data_terms (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,agreement_id UUID NOT NULL REFERENCES mission_partnership_agreements(id),
 data_category TEXT NOT NULL,purpose TEXT,allowed_parties JSONB NOT NULL DEFAULT '[]'::jsonb,consent_requirement TEXT NOT NULL DEFAULT 'individual_consent',
 retention_period TEXT,deletion_on_termination BOOLEAN NOT NULL DEFAULT TRUE,created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_support_networks (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,worker_profile_id TEXT,team_id TEXT,sending_journey_id TEXT,
 network_type TEXT NOT NULL,network_status TEXT NOT NULL DEFAULT 'active',created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_prayer_updates (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,support_network_id UUID NOT NULL REFERENCES mission_support_networks(id),
 title TEXT NOT NULL,update_type TEXT NOT NULL,content_reference TEXT,sensitivity_level TEXT NOT NULL DEFAULT 'P1' CHECK(sensitivity_level IN('P0','P1','P2')),
 review_status TEXT NOT NULL DEFAULT 'draft',visibility TEXT NOT NULL DEFAULT 'registered_supporters' CHECK(visibility IN('public','registered_supporters','sending_church_only','care_team_only','restricted_named_audience','emergency_team_only')),
 scheduled_at TIMESTAMPTZ,published_at TIMESTAMPTZ,created_by TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
ALTER TABLE mission_local_partner_profiles ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_partner_due_diligence ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_partnership_agreements ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_agreement_data_terms ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_support_networks ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_prayer_updates ENABLE ROW LEVEL SECURITY;
DO $$DECLARE t TEXT;BEGIN FOREACH t IN ARRAY ARRAY['mission_local_partner_profiles','mission_partner_due_diligence','mission_partnership_agreements','mission_agreement_data_terms','mission_support_networks','mission_prayer_updates'] LOOP EXECUTE format('CREATE POLICY mission_tenant_isolation ON %I USING(tenant_id=current_setting(''app.tenant_id'',true)) WITH CHECK(tenant_id=current_setting(''app.tenant_id'',true))',t);END LOOP;END$$;
CREATE INDEX IF NOT EXISTS idx_mission_partner_field ON mission_local_partner_profiles(tenant_id,field_id,profile_status);
CREATE INDEX IF NOT EXISTS idx_mission_agreement_status ON mission_partnership_agreements(tenant_id,agreement_status,expires_at);
CREATE INDEX IF NOT EXISTS idx_mission_prayer_update_net ON mission_prayer_updates(tenant_id,support_network_id,review_status);
-- Rollback: drop prayer_updates, support_networks, agreement_data_terms, partnership_agreements, partner_due_diligence, then local_partner_profiles.
