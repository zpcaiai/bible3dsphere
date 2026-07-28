-- MANUAL ROLLBACK ONLY. The migration runner intentionally scans only
-- backend/migrations/*.sql, so this file is never applied automatically.
-- This rollback permanently removes all EMD-OS Batch 6 data and must be executed
-- only after an explicit backup/retention decision.

BEGIN;

DROP TABLE IF EXISTS formation_twin_emd_trust_assessments;
DROP TABLE IF EXISTS formation_twin_emd_restitution_plans;
DROP TABLE IF EXISTS formation_twin_emd_forgiveness_maps;
DROP TABLE IF EXISTS formation_twin_emd_apologies;
DROP TABLE IF EXISTS formation_twin_emd_dialogues;
DROP TABLE IF EXISTS formation_twin_emd_conflict_issues;
DROP TABLE IF EXISTS formation_twin_emd_boundary_enforcements;
DROP TABLE IF EXISTS formation_twin_emd_boundaries;

COMMIT;
