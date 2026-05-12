# SFDS v3 — System Architecture

## Core Philosophy

SFDS v3 is a **layered cognition system** — not a microservices mesh, not an advice engine.

Each layer has a single, non-overlapping cognitive responsibility:

| Layer | Service | Core Question | Data Store |
|---|---|---|---|
| Semantic | `vector-service` | WHAT principles apply? | PostgreSQL + pgvector |
| Structural | `graph-service` | WHY does this pattern repeat? | Neo4j |
| Temporal | `time-series-service` | WHEN / HOW LONG? | TimescaleDB |
| Reasoning | `core-engine` + `ai/` | HOW to interpret all of this? | LLM (OpenAI) |
| Formation | `formation-engine` | WHO AM I BECOMING? | TimescaleDB |

---

## Data Flow

```
User Input (DecisionRequest)
        │
        ▼
┌─────────────────────────────┐
│        API Layer            │  apps/api  — orchestration gateway only
│  POST /decision/create      │  No business logic here
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│   Core Engine               │  services/core-engine
│   Brain Coordinator         │  Fuses all layer outputs
└──┬──────┬──────┬────────────┘
   │      │      │
   ▼      ▼      ▼
Vector  Graph  TimeSeries     ← Run in parallel (independent concerns)
Service Service  Service
   │      │      │
   └──────┴──────┘
             │
             ▼
┌─────────────────────────────┐
│   AI Reasoning Fusion       │  ai/reasoning/fusion.py
│   LLM synthesis call        │  Prompts from packages/prompts
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│   Formation Engine          │  services/formation-engine
│   Long-term trajectory      │  5-layer character analysis
└─────────────┬───────────────┘
              │
              ▼
         Response Output
              │
              ▼
    Persistence Write-Back
   (Postgres + Neo4j + Timescale)
```

---

## Service Boundaries

### `vector-service` — Meaning Layer
- **In**: text query / decision description
- **Out**: ranked spiritual principles with similarity scores
- **Does NOT**: reason, judge, run graph queries

### `graph-service` — Structure Layer
- **In**: user_id, behavior types, motive
- **Out**: active loops, causal chains, intervention points
- **Does NOT**: embed, run LLM, query Timescale

### `time-series-service` — Temporal Layer
- **In**: user_id, time window
- **Out**: trend direction, cycles, instability signals
- **Does NOT**: embed, run graph queries, run LLM

### `core-engine` — Reasoning Coordinator
- **In**: DecisionRequest + all 3 service outputs
- **Out**: integrated discernment, formation update
- **Does NOT**: query any DB directly (delegates to services)

### `formation-engine` — Formation Layer
- **In**: pattern_categories, loop_broken, emotional_intensity, history
- **Out**: 8-dimension FormationStateVector + 5-layer analysis
- **Does NOT**: run LLM, query Neo4j, query principles

---

## Design Invariants (Hard Rules)

These are **architectural constants**, not configurable options:

1. `SYSTEM_ALLOW_IDENTITY_LABELS = False` — never assign permanent labels
2. `SYSTEM_ALLOW_MORAL_SCORING = False` — never judge moral worth
3. `SYSTEM_MAX_CONFIDENCE = 0.90` — never claim certainty
4. Formation scores bounded `[0.05, 0.95]` — no absolutes
5. All layers **fail gracefully** — never block user response
6. Probabilistic language enforced in all LLM prompts

---

## Replaceability

The architecture is designed so each component can be replaced independently:

| Component | Replaceable with |
|---|---|
| OpenAI GPT-4o | Any OpenAI-compatible LLM |
| pgvector | Qdrant, Weaviate, Pinecone |
| Neo4j | Memgraph, Amazon Neptune |
| TimescaleDB | InfluxDB, QuestDB |
| FastAPI | Any ASGI framework |
