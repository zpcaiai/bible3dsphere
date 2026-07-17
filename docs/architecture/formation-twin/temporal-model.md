# Formation Twin Temporal Model

Batch 5 distinguishes `occurred_at`, `recorded_at`, and processing time. Pattern
discovery orders evidence by `occurred_at`; delayed recording is retained as
provenance and is never rewritten into an exact occurrence time.

`resolve_temporal_windows()` calculates DAY, WEEK, MONTH, QUARTER, and YEAR
boundaries in the user's IANA timezone and then stores UTC instants. This keeps
local calendar meaning across daylight-saving transitions. An event can also
belong to user-defined, project, life-season, recovery, or church-season windows.
Changing a current timezone does not rewrite historical instants or duplicate
events.

Approximate ranges retain their precision and original expression. `UNKNOWN`
requires an original expression such as “刚信主的时候”; it is not converted to
an invented date. All persisted windows have an explicit source, status, owner,
start, end, and timezone.

Incremental jobs use event time plus an event ID checkpoint. Rebuild is versioned
and excludes deleted, excluded, `STORE_ONLY`, or unconsented source records.
