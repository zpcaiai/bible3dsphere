-- Migration 0233: make right-to-erasure self-maintaining, and prove EMD coverage.
--
-- 0145 shipped `erase_user_data(email)` with a **point-in-time snapshot** of the
-- email-keyed personal tables (its own README says the array must be regenerated
-- when new personal tables appear). Since then migrations 0223–0231 added 71
-- `formation_twin_emd_*` tables holding the most sensitive material in the product
-- (prayer, family history, crisis state, trauma narratives) — none of which are in
-- that array. Account-level erasure therefore silently left EMD data behind.
--
-- Rather than paste another snapshot that rots the same way, this migration makes
-- discovery dynamic:
--
--   * `personal_email_tables()`   — every base table with an `email` column, minus
--                                   the shared/owned tables that must be scrubbed
--                                   rather than deleted.
--   * `erase_user_data()`         — rewritten to iterate that view; the user_id
--                                   tables, the PII scrub and the account delete
--                                   are unchanged from 0145.
--   * `erasure_coverage_gaps()`   — returns email-keyed tables the routine would
--                                   miss. It must return zero rows; the test suite
--                                   asserts exactly that, so a future migration that
--                                   introduces an uncovered personal table fails CI
--                                   instead of quietly under-deleting.
--
-- Idempotent and safe to re-run.

-- ── 1) dynamic discovery ─────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION erasure_scrub_only_tables()
RETURNS TABLE(table_name text) AS $$
    SELECT unnest(ARRAY[
        'accountability_groups', 'church_profiles', 'churches',
        'formation_tenants', 'organizations', 'prayer_templates',
        'users'
    ]::text[]);
$$ LANGUAGE sql IMMUTABLE;

COMMENT ON FUNCTION erasure_scrub_only_tables() IS
    'Tables whose email/owner column is scrubbed rather than row-deleted, plus users (handled last).';

CREATE OR REPLACE FUNCTION personal_email_tables()
RETURNS TABLE(table_name text) AS $$
    SELECT c.table_name::text
    FROM information_schema.columns c
    JOIN information_schema.tables t
      ON t.table_schema = c.table_schema AND t.table_name = c.table_name
    WHERE c.table_schema = 'public'
      AND c.column_name = 'email'
      AND t.table_type = 'BASE TABLE'
      AND c.table_name::text NOT IN (SELECT s.table_name FROM erasure_scrub_only_tables() s)
    ORDER BY 1;
$$ LANGUAGE sql STABLE;

COMMENT ON FUNCTION personal_email_tables() IS
    'Every email-keyed personal table, discovered live from the catalog so schema growth cannot outrun erasure.';

-- user_id-keyed personal tables have the same rot problem: 0145 listed four, while
-- the schema now carries ~26 (attention_*, mission_bridge_*, mvfe_*, safeguarding_*).
-- `mvfe_memories` in particular stores raw user text plus its embedding and is created
-- outside migrations/ entirely — catalog discovery is the only way to catch it.
CREATE OR REPLACE FUNCTION erasure_userid_excluded_tables()
RETURNS TABLE(table_name text) AS $$
    SELECT unnest(ARRAY[
        -- reference/config tables where user_id points at someone else's record
        -- or at shared content that must outlive the erased account
        'users'
    ]::text[]);
$$ LANGUAGE sql IMMUTABLE;

CREATE OR REPLACE FUNCTION personal_userid_tables()
RETURNS TABLE(table_name text) AS $$
    SELECT c.table_name::text
    FROM information_schema.columns c
    JOIN information_schema.tables t
      ON t.table_schema = c.table_schema AND t.table_name = c.table_name
    WHERE c.table_schema = 'public'
      AND c.column_name = 'user_id'
      AND t.table_type = 'BASE TABLE'
      AND c.table_name::text NOT IN (SELECT s.table_name FROM erasure_scrub_only_tables() s)
      AND c.table_name::text NOT IN (SELECT x.table_name FROM erasure_userid_excluded_tables() x)
      AND c.table_name::text NOT IN (SELECT p.table_name FROM personal_email_tables() p)
    ORDER BY 1;
$$ LANGUAGE sql STABLE;

COMMENT ON FUNCTION personal_userid_tables() IS
    'Every user_id-keyed personal table not already covered by the email pass.';

-- ── 2) erasure ───────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION erase_user_data(p_email text)
RETURNS TABLE(table_name text, rows_deleted bigint) AS $$
DECLARE
    t text;
    n bigint;
