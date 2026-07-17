# Purpose-based access

Policy is default deny. A decision intersects four dimensions:

1. authenticated caller and current-user subject;
2. registered purpose and requester module;
3. registered projection for that purpose;
4. active user consent and its field subset.

Examples:

| Purpose | Requester | Projection |
|---|---|---|
| `GENERATE_PRAYER_PROMPT` | Prayer OS | `prayer_context_v1` |
| `CREATE_FORMATION_PRACTICE` | Formation Engine / Twin | formation or habit context |
| `CREATE_ATTENTION_BOUNDARY` | Attention OS | `attention_context_v1` |
| `PREPARE_CALLING_REFLECTION` | Gift and Calling OS | `calling_context_v1` |
| `PREPARE_PASTORAL_BRIEF` | Church Health OS | `church_context_v1` |
| `PREPARE_MISSION_REFLECTION` | Mission System | `mission_context_v1` |
| `GENERATE_UNIFIED_HOME` | Platform Orchestrator | `unified_home_context_v1` |
| `ROUTE_CRISIS_CASE` | Crisis Care | `crisis_routing_context_v1` |

The access audit stores requester, purpose, projection, allowed/denied field
names, decision reason codes, correlation ID and expiry—never source content.
