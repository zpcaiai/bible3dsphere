-- MANUAL ROLLBACK ONLY. The migration runner intentionally scans only
-- backend/migrations/*.sql, so this file is never applied automatically.
-- This rollback permanently removes all EMD-OS Batch 8 data and must be executed
-- only after an explicit backup/retention decision.

BEGIN;

DROP TABLE IF EXISTS formation_twin_emd_community_feedback;
DROP TABLE IF EXISTS formation_twin_emd_group_practices;
DROP TABLE IF EXISTS formation_twin_emd_handoffs;
DROP TABLE IF EXISTS formation_twin_emd_pastoral_summaries;
DROP TABLE IF EXISTS formation_twin_emd_formation_plans;
DROP TABLE IF EXISTS formation_twin_emd_rules_of_life;
DROP TABLE IF EXISTS formation_twin_emd_prayer_routings;
DROP TABLE IF EXISTS formation_twin_emd_identity_alignments;
DROP TABLE IF EXISTS formation_twin_emd_twin_bridges;

COMMIT;
