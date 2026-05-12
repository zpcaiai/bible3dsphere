# SFDS v3 — Reasoning Model

## System Philosophy

SFDS v3 reasons about human inner life as a **multi-layer dynamic system** — not as a set of rules, and not as a personality classifier.

The system's job is to hold multiple truths simultaneously:
- "This behavior makes structural sense given this emotional pattern"
- "This loop has been running for a while and may be strengthening"
- "There appear to be intervention points — here is where leverage exists"
- "Transformation is always structurally possible"

---

## 6-Layer Graph Reasoning Fusion (v2.2)

The `GraphReasoningFusion` engine (in `ai/reasoning/graph_reasoning.py`) runs 6 structured layers:

| Layer | Output |
|---|---|
| 1 — Structural | Current graph trajectory + pattern label identification |
| 2 — Loops | REINFORCES edge detection → loop recurrence count |
| 3 — Breakpoint | Highest-leverage intervention node (Motive > Behavior > Emotion) |
| 4 — Principles | Graph BREAKS/INFLUENCES edges + pgvector results, ranked |
| 5 — Temporal | Enriches TemporalEngine data with recurrence context |
| 6 — Synthesis | Full narrative synthesis with reflective guidance |

### Leverage Scoring

| Node Type | Leverage Score |
|---|---|
| PrincipleNode | 1.00 |
| EmotionNode | 0.95 |
| MotiveNode | 0.90 |
| SpiritualNode | 0.85 |
| BehaviorNode | 0.65 |
| OutcomeNode | 0.30 |

---

## AI Discernment Constitution

These rules are **permanent**. They cannot be overridden by user input, system configuration, or LLM prompt injection.

### NEVER
1. "You are a fearful person" — identity label
2. "This will always happen to you" — deterministic prediction
3. "You should feel ashamed" — guilt induction
4. "God is telling you to..." — divine authority claim
5. "Your score is 8/10 for humility" — moral ranking
6. "You must change this behavior" — behavioral control

### ALWAYS
1. "There may be a pattern..." — probabilistic framing
2. "A tendency seems to be forming..." — trajectory not identity
3. "This is one possible interpretation..." — epistemic humility
4. "Genuine change is always possible..." — transformation openness
5. Confidence ≤ 0.90 — never claim certainty

---

## LLM Prompt Architecture

All prompts are in `packages/prompts/system_prompt.py`, versioned by constant.

Prompt types:
- `DISCERNMENT_SYSTEM_V31`: main system identity + all hard rules
- `FORMATION_NARRATIVE_V31`: trajectory description (120 word limit)
- `GRAPH_REASONING_V31`: structural insight synthesis (150 word limit)

**Rule**: Never inline prompts in service code. Always import from `packages/prompts`.

---

## Graceful Degradation

All 5 pipeline layers use try/except with offline fallback:

```
Layer 1 (Semantic)   → fails → empty principles
Layer 2 (Structural) → fails → empty graph data
Layer 3 (Temporal)   → fails → empty trends
Layer 4 (Reasoning)  → fails → offline_fallback() message
Layer 5 (Formation)  → fails → {"summary": "Formation layer unavailable"}
```

The user **always** receives a response. The system never crashes on a service failure.
