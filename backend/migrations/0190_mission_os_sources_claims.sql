-- Skill 22/23: Source, immutable Snapshot, Claim and Evidence with conflict handling.
CREATE TABLE IF NOT EXISTS mission_sources (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,
 source_type TEXT NOT NULL CHECK(source_type IN('official_statistics','public_government_document','academic_research','mission_agency_report','bible_translation_organization','local_church_report','local_partner_interview','community_member_interview','field_observation','public_media','organization_internal_record','user_submission','ai_generated_candidate','unknown')),
 title TEXT NOT NULL,publisher_or_owner TEXT,author TEXT,publication_date DATE,original_language TEXT,source_locator TEXT,
 license_or_usage_notes TEXT,trust_profile JSONB NOT NULL DEFAULT '{}'::jsonb,public_visibility BOOLEAN NOT NULL DEFAULT FALSE,
 sensitivity_level TEXT NOT NULL DEFAULT 'P1' CHECK(sensitivity_level IN('P0','P1','P2','P3','P4')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_source_snapshots (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,source_id UUID NOT NULL REFERENCES mission_sources(id),
 captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),content_hash TEXT NOT NULL,storage_reference TEXT,extracted_text_reference TEXT,
 metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,snapshot_status TEXT NOT NULL DEFAULT 'captured',created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE(tenant_id,source_id,content_hash));
CREATE TABLE IF NOT EXISTS mission_claims (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,subject_type TEXT NOT NULL,subject_id TEXT NOT NULL,
 predicate TEXT NOT NULL,normalized_value_json JSONB,human_readable_claim TEXT NOT NULL,
 claim_type TEXT NOT NULL CHECK(claim_type IN('observed_fact','reported_statistic','reported_assessment','local_testimony','researcher_interpretation','strategic_hypothesis','ai_candidate','theological_reflection')),
 status TEXT NOT NULL DEFAULT 'candidate' CHECK(status IN('candidate','under_review','supported','locally_confirmed','disputed','outdated','rejected','superseded')),
 confidence TEXT NOT NULL DEFAULT 'unknown',valid_from DATE,valid_to DATE,as_of_date DATE,
 created_by_type TEXT NOT NULL CHECK(created_by_type IN('human','ai','system')),created_by_id TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK(claim_type<>'reported_statistic' OR as_of_date IS NOT NULL),CHECK(claim_type<>'ai_candidate' OR created_by_type IN('ai','system')));
CREATE TABLE IF NOT EXISTS mission_claim_evidence (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,claim_id UUID NOT NULL REFERENCES mission_claims(id),
 source_id UUID NOT NULL REFERENCES mission_sources(id),snapshot_id UUID REFERENCES mission_source_snapshots(id),
 evidence_type TEXT NOT NULL,stance TEXT NOT NULL CHECK(stance IN('supports','partially_supports','contradicts','contextualizes','supersedes','uncertain')),
 excerpt_or_summary TEXT,locator_detail TEXT,evidence_weight TEXT NOT NULL DEFAULT 'medium',added_by TEXT NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_claim_conflicts (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,subject_type TEXT NOT NULL,subject_id TEXT NOT NULL,
 claim_a_id UUID NOT NULL REFERENCES mission_claims(id),claim_b_id UUID NOT NULL REFERENCES mission_claims(id),
 conflict_type TEXT NOT NULL,materiality TEXT NOT NULL DEFAULT 'medium',
 resolution_status TEXT NOT NULL DEFAULT 'detected' CHECK(resolution_status IN('detected','triaged','research_required','local_review_required','resolved_keep_both','resolved_prefer_a','resolved_prefer_b','resolved_new_claim','unresolved')),
 resolution_summary TEXT,resolved_by TEXT,resolved_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),CHECK(claim_a_id<>claim_b_id));
ALTER TABLE mission_sources ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_source_snapshots ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_claims ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_claim_evidence ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_claim_conflicts ENABLE ROW LEVEL SECURITY;
DO $$DECLARE t TEXT;BEGIN FOREACH t IN ARRAY ARRAY['mission_sources','mission_source_snapshots','mission_claims','mission_claim_evidence','mission_claim_conflicts'] LOOP EXECUTE format('CREATE POLICY mission_tenant_isolation ON %I USING(tenant_id=current_setting(''app.tenant_id'',true)) WITH CHECK(tenant_id=current_setting(''app.tenant_id'',true))',t);END LOOP;END$$;
CREATE INDEX IF NOT EXISTS idx_mission_claims_subject ON mission_claims(tenant_id,subject_type,subject_id,status);
CREATE INDEX IF NOT EXISTS idx_mission_claim_evidence_claim ON mission_claim_evidence(tenant_id,claim_id);
CREATE INDEX IF NOT EXISTS idx_mission_sources_type ON mission_sources(tenant_id,source_type,publication_date);
-- Rollback: drop conflicts, evidence, claims, snapshots, then sources.
