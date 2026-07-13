-- Skill 24: field assessment with separate Need/Evidence/Readiness/Risk and hard blocks.
CREATE TABLE IF NOT EXISTS mission_field_assessment_frameworks (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT,name TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,
 description TEXT,dimension_definitions JSONB NOT NULL DEFAULT '{}'::jsonb,status TEXT NOT NULL DEFAULT 'active' CHECK(status IN('draft','active','retired')),
 effective_at TIMESTAMPTZ NOT NULL DEFAULT now(),retired_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(tenant_id,name,version));
CREATE TABLE IF NOT EXISTS mission_field_assessments (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,field_id UUID NOT NULL REFERENCES mission_fields(id),
 framework_id UUID NOT NULL REFERENCES mission_field_assessment_frameworks(id),organization_id TEXT,team_id TEXT,worker_id TEXT,
 assessment_scope TEXT NOT NULL DEFAULT 'field',status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN('draft','calculated','blocked','under_review','approved','rejected','expired','superseded')),
 need_score NUMERIC(4,3),evidence_score NUMERIC(4,3),readiness_score NUMERIC(4,3),
 risk_level TEXT CHECK(risk_level IS NULL OR risk_level IN('low','medium','high','critical')),
 hard_blocks JSONB NOT NULL DEFAULT '[]'::jsonb,recommendation TEXT,overall_summary TEXT,
 generated_by_type TEXT NOT NULL DEFAULT 'system' CHECK(generated_by_type IN('human','ai','system')),generated_by_id TEXT,
 reviewed_by TEXT,reviewed_at TIMESTAMPTZ,next_review_due_at TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_field_assessment_dimensions (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,assessment_id UUID NOT NULL REFERENCES mission_field_assessments(id),
 dimension_key TEXT NOT NULL,dimension_group TEXT NOT NULL CHECK(dimension_group IN('need','evidence','readiness','risk')),
 raw_value TEXT,normalized_level TEXT,weight NUMERIC(4,3) NOT NULL DEFAULT 1,evidence_claim_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
 confidence TEXT NOT NULL DEFAULT 'unknown',explanation TEXT,blocking BOOLEAN NOT NULL DEFAULT FALSE,created_at TIMESTAMPTZ NOT NULL DEFAULT now());
ALTER TABLE mission_field_assessment_frameworks ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_field_assessments ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_field_assessment_dimensions ENABLE ROW LEVEL SECURITY;
DO $$DECLARE t TEXT;BEGIN FOREACH t IN ARRAY ARRAY['mission_field_assessment_frameworks','mission_field_assessments','mission_field_assessment_dimensions'] LOOP EXECUTE format('DROP POLICY IF EXISTS mission_tenant_isolation ON %I',t);EXECUTE format('CREATE POLICY mission_tenant_isolation ON %I USING(tenant_id=current_setting(''app.tenant_id'',true) OR tenant_id IS NULL) WITH CHECK(tenant_id=current_setting(''app.tenant_id'',true))',t);END LOOP;END$$;
CREATE INDEX IF NOT EXISTS idx_mission_field_assess_field ON mission_field_assessments(tenant_id,field_id,status);
CREATE INDEX IF NOT EXISTS idx_mission_field_assess_dim ON mission_field_assessment_dimensions(tenant_id,assessment_id,dimension_group);
-- Rollback: drop dimensions, assessments, then frameworks.
