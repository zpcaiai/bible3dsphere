-- Migration 0144: enforce NOT NULL on personal-table ownership columns.
--
-- Some private/personal tables were created with a nullable owner column, so
-- rows without an owner (unattributable personal data) could slip in. This
-- migration tightens the clearest offender flagged in migrations 0105/0116/0122.
--
-- Targeted here:
--   * subscriptions.email  (migration 0122) — per-user billing/subscription
--     row was created as `email VARCHAR(255)` (nullable). A subscription with a
--     NULL owner is unusable and un-erasable, so require NOT NULL.
--
-- Deliberately NOT targeted (shared/public content, an empty owner is a valid
-- "system/community authored" state — a NOT NULL wouldn't add integrity):
--   * prayer_templates.created_by_email (0105), church_profiles.created_by_email
--     (0116), churches.owner_email, organizations.owner_email,
--     formation_tenants.owner_email, accountability_groups.created_by_email.
--
-- SAFETY / HUMAN DECISION: this will FAIL if subscriptions already contains rows
-- with a NULL email. That is intentional — such rows must be reviewed/cleaned
-- first (they are orphaned personal data). To unblock, either backfill the owner
-- or delete the orphans, e.g.:
--     DELETE FROM subscriptions WHERE email IS NULL;   -- if truly orphaned
-- then re-run. Idempotent: re-running after the column is already NOT NULL is a
-- no-op.

DO $$
BEGIN
    IF to_regclass('subscriptions') IS NOT NULL THEN
        -- Only act if the column is currently nullable (idempotent).
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'subscriptions'
              AND column_name = 'email'
              AND is_nullable = 'YES'
        ) THEN
            IF EXISTS (SELECT 1 FROM subscriptions WHERE email IS NULL) THEN
                RAISE EXCEPTION
                    'subscriptions has NULL email rows; clean them up before enforcing NOT NULL (see migration comment)';
            END IF;
            ALTER TABLE subscriptions ALTER COLUMN email SET NOT NULL;
        END IF;
    END IF;
END $$;
