-- MANUAL ROLLBACK ONLY. The migration runner intentionally scans only
-- backend/migrations/*.sql, so this file is never applied automatically.
-- This rollback permanently removes all EMD-OS Batch 4 data and must be executed
-- only after an explicit backup/retention decision.

BEGIN;

DROP TABLE IF EXISTS formation_twin_emd_rehearsals;
DROP TABLE IF EXISTS formation_twin_emd_recovery_plans;
DROP TABLE IF EXISTS formation_twin_emd_coregulation_requests;
DROP TABLE IF EXISTS formation_twin_emd_support_persons;
DROP TABLE IF EXISTS formation_twin_emd_impulse_guards;
DROP TABLE IF EXISTS formation_twin_emd_pause_protocols;
DROP TABLE IF EXISTS formation_twin_emd_trigger_profiles;
DROP TABLE IF EXISTS formation_twin_emd_regulation_sessions;

COMMIT;
