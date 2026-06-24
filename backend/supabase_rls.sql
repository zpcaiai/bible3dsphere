-- ============================================================================
-- supabase_rls.sql — Advanced Batch · Module 2 (Supabase Row Level Security)
-- ============================================================================
-- FORWARD-LOOKING. The live app uses email-keyed tables + a custom session-auth
-- backend (raw psycopg2), NOT Supabase Auth. This file is what you apply IF/WHEN
-- you put Supabase Auth in front of this Postgres.
--
-- Bridge: every private table in this repo is keyed by `email` (TEXT). A Supabase
-- JWT carries the signed-in user's email, so RLS can match WITHOUT renaming any
-- column to a UUID:
--
--        email = (auth.jwt() ->> 'email')
--
-- (If you instead migrate to users.id = auth.uid() UUIDs, swap the helper below
--  for `auth.uid()` comparisons against a user_id column.)
--
-- Principles enforced here (spec §二):
--   • Users can only read/write their OWN private data.
--   • Spiritual companions see only shared_reports the owner granted.
--   • Group leaders see only care_signals for groups they lead (authorised
--     summaries) — never raw private tables.
--   • Pastors / emergency contacts read crisis context ONLY via service_role
--     (the backend), never via a broad client policy.
--   • audit_logs: a user may read only audit rows ABOUT themselves; full log
--     access is service_role only.
--   • The backend service_role key bypasses RLS for aggregation / crisis flow.
--
-- Idempotent: policies are DROP ... IF EXISTS then CREATE; every block is guarded
-- with to_regclass so it is safe to run even if a table is not present yet.
-- ============================================================================

-- Helper: the email claim of the current Supabase JWT (NULL for anon). --------
CREATE SCHEMA IF NOT EXISTS app;
CREATE OR REPLACE FUNCTION app.current_email() RETURNS text
LANGUAGE sql STABLE AS $$
    SELECT NULLIF(current_setting('request.jwt.claims', true)::jsonb ->> 'email', '')
$$;

-- ── 1. Bulk: simple "owner-only" private tables keyed by `email` ────────────
-- Each gets SELECT/INSERT/UPDATE/DELETE restricted to email = app.current_email().
DO $$
DECLARE
    t text;
    owned text[] := ARRAY[
        -- worldview formation OS
        'worldview_profiles','worldview_assessments','worldview_responses',
        'worldview_dimension_scores','worldview_beliefs','worldview_presuppositions',
        'worldview_metric_snapshots','distorted_beliefs','biblical_truth_maps',
        'narrative_rewrites','apologetics_cases','cultural_discernment_cases',
        'vocation_worldview_cases','decision_cases','formation_plans','formation_tasks',
        'formation_task_logs','crisis_risk_assessments',
        -- gifts & calling
        'gift_assessments','strength_profiles','fruit_scores','calling_patterns',
        'community_feedback','misuse_risks','ministry_matches','growth_plans','review_logs',
        -- suffering & crisis
        'suffering_cases','lament_prayers','suffering_care_plans',
        -- governance / provider layer (own rows only)
        'agent_runs','agent_events','theological_review_logs',
        'community_guardians','guardian_alerts','user_consents',
        -- canonical spec names (created only if you add them)
        'spiritual_profiles','diagnostic_sessions','diagnostic_findings','practice_plans',
        'practice_tasks','practice_task_completions','daily_checkins','reflection_logs',
        'weekly_reviews','feedback_summaries','formation_cycles','formation_memory_events'
    ];
BEGIN
    FOREACH t IN ARRAY owned LOOP
        IF to_regclass('public.' || t) IS NOT NULL THEN
            EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
            EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', t || '_owner_sel', t);
            EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', t || '_owner_ins', t);
            EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', t || '_owner_upd', t);
            EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', t || '_owner_del', t);
            EXECUTE format('CREATE POLICY %I ON public.%I FOR SELECT USING (email = app.current_email())', t || '_owner_sel', t);
            EXECUTE format('CREATE POLICY %I ON public.%I FOR INSERT WITH CHECK (email = app.current_email())', t || '_owner_ins', t);
            EXECUTE format('CREATE POLICY %I ON public.%I FOR UPDATE USING (email = app.current_email()) WITH CHECK (email = app.current_email())', t || '_owner_upd', t);
            EXECUTE format('CREATE POLICY %I ON public.%I FOR DELETE USING (email = app.current_email())', t || '_owner_del', t);
        END IF;
    END LOOP;
END $$;

-- ── 2. users: a user sees/updates only their own row ────────────────────────
DO $$ BEGIN
    IF to_regclass('public.users') IS NOT NULL THEN
        ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS users_self_sel ON public.users;
        DROP POLICY IF EXISTS users_self_upd ON public.users;
        CREATE POLICY users_self_sel ON public.users FOR SELECT USING (email = app.current_email());
        CREATE POLICY users_self_upd ON public.users FOR UPDATE USING (email = app.current_email()) WITH CHECK (email = app.current_email());
    END IF;
END $$;

