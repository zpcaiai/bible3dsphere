-- MANUAL ROLLBACK ONLY. The migration runner intentionally scans only
-- backend/migrations/*.sql, so this file is never applied automatically.
-- This rollback permanently removes all EMD-OS Batch 10 certification artefacts
-- and must be executed only after an explicit backup/retention decision.

BEGIN;

DROP TABLE IF EXISTS production_emd_incidents;
DROP TABLE IF EXISTS production_emd_change_controls;
DROP TABLE IF EXISTS production_emd_release_certificates;
DROP TABLE IF EXISTS production_emd_gate_reports;
DROP TABLE IF EXISTS production_emd_intended_use_profiles;

COMMIT;
