# Formation Graph

## Role

Neo4j is an optional projection for navigating user-confirmed formation chains. PostgreSQL remains authoritative. Manual records, review, deterministic chain assembly, snapshots, export, and erase continue when Neo4j is absent.

## Projection boundary

A projected node contains only:

- tenant ID and profile ID;
- canonical node and chain IDs;
- node type, source kind, statement type, and review status;
- SHA-256 content hash.

Projected edges contain tenant/profile IDs, edge ID, relation type, and statement type. Full content is never included. In particular, no diary, prayer, confession, temptation, transcript, crisis body, evidence excerpt, alternatives, or user comment is projected.

## Isolation

Every `MATCH` and `MERGE` includes both `tenant_id` and `profile_id`. An edge is created only when both endpoints were selected from the same reviewed chain and same identity. Graph erase uses the exact tenant/profile pair and does not issue a broad graph delete.

## Eligibility and operation

Graph projection is off by default and requires both per-profile consent and the environment feature flag. Only a user-confirmed chain can be synced. Unreviewed model hypotheses are filtered even inside a confirmed chain.

Each attempt produces a PostgreSQL metadata receipt with status and counts. Connection details and sensitive content are not placed in that receipt. `DISABLED` and `UNAVAILABLE` are normal, fail-closed states.
