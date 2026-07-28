-- MANUAL ROLLBACK ONLY. The migration runner intentionally scans only
-- backend/migrations/*.sql, so this file is never applied automatically.
-- This rollback permanently removes all EMD-OS Batch 3 data and must be executed
-- only after an explicit backup/retention decision.

BEGIN;

DROP TABLE IF EXISTS formation_twin_emd_growth_evaluations;
DROP TABLE IF EXISTS formation_twin_emd_checkpoints;
DROP TABLE IF EXISTS formation_twin_emd_patterns;
DROP TABLE IF EXISTS formation_twin_emd_transfer_observations;
DROP TABLE IF EXISTS formation_twin_emd_repair_verifications;
DROP TABLE IF EXISTS formation_twin_emd_recovery_metric_sets;
DROP TABLE IF EXISTS formation_twin_emd_event_timelines;
DROP TABLE IF EXISTS formation_twin_emd_real_life_events;

COMMIT;
