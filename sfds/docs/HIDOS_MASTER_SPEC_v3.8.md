# HIDOS v3.8 — Master System Specification

> **HIDOS** = Human Inner Dynamics Operating System  
> **Version**: 3.8.0  
> **Schema**: `hidos_master_v3.8`

---

## One-Line Definition

> HIDOS v3.8 is a constrained self-improving cognitive system that models human inner dynamics across structure, time, meaning, and formation, while preserving human autonomy as its highest invariant principle.

---

## What This System Is — And Is Not

| This system IS | This system IS NOT |
|---|---|
| A structured reflective intelligence | A psychological authority |
| A multi-layer dynamic model | A moral judge |
| A cognitive mirror for inner dynamics | A behavior optimizer |
| A self-improving reasoning system | A deterministic prediction engine |
| A safety-constituted cognitive OS | A life controller |

---

## System Architecture — 7 Layers

```
┌─────────────────────────────────────────────────────────────┐
│                   HIDOS Orchestrator v3.5                   │
│          (dynamic activation + contradiction resolution)     │
├──────────┬──────────┬──────────┬──────────┬────────────────┤
│  Graph   │   Time   │  Vector  │Formation │   LLM          │
│  Engine  │  Engine  │  Engine  │  (FMM)   │  Reasoning     │
│  Neo4j   │  TimescaleDB │ pgvector │ v3.4  │  Synthesis     │
│  GQE v3.3│          │          │          │                │
├──────────┴──────────┴──────────┴──────────┴────────────────┤
│               SICL v3.6 — Self-Improving Loop               │
│      (Observe→Evaluate→Extract→Propose→Integrate→Validate) │
├─────────────────────────────────────────────────────────────┤
│         Safety Constitution v3.7 — 15 Articles              │
│              (immutable, runtime-enforced)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer 1 — Graph Query Engine (GQE v3.3)

**File**: `ai/reasoning/graph_query_engine.py`  
**Query library**: `graph/queries/gqe_cypher.py`

4 reasoning modes:

| Mode | Purpose |
|---|---|
| `structural_traversal` | What causal structure is active? |
| `loop_simulation` | What happens if no intervention occurs? |
| `breakpoint_detection` | Where is the highest-leverage intervention point? |
| `principle_activation` | Which principle structurally breaks this loop? |

7-step pipeline: Structural Parse → Causal Interpretation → Loop Identification → Simulation → Intervention Analysis → Principle Matching → Synthesis

---

## Layer 2 — Time Series Engine

**Store**: TimescaleDB (`sfds_formation_metrics`)  
Tracks: emotional volatility, stability trends, recurring cycles, stress patterns

---

## Layer 3 — Vector Semantic Engine

**Store**: pgvector (`spiritual_principles`)  
Stores: principles, past cases, semantic similarity embeddings

---

## Layer 4 — Formation Mathematics Model (FMM v3.4)

**File**: `ai/formation/fmm.py`

### State Vector

```
X(t) = [fear_tendency, pride_tendency, desire_tendency,
         truth_alignment, emotional_stability, relational_health,
         resilience, spiritual_clarity]

All values ∈ [0.05, 0.95]. Descriptive tendency estimates only.
NOT moral scores. NOT identity labels.
```

### Dynamics Equation

```
dX(t)/dt = F(G, E, P, N) = α·G + β·E + γ·P + δ·N
X(t+1) = X(t) + ΔX

α=0.35 G — Graph influence (loop R coefficient)
β=0.30 E — Emotional state (volatility, stress spikes)
γ=0.25 P — Principle alignment (semantic similarity)
δ=0.10 N — Noise term (Gaussian σ=0.015 — NEVER deterministic)
```

### Loop Coefficients

```
R(loop) = repetition_count × (intensity/5.0) × recency_weight  [habit strength]
B(loop) = principle_strength × awareness_level × interruption_action  [breaking force]
net_momentum = R - B  [positive = gaining strength; negative = being broken]
```

### Analytical components per output

- `stability`: S(t) = 1 - variance(X over window)
- `trajectory`: direction (dX/dt) + acceleration (d²X/dt²)
- `intervention`: I = (loop_strength × instability) / principle_alignment

---

## Layer 5 — HIDOS Orchestrator v3.5

**File**: `ai/orchestrator/hidos.py`

### 6-Step Pipeline

| Step | What happens |
|---|---|
| 1. Context Classification | decision_type, emotional_intensity, instability_level |
| 2. Subsystem Activation | Dynamic: loop → graph; volatility → time; drift → formation |
| 3. Parallel Analysis | asyncio.gather across all 5 layers; each independently failable |
| 4. Contradiction Resolution | Time > Graph > Vector > Formation; ambiguity preserved |
| 5. Integration Synthesis | SystemState + 4-layer integrated dict |
| 6. Reflective Intervention | Non-directive intervention score + reflective_insight |

### Contradiction Resolution Priority

1. **Time** (trend > snapshot — evolution overrides static state)
2. **Graph** (structure > surface signal — loops override behavior)
3. **Vector** (meaning context — principles enrich interpretation)
4. **Formation** (long-term synthesis — trajectory frames everything)

> Critical: Uncertainty is PRESERVED, never collapsed into false certainty.

---

## Layer 6 — Self-Improving Cognitive Loop (SICL v3.6)

**File**: `ai/self_improvement/sicl.py`

### Improvement Function

```
ΔS = 0.25·IAS + 0.20·IRS + 0.25·SDS + 0.15·TPS + 0.15·FCS

