# Right-to-erasure (migration 0145)

`0145_right_to_erasure.sql` defines a Postgres function:

```sql
SELECT * FROM erase_user_data('user@example.com');
```

It purges all personal data for one user:

1. **Deletes** every row keyed by `email` across the 164 personal tables found by
   scanning `backend/migrations/*.sql`.
2. **Deletes** rows in the 4 `user_id`-keyed personal tables
   (`habit_daily_notes`, `mvfe_pipeline_stats`, `spiritual_holy_life_day_logs`,
   `user_verse_feedback`), resolving `user_id` as either the numeric `users.id`
   or the email itself.
3. **Scrubs PII** (does NOT delete) from shared/owned content where deleting the
   row would destroy other members' data — the owner column is blanked on
   `accountability_groups`, `church_profiles`, `churches`, `formation_tenants`,
   `organizations`, `prayer_templates`. Reassigning ownership of a still-active
   shared entity is a manual follow-up.
4. **Deletes** the account row in `users`.

Every table is guarded with `to_regclass`, so missing tables are skipped and the
routine is safe to re-run (idempotent). It returns one `(table_name,
rows_deleted)` row per table touched, for an audit trail.

## Follow-ups (out of scope for this migration set)

- **Wire an endpoint.** An authenticated `POST /api/account/erase` that calls
  `erase_user_data(current_user_email)` belongs in `main.py` (owned by another
  agent). This migration only ships the DB routine.
- **Regenerate on schema growth.** The table list is a point-in-time snapshot.
  When new personal tables are added, regenerate the arrays by re-scanning
  `migrations/*.sql` for `email` / `user_id` / `owner_email` / `created_by_email`
  columns.
- **Backups / logs.** Erasure covers the primary DB only; backups, exported
  analytics, and log stores must be handled separately per your retention policy.
