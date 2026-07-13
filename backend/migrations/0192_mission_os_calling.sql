-- Skill 28/29/30/35: calling journey, motives/blockers, confirmation, pause/appeal.
CREATE TABLE IF NOT EXISTS mission_calling_journeys (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,user_id TEXT NOT NULL,organization_id TEXT,mentor_id TEXT,
 journey_status TEXT NOT NULL DEFAULT 'draft' CHECK(journey_status IN('draft','active_discernment','waiting_for_feedback','local_practice_required','training_required','paused','ready_for_readiness_assessment','completed','withdrawn','archived')),
 calling_orientation TEXT CHECK(calling_orientation IS NULL OR calling_orientation IN('general_christian_mission','local_evangelism','cross_cultural_mission','diaspora_ministry','church_equipping','bible_translation_support','professional_mission','member_care','prayer_and_mobilization','sending_church_service','mission_research','digital_mission_infrastructure','undetermined')),
 field_interest TEXT,primary_question TEXT,current_stage TEXT,visibility_level TEXT NOT NULL DEFAULT 'P2',
 started_at TIMESTAMPTZ NOT NULL DEFAULT now(),target_review_at TIMESTAMPTZ,completed_at TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_calling_reflections (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,calling_journey_id UUID NOT NULL REFERENCES mission_calling_journeys(id),
 reflection_type TEXT NOT NULL,title TEXT,content TEXT,occurred_at TIMESTAMPTZ,confidence_level TEXT,
 privacy_level TEXT NOT NULL DEFAULT 'P2',ai_processing_allowed BOOLEAN NOT NULL DEFAULT FALSE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_calling_evidence (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,calling_journey_id UUID NOT NULL REFERENCES mission_calling_journeys(id),
 evidence_type TEXT NOT NULL CHECK(evidence_type IN('subjective_impression','church_feedback','mentor_feedback','family_feedback','ministry_supervision','local_practice','cross_cultural_practice','formation_progress')),
 evidence_summary TEXT,source_type TEXT,source_id TEXT,strength TEXT,supports_direction TEXT,requires_review BOOLEAN NOT NULL DEFAULT FALSE,created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_calling_blockers (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,calling_journey_id UUID NOT NULL REFERENCES mission_calling_journeys(id),
 blocker_type TEXT NOT NULL,severity TEXT NOT NULL CHECK(severity IN('observation','development_needed','significant_concern','hard_block')),
 summary TEXT,remediation_required BOOLEAN NOT NULL DEFAULT TRUE,status TEXT NOT NULL DEFAULT 'open',owner_id TEXT,review_due_at TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_feedback_requests (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,calling_journey_id UUID NOT NULL REFERENCES mission_calling_journeys(id),
 requester_id TEXT NOT NULL,respondent_type TEXT NOT NULL,respondent_user_id TEXT,external_recipient_reference TEXT,
 requested_sections JSONB NOT NULL DEFAULT '[]'::jsonb,consent_record_id TEXT,status TEXT NOT NULL DEFAULT 'pending',
 due_at TIMESTAMPTZ,expires_at TIMESTAMPTZ NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK(respondent_user_id IS NULL OR respondent_user_id<>requester_id));
CREATE TABLE IF NOT EXISTS mission_feedback_responses (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,feedback_request_id UUID NOT NULL REFERENCES mission_feedback_requests(id),
 response_summary TEXT,structured_response_json JSONB,confidentiality_level TEXT NOT NULL DEFAULT 'P3',
 recommendation TEXT CHECK(recommendation IS NULL OR recommendation IN('support_continue','support_with_development','recommend_pause','significant_concern','insufficient_observation','unable_to_assess')),
 concern_level TEXT,submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_worker_pauses (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,subject_type TEXT NOT NULL,subject_id TEXT NOT NULL,
 pause_reason TEXT NOT NULL,visibility_level TEXT NOT NULL DEFAULT 'P3',summary TEXT,initiated_by TEXT NOT NULL,
 starts_at TIMESTAMPTZ NOT NULL DEFAULT now(),expected_review_at TIMESTAMPTZ,status TEXT NOT NULL DEFAULT 'active',
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_assessment_appeals (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,assessment_id TEXT NOT NULL,appellant_id TEXT NOT NULL,
 appeal_type TEXT NOT NULL,appeal_summary TEXT,status TEXT NOT NULL DEFAULT 'submitted',
 independent_reviewer_id TEXT,original_decider_id TEXT,resolution_summary TEXT,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),resolved_at TIMESTAMPTZ,
 CHECK(independent_reviewer_id IS NULL OR (independent_reviewer_id<>appellant_id AND (original_decider_id IS NULL OR independent_reviewer_id<>original_decider_id))));
ALTER TABLE mission_calling_journeys ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_calling_reflections ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_calling_evidence ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_calling_blockers ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_feedback_requests ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_feedback_responses ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_worker_pauses ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_assessment_appeals ENABLE ROW LEVEL SECURITY;
DO $$DECLARE t TEXT;BEGIN FOREACH t IN ARRAY ARRAY['mission_calling_journeys','mission_calling_reflections','mission_calling_evidence','mission_calling_blockers','mission_feedback_requests','mission_feedback_responses','mission_worker_pauses','mission_assessment_appeals'] LOOP EXECUTE format('DROP POLICY IF EXISTS mission_tenant_isolation ON %I',t);EXECUTE format('CREATE POLICY mission_tenant_isolation ON %I USING(tenant_id=current_setting(''app.tenant_id'',true)) WITH CHECK(tenant_id=current_setting(''app.tenant_id'',true))',t);END LOOP;END$$;
CREATE INDEX IF NOT EXISTS idx_mission_calling_user ON mission_calling_journeys(tenant_id,user_id,journey_status);
CREATE INDEX IF NOT EXISTS idx_mission_calling_reflection_j ON mission_calling_reflections(tenant_id,calling_journey_id);
CREATE INDEX IF NOT EXISTS idx_mission_feedback_req_j ON mission_feedback_requests(tenant_id,calling_journey_id,status);
-- Rollback: drop appeals, pauses, feedback_responses, feedback_requests, blockers, evidence, reflections, then journeys.
