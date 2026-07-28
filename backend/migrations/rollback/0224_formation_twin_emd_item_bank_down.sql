-- MANUAL ROLLBACK ONLY. The migration runner intentionally scans only
-- backend/migrations/*.sql, so this file is never applied automatically.
-- This rollback permanently removes all EMD-OS Batch 2 data and must be executed
-- only after an explicit backup/retention decision.

BEGIN;

DROP TABLE IF EXISTS formation_twin_emd_sufficiency_runs;
DROP TABLE IF EXISTS formation_twin_emd_calibrations;
DROP TABLE IF EXISTS formation_twin_emd_counterfactual_probes;
DROP TABLE IF EXISTS formation_twin_emd_scenarios;
DROP TABLE IF EXISTS formation_twin_emd_rubric_results;
DROP TABLE IF EXISTS formation_twin_emd_behavior_evidence;
DROP TABLE IF EXISTS formation_twin_emd_responses;
DROP TABLE IF EXISTS formation_twin_emd_items;
DROP TABLE IF EXISTS formation_twin_emd_item_banks;

COMMIT;
