-- MANUAL ROLLBACK ONLY. The migration runner intentionally scans only
-- backend/migrations/*.sql, so this file is never applied automatically.
-- This rollback permanently removes all Batch 7 data and must be executed only
-- after an explicit backup/retention decision.

BEGIN;

DROP TABLE IF EXISTS formation_twin_recovery_reviews;
DROP TABLE IF EXISTS formation_twin_warning_feedback;
DROP TABLE IF EXISTS formation_twin_support_requests;
DROP TABLE IF EXISTS formation_twin_protection_actions;
DROP TABLE IF EXISTS formation_twin_early_warnings;
DROP TABLE IF EXISTS formation_twin_risk_snapshots;
DROP TABLE IF EXISTS formation_twin_risk_conditions;
DROP TABLE IF EXISTS formation_twin_temptation_cycle_edges;
DROP TABLE IF EXISTS formation_twin_temptation_cycle_nodes;
DROP TABLE IF EXISTS formation_twin_protection_plans;
DROP TABLE IF EXISTS formation_twin_support_contacts;
DROP TABLE IF EXISTS formation_twin_temptation_cycles;
DROP TABLE IF EXISTS formation_twin_recovery_records;
DROP TABLE IF EXISTS formation_twin_risk_settings;
DROP TABLE IF EXISTS formation_twin_protection_action_templates;

COMMIT;
