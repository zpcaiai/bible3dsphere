# Life-event model

The authoritative Python model is `backend/formation_twin/contracts.py`; the checked-in JSON Schema is `backend/formation_twin/canonical-life-event.schema.json`; the web contract is `src/features/formation-twin/lifeEventContract.ts` in the web repository.

All three use event version `1.0`, explicit statement types, separate occurred/recorded time, source provenance, consent, safety, lifecycle status, and an opaque sensitive-content reference. `OTHER` is the forward-compatible event/source fallback. The contract has no `SYSTEM_INFERENCE` value.
