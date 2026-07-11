CREATE TABLE IF NOT EXISTS mission_feature_flags (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), key TEXT UNIQUE NOT NULL, description TEXT NOT NULL,
 default_value BOOLEAN NOT NULL DEFAULT FALSE, risk_level TEXT NOT NULL CHECK(risk_level IN('low','medium','high','critical')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_feature_flag_overrides (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(), flag_id UUID NOT NULL REFERENCES mission_feature_flags(id) ON DELETE CASCADE,
 scope_type TEXT NOT NULL CHECK(scope_type IN('global','tenant','organization','program','user','environment')),
 scope_id TEXT NOT NULL, value BOOLEAN NOT NULL, reason TEXT NOT NULL CHECK(length(reason)>=4),
 starts_at TIMESTAMPTZ NOT NULL DEFAULT now(), expires_at TIMESTAMPTZ, created_by TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK(expires_at IS NULL OR expires_at>starts_at));
CREATE INDEX IF NOT EXISTS idx_mission_flag_override_lookup ON mission_feature_flag_overrides(flag_id,scope_type,scope_id,starts_at DESC);
INSERT INTO mission_feature_flags(key,description,default_value,risk_level) VALUES
('mission_os_enabled','Mission OS master switch',FALSE,'critical'),
('mission_field_intelligence_enabled','Field intelligence',FALSE,'medium'),
('mission_calling_enabled','Calling discernment',FALSE,'high'),('mission_readiness_enabled','Worker readiness',FALSE,'high'),
('mission_training_enabled','Mission training',FALSE,'medium'),('mission_sending_enabled','Sending workflows',FALSE,'critical'),
('mission_deployment_enabled','Deployment workflows',FALSE,'critical'),('mission_member_care_enabled','Member care',FALSE,'high'),
('mission_ai_enabled','Mission AI assistance',FALSE,'critical'),('mission_sensitive_fields_enabled','Sensitive field visibility',FALSE,'critical'),
('mission_minor_programs_enabled','Programs involving minors',FALSE,'critical') ON CONFLICT(key) DO NOTHING;
-- Rollback: DROP TABLE mission_feature_flag_overrides; DROP TABLE mission_feature_flags;
