# Cross-module command routing

Recommendations are not commands. A command requires:

- an explicit user-confirmation UUID;
- current consent and a fresh proposal;
- a registered target-module executor;
- a target-specific payload schema and field allowlist;
- an idempotency key and optional expiry;
- a rechecked safety gate.

The target module creates its own canonical record and returns the record ID.
The platform stores the command/result/reference only. Failed execution never
switches silently to another high-impact action.

Batch 9 registers a local platform action adapter so a user can manage a
platform-coordination action. Existing Prayer, Habit, Attention, Formation,
Calling and Mission modules are marked degraded until their explicit Batch 9
command adapters are registered; the router does not write their core tables.
