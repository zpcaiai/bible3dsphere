# Source of truth matrix

| Data or state | Canonical owner | Platform may retain | Platform must not retain |
|---|---|---|---|
| User identity and tenant membership | Identity OS | subject reference and tenant key | duplicate credentials or organization-wide life profiles |
| Worldview reflections | Worldview Formation OS | user-confirmed theme reference | raw reflection body |
| Normalized life events | Formation Twin | canonical event metadata | source-module raw body |
| Current emotional state | Formation Twin | confirmed label references in an authorized projection | diagnosis or a unified emotion score |
| Formation chains and reviewed patterns | Formation Twin | node/chain references and statement status | unconfirmed hypothesis as fact |
| Prayer body and sessions | Prayer OS | confirmed need/reference | complete prayer text |
| Devotion sessions | Devotion System | session/reference and selected theme | private devotion journal body |
| Habit definition and occurrence | Holy Habit Engine | action reference and non-moral status | compliance or streak score |
| Attention boundary | Attention OS | confirmed boundary reference | secret browsing content or inferred temptation |
| Crisis case and safety plan | Crisis Care | minimum routing level and route availability | crisis narrative or internal risk score |
| Formation practice | Formation Engine | proposal/command/source reference | target module's canonical practice row |
| Gifts and calling reflection | Gift and Calling OS | confirmed gift/calling reference | declaration of God's certain will |
| Church participation | Church Health OS | user-selected participation/support reference | full Twin, member ranking or discipline action |
| Mission preparation/deployment | Mission System | confirmed readiness reference | unshared health, family, crisis or temptation details |
| Scripture entities and references | Bible Knowledge Graph | scripture reference | private user state in Neo4j |
| Notification delivery | Notification System | redacted delivery candidate/reference | sensitive lock-screen text |
| Search index | Search System | revocable confirmed reference | crisis, third-party, pending, excluded or `STORE_ONLY` text |
| Access and operation audit | Audit System | reason codes, purpose, field names, IDs and times | source body, search query or model prompt |

Formation Twin is the life-state context hub. It is explicitly not the global
raw data store, task executor, crisis authority, church authority or identity
provider.
