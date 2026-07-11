-- MissionBridge Skill 03: independent consent and data lifecycle.
CREATE TABLE IF NOT EXISTS mission_bridge_consent_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id TEXT NOT NULL,
  user_id TEXT NOT NULL, consent_type TEXT NOT NULL,
  policy_version TEXT NOT NULL, language TEXT NOT NULL DEFAULT 'zh-CN',
  purpose TEXT NOT NULL, data_categories JSONB NOT NULL DEFAULT '[]'::jsonb,
  retention_days INTEGER NOT NULL CHECK(retention_days BETWEEN 1 AND 3650),
  granted BOOLEAN NOT NULL DEFAULT FALSE, granted_at TIMESTAMPTZ,
  revoked_at TIMESTAMPTZ, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(tenant_id,user_id,consent_type)
);
CREATE TABLE IF NOT EXISTS mission_bridge_data_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id TEXT NOT NULL,
  user_id TEXT NOT NULL, request_type TEXT NOT NULL CHECK(request_type IN ('export','delete')),
  status TEXT NOT NULL DEFAULT 'pending', scope JSONB NOT NULL DEFAULT '{}'::jsonb,
  safety_records_retained BOOLEAN NOT NULL DEFAULT TRUE,
  requested_at TIMESTAMPTZ NOT NULL DEFAULT now(), completed_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS mission_bridge_retention_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id TEXT,
  records_anonymized INTEGER NOT NULL DEFAULT 0, records_deleted INTEGER NOT NULL DEFAULT 0,
  errors JSONB NOT NULL DEFAULT '[]'::jsonb, started_at TIMESTAMPTZ NOT NULL DEFAULT now(), completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_mb_consent_user ON mission_bridge_consent_records(tenant_id,user_id,consent_type);
CREATE INDEX IF NOT EXISTS idx_mb_data_requests_status ON mission_bridge_data_requests(status,requested_at);
ALTER TABLE mission_bridge_consent_records ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS mission_bridge_tenant_isolation ON mission_bridge_consent_records;
CREATE POLICY mission_bridge_tenant_isolation ON mission_bridge_consent_records USING(tenant_id=current_setting('app.tenant_id',true)) WITH CHECK(tenant_id=current_setting('app.tenant_id',true));
ALTER TABLE mission_bridge_data_requests ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS mission_bridge_tenant_isolation ON mission_bridge_data_requests;
CREATE POLICY mission_bridge_tenant_isolation ON mission_bridge_data_requests USING(tenant_id=current_setting('app.tenant_id',true)) WITH CHECK(tenant_id=current_setting('app.tenant_id',true));
