-- MANUAL ROLLBACK ONLY. The migration runner intentionally scans only
-- backend/migrations/*.sql, so this file is never applied automatically.
-- This rollback permanently removes all EMD-OS Batch 7 data and must be executed
-- only after an explicit backup/retention decision.

BEGIN;

DROP TABLE IF EXISTS formation_twin_emd_grief_integrations;
DROP TABLE IF EXISTS formation_twin_emd_rest_rhythms;
DROP TABLE IF EXISTS formation_twin_emd_rituals;
DROP TABLE IF EXISTS formation_twin_emd_bypassing_checks;
DROP TABLE IF EXISTS formation_twin_emd_ambiguous_losses;
DROP TABLE IF EXISTS formation_twin_emd_control_calibrations;
DROP TABLE IF EXISTS formation_twin_emd_grief_sessions;
DROP TABLE IF EXISTS formation_twin_emd_losses;

COMMIT;
