-- Migration 0249: Industrial right-to-erasure hardening, non-email PII coverage audit,
-- social safety composite indexes, prayers share_token index, ordo_amoris_entries FK cascade,
-- and attention_focus_sessions CHECK invariants.
-- Additive migration preserving 0245-0248 SHA-256 digests unchanged.

CREATE OR REPLACE FUNCTION erasure_scrub_only_tables()
RETURNS TABLE(table_name text)
LANGUAGE sql
IMMUTABLE
AS '
    SELECT unnest(ARRAY[
        ''accountability_groups'',
        ''church_profiles'',
        ''churches'',
        ''formation_tenants'',
        ''organizations'',
        ''prayer_templates'',
        ''users''
    ]::text[])
';

CREATE OR REPLACE FUNCTION personal_email_tables()
RETURNS TABLE(table_name text)
LANGUAGE sql
STABLE
AS '
    SELECT c.table_name::text
    FROM information_schema.columns c
    JOIN information_schema.tables t
      ON t.table_schema = c.table_schema AND t.table_name = c.table_name
    WHERE c.table_schema = COALESCE(current_schema(), ''public'')
      AND c.column_name = ''email''
      AND t.table_type = ''BASE TABLE''
      AND c.table_name::text NOT IN (SELECT s.table_name FROM erasure_scrub_only_tables() s)
    ORDER BY 1
';

CREATE OR REPLACE FUNCTION erasure_userid_excluded_tables()
RETURNS TABLE(table_name text)
LANGUAGE sql
IMMUTABLE
AS '
    SELECT unnest(ARRAY[''users'']::text[])
';

CREATE OR REPLACE FUNCTION personal_userid_tables()
RETURNS TABLE(table_name text)
LANGUAGE sql
STABLE
AS '
    SELECT c.table_name::text
    FROM information_schema.columns c
    JOIN information_schema.tables t
      ON t.table_schema = c.table_schema AND t.table_name = c.table_name
    WHERE c.table_schema = COALESCE(current_schema(), ''public'')
      AND c.column_name = ''user_id''
      AND t.table_type = ''BASE TABLE''
      AND c.table_name::text NOT IN (SELECT s.table_name FROM erasure_scrub_only_tables() s)
      AND c.table_name::text NOT IN (SELECT x.table_name FROM erasure_userid_excluded_tables() x)
      AND c.table_name::text NOT IN (SELECT p.table_name FROM personal_email_tables() p)
    ORDER BY 1
';

CREATE OR REPLACE FUNCTION erasure_non_email_identity_columns()
RETURNS TABLE(column_name text)
LANGUAGE sql
IMMUTABLE
AS '
    SELECT unnest(ARRAY[
        ''sender'',
        ''recipient'',
        ''requester'',
        ''addressee'',
        ''user_low'',
        ''user_high'',
        ''owner'',
        ''owner_email'',
        ''target_email'',
        ''reviewer_email'',
        ''reporter_email'',
        ''blocker_email'',
        ''blocked_email'',
        ''requester_user_id'',
        ''partner_user_id'',
        ''owner_user_id'',
        ''target_user_id'',
        ''partner''
    ]::text[])
';

CREATE OR REPLACE FUNCTION erasure_covered_identity_tables()
RETURNS TABLE(table_name text)
LANGUAGE sql
IMMUTABLE
AS '
    SELECT unnest(ARRAY[
        ''accountability_groups'',
        ''attention_accountability_relationships'',
        ''attention_groups'',
        ''attention_prayer_requests'',
        ''attention_share_snapshots'',
        ''care_actions'',
        ''chat_messages'',
        ''church_profiles'',
        ''churches'',
        ''digital_human_turn_audit'',
        ''direct_voice_rooms'',
        ''evangelism_contacts'',
        ''evangelism_prayer_logs'',
        ''formation_moderation_cases'',
        ''formation_tenants'',
        ''friendships'',
        ''group_messages'',
        ''mission_bridge_care_reminders'',
        ''mission_bridge_church_harm_profiles'',
        ''mission_bridge_family_communication_logs'',
        ''mission_bridge_family_crisis_plans'',
        ''mission_bridge_family_households'',
        ''mission_bridge_family_mental_health_profiles'',
        ''mission_bridge_ministry_family_profiles'',
        ''mission_bridge_reentry_profiles'',
        ''mission_prompt_registry'',
        ''organizations'',
        ''prayer_templates'',
        ''social_reports'',
        ''spiritual_partners'',
        ''sunday_school_ai_formation_content_reviews'',
        ''user_blocks'',
        ''users'',
        ''voice_group_members'',
        ''voice_groups''
    ]::text[])