-- ── 3. shared_reports: owner full; recipient only active (unrevoked/unexpired) ─
DO $$ BEGIN
    IF to_regclass('public.shared_reports') IS NOT NULL THEN
        ALTER TABLE public.shared_reports ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS shared_reports_owner_sel ON public.shared_reports;
        DROP POLICY IF EXISTS shared_reports_recipient_sel ON public.shared_reports;
        DROP POLICY IF EXISTS shared_reports_owner_ins ON public.shared_reports;
        DROP POLICY IF EXISTS shared_reports_owner_upd ON public.shared_reports;
        CREATE POLICY shared_reports_owner_sel ON public.shared_reports
            FOR SELECT USING (owner_email = app.current_email());
        CREATE POLICY shared_reports_recipient_sel ON public.shared_reports
            FOR SELECT USING (
                recipient_email = app.current_email()
                AND revoked_at IS NULL
                AND (expires_at IS NULL OR expires_at > now())
            );
        CREATE POLICY shared_reports_owner_ins ON public.shared_reports
            FOR INSERT WITH CHECK (owner_email = app.current_email());
        CREATE POLICY shared_reports_owner_upd ON public.shared_reports
            FOR UPDATE USING (owner_email = app.current_email())
            WITH CHECK (owner_email = app.current_email());
    END IF;
END $$;

-- ── 4. accountability_partners: either side may view ────────────────────────
DO $$ BEGIN
    IF to_regclass('public.accountability_partners') IS NOT NULL THEN
        ALTER TABLE public.accountability_partners ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS ap_either_sel ON public.accountability_partners;
        CREATE POLICY ap_either_sel ON public.accountability_partners
            FOR SELECT USING (email = app.current_email() OR partner_email = app.current_email());
    END IF;
END $$;

-- ── 5. care_signals: own rows + leaders/pastors of that group ───────────────
DO $$ BEGIN
    IF to_regclass('public.care_signals') IS NOT NULL THEN
        ALTER TABLE public.care_signals ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS care_signals_own_sel ON public.care_signals;
        DROP POLICY IF EXISTS care_signals_leader_sel ON public.care_signals;
        CREATE POLICY care_signals_own_sel ON public.care_signals
            FOR SELECT USING (email = app.current_email());
        CREATE POLICY care_signals_leader_sel ON public.care_signals
            FOR SELECT USING (
                EXISTS (
                    SELECT 1 FROM public.church_members cm
                    WHERE cm.email = app.current_email()
                      AND cm.church_id = care_signals.church_id
                      AND cm.role IN ('leader','small_group_leader','co_leader','pastor','elder','owner','admin')
                )
                AND (
                    (consent_share = TRUE AND visible_to_group_leader = TRUE)
                    OR signal_level IN ('high','critical')
                )
            );
    END IF;
END $$;

-- ── 6. care_actions: only the actor or the cared-for member ─────────────────
DO $$ BEGIN
    IF to_regclass('public.care_actions') IS NOT NULL THEN
        ALTER TABLE public.care_actions ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS care_actions_party_sel ON public.care_actions;
        CREATE POLICY care_actions_party_sel ON public.care_actions
            FOR SELECT USING (actor_email = app.current_email() OR target_email = app.current_email());
    END IF;
END $$;

-- ── 7. crisis_events: the user themself only (keyed by user_id = email). ─────
--      Pastors / emergency contacts read necessary summaries via service_role,
--      never through a broad client policy.
DO $$ BEGIN
    IF to_regclass('public.crisis_events') IS NOT NULL THEN
        ALTER TABLE public.crisis_events ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS crisis_events_self_sel ON public.crisis_events;
        CREATE POLICY crisis_events_self_sel ON public.crisis_events
            FOR SELECT USING (user_id = app.current_email());
    END IF;
END $$;

-- ── 8. audit_logs: a user may read only audit rows ABOUT themselves. ────────
--      No client INSERT/UPDATE/DELETE — the backend writes via service_role.
DO $$ BEGIN
    IF to_regclass('public.audit_logs') IS NOT NULL THEN
        ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS audit_logs_subject_sel ON public.audit_logs;
        CREATE POLICY audit_logs_subject_sel ON public.audit_logs
            FOR SELECT USING (subject_email = app.current_email());
    END IF;
END $$;

-- ============================================================================
-- Canonical spec examples (verbatim shape) — run only if the table exists.
-- These mirror the policies in the Advanced Batch spec §二 for the idealised
-- table names, kept here as documentation + ready-to-use definitions.
-- ============================================================================
DO $$ BEGIN
    IF to_regclass('public.spiritual_profiles') IS NOT NULL THEN
        ALTER TABLE public.spiritual_profiles ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS "Users can view own spiritual profile" ON public.spiritual_profiles;
        DROP POLICY IF EXISTS "Users can insert own spiritual profile" ON public.spiritual_profiles;
        DROP POLICY IF EXISTS "Users can update own spiritual profile" ON public.spiritual_profiles;
        CREATE POLICY "Users can view own spiritual profile" ON public.spiritual_profiles
            FOR SELECT USING (email = app.current_email());
        CREATE POLICY "Users can insert own spiritual profile" ON public.spiritual_profiles
            FOR INSERT WITH CHECK (email = app.current_email());
        CREATE POLICY "Users can update own spiritual profile" ON public.spiritual_profiles
            FOR UPDATE USING (email = app.current_email()) WITH CHECK (email = app.current_email());
    END IF;
    IF to_regclass('public.reflection_logs') IS NOT NULL THEN
        ALTER TABLE public.reflection_logs ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS "Users can view own reflection logs" ON public.reflection_logs;
        CREATE POLICY "Users can view own reflection logs" ON public.reflection_logs
            FOR SELECT USING (email = app.current_email());
    END IF;
END $$;

-- ============================================================================
-- NOTE ON service_role: the backend connects with the Supabase service_role key,
-- which BYPASSES RLS. Keep that key server-side only. Use it strictly for:
--   • cross-user aggregation (e.g. building care dashboards),
--   • crisis linkage (notifying authorised guardians / pastors),
--   • administrative / migration tasks.
-- All client (anon/auth) traffic is constrained by the policies above.
-- ============================================================================
