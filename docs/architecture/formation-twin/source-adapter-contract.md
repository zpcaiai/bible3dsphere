# Source-adapter contract

Nine adapters are registered in `backend/formation_twin/normalizer.py`. The minimum Batch 02 set—Prayer, Holy Habit, Devotion, Attention, and Crisis—is present, with Formation, Worldview, Gift/Calling, and Church adapters added through the same contract.

Each adapter declares a source type, canonical event type, allowed fields, and blocked fields. New source connections start paused. Internal delivery requires service identity, user/source match, active consent, source event ID, aware occurrence time, and the raw payload. Unknown fields are discarded by name; discarded values are never stored.