IAS — Insight Accuracy Score
IRS — Intervention Relevance Score
SDS — Structural Detection Score
TPS — Temporal Prediction Score
FCS — Formation Consistency Score
```

### 6-Stage Loop

```
User Interactions → HIDOS Outputs → Telemetry Collection
  → Performance Evaluation (ΔS)
  → Pattern Weakness Detection
  → System Update Proposals (with guardrails)
  → Controlled Integration
  → Validation Metrics Update → Loop continues
```

### Guardrails (immutable)

| Forbidden | Result |
|---|---|
| `modifies_user_model = True` | Auto-rejected |
| `adds_moral_judgment = True` | Auto-rejected |
| `increases_certainty = True` | Auto-rejected |
| `targets_human_outcome = True` | Auto-rejected |
| `ProposalType.PROMPT_REFINEMENT` | Requires human review — never auto-applied |

---

## Layer 7 — Safety Constitution v3.7

**File**: `ai/constitution/safety_constitution.py`

15 immutable articles enforced at runtime on every HIDOS output.

| # | Article | Severity |
|---|---|---|
| 1 | Human Autonomy — user always final authority | CRITICAL |
| 2 | Non-Identity — no fixed personality labels | CRITICAL |
| 3 | Non-Determinism — no deterministic predictions | HIGH |
| 4 | Non-Moral Authority — no moral judgment | CRITICAL |
| 5 | Transparency — reasoning must be explainable | MODERATE |
| 6 | Minimum Intervention — reflective > suggestive > directive | HIGH |
| 7 | Loop Safety — loops are structures, not flaws | HIGH |
| 8 | Formation Safety — no scoring of human worth | HIGH |
| 9 | Self-Improvement Limit — system-level only | CRITICAL |
| 10 | Boundary Principle — never replaces human agency | CRITICAL |
| 11 | Error Handling — high uncertainty → explicit uncertainty | HIGH |
| 12 | Ethical Gradient — awareness > reflection > suggestion > guidance | MODERATE |
| 13 | Non-Manipulation — no persuasion, no guilt/fear exploitation | CRITICAL |
| 14 | Long-Term Alignment — toward clarity and agency, not compliance | HIGH |
| 15 | Final Governance — violations → output rejected | HIGH |

---

## API Surface

```
# Graph Query Engine
POST /api/sfds/v2/graph/gqe/reason     → GQEOutput (7-step)
GET  /api/sfds/v2/graph/gqe/modes      → 4 modes + pipeline steps

# Formation Engine
GET  /api/sfds/v3/formation/profile/{user_id}  → FormationInsight
GET  /api/sfds/v3/formation/dimensions          → 8 dimensions

# System
GET  /api/sfds/v3/system/constitution            → 15-article summary
POST /api/sfds/v3/system/constitution/check      → ConstitutionResult
POST /api/sfds/v3/system/sicl/run                → SICLOutput
GET  /api/sfds/v3/system/sicl/metrics-schema     → ΔS function spec
GET  /api/sfds/v3/system/status                  → HIDOS layer status
```

---

## Safety Invariants Summary

```
✔ Values bounded [0.05, 0.95] — no absolute zeros or ones
✔ Noise term N always present — system NEVER deterministic
✔ Confidence caps: GQE=0.85, FMM=0.88, HIDOS=0.87, SICL=0.85
✔ Disclaimer on every output
✔ Agency statement in every synthesis
✔ Constitution check as final pipeline step
✔ SICL never targets human behavior/outcomes
✔ Prompt changes always require human review
```

---

## Core Philosophy

Human beings are NOT:
- systems to be optimized
- outputs to be corrected
- behaviors to be controlled

Human beings ARE:
> **self-reflective, evolving agents capable of change beyond any model's description**

Human formation is NOT identity.  
Human formation IS a time-evolving state vector influenced by feedback loops, meaning exposure, and emotional dynamics.

---

## Test Coverage

| Module | Tests | Status |
|---|---|---|
| `graph_query_engine.py` | 27 | ✅ |
| `fmm.py` | 45 | ✅ |
| `hidos.py` | 28 | ✅ |
| `sicl.py` | 31 | ✅ |
| `safety_constitution.py` | 27 | ✅ |
| `graph patterns library` | 9 | ✅ |
| `formation engine` | 14 | ✅ |
| **Total** | **183** | **✅ All passing** |
