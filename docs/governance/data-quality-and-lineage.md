# Data Quality and Lineage

Quality rules cover schema/version validity, source references, consent state, tenant ownership, timestamps, user-confirmation state, deletion state, and forbidden sensitive payloads. High-severity issues block display and release.

Every derived record links source IDs, transformation/rule version, creation time, consent purpose, and invalidation state. User corrections and denials are durable lineage events. Rebuild and restore must replay consent withdrawals and deletion tombstones before derived data becomes visible.

Dashboards expose counts, states, reason codes, and safe references; they do not expose journal bodies or a consolidated life profile.
