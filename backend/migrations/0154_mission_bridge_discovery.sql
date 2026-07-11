-- MissionBridge Skill 04: community-led discovery and need mapping.
CREATE TABLE IF NOT EXISTS mission_bridge_group_proposals (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,title TEXT NOT NULL,group_description TEXT NOT NULL,
 need_claimed_by TEXT NOT NULL,community_self_description TEXT NOT NULL,existing_resources JSONB NOT NULL DEFAULT '[]'::jsonb,
 entry_channels JSONB NOT NULL DEFAULT '[]'::jsonb,potential_risks JSONB NOT NULL DEFAULT '[]'::jsonb,
 capability_gaps JSONB NOT NULL DEFAULT '[]'::jsonb,status TEXT NOT NULL DEFAULT 'discovery',created_by TEXT NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS mission_bridge_discovery_interviews (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,proposal_id UUID NOT NULL REFERENCES mission_bridge_group_proposals(id),
 participant_kind TEXT NOT NULL,anonymous BOOLEAN NOT NULL DEFAULT TRUE,consent_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
 interviewer_user_id TEXT NOT NULL,conducted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS mission_bridge_interview_responses (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,interview_id UUID NOT NULL REFERENCES mission_bridge_discovery_interviews(id),
 question TEXT NOT NULL,response TEXT NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS mission_bridge_observed_needs (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,proposal_id UUID NOT NULL REFERENCES mission_bridge_group_proposals(id),
 label TEXT NOT NULL,category TEXT NOT NULL,frequency INTEGER NOT NULL DEFAULT 1,severity INTEGER NOT NULL DEFAULT 1,
 expressed_by_community BOOLEAN NOT NULL DEFAULT FALSE,service_boundary TEXT NOT NULL DEFAULT 'church_can_support',
 source TEXT NOT NULL DEFAULT 'researcher',confirmed_by TEXT,confirmed_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS mission_bridge_community_assets (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,proposal_id UUID NOT NULL REFERENCES mission_bridge_group_proposals(id),
 name TEXT NOT NULL,asset_type TEXT NOT NULL,verified BOOLEAN NOT NULL DEFAULT FALSE,notes TEXT
);
CREATE TABLE IF NOT EXISTS mission_bridge_pilot_hypotheses (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,proposal_id UUID NOT NULL REFERENCES mission_bridge_group_proposals(id),
 hypothesis TEXT NOT NULL,success_evidence JSONB NOT NULL DEFAULT '[]'::jsonb,decision TEXT NOT NULL DEFAULT 'pending',review_notes TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_mb_discovery_proposal ON mission_bridge_discovery_interviews(tenant_id,proposal_id,conducted_at);
CREATE INDEX IF NOT EXISTS idx_mb_needs_proposal ON mission_bridge_observed_needs(tenant_id,proposal_id,confirmed_at);
