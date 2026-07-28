-- MANUAL ROLLBACK ONLY. The migration runner intentionally scans only
-- backend/migrations/*.sql, so this file is never applied automatically.
-- This rollback permanently removes all EMD-OS Batch 1 data and must be executed
-- only after an explicit backup/retention decision.

BEGIN;

DROP TABLE IF EXISTS formation_twin_emd_reassessment_plans;
DROP TABLE IF EXISTS formation_twin_emd_corrections;
DROP TABLE IF EXISTS formation_twin_emd_growth_routes;
DROP TABLE IF EXISTS formation_twin_emd_profiles;
DROP TABLE IF EXISTS formation_twin_emd_dimension_snapshots;
DROP TABLE IF EXISTS formation_twin_emd_evidence_items;
DROP TABLE IF EXISTS formation_twin_emd_sessions;
DROP TABLE IF EXISTS formation_twin_emd_consents;

COMMIT;
