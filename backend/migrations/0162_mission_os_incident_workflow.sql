ALTER TABLE incident_reports ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE incident_reports ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ;
ALTER TABLE incident_reports ADD COLUMN IF NOT EXISTS subject_type TEXT NOT NULL DEFAULT 'participant';
ALTER TABLE incident_reports ADD COLUMN IF NOT EXISTS subject_id TEXT;
CREATE TABLE IF NOT EXISTS mission_incident_events (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,incident_id UUID NOT NULL REFERENCES incident_reports(id),
 event_type TEXT NOT NULL,from_status TEXT,to_status TEXT,from_risk_level TEXT,to_risk_level TEXT,
 reason TEXT NOT NULL,actor_id TEXT NOT NULL,actor_role TEXT NOT NULL,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_incident_close_reviews (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,incident_id UUID NOT NULL REFERENCES incident_reports(id),
 reviewer_id TEXT NOT NULL,decision TEXT NOT NULL CHECK(decision IN('approve','reject')),reason TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(incident_id,reviewer_id));
ALTER TABLE mission_incident_events ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_incident_close_reviews ENABLE ROW LEVEL SECURITY;
CREATE POLICY mission_tenant_isolation ON mission_incident_events USING(tenant_id=current_setting('app.tenant_id',true)) WITH CHECK(tenant_id=current_setting('app.tenant_id',true));
CREATE POLICY mission_tenant_isolation ON mission_incident_close_reviews USING(tenant_id=current_setting('app.tenant_id',true)) WITH CHECK(tenant_id=current_setting('app.tenant_id',true));
CREATE INDEX IF NOT EXISTS idx_mission_incident_events ON mission_incident_events(tenant_id,incident_id,created_at);
-- Rollback retains incident columns; drop review/event tables only after exporting required safeguarding history.
