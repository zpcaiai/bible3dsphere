# Formation Chain Model

## Shape

A chain may contain the following sequence without requiring every position:

```text
Life event → interpretation → identity/belief → desire/fear → emotion
→ temptation/choice → behavior/practice → outcome → formation direction
```

Grace evidence, protective factors, and recovery responses may be attached wherever the user places them. Missing nodes remain missing.

## Records

- `formation_twin_formation_nodes` contains content, node type, provenance, scope, evidence, review state, revision, and expiration.
- Category tables preserve canonical identity, interpretation, belief, desire, fear, temptation, behavior/practice, and outcome records.
- `formation_twin_formation_edges` contains only closed relation values. `CAUSED`, `PROVED`, and `DETERMINED` are rejected by the database.
- `formation_twin_formation_chains` stores scope, review state, completeness, alternative-chain reference, version, limitations, and context exclusion.
- `formation_twin_chain_nodes` and `formation_twin_chain_edges` keep editable order.

## Relation semantics

Rule assembly uses only `OBSERVED_IN_SAME_EVENT` (and may use neutral chronological relations). This means two records occurred in one authorized event; it does not prove a psychological, moral, or spiritual cause.

User-created edges use `USER_ASSOCIATED_WITH`. When a user confirms a model pattern, the system creates a new `USER_CONFIRMED_FORMATION_PATTERN` record; the model record remains a model record.

## Alternatives and editing

A chain can be duplicated with `alternative_of_chain_id`. The user may reorder nodes, add/remove nodes and edges, edit title and scope, confirm, reject, exclude, or delete a chain. Completeness is structural coverage only and is never presented as spiritual completeness or quality.

## Lifecycle

Deletion and event exclusion invalidate active snapshots. Rebuild supersedes deterministic/model nodes and rule-assembled chains while retaining active user-authored and user-confirmed records. A revoked review deletes the derived confirmed record and returns the original hypothesis to pending.
