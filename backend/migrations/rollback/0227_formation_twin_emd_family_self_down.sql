-- MANUAL ROLLBACK ONLY. The migration runner intentionally scans only
-- backend/migrations/*.sql, so this file is never applied automatically.
-- This rollback permanently removes all EMD-OS Batch 5 data and must be executed
-- only after an explicit backup/retention decision.

BEGIN;

DROP TABLE IF EXISTS formation_twin_emd_vulnerability_experiments;
DROP TABLE IF EXISTS formation_twin_emd_true_self_compasses;
DROP TABLE IF EXISTS formation_twin_emd_mask_profiles;
DROP TABLE IF EXISTS formation_twin_emd_survival_oaths;
DROP TABLE IF EXISTS formation_twin_emd_differentiation_assessments;
DROP TABLE IF EXISTS formation_twin_emd_attachment_cycles;
DROP TABLE IF EXISTS formation_twin_emd_family_patterns;
DROP TABLE IF EXISTS formation_twin_emd_genograms;

COMMIT;
