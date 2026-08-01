-- DESTRUCTIVE ROLLBACK — require reviewed export/deletion evidence first.
-- Preconditions:
--   1. SUNDAY_SCHOOL_AI_FORMATION_ENABLED=false in every environment.
--   2. No deployment still writes these tables.
--   3. The data-rights owner has approved retention/export/deletion handling.
--   4. A database owner has a verified backup and incident ticket.

DROP TABLE IF EXISTS sunday_school_ai_formation_release_decisions;
DROP TABLE IF EXISTS sunday_school_ai_formation_release_evidence;
DROP TABLE IF EXISTS sunday_school_ai_formation_content_reviews;
DROP TABLE IF EXISTS sunday_school_ai_formation_content;
DROP TABLE IF EXISTS sunday_school_ai_formation_audit;
DROP TABLE IF EXISTS sunday_school_ai_formation_records;
