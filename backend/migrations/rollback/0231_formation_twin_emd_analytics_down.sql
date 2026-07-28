-- MANUAL ROLLBACK ONLY. The migration runner intentionally scans only
-- backend/migrations/*.sql, so this file is never applied automatically.
-- This rollback permanently removes all EMD-OS Batch 9 data and must be executed
-- only after an explicit backup/retention decision.

BEGIN;

DROP TABLE IF EXISTS formation_twin_emd_growth_reports;
DROP TABLE IF EXISTS formation_twin_emd_attributions;
DROP TABLE IF EXISTS formation_twin_emd_generalizations;
DROP TABLE IF EXISTS formation_twin_emd_trajectories;
DROP TABLE IF EXISTS formation_twin_emd_comparability_checks;
DROP TABLE IF EXISTS formation_twin_emd_reassessment_compositions;
DROP TABLE IF EXISTS formation_twin_emd_metric_observations;
DROP TABLE IF EXISTS formation_twin_emd_metric_catalog;

COMMIT;