';

CREATE OR REPLACE FUNCTION erase_user_data(p_email text)
RETURNS TABLE(table_name text, rows_deleted bigint)
LANGUAGE plpgsql
AS E'
DECLARE
    t text\x3b
    n bigint\x3b
    n_sub bigint\x3b
    v_email text := lower(COALESCE(p_email, ''''))\x3b
    v_uid text := NULL\x3b
    r_fk record\x3b
    mb_tbl text\x3b
BEGIN
    IF to_regclass(''users'') IS NOT NULL THEN
        PERFORM 1 FROM users WHERE lower(email) = v_email FOR UPDATE\x3b
        SELECT u.id::text INTO v_uid
        FROM users u
        WHERE lower(u.email) = v_email
        ORDER BY (u.email = p_email) DESC, u.id ASC
        LIMIT 1\x3b
    END IF\x3b

    IF to_regclass(''user_tokens'') IS NOT NULL THEN
        DELETE FROM user_tokens WHERE lower(email) = v_email\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := ''user_tokens''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END IF\x3b

    FOR t IN SELECT p.table_name FROM personal_email_tables() p WHERE p.table_name <> ''user_tokens'' LOOP
        EXECUTE format(''DELETE FROM %I WHERE lower(email) = $1'', t) USING v_email\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := t\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END LOOP\x3b

    FOR t IN SELECT u.table_name FROM personal_userid_tables() u LOOP
        IF to_regclass(''users'') IS NOT NULL THEN
            EXECUTE format(
                ''DELETE FROM %I WHERE lower(user_id::text) = $1 OR user_id::text IN (SELECT id::text FROM users WHERE lower(email) = $1)'',
                t
            ) USING v_email\x3b
        ELSE
            EXECUTE format(''DELETE FROM %I WHERE lower(user_id::text) = $1'', t) USING v_email\x3b
        END IF\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := t\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END LOOP\x3b

    IF to_regclass(''friendships'') IS NOT NULL THEN
        DELETE FROM friendships
        WHERE lower(requester) = v_email
           OR lower(addressee) = v_email
           OR lower(user_low) = v_email
           OR lower(user_high) = v_email\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := ''friendships''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END IF\x3b

    IF to_regclass(''chat_messages'') IS NOT NULL THEN
        DELETE FROM chat_messages
        WHERE lower(sender) = v_email OR lower(recipient) = v_email\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := ''chat_messages''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END IF\x3b

    IF to_regclass(''group_messages'') IS NOT NULL THEN
        DELETE FROM group_messages WHERE lower(sender) = v_email\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := ''group_messages''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END IF\x3b

    IF to_regclass(''voice_group_members'') IS NOT NULL THEN
        IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = COALESCE(current_schema(), ''public'')
              AND information_schema.columns.table_name = ''voice_group_members''
              AND column_name = ''member_email''
        ) THEN
            EXECUTE ''DELETE FROM voice_group_members WHERE lower(member_email) = $1'' USING v_email\x3b
            GET DIAGNOSTICS n = ROW_COUNT\x3b
            table_name := ''voice_group_members.member_email''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
        END IF\x3b
    END IF\x3b

    IF to_regclass(''voice_groups'') IS NOT NULL THEN
        DELETE FROM voice_groups WHERE lower(owner) = v_email\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := ''voice_groups''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
        IF to_regclass(''voice_group_members'') IS NOT NULL THEN
            DELETE FROM voice_group_members WHERE group_id NOT IN (SELECT id FROM voice_groups)\x3b
            GET DIAGNOSTICS n_sub = ROW_COUNT\x3b
            table_name := ''voice_group_members.orphans''\x3b rows_deleted := n_sub\x3b RETURN NEXT\x3b
        END IF\x3b
    END IF\x3b

    IF to_regclass(''direct_voice_rooms'') IS NOT NULL THEN
        DELETE FROM direct_voice_rooms
        WHERE lower(user_low) = v_email OR lower(user_high) = v_email\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := ''direct_voice_rooms''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END IF\x3b

    IF to_regclass(''user_blocks'') IS NOT NULL THEN
        DELETE FROM user_blocks
        WHERE lower(blocker_email) = v_email OR lower(blocked_email) = v_email\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := ''user_blocks''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END IF\x3b

    IF to_regclass(''evangelism_prayer_logs'') IS NOT NULL THEN
        DELETE FROM evangelism_prayer_logs WHERE lower(owner_email) = v_email\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := ''evangelism_prayer_logs''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END IF\x3b

    IF to_regclass(''evangelism_contacts'') IS NOT NULL THEN
        DELETE FROM evangelism_contacts WHERE lower(owner_email) = v_email\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := ''evangelism_contacts''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END IF\x3b

    IF to_regclass(''spiritual_partners'') IS NOT NULL THEN
        DELETE FROM spiritual_partners
        WHERE lower(requester) = v_email OR lower(partner) = v_email\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := ''spiritual_partners''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END IF\x3b

    IF to_regclass(''attention_accountability_relationships'') IS NOT NULL THEN
        DELETE FROM attention_accountability_relationships
        WHERE lower(requester_user_id) = v_email
           OR lower(partner_user_id) = v_email
           OR (v_uid IS NOT NULL AND (requester_user_id = v_uid OR partner_user_id = v_uid))\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := ''attention_accountability_relationships''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END IF\x3b

    IF to_regclass(''attention_prayer_requests'') IS NOT NULL THEN
        DELETE FROM attention_prayer_requests
        WHERE lower(owner_user_id) = v_email
           OR lower(target_user_id) = v_email
           OR (v_uid IS NOT NULL AND (owner_user_id = v_uid OR target_user_id = v_uid))\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := ''attention_prayer_requests''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END IF\x3b

    IF to_regclass(''attention_share_snapshots'') IS NOT NULL THEN
        DELETE FROM attention_share_snapshots
        WHERE lower(owner_user_id) = v_email
           OR lower(target_user_id) = v_email
           OR (v_uid IS NOT NULL AND (owner_user_id = v_uid OR target_user_id = v_uid))\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := ''attention_share_snapshots''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END IF\x3b

    IF to_regclass(''attention_groups'') IS NOT NULL THEN
        DELETE FROM attention_groups
        WHERE lower(owner_user_id) = v_email
           OR (v_uid IS NOT NULL AND owner_user_id = v_uid)\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := ''attention_groups''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END IF\x3b

    IF to_regclass(''social_reports'') IS NOT NULL THEN
        n := 0\x3b
        DELETE FROM social_reports WHERE lower(reporter_email) = v_email\x3b
        GET DIAGNOSTICS n_sub = ROW_COUNT\x3b
        n := n + n_sub\x3b
        DELETE FROM social_reports WHERE lower(target_email) = v_email AND status = ''closed''\x3b
        GET DIAGNOSTICS n_sub = ROW_COUNT\x3b
        n := n + n_sub\x3b
        UPDATE social_reports SET target_email = ''[erased]'' WHERE lower(target_email) = v_email\x3b
        GET DIAGNOSTICS n_sub = ROW_COUNT\x3b
        n := n + n_sub\x3b
        UPDATE social_reports SET reviewer_email = NULL WHERE lower(reviewer_email) = v_email\x3b
        GET DIAGNOSTICS n_sub = ROW_COUNT\x3b
        n := n + n_sub\x3b
        table_name := ''social_reports''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END IF\x3b

    IF to_regclass(''care_actions'') IS NOT NULL THEN
        DELETE FROM care_actions WHERE lower(target_email) = v_email\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        UPDATE care_actions SET actor_email = ''[erased]'' WHERE lower(actor_email) = v_email\x3b
        GET DIAGNOSTICS n_sub = ROW_COUNT\x3b
        table_name := ''care_actions''\x3b rows_deleted := n + n_sub\x3b RETURN NEXT\x3b
    END IF\x3b

    IF to_regclass(''digital_human_turn_audit'') IS NOT NULL THEN
        DELETE FROM digital_human_turn_audit WHERE lower(owner_email) = v_email\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := ''digital_human_turn_audit''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END IF\x3b

    FOREACH mb_tbl IN ARRAY ARRAY[
        ''mission_bridge_care_reminders'',
        ''mission_bridge_church_harm_profiles'',
        ''mission_bridge_family_communication_logs'',
        ''mission_bridge_family_crisis_plans'',
        ''mission_bridge_family_households'',
        ''mission_bridge_family_mental_health_profiles'',
        ''mission_bridge_ministry_family_profiles'',
        ''mission_bridge_reentry_profiles''
    ] LOOP
        IF to_regclass(mb_tbl) IS NOT NULL THEN
            FOR r_fk IN
                SELECT c.conrelid::regclass::text AS child_tbl, a.attname AS fk_col
                FROM pg_constraint c
                JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
                WHERE c.contype = ''f''
                  AND c.confrelid = to_regclass(mb_tbl)
                  AND array_length(c.conkey, 1) = 1
                  AND c.confdeltype <> ''c''
            LOOP
                EXECUTE format(
                    ''DELETE FROM %s WHERE %I IN (SELECT id FROM %I WHERE lower(owner_user_id) = $1 OR ($2 IS NOT NULL AND owner_user_id = $2))'',
                    r_fk.child_tbl, r_fk.fk_col, mb_tbl
                ) USING v_email, v_uid\x3b
            END LOOP\x3b
            EXECUTE format(
                ''DELETE FROM %I WHERE lower(owner_user_id) = $1 OR ($2 IS NOT NULL AND owner_user_id = $2)'',
                mb_tbl
            ) USING v_email, v_uid\x3b
            GET DIAGNOSTICS n = ROW_COUNT\x3b
            table_name := mb_tbl\x3b rows_deleted := n\x3b RETURN NEXT\x3b
        END IF\x3b
    END LOOP\x3b

    IF to_regclass(''mission_prompt_registry'') IS NOT NULL THEN
        UPDATE mission_prompt_registry SET owner = NULL WHERE lower(owner) = v_email\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := ''mission_prompt_registry.owner''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END IF\x3b

    IF to_regclass(''sunday_school_ai_formation_content_reviews'') IS NOT NULL THEN
        UPDATE sunday_school_ai_formation_content_reviews
        SET reviewer_email = ''[erased]''
        WHERE lower(reviewer_email) = v_email\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := ''sunday_school_ai_formation_content_reviews.reviewer_email''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END IF\x3b

    IF to_regclass(''formation_moderation_cases'') IS NOT NULL THEN
        DELETE FROM formation_moderation_cases WHERE lower(reporter_email) = v_email\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := ''formation_moderation_cases''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END IF\x3b

    IF to_regclass(''accountability_groups'') IS NOT NULL THEN
        UPDATE accountability_groups SET created_by_email = '''' WHERE lower(created_by_email) = v_email\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := ''accountability_groups.created_by_email''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END IF\x3b
    IF to_regclass(''church_profiles'') IS NOT NULL THEN
        UPDATE church_profiles SET created_by_email = '''' WHERE lower(created_by_email) = v_email\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := ''church_profiles.created_by_email''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END IF\x3b
    IF to_regclass(''churches'') IS NOT NULL THEN
        UPDATE churches SET owner_email = '''' WHERE lower(owner_email) = v_email\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := ''churches.owner_email''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END IF\x3b
    IF to_regclass(''formation_tenants'') IS NOT NULL THEN
        UPDATE formation_tenants SET owner_email = '''' WHERE lower(owner_email) = v_email\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := ''formation_tenants.owner_email''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END IF\x3b
    IF to_regclass(''organizations'') IS NOT NULL THEN
        UPDATE organizations SET owner_email = '''' WHERE lower(owner_email) = v_email\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := ''organizations.owner_email''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END IF\x3b
    IF to_regclass(''prayer_templates'') IS NOT NULL THEN
        UPDATE prayer_templates SET created_by_email = '''' WHERE lower(created_by_email) = v_email\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := ''prayer_templates.created_by_email''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END IF\x3b

    IF to_regclass(''users'') IS NOT NULL THEN
        DELETE FROM users WHERE lower(email) = v_email\x3b
        GET DIAGNOSTICS n = ROW_COUNT\x3b
        table_name := ''users''\x3b rows_deleted := n\x3b RETURN NEXT\x3b
    END IF\x3b

    RETURN\x3b
END\x3b
';

CREATE OR REPLACE FUNCTION erasure_coverage_gaps()
RETURNS TABLE(table_name text, reason text)
LANGUAGE sql
STABLE
AS '
    SELECT c.table_name::text, ''email column not covered by erase_user_data''::text
    FROM information_schema.columns c
    JOIN information_schema.tables t
      ON t.table_schema = c.table_schema AND t.table_name = c.table_name
    WHERE c.table_schema = COALESCE(current_schema(), ''public'')
      AND c.column_name = ''email''
      AND t.table_type = ''BASE TABLE''
      AND c.table_name::text NOT IN (SELECT s.table_name FROM erasure_scrub_only_tables() s)
      AND c.table_name::text NOT IN (SELECT p.table_name FROM personal_email_tables() p)
    UNION ALL
    SELECT c.table_name::text, ''user_id column not covered by erase_user_data''::text
    FROM information_schema.columns c
    JOIN information_schema.tables t
      ON t.table_schema = c.table_schema AND t.table_name = c.table_name
    WHERE c.table_schema = COALESCE(current_schema(), ''public'')
      AND c.column_name = ''user_id''
      AND t.table_type = ''BASE TABLE''
      AND c.table_name::text NOT IN (SELECT s.table_name FROM erasure_scrub_only_tables() s)
      AND c.table_name::text NOT IN (SELECT x.table_name FROM erasure_userid_excluded_tables() x)
      AND c.table_name::text NOT IN (SELECT p.table_name FROM personal_email_tables() p)
      AND c.table_name::text NOT IN (SELECT u.table_name FROM personal_userid_tables() u)
    UNION ALL
    SELECT DISTINCT c.table_name::text,
           (''non-email identity column ('' || c.column_name::text || '') not covered by erase_user_data'')::text
    FROM information_schema.columns c
    JOIN information_schema.tables t
      ON t.table_schema = c.table_schema AND t.table_name = c.table_name
    WHERE c.table_schema = COALESCE(current_schema(), ''public'')
      AND t.table_type = ''BASE TABLE''
      AND c.column_name::text IN (SELECT col.column_name FROM erasure_non_email_identity_columns() col)
      AND c.table_name::text NOT IN (SELECT p.table_name FROM personal_email_tables() p)
      AND c.table_name::text NOT IN (SELECT u.table_name FROM personal_userid_tables() u)
      AND c.table_name::text NOT IN (SELECT s.table_name FROM erasure_scrub_only_tables() s)
      AND c.table_name::text NOT IN (SELECT cov.table_name FROM erasure_covered_identity_tables() cov)
    ORDER BY 1
';

DO E'
BEGIN
    IF to_regclass(''user_blocks'') IS NOT NULL THEN
        CREATE INDEX IF NOT EXISTS idx_user_blocks_pair ON user_blocks(blocker_email, blocked_email)\x3b
    END IF\x3b

    IF to_regclass(''direct_voice_rooms'') IS NOT NULL THEN
        CREATE INDEX IF NOT EXISTS idx_direct_voice_rooms_pair ON direct_voice_rooms(user_low, user_high, expires_at)\x3b
    END IF\x3b

    IF to_regclass(''account_deletion_requests'') IS NOT NULL THEN
        CREATE INDEX IF NOT EXISTS idx_account_deletion_requests_status ON account_deletion_requests(status, requested_at)\x3b
    END IF\x3b

    IF to_regclass(''social_reports'') IS NOT NULL THEN
        ALTER TABLE social_reports ALTER COLUMN id SET DEFAULT gen_random_uuid()\x3b
    END IF\x3b

    IF to_regclass(''prayers'') IS NOT NULL THEN
        ALTER TABLE prayers ADD COLUMN IF NOT EXISTS share_token VARCHAR(64)\x3b
        CREATE UNIQUE INDEX IF NOT EXISTS idx_prayers_share_token ON prayers(share_token) WHERE share_token IS NOT NULL\x3b
    END IF\x3b

    IF to_regclass(''ordo_amoris_entries'') IS NOT NULL AND to_regclass(''users'') IS NOT NULL THEN
        DELETE FROM ordo_amoris_entries WHERE email NOT IN (SELECT email FROM users)\x3b
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conrelid = to_regclass(''ordo_amoris_entries'')
              AND conname = ''fk_ordo_amoris_entries_user_email''
        ) THEN
            ALTER TABLE ordo_amoris_entries
                ADD CONSTRAINT fk_ordo_amoris_entries_user_email
                FOREIGN KEY (email) REFERENCES users(email)
                ON UPDATE CASCADE ON DELETE CASCADE\x3b
        END IF\x3b
    END IF\x3b

    IF to_regclass(''attention_focus_sessions'') IS NOT NULL THEN
        UPDATE attention_focus_sessions
        SET planned_minutes = LEAST(GREATEST(planned_minutes, 1), 240)
        WHERE planned_minutes < 1 OR planned_minutes > 240\x3b

        UPDATE attention_focus_sessions
        SET actual_minutes = LEAST(GREATEST(actual_minutes, 0), 1440)
        WHERE actual_minutes IS NOT NULL AND (actual_minutes < 0 OR actual_minutes > 1440)\x3b

        UPDATE attention_focus_sessions
        SET ended_at = started_at
        WHERE ended_at IS NOT NULL AND ended_at < started_at\x3b

        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conrelid = to_regclass(''attention_focus_sessions'')
              AND conname = ''chk_attention_focus_planned_minutes''
        ) THEN
            ALTER TABLE attention_focus_sessions
                ADD CONSTRAINT chk_attention_focus_planned_minutes
                CHECK (planned_minutes BETWEEN 1 AND 240)\x3b
        END IF\x3b

        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conrelid = to_regclass(''attention_focus_sessions'')
              AND conname = ''chk_attention_focus_actual_minutes''
        ) THEN
            ALTER TABLE attention_focus_sessions
                ADD CONSTRAINT chk_attention_focus_actual_minutes
                CHECK (actual_minutes IS NULL OR actual_minutes BETWEEN 0 AND 1440)\x3b
        END IF\x3b

        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conrelid = to_regclass(''attention_focus_sessions'')
              AND conname = ''chk_attention_focus_ended_after_started''
        ) THEN
            ALTER TABLE attention_focus_sessions
                ADD CONSTRAINT chk_attention_focus_ended_after_started
                CHECK (ended_at IS NULL OR ended_at >= started_at)\x3b
        END IF\x3b
    END IF\x3b
END\x3b
' LANGUAGE plpgsql;