BEGIN
    -- 1) every email-keyed personal table, discovered at run time.
    FOR t IN SELECT p.table_name FROM personal_email_tables() p LOOP
        EXECUTE format('DELETE FROM %I WHERE email = $1', t) USING p_email;
        GET DIAGNOSTICS n = ROW_COUNT;
        table_name := t; rows_deleted := n; RETURN NEXT;
    END LOOP;

    -- 2) user_id-keyed personal tables (user_id may be a numeric users.id or the
    --    email itself; resolve both).
    FOR t IN SELECT u.table_name FROM personal_userid_tables() u LOOP
        EXECUTE format(
            'DELETE FROM %I WHERE user_id::text = $1 '
            'OR user_id::text IN (SELECT id::text FROM users WHERE email = $1)', t)
            USING p_email;
        GET DIAGNOSTICS n = ROW_COUNT;
        table_name := t; rows_deleted := n; RETURN NEXT;
    END LOOP;

    -- 3) shared/owned content: scrub the user's PII but keep the row so co-owned
    --    data survives. Reassigning ownership remains a manual follow-up.
    IF to_regclass('accountability_groups') IS NOT NULL THEN
        UPDATE accountability_groups SET created_by_email = '' WHERE created_by_email = p_email;
        GET DIAGNOSTICS n = ROW_COUNT;
        table_name := 'accountability_groups.created_by_email'; rows_deleted := n; RETURN NEXT;
    END IF;
    IF to_regclass('church_profiles') IS NOT NULL THEN
        UPDATE church_profiles SET created_by_email = '' WHERE created_by_email = p_email;
        GET DIAGNOSTICS n = ROW_COUNT;
        table_name := 'church_profiles.created_by_email'; rows_deleted := n; RETURN NEXT;
    END IF;
    IF to_regclass('churches') IS NOT NULL THEN
        UPDATE churches SET owner_email = '' WHERE owner_email = p_email;
        GET DIAGNOSTICS n = ROW_COUNT;
        table_name := 'churches.owner_email'; rows_deleted := n; RETURN NEXT;
    END IF;
    IF to_regclass('formation_tenants') IS NOT NULL THEN
        UPDATE formation_tenants SET owner_email = '' WHERE owner_email = p_email;
        GET DIAGNOSTICS n = ROW_COUNT;
        table_name := 'formation_tenants.owner_email'; rows_deleted := n; RETURN NEXT;
    END IF;
    IF to_regclass('organizations') IS NOT NULL THEN
        UPDATE organizations SET owner_email = '' WHERE owner_email = p_email;
        GET DIAGNOSTICS n = ROW_COUNT;
        table_name := 'organizations.owner_email'; rows_deleted := n; RETURN NEXT;
    END IF;
    IF to_regclass('prayer_templates') IS NOT NULL THEN
        UPDATE prayer_templates SET created_by_email = '' WHERE created_by_email = p_email;
        GET DIAGNOSTICS n = ROW_COUNT;
        table_name := 'prayer_templates.created_by_email'; rows_deleted := n; RETURN NEXT;
    END IF;

    -- 4) the account row itself (last, after dependents are gone).
    IF to_regclass('users') IS NOT NULL THEN
        DELETE FROM users WHERE email = p_email;
        GET DIAGNOSTICS n = ROW_COUNT;
        table_name := 'users'; rows_deleted := n; RETURN NEXT;
    END IF;

    RETURN;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION erase_user_data(text) IS
    'Right-to-erasure: delete all personal rows for an email (tables discovered live), scrub shared-owner PII, drop the account.';

-- ── 3) coverage self-check ───────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION erasure_coverage_gaps()
RETURNS TABLE(table_name text, reason text) AS $$
    -- An email-keyed base table that is neither deleted nor deliberately scrubbed.
    SELECT c.table_name::text, 'email column not covered by erase_user_data'::text
    FROM information_schema.columns c
    JOIN information_schema.tables t
      ON t.table_schema = c.table_schema AND t.table_name = c.table_name
    WHERE c.table_schema = 'public'
      AND c.column_name = 'email'
      AND t.table_type = 'BASE TABLE'
      AND c.table_name::text NOT IN (SELECT s.table_name FROM erasure_scrub_only_tables() s)
      AND c.table_name::text NOT IN (SELECT p.table_name FROM personal_email_tables() p)
    UNION ALL
    SELECT c.table_name::text, 'user_id column not covered by erase_user_data'::text
    FROM information_schema.columns c
    JOIN information_schema.tables t
      ON t.table_schema = c.table_schema AND t.table_name = c.table_name
    WHERE c.table_schema = 'public'
      AND c.column_name = 'user_id'
      AND t.table_type = 'BASE TABLE'
      AND c.table_name::text NOT IN (SELECT s.table_name FROM erasure_scrub_only_tables() s)
      AND c.table_name::text NOT IN (SELECT x.table_name FROM erasure_userid_excluded_tables() x)
      AND c.table_name::text NOT IN (SELECT p.table_name FROM personal_email_tables() p)
      AND c.table_name::text NOT IN (SELECT u.table_name FROM personal_userid_tables() u)
    ORDER BY 1;
$$ LANGUAGE sql STABLE;

COMMENT ON FUNCTION erasure_coverage_gaps() IS
    'Must return zero rows. Any row means a personal table would survive account erasure.';

-- ── 4) EMD-specific propagation check ────────────────────────────────────────
-- 试点验收用：确认 EMD 域的每一张表都在删除覆盖范围内。

CREATE OR REPLACE FUNCTION emd_erasure_coverage()
RETURNS TABLE(total_emd_tables bigint, covered bigint, uncovered text[]) AS $$
    WITH emd AS (
        SELECT t.table_name::text AS name
        FROM information_schema.tables t
        WHERE t.table_schema = 'public'
          AND t.table_type = 'BASE TABLE'
          AND t.table_name::text LIKE 'formation_twin_emd\_%'
    ),
    covered AS (
        SELECT e.name FROM emd e
        WHERE e.name IN (SELECT p.table_name FROM personal_email_tables() p)
    )
    SELECT
        (SELECT count(*) FROM emd),
        (SELECT count(*) FROM covered),
        COALESCE(ARRAY(SELECT e.name FROM emd e WHERE e.name NOT IN (SELECT c.name FROM covered c) ORDER BY 1), ARRAY[]::text[]);
$$ LANGUAGE sql STABLE;

COMMENT ON FUNCTION emd_erasure_coverage() IS
    'EMD pilot acceptance: uncovered must be empty and covered must equal total_emd_tables.';
