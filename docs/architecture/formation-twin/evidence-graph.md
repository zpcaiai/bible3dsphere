# Temporal Evidence Graph

PostgreSQL is the source of truth. The optional Neo4j projection contains only
owner-scoped IDs, node/relationship types, lifecycle/review status, version, and
temporal properties. It never contains full diary, prayer, confession,
temptation, transcript, third-party, or crisis text.

Projected labels include FormationPattern, PatternEvidence, and LifeSeason, all
also labeled `FormationTwinOwned`. Relationships include evidence-to-pattern and
active-during-season links with tenant ID, profile ID, observed time, and status.
All Cypher queries require both owner identifiers.

Graph operation is feature-flagged and fail-closed. Disabled returns DISABLED;
missing infrastructure returns UNAVAILABLE. Neither is reported as synchronized.
Evidence deletion marks its projection invalid. Long-term-model erasure removes
only `FormationTwinOwned` nodes for the exact tenant/profile. Full Formation Twin
erasure additionally removes Batch 1–4 FormationNode projections.

Consistency scans compare PostgreSQL pattern IDs with graph IDs. A mismatch is a
high-severity data-quality issue and blocks graph-dependent context, while the
PostgreSQL user experience continues in degraded mode.
