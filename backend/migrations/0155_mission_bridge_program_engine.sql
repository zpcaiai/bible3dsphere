-- MissionBridge Skill 05: configurable, immutable program engine.
CREATE TABLE IF NOT EXISTS mission_bridge_program_instances (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,program_id TEXT NOT NULL,program_version TEXT NOT NULL,
 title TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'draft',starts_at TIMESTAMPTZ,ends_at TIMESTAMPTZ,created_by TEXT NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS mission_bridge_program_pathways (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),program_id TEXT NOT NULL,program_version TEXT NOT NULL,key TEXT NOT NULL,title TEXT NOT NULL,
 eligibility JSONB NOT NULL DEFAULT '{}'::jsonb,UNIQUE(program_id,program_version,key)
);
CREATE TABLE IF NOT EXISTS mission_bridge_program_steps (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),program_id TEXT NOT NULL,program_version TEXT NOT NULL,pathway_key TEXT NOT NULL,
 step_order INTEGER NOT NULL,title TEXT NOT NULL,step_type TEXT NOT NULL,required BOOLEAN NOT NULL DEFAULT TRUE,
 condition JSONB,content_refs JSONB NOT NULL DEFAULT '[]'::jsonb,UNIQUE(program_id,program_version,pathway_key,step_order)
);
CREATE TABLE IF NOT EXISTS mission_bridge_program_pauses (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,enrollment_id UUID NOT NULL REFERENCES mission_bridge_enrollments(id),
 paused_by TEXT NOT NULL,paused_at TIMESTAMPTZ NOT NULL DEFAULT now(),resumed_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS mission_bridge_program_outcomes (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,enrollment_id UUID NOT NULL REFERENCES mission_bridge_enrollments(id),
 metric_key TEXT NOT NULL,value JSONB NOT NULL,evidence_source TEXT NOT NULL,recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_mb_instances_tenant ON mission_bridge_program_instances(tenant_id,status,starts_at);
