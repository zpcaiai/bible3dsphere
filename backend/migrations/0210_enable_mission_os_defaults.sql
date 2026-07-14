-- 0210: Enable Mission OS for production use.
-- The master switch and non-safety-critical module flags default to ON so the
-- 宣教 tab（邻舍之桥 / 工作台）works out of the box. Safety-critical flags
-- (AI, sensitive field visibility, minor programs) stay fail-closed and must be
-- enabled explicitly per tenant via mission_feature_flag_overrides.
-- NOTE: evaluate_flag() additionally requires env MISSION_OS_ENABLED=1.

UPDATE mission_feature_flags SET default_value = TRUE, updated_at = now()
WHERE key IN (
  'mission_os_enabled',
  'mission_field_intelligence_enabled',
  'mission_calling_enabled',
  'mission_readiness_enabled',
  'mission_training_enabled',
  'mission_sending_enabled',
  'mission_deployment_enabled',
  'mission_member_care_enabled'
);

-- Rollback:
-- UPDATE mission_feature_flags SET default_value = FALSE WHERE key IN (...);
