-- Skill 16: Mission Field core model (geographic + non-geographic), public/sensitive split.
CREATE TABLE IF NOT EXISTS mission_fields (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,parent_field_id UUID REFERENCES mission_fields(id),
 field_type TEXT NOT NULL CHECK(field_type IN('geographic_region','country','province_or_state','city','urban_district','rural_area','people_group','language_community','diaspora_community','migrant_worker_community','international_student_community','professional_community','digital_community','church_internal_group','caregiver_community','accessibility_community','ministry_network')),
 canonical_name TEXT NOT NULL,display_name TEXT,slug TEXT,description TEXT,
 country_code TEXT CHECK(country_code IS NULL OR length(country_code)=2),primary_region_code TEXT,
 public_visibility BOOLEAN NOT NULL DEFAULT FALSE,sensitivity_level TEXT NOT NULL DEFAULT 'P1' CHECK(sensitivity_level IN('P0','P1','P2','P3','P4')),
 lifecycle_status TEXT NOT NULL DEFAULT 'draft' CHECK(lifecycle_status IN('draft','active','inactive','merged','archived')),
 research_status TEXT NOT NULL DEFAULT 'unresearched' CHECK(research_status IN('unresearched','initial_research','evidence_gathering','local_validation_pending','locally_validated','review_required','disputed')),
 data_confidence TEXT NOT NULL DEFAULT 'unknown' CHECK(data_confidence IN('unknown','low','medium','high','locally_verified')),
 owner_organization_id TEXT,created_by TEXT NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),archived_at TIMESTAMPTZ);
CREATE TABLE IF NOT EXISTS mission_field_names (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,field_id UUID NOT NULL REFERENCES mission_fields(id),
 name TEXT NOT NULL,language_code TEXT,name_type TEXT NOT NULL CHECK(name_type IN('canonical','self_identified','external','historical','sensitive_or_discouraged','local_church')),
 usage_status TEXT NOT NULL DEFAULT 'active' CHECK(usage_status IN('active','historical','discouraged')),is_preferred BOOLEAN NOT NULL DEFAULT FALSE,
 source_claim_id UUID,created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_field_geographies (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,field_id UUID NOT NULL REFERENCES mission_fields(id),
 geography_type TEXT NOT NULL,country_code TEXT,administrative_level INTEGER,administrative_code TEXT,
 public_geometry JSONB,sensitive_geometry_reference TEXT,location_precision TEXT NOT NULL DEFAULT 'P1' CHECK(location_precision IN('P0','P1','P2','P3','P4')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_field_relationships (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,source_field_id UUID NOT NULL REFERENCES mission_fields(id),
 target_field_id UUID NOT NULL REFERENCES mission_fields(id),
 relationship_type TEXT NOT NULL CHECK(relationship_type IN('contains','overlaps','migration_source_for','migration_destination_for','diaspora_of','language_related_to','ministry_connected_to','historically_related_to','do_not_merge_with')),
 confidence TEXT NOT NULL DEFAULT 'unknown',source_claim_id UUID,valid_from TIMESTAMPTZ,valid_to TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),CHECK(source_field_id<>target_field_id),UNIQUE(tenant_id,source_field_id,target_field_id,relationship_type));
ALTER TABLE mission_fields ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_field_names ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_field_geographies ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_field_relationships ENABLE ROW LEVEL SECURITY;
DO $$DECLARE t TEXT;BEGIN FOREACH t IN ARRAY ARRAY['mission_fields','mission_field_names','mission_field_geographies','mission_field_relationships'] LOOP EXECUTE format('DROP POLICY IF EXISTS mission_tenant_isolation ON %I',t);EXECUTE format('CREATE POLICY mission_tenant_isolation ON %I USING(tenant_id=current_setting(''app.tenant_id'',true)) WITH CHECK(tenant_id=current_setting(''app.tenant_id'',true))',t);END LOOP;END$$;
CREATE INDEX IF NOT EXISTS idx_mission_fields_tenant_type ON mission_fields(tenant_id,field_type,lifecycle_status);
CREATE INDEX IF NOT EXISTS idx_mission_field_names_field ON mission_field_names(tenant_id,field_id);
CREATE INDEX IF NOT EXISTS idx_mission_field_rel_target ON mission_field_relationships(tenant_id,target_field_id,relationship_type);
-- Rollback: drop relationships, geographies, names, then mission_fields.
