# SFDS v3 — Human Formation Intelligence System

> **"See yourself becoming yourself."**

SFDS v3 is a modular cognitive architecture that models human inner life as a multi-layer dynamic system. It integrates structural graph reasoning, temporal evolution tracking, semantic memory, LLM fusion intelligence, and long-term character formation modeling.

---

## System Purpose

This system is **NOT**:
- a decision-making oracle
- a psychological diagnosis tool
- a moral judgment system
- a religious authority

This system **IS**:
> A structural mirror of human inner dynamics over time.

It helps users:
- see internal patterns clearly
- understand emotional and motivational drivers
- recognize repeating behavioral loops
- detect long-term formation trajectories
- develop reflective awareness

---

## Architecture: 5 Cognitive Layers

```
User Input
    ↓
[Layer 1] Semantic     — pgvector: meaning, principles, similar cases
    ↓
[Layer 2] Structural   — Neo4j: behavioral loops, causal chains
    ↓
[Layer 3] Temporal     — TimescaleDB: cycles, trends, seasons
    ↓
[Layer 4] Reasoning    — LLM Fusion: integrated discernment
    ↓
[Layer 5] Formation    — FormationEngine: long-term character trajectory
    ↓
Output + Persistence (all 4 stores)
```

---

## Quick Start

```bash
cp .env.example .env
# fill in OPENAI_API_KEY and passwords

make up
make migrate
make seed
```

API: http://localhost:8000  
Web: http://localhost:3000  
API Docs: http://localhost:8000/docs  
Neo4j Browser: http://localhost:7474

---

## Repo Structure

```
sfds/
├── apps/
│   ├── api/              FastAPI backend (orchestration gateway)
│   └── web/              Next.js frontend
│
├── services/
│   ├── core-engine/      LLM fusion + reasoning coordinator
│   ├── formation-engine/ Long-term character trajectory model
│   ├── graph-service/    Neo4j query + pattern detection
│   ├── time-series-service/ TimescaleDB analytics
│   └── vector-service/   pgvector semantic search
│
├── packages/
│   ├── shared-types/     Shared DTOs, schemas, enums
│   ├── prompts/          Versioned LLM prompts
│   └── config/           System config + env
│
├── infra/
│   ├── postgres/         SQL schemas + migrations
│   ├── neo4j/            Graph schema + seed Cypher
│   ├── timescale/        Time-series schema
│   └── docker/           Dockerfiles
│
├── ai/
│   ├── embeddings/       Embedding pipeline
│   ├── reasoning/        LLM orchestration
│   └── prompt-engine/    Prompt builders + versioning
│
├── domain/
│   ├── decision/         Decision domain model
│   ├── emotion/          Emotion model
│   ├── motive/           Motive analysis model
│   ├── formation/        Formation state model
│   └── principle/        Spiritual principle model
│
├── graph/
│   ├── patterns/         Human behavioral loop library
│   ├── queries/          Reusable Cypher queries
│   └── loaders/          Graph ingestion scripts
│
├── docs/                 Architecture + design docs
├── scripts/              Seed + rebuild scripts
└── tests/                Unit + integration + graph tests
```

---

## Service Responsibility Boundaries

| Service | Responsibility | Core Question |
|---|---|---|
| `vector-service` | Meaning | WHAT principles apply? |
| `graph-service` | Structure | WHY does this pattern repeat? |
| `time-series-service` | Evolution | WHEN and HOW LONG has this been happening? |
| `core-engine` | Reasoning | HOW to interpret all of this? |
| `formation-engine` | Identity trajectory | WHO AM I BECOMING? |
| `api` | Orchestration | Route, validate, coordinate |

---

## Design Invariants

The system **MUST**:
- ✔ Never assign permanent identity labels
- ✔ Never judge moral worth
- ✔ Never act as authority over human value
- ✔ Never enforce behavioral control
- ✔ Always use probabilistic language ("may", "might", "possible")
- ✔ Always cap confidence at 0.90
- ✔ Always fail gracefully — never block the user

---

## Formation State Vector (v3.1)

The Formation Engine outputs an 8-dimension vector:

```json
{
  "humility":            0.0 - 1.0,
  "fear_tendency":       0.0 - 1.0,
  "pride_tendency":      0.0 - 1.0,
  "emotional_stability": 0.0 - 1.0,
  "truth_alignment":     0.0 - 1.0,
  "relational_health":   0.0 - 1.0,
  "resilience":          0.0 - 1.0,
  "spiritual_clarity":   0.0 - 1.0
}
```

> These are **behavioral tendency indicators**, not moral scores. They describe trajectory, not identity.

---

## Key API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/sfds/v2/analyze` | Full pipeline analysis |
| GET | `/api/sfds/v3/formation/profile/{user_id}` | Formation trajectory profile |
| GET | `/api/sfds/v3/formation/dimensions` | Dimension metadata |
| POST | `/api/sfds/v2/graph/reason` | 6-layer graph reasoning |
| GET | `/api/sfds/v2/graph/detect-loop/{user_id}` | Loop detection |
| GET | `/api/sfds/v2/graph/patterns` | Pattern library |

---

## Docs

- [Architecture Overview](docs/architecture.md)
- [Reasoning Model](docs/reasoning_model.md)
- [Formation Engine](docs/formation_engine.md)
