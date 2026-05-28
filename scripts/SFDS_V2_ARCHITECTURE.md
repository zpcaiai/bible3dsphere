# SFDS V2 — Spiritual Formation & Discernment System Architecture

## System Purpose

This system is **NOT**:
- A chatbot
- A moral judge
- A religious authority

It **IS**:
> A multi-layer intelligence system that helps users **see** — hidden motives, repeating patterns, emotional cycles, and spiritual formation over time — while preserving their autonomy and freedom.

**The system is a mirror, not a judge.**

---

## Design Constraints

| Constraint | Implementation |
|---|---|
| Do NOT over-moralize | All output uses "may", "might", "possible" framing |
| Do NOT claim divine certainty | Disclaimer attached to every output |
| Do NOT generate guilt scoring | No negative scoring systems |
| Preserve autonomy | Reflective questions, never commands |
| Preserve uncertainty | Confidence scores shown; fallback graceful |
| Human formation ≠ machine prediction | Free will, grace, mystery acknowledged |

---

## System Flow

```
User Input
    ↓
1. State Snapshot         PostgreSQL — FACTS
    ↓
2. Semantic Retrieval     pgvector — MEANING
    ↓
3. Graph Query            Neo4j — STRUCTURE (WHY)
    ↓
4. Time-Series Query      TimescaleDB — TIME (WHEN)
    ↓
5. LLM Discernment        Fusion Reasoning (WHAT NOW)
    ↓
Guidance Output
    ↓
Write-back:
    ├── Neo4j graph update
    ├── TimescaleDB timeline update
    └── PostgreSQL decision log
```

---

## Four Intelligence Layers

### 1. PostgreSQL — Facts
- Decision events, motive scores, emotional logs, review outcomes
- Provides factual history and V1 discernment results
- File: `backend/decision_support.py`, `backend/sfds_schema_core.sql`

### 2. pgvector — Meaning (semantic)
- Embeddings of spiritual principles and past decisions
- Retrieves semantically similar principles for current situation
- Integrated: caller passes `semantic_principles` list into pipeline

### 3. Neo4j — Structure (WHY)
- **Answers: Why does this pattern keep appearing?**
- 22 seeded human formation loop patterns across 7 categories:
  - `fear`: control/burnout, avoidance/stagnation, people-pleasing, urgency/decision
  - `pride`: comparison, self-sufficiency, defensiveness, ambition/shortcuts
  - `shame`: avoidance/procrastination, self-punishment, overcompensation
  - `desire`: loneliness/attachment, gratification/debt, escapism/numbing
  - `relational`: unforgiveness, codependency, comparison/envy
  - `spiritual`: duty/exhaustion, calling/fear
  - `growth`: truth/humility, suffering/character, gratitude/generosity
- Causal chains with cycle detection
- Pattern write-back per user for longitudinal tracking
- File: `backend/graph_layer.py`

### 4. TimescaleDB — Time (WHEN)
- **Answers: How did I get here? When does this happen?**
- Hypertables: `sfds_user_spiritual_timeline`, `sfds_decision_outcome_timeline`, `sfds_emotional_cycle_series`
- Detects: anxiety cycles, burnout trajectories, spirals, seasonal patterns
- Classifies spiritual season: dry / stable / growing / confused / restoring
- Computes trend: improving / declining / stable / volatile
- File: `backend/temporal_engine.py`, `backend/sfds_timescale_schema.sql`

### 5. LLM Discernment — Reasoning
- Fuses all four layers into coherent spiritual formation intelligence
- V1: rule-based motive/source analysis (fear, pride, shame, love, etc.)
- V2: integrates graph + temporal + semantic + state into `V2DiscernmentResult`
- File: `backend/discernment_engine.py`

---

## Formation Pipeline

File: `backend/formation_pipeline.py`

```python
pipeline = FormationPipeline(db_pool=pool)
output = pipeline.run(PipelineInput(...))
pipeline.write_back(inp, matched_pattern_ids, outcome)
```

`FormationOutput` contains:
- `1_structural` — WHY (graph patterns, cycles, intervention break points)
- `2_temporal`   — WHEN (trend, season, detected patterns)
- `3_alignment`  — WHERE (spiritual trajectory)
- `4_intervention` — NOW (awareness prompts + reflective questions)
- `reflective_questions` — Open questions for the user's own discernment
- `disclaimer` — Always present; preserves autonomy

---

## API Endpoints

All under `/api/sfds/`:

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v2/discern` | Full 5-layer formation analysis |
| POST | `/v2/timeline/record` | Record spiritual formation checkpoint |
| POST | `/v2/emotions/record` | Record emotion intensity event |
| GET  | `/v2/timeline/{user_id}` | Temporal dashboard (trend, season, patterns) |
| GET  | `/v2/graph/patterns` | Browse all 22 formation loop patterns |
| POST | `/reflective-discern` | V1 reflective discernment (preserved) |

---

## Environment Variables

```bash
# Neo4j (optional — engine falls back to offline mode without it)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# PostgreSQL / TimescaleDB (same connection)
DATABASE_URL=postgresql://user:password@host:5432/dbname
# TimescaleDB extension must be enabled:
# CREATE EXTENSION IF NOT EXISTS timescaledb;
```

---

## File Index

| File | Role |
|------|------|
| `backend/graph_layer.py` | Neo4j connection, 22 patterns, GraphService |
| `backend/temporal_engine.py` | TimescaleDB access, cycle/burnout/season detection |
| `backend/sfds_timescale_schema.sql` | TimescaleDB schema with hypertables + aggregates |
| `backend/formation_pipeline.py` | Unified 5-layer pipeline orchestrator |
| `backend/discernment_engine.py` | V1 engine + V2 fusion engine |
| `backend/decision_support.py` | FastAPI router, V2 endpoints, models |
| `backend/main.py` | App startup, init_v2_engine hook |
| `backend/requirements.txt` | Python dependencies (includes neo4j>=5.14.0) |
| `sfds-frontend/lib/types.ts` | TypeScript V2 types |
| `sfds-frontend/lib/api.ts` | Frontend API client |
| `sfds-frontend/app/decision/[id]/analysis/page.tsx` | Analysis UI — 4 insight pillars |

---

## Key Design Decision: Formation vs. Prediction

> **Spiritual formation is not computable.**

The system tracks patterns and surfaces possibilities — but it:
- Never claims a pattern IS present (only "may be")
- Never predicts outcomes
- Never removes the user's freedom to disagree
- Always appends a disclaimer
- Expresses confidence scores to show uncertainty

The graph and time-series layers increase the *resolution* of the mirror.
They do not replace the user's discernment — they inform it.

---

## Upgrade History

| Version | Changes |
|---------|---------|
| V1 | Single-decision motive/source analysis |
| V2 | + Neo4j graph layer (22 patterns, cycle detection, write-back) |
| V2 | + TimescaleDB temporal layer (seasons, trends, burnout detection) |
| V2 | + FormationPipeline (5-layer unified orchestrator) |
| V2 | + Reflective questions per pattern (never commands) |
| V2 | + Updated frontend with 4-pillar analysis UI |
