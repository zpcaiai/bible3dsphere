# Temptation Cycle Model

Batch 7 models a user-confirmed, scoped sequence rather than a permanent
identity. `TRIGGER`, `VULNERABILITY`, `URGE`, `TEMPTATION`, `CHOICE_POINT`,
`BEHAVIOR_*` and `RECOVERY` are distinct nodes. A temptation node cannot assert
that behavior occurred.

Sensitive cycle types are accepted only when the user selects or confirms them.
One event never creates a global cycle automatically. Cycles can be draft,
active, paused, outdated, superseded or deleted, and updates create a new
version. A cycle may include interruption, resistance, protection,
reconnection and recovery paths—not only a fall/shame path.

The rule section records required and optional conditions, the minimum number
of independent conditions and a rule version. Unknown nodes and partial cycles
are valid. Cycle names remain user-owned and are never copied into ordinary
logs, notifications or domain-event payloads.
