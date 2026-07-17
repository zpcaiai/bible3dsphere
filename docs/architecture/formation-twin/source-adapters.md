# Formation Twin source adapters

The adapter registry is allowlist-based and covers nine existing domains: prayer, holy habit, devotion, attention, crisis care, formation, worldview, gift/calling, and church life.

Every source is `PAUSED` by default. The user must enable it in Data Sources before `/api/v1/formation-twin/internal/module-events` accepts events. The endpoint requires `X-Formation-Twin-Service-Key` and maps only fields declared in `backend/formation_twin/normalizer.py`.

Examples of blocked data include prayer body, private habit notes, browsing history, crisis text, pastoral notes, member identity, unconfirmed worldview inference, spiritual scores, and declarations about divine calling. The canonical event bus receives metadata only.
