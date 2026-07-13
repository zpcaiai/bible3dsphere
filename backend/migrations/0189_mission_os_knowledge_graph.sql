-- Skill 17: people-group / language / religion many-to-many knowledge graph.
CREATE TABLE IF NOT EXISTS mission_people_groups (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,canonical_name TEXT NOT NULL,
 preferred_self_name TEXT,description TEXT,sensitivity_level TEXT NOT NULL DEFAULT 'P1' CHECK(sensitivity_level IN('P0','P1','P2','P3','P4')),
 research_status TEXT NOT NULL DEFAULT 'unresearched',data_confidence TEXT NOT NULL DEFAULT 'unknown',
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_languages (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,canonical_name TEXT NOT NULL,autonym TEXT,
 standardized_code TEXT,language_family TEXT,writing_system_summary TEXT,vitality_status TEXT,
 data_confidence TEXT NOT NULL DEFAULT 'unknown',created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_religious_traditions (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,name TEXT NOT NULL,parent_tradition_id UUID REFERENCES mission_religious_traditions(id),
 description TEXT,public_reference_only BOOLEAN NOT NULL DEFAULT TRUE,created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_people_group_language_links (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,people_group_id UUID NOT NULL REFERENCES mission_people_groups(id),
 language_id UUID NOT NULL REFERENCES mission_languages(id),
 relationship_type TEXT NOT NULL CHECK(relationship_type IN('primary_language','heritage_language','trade_language','liturgical_language','second_language','sign_language','declining_language')),
 estimated_usage_level TEXT,source_claim_id UUID,confidence TEXT NOT NULL DEFAULT 'unknown',created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE(tenant_id,people_group_id,language_id,relationship_type));
CREATE TABLE IF NOT EXISTS mission_people_group_region_links (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,people_group_id UUID NOT NULL REFERENCES mission_people_groups(id),
 field_id UUID NOT NULL REFERENCES mission_fields(id),
 relationship_type TEXT NOT NULL CHECK(relationship_type IN('historic_homeland','current_majority_region','current_minority_region','diaspora_region','seasonal_presence','migration_corridor')),
 population_estimate_low INTEGER,population_estimate_high INTEGER,estimate_as_of_date DATE,source_claim_id UUID,confidence TEXT NOT NULL DEFAULT 'unknown',created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_people_group_religion_links (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,people_group_id UUID NOT NULL REFERENCES mission_people_groups(id),
 religious_tradition_id UUID NOT NULL REFERENCES mission_religious_traditions(id),
 relationship_type TEXT NOT NULL CHECK(relationship_type IN('majority_affiliation','minority_affiliation','historic_tradition','syncretic_practice','secularizing_context','unknown_or_diverse')),
 estimated_share_low NUMERIC(4,3),estimated_share_high NUMERIC(4,3),context_summary TEXT,source_claim_id UUID,confidence TEXT NOT NULL DEFAULT 'unknown',created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK(estimated_share_low IS NULL OR (estimated_share_low>=0 AND estimated_share_high>=estimated_share_low AND estimated_share_high<=1)));
ALTER TABLE mission_people_groups ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_languages ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_religious_traditions ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_people_group_language_links ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_people_group_region_links ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_people_group_religion_links ENABLE ROW LEVEL SECURITY;
DO $$DECLARE t TEXT;BEGIN FOREACH t IN ARRAY ARRAY['mission_people_groups','mission_languages','mission_religious_traditions','mission_people_group_language_links','mission_people_group_region_links','mission_people_group_religion_links'] LOOP EXECUTE format('CREATE POLICY mission_tenant_isolation ON %I USING(tenant_id=current_setting(''app.tenant_id'',true)) WITH CHECK(tenant_id=current_setting(''app.tenant_id'',true))',t);END LOOP;END$$;
CREATE INDEX IF NOT EXISTS idx_mission_pg_lang ON mission_people_group_language_links(tenant_id,people_group_id);
CREATE INDEX IF NOT EXISTS idx_mission_pg_region ON mission_people_group_region_links(tenant_id,people_group_id,field_id);
CREATE INDEX IF NOT EXISTS idx_mission_pg_religion ON mission_people_group_religion_links(tenant_id,people_group_id);
-- Rollback: drop the three link tables, then religions, languages, people_groups.
