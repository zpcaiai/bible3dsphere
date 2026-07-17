# Risk Condition Model

Risk conditions are expiring observations, not moral conclusions. Each record
has a condition type/code, user-visible description, source kind, statement
type, occurrence/expiry time, evidence references and confirmation state.

Only current, confirmed conditions participate. Evidence with the same
`independence_group` is counted once. Unknown conditions remain unknown; the
engine never assumes device access, isolation or another sensitive condition.
Emotion alone and ordinary sleep/stress conditions cannot produce a high-level
warning.

Allowed inputs are user reports, confirmed emotional/formation structure,
confirmed cycles, consented metadata, life-season context and active
protections. Rejected, outdated, `STORE_ONLY`, secretly supplied or expired
data fail closed. Source deletion or rejection invalidates dependent conditions,
snapshots and warnings.
