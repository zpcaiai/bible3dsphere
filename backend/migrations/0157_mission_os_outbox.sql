-- Mission OS Skill 05: transactional outbox and idempotent delivery ledger.
CREATE TABLE IF NOT EXISTS mission_outbox_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(), tenant_id TEXT NOT NULL,
  aggregate_type TEXT NOT NULL, aggregate_id TEXT NOT NULL,
  event_type TEXT NOT NULL, event_version INTEGER NOT NULL CHECK(event_version>0),
  payload JSONB NOT NULL, occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  published_at TIMESTAMPTZ, attempts INTEGER NOT NULL DEFAULT 0,
  next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(), last_error TEXT,
  correlation_id TEXT NOT NULL, causation_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_mission_outbox_pending ON mission_outbox_events(next_attempt_at,occurred_at) WHERE published_at IS NULL;
CREATE TABLE IF NOT EXISTS mission_event_deliveries (
  consumer_key TEXT NOT NULL, event_id UUID NOT NULL REFERENCES mission_outbox_events(id),
  status TEXT NOT NULL CHECK(status IN('processing','completed','failed')),
  attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT, completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY(consumer_key,event_id)
);
CREATE TABLE IF NOT EXISTS mission_dead_letter_events (
  event_id UUID PRIMARY KEY REFERENCES mission_outbox_events(id), reason TEXT NOT NULL,
  failed_at TIMESTAMPTZ NOT NULL DEFAULT now(), replayed_at TIMESTAMPTZ,
  replayed_by TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE mission_outbox_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS mission_outbox_tenant_isolation ON mission_outbox_events;
CREATE POLICY mission_outbox_tenant_isolation ON mission_outbox_events
 USING(tenant_id=current_setting('app.tenant_id',true)) WITH CHECK(tenant_id=current_setting('app.tenant_id',true));
-- Rollback: DROP TABLE mission_dead_letter_events, mission_event_deliveries, mission_outbox_events;
