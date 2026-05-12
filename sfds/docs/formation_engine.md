# Formation Engine — Design Document

> "You are not what you scored. You are what you are becoming."

---

## Core Concept

Character is **NOT a static score**.

It is a **trajectory** formed by:
- repeated decisions
- emotional response patterns
- motive reinforcement loops
- reflection and awareness moments

The Formation Engine answers: **"WHO AM I BECOMING?"**

---

## 8-Dimension FormationStateVector

```json
{
  "humility":            0.05 – 0.95,
  "fear_tendency":       0.05 – 0.95,
  "pride_tendency":      0.05 – 0.95,
  "emotional_stability": 0.05 – 0.95,
  "truth_alignment":     0.05 – 0.95,
  "relational_health":   0.05 – 0.95,
  "resilience":          0.05 – 0.95,
  "spiritual_clarity":   0.05 – 0.95
}
```

**Critical note on `fear_tendency` and `pride_tendency`:**
- Higher = more active loop momentum
- This is a **structural signal**, not a moral judgment
- Higher fear_tendency means: "the fear loop is more entrenched" — not "this person is a coward"

---

## 5 Internal Computation Layers

### Layer 1 — Behavioral Reinforcement Analysis
- Which dimensions are gaining/losing momentum?
- What is the loop intensity (0–1)?
- Which patterns are entrenching vs. weakening?

### Layer 2 — Trajectory Direction Analysis
Output: one of `stabilizing | fragmenting | improving_clarity | increasing_volatility | cyclical | unknown`

Decision logic:
- `improving_clarity`: clarity_delta > 0.05 AND truth_delta > 0.05
- `increasing_volatility`: stability_delta < -0.08 AND fear_delta > 0.08
- `stabilizing`: resilience_delta > 0.05 AND fear_delta < -0.03
- `fragmenting`: fear_delta > 0.10 OR stability_delta < -0.12
- `cyclical`: history variance > 0.02 (repeating up/down)

### Layer 3 — Character Drift Detection
- Dimensions >0.12 from baseline (0.5) = **structural drift**
- Drift = slow long-term change, not session-level noise
- 2+ dimensions drifting simultaneously = **drift_detected: True**

### Layer 4 — Loop Dominance Analysis
- Counts category frequency in full history
- Current session weighted 3x
- Falls back to state vector inference when no history

### Layer 5 — Spiritual Alignment Trend
- Signal = `truth_delta + humility_delta + clarity_delta + stability_delta`
- `> 0.08` → "improving"
- `< -0.08` → "declining"
- else → "stable"

---

## Update Weighting Rules

| Rule | Mechanism |
|---|---|
| **Recency** | Exponential decay: `weight = 0.92^k` (k = sessions back) |
| **Emotional intensity** | `delta *= (intensity / 5.0)` — intensity=10 doubles impact |
| **Reflection damping** | Negative impact `*= 0.60` when `reflection_active=True` |
| **Loop repetition** | Embedded in recency-weighted history accumulation |

---

## Formation Arc Classification

| Arc | Condition |
|---|---|
| `breaking_through` | ≥3 healthy dims with delta >0.04 (excl. fear/pride tendency) |
| `deepening_loops` | fear_tendency or pride_tendency delta >0.06 |
| `stabilizing` | >8 sessions history, avg healthy score >0.58 |
| `unknown` | Default (insufficient data) |

---

## 5 Dominant Loop Types

| Loop | Pattern |
|---|---|
| `fear_control_loop` | fear → control → overwork → burnout → fear |
| `shame_avoidance_loop` | shame → avoidance → procrastination → anxiety |
| `pride_comparison_loop` | pride → comparison → anxiety → instability |
| `desire_impulse_loop` | desire → impulsive action → regret → desire |
| `truth_stability_loop` | truth-facing → reflection → stability (healthy) |

---

## Design Invariants

| Invariant | Enforcement |
|---|---|
| No identity labels | Never output "you are X person" |
| No moral scoring | fear/pride tendency = signal, not judgment |
| No deterministic predictions | All language: "may", "might", "possible" |
| Bounded scores | `[0.05, 0.95]` always — no absolute zeros or ones |
| Confidence cap | Max 0.90 — never claim certainty |
| Graceful degradation | All layers fail silently — never block response |

---

## TimescaleDB Storage

Table: `sfds_formation_metrics`

| Column | Type | Description |
|---|---|---|
| `*_delta` x8 | REAL | Per-dimension weighted delta |
| `trajectory_direction` | VARCHAR(40) | Trajectory classification |
| `dominant_loop` | VARCHAR(60) | Dominant loop type |
| `emotional_intensity` | REAL | Session emotional intensity |
| `reflection_active` | BOOLEAN | Was reflection damping active? |
| `loop_broken` | BOOLEAN | Was a loop interrupted? |

Continuous aggregate: `sfds_formation_rolling_avg` (30-day rolling window)
Retention: 2 years
