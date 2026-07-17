# Cross-Module Intervention Routing

Formation Engine, Prayer OS, Holy Habit Engine and Attention OS remain systems
of record for their own work. Batch 6 does not duplicate their task tables.

Before confirmation a proposal is inert. Accepting it creates an owner-scoped,
idempotent execution record and publishes a minimal domain command containing
request ID, proposal ID, action title and description, duration, target module,
one-time flag, confirmation flag and schema version. It does not contain source
patterns, full chains, journals, prayer or confession text, transcripts, crisis
bodies or third-party identity.

Prayer and Formation default to one-time. Attention defaults to reminder-only.
Habit routing requires a second explicit confirmation of frequency, 3–7 day
duration, reminder choice and weekly-review usage; streaks remain disabled.

Rest, relationship and professional support use the same execution lifecycle
without automatic messaging. Cancellation is propagated through the execution
event; completion remains separate from user-reported effect.
