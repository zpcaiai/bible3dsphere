-- Rollback 0233: drop the dynamic-discovery helpers.
-- NOTE: erase_user_data() is left in its dynamic form on purpose — reverting it to
-- the 0145 snapshot would silently restore the EMD deletion gap. Re-apply 0145
-- explicitly if the snapshot behaviour is genuinely wanted.
DROP FUNCTION IF EXISTS emd_erasure_coverage();
DROP FUNCTION IF EXISTS erasure_coverage_gaps();
