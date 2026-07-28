-- 回滚 0235：恢复 0233 的统计口径（注意：0233 的口径本身是错的，
-- 回滚后 emd_erasure_coverage() 会重新变成永远无法满足的自检）。
DROP FUNCTION IF EXISTS emd_erasure_excluded_tables();
DROP FUNCTION IF EXISTS emd_personal_identifier_columns();
-- emd_erasure_coverage() 由 0233 重新 CREATE OR REPLACE 覆盖即可，签名未变。
