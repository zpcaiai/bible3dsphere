-- Skill 50/52/53: church confirmation, candidate application, committee and decision.
CREATE TABLE IF NOT EXISTS mission_church_confirmations (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,sending_journey_id TEXT,church_organization_id TEXT NOT NULL,
 confirmation_version INTEGER NOT NULL DEFAULT 1,confirmation_status TEXT NOT NULL DEFAULT 'draft',observation_period_months INTEGER NOT NULL DEFAULT 0,
 support_level TEXT CHECK(support_level IS NULL OR support_level IN('unable_to_confirm','insufficient_observation','support_exploration','support_with_conditions','support_sending_process','recommend_pause')),
 conditions JSONB NOT NULL DEFAULT '[]'::jsonb,decided_by_panel_id TEXT,effective_at TIMESTAMPTZ,expires_at TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_church_confirmation_reviews (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,church_confirmation_id UUID NOT NULL REFERENCES mission_church_confirmations(id),
 reviewer_id TEXT NOT NULL,reviewer_role TEXT,relationship_duration_months INTEGER,recommendation TEXT,conflict_of_interest_status TEXT NOT NULL DEFAULT 'none',
 submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),created_at TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(tenant_id,church_confirmation_id,reviewer_id));
CREATE TABLE IF NOT EXISTS mission_candidate_applications (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,sending_journey_id TEXT,worker_profile_id TEXT NOT NULL,
 target_role_id TEXT,target_field_id TEXT,sending_church_id TEXT,mission_agency_id TEXT,receiving_organization_id TEXT,target_team_id TEXT,
 application_version INTEGER NOT NULL DEFAULT 1,application_status TEXT NOT NULL DEFAULT 'draft',intended_start_window TEXT,expected_term_months INTEGER,
 submitted_at TIMESTAMPTZ,withdrawn_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_application_sections (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,application_id UUID NOT NULL REFERENCES mission_candidate_applications(id),
 section_key TEXT NOT NULL,section_status TEXT NOT NULL DEFAULT 'missing',content_reference TEXT,required BOOLEAN NOT NULL DEFAULT TRUE,
 last_verified_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(tenant_id,application_id,section_key));
CREATE TABLE IF NOT EXISTS mission_sending_committees (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,name TEXT NOT NULL,committee_type TEXT,quorum_rules JSONB NOT NULL DEFAULT '{}'::jsonb,
 voting_rules JSONB NOT NULL DEFAULT '{}'::jsonb,status TEXT NOT NULL DEFAULT 'active',created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_sending_committee_members (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,committee_id UUID NOT NULL REFERENCES mission_sending_committees(id),
 user_id TEXT NOT NULL,member_role TEXT NOT NULL,represents_organization_id TEXT,voting_right BOOLEAN NOT NULL DEFAULT TRUE,is_ai BOOLEAN NOT NULL DEFAULT FALSE,
 status TEXT NOT NULL DEFAULT 'active',created_at TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(tenant_id,committee_id,user_id));
CREATE TABLE IF NOT EXISTS mission_sending_committee_meetings (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,committee_id UUID NOT NULL REFERENCES mission_sending_committees(id),
 application_id UUID NOT NULL REFERENCES mission_candidate_applications(id),meeting_status TEXT NOT NULL DEFAULT 'scheduled',scheduled_at TIMESTAMPTZ,
 quorum_status TEXT NOT NULL DEFAULT 'unknown',chair_id TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),completed_at TIMESTAMPTZ);
CREATE TABLE IF NOT EXISTS mission_sending_committee_votes (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,meeting_id UUID NOT NULL REFERENCES mission_sending_committee_meetings(id),
 committee_member_id UUID NOT NULL REFERENCES mission_sending_committee_members(id),vote TEXT NOT NULL CHECK(vote IN('approve','conditionally_approve','abstain','oppose')),
 conflict_disclosed BOOLEAN NOT NULL DEFAULT FALSE,rationale_summary TEXT,cast_at TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(tenant_id,meeting_id,committee_member_id));
CREATE TABLE IF NOT EXISTS mission_sending_decisions (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,application_id UUID NOT NULL REFERENCES mission_candidate_applications(id),meeting_id TEXT,
 decision_type TEXT NOT NULL CHECK(decision_type IN('approved_for_next_stage','conditionally_approved','deferred','revision_required','declined_current_application','withdrawn','revoked','expired')),
 decision_version INTEGER NOT NULL DEFAULT 1,rationale_summary TEXT,conditions JSONB NOT NULL DEFAULT '[]'::jsonb,unlocks TEXT NOT NULL DEFAULT 'unlock_batch6_preparation',
 effective_at TIMESTAMPTZ NOT NULL DEFAULT now(),expires_at TIMESTAMPTZ,supersedes_decision_id TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT now());
ALTER TABLE mission_church_confirmations ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_church_confirmation_reviews ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_candidate_applications ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_application_sections ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_sending_committees ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_sending_committee_members ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_sending_committee_meetings ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_sending_committee_votes ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_sending_decisions ENABLE ROW LEVEL SECURITY;
DO $$DECLARE t TEXT;BEGIN FOREACH t IN ARRAY ARRAY['mission_church_confirmations','mission_church_confirmation_reviews','mission_candidate_applications','mission_application_sections','mission_sending_committees','mission_sending_committee_members','mission_sending_committee_meetings','mission_sending_committee_votes','mission_sending_decisions'] LOOP EXECUTE format('DROP POLICY IF EXISTS mission_tenant_isolation ON %I',t);EXECUTE format('CREATE POLICY mission_tenant_isolation ON %I USING(tenant_id=current_setting(''app.tenant_id'',true)) WITH CHECK(tenant_id=current_setting(''app.tenant_id'',true))',t);END LOOP;END$$;
CREATE INDEX IF NOT EXISTS idx_mission_candidate_app_worker ON mission_candidate_applications(tenant_id,worker_profile_id,application_status);
CREATE INDEX IF NOT EXISTS idx_mission_committee_votes_meeting ON mission_sending_committee_votes(tenant_id,meeting_id);
CREATE INDEX IF NOT EXISTS idx_mission_sending_decisions_app ON mission_sending_decisions(tenant_id,application_id,decision_type);
-- Rollback: drop decisions, votes, meetings, committee_members, committees, application_sections, candidate_applications, confirmation_reviews, then church_confirmations.
