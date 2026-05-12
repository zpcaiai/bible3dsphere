"""
Graph Pattern Library — SFDS v3 Human Behavioral Loop Catalog (50 Loops)

DESIGN PRINCIPLE:
  Each pattern is a DYNAMIC, INTERRUPTIBLE behavioral loop — NOT an identity type.
  Pattern = Emotion → Motive → Behavior → Outcome → Emotion (feedback loop)

  These patterns are:
    ✔ Repeatable dynamics — not fixed traits
    ✔ Interruptible at any node — especially at Motive or Principle level
    ✔ Structurally neutral — higher intensity = more active loop, NOT moral failure

  SAFETY: Never use these to label a person. Never suggest inevitability.
          Always emphasize possibility of interruption. Preserve user autonomy.

Categories:
  A (1–10)   — Fear-based loops
  B (11–20)  — Pride-based loops
  C (21–30)  — Shame/Avoidance loops
  D (31–38)  — Desire/Impulse loops
  E (39–44)  — Relational loops
  F (45–50)  — Spiritual/Meaning loops

Each pattern structure:
  id:           unique slug
  label:        human-readable loop name
  category:     driving emotion category (fear | pride | shame | desire | relational | spiritual)
  loop_type:    maps to FormationEngine DominantLoop enum
  chain:        [node_type, ...] — ordered causal sequence
  edges:        [(from, EDGE_TYPE, to), ...]
  break_edges:  [(principle_id, BREAKS, target_node)] — intervention points
  trigger_emotion:   entry-point emotion
  break_principle:   primary intervention principle label
  formation_dims:    {dimension: delta_direction} — which FSV dims this loop affects
"""

from typing import Any, Dict, List

from graph.patterns._loops_part1 import _LOOPS_A_B_C  # noqa: E402
from graph.patterns._loops_part2 import _LOOPS_D_E_F  # noqa: E402

PATTERN_LIBRARY: List[Dict[str, Any]] = _LOOPS_A_B_C + _LOOPS_D_E_F

_PATTERN_LIBRARY_LEGACY: List[Dict[str, Any]] = [

    # ── Legacy stubs (kept for backward-compat with old graph seeds) ──
    {
        "id":       "fear_control_overwork",
        "label":    "Fear → Control → Overwork → Burnout Loop",
        "category": "fear",
        "loop_type":"fear_control_loop",
        "description": (
            "Fear of failure or loss activates a control drive, "
            "leading to overwork, eventually causing burnout, "
            "which re-activates the fear response."
        ),
        "chain": ["fear", "control_drive", "overwork", "burnout"],
        "edges": [
            ("fear",          "CAUSES",     "control_drive"),
            ("control_drive", "LEADS_TO",   "overwork"),
            ("overwork",      "LEADS_TO",   "burnout"),
            ("burnout",       "REINFORCES", "fear"),
        ],
    },
    {
        "id":       "fear_avoidance_anxiety",
        "label":    "Fear → Avoidance → Anxiety Spiral",
        "category": "fear",
        "loop_type":"fear_control_loop",
        "description": (
            "Fear triggers avoidance of the feared situation. "
            "Avoidance provides short-term relief but amplifies long-term anxiety."
        ),
        "chain": ["fear", "avoidance", "relief", "anxiety_increase"],
        "edges": [
            ("fear",              "CAUSES",     "avoidance"),
            ("avoidance",         "LEADS_TO",   "relief"),
            ("relief",            "REINFORCES", "avoidance"),
            ("anxiety_increase",  "REINFORCES", "fear"),
        ],
    },

    # ── Shame Loops ───────────────────────────────────────────
    {
        "id":       "shame_hiding_isolation",
        "label":    "Shame → Hiding → Isolation Loop",
        "category": "shame",
        "loop_type":"shame_avoidance_loop",
        "description": (
            "Shame triggers concealment behaviors. "
            "Hiding prevents authentic connection, deepening shame over time."
        ),
        "chain": ["shame", "hiding", "isolation", "shame_deepening"],
        "edges": [
            ("shame",            "CAUSES",     "hiding"),
            ("hiding",           "LEADS_TO",   "isolation"),
            ("isolation",        "REINFORCES", "shame_deepening"),
            ("shame_deepening",  "REINFORCES", "shame"),
        ],
    },
    {
        "id":       "shame_perfectionism_failure",
        "label":    "Shame → Perfectionism → Failure Sensitivity",
        "category": "shame",
        "loop_type":"shame_avoidance_loop",
        "description": (
            "Shame drives perfectionism as a defense mechanism. "
            "Any perceived failure re-activates the shame response."
        ),
        "chain": ["shame", "perfectionism", "failure_sensitivity", "shame_trigger"],
        "edges": [
            ("shame",               "CAUSES",     "perfectionism"),
            ("perfectionism",       "LEADS_TO",   "failure_sensitivity"),
            ("failure_sensitivity", "REINFORCES", "shame_trigger"),
            ("shame_trigger",       "REINFORCES", "shame"),
        ],
    },

    # ── Pride Loops ───────────────────────────────────────────
    {
        "id":       "pride_comparison_instability",
        "label":    "Pride → Comparison → Anxiety → Instability",
        "category": "pride",
        "loop_type":"pride_comparison_loop",
        "description": (
            "Pride drives constant comparison with others. "
            "Comparison creates chronic anxiety and emotional instability."
        ),
        "chain": ["pride", "comparison", "anxiety", "instability"],
        "edges": [
            ("pride",       "CAUSES",     "comparison"),
            ("comparison",  "LEADS_TO",   "anxiety"),
            ("anxiety",     "LEADS_TO",   "instability"),
            ("instability", "REINFORCES", "pride"),
        ],
    },
    {
        "id":       "pride_image_management",
        "label":    "Pride → Image Management → Exhaustion",
        "category": "pride",
        "loop_type":"pride_comparison_loop",
        "description": (
            "Pride creates constant self-image management. "
            "The exhaustion from maintaining a false self reinforces the pride defense."
        ),
        "chain": ["pride", "image_management", "performance_anxiety", "exhaustion"],
        "edges": [
            ("pride",               "CAUSES",     "image_management"),
            ("image_management",    "LEADS_TO",   "performance_anxiety"),
            ("performance_anxiety", "LEADS_TO",   "exhaustion"),
            ("exhaustion",          "REINFORCES", "pride"),
        ],
    },

    # ── Healthy Loops ─────────────────────────────────────────
    {
        "id":       "truth_reflection_stability",
        "label":    "Truth-Facing → Reflection → Stability Loop (Healthy)",
        "category": "growth",
        "loop_type":"truth_stability_loop",
        "description": (
            "Truth-facing activates reflective processing. "
            "Reflection produces emotional stability and clarity. "
            "Stability enables further truth-facing — a virtuous cycle."
        ),
        "chain": ["truth_facing", "reflection", "stability", "clarity"],
        "edges": [
            ("truth_facing", "LEADS_TO",   "reflection"),
            ("reflection",   "LEADS_TO",   "stability"),
            ("stability",    "LEADS_TO",   "clarity"),
            ("clarity",      "REINFORCES", "truth_facing"),
        ],
    },
    {
        "id":       "humility_learning_growth",
        "label":    "Humility → Learning → Resilience Loop (Healthy)",
        "category": "growth",
        "loop_type":"truth_stability_loop",
        "description": (
            "Humility opens learning pathways. "
            "Learning from adversity builds resilience. "
            "Resilience deepens humility over time."
        ),
        "chain": ["humility", "learning_openness", "resilience", "wisdom"],
        "edges": [
            ("humility",         "LEADS_TO",   "learning_openness"),
            ("learning_openness","LEADS_TO",   "resilience"),
            ("resilience",       "LEADS_TO",   "wisdom"),
            ("wisdom",           "REINFORCES", "humility"),
        ],
    },

    # ── Desire Loops ──────────────────────────────────────────
    {
        "id":       "desire_impulse_regret",
        "label":    "Desire → Impulse → Regret Loop",
        "category": "desire",
        "loop_type":"desire_impulse_loop",
        "description": (
            "Unexamined desire drives impulsive action. "
            "Regret following the action intensifies desire for relief, "
            "which re-activates the impulse cycle."
        ),
        "chain": ["desire", "impulsive_action", "regret", "relief_seeking"],
        "edges": [
            ("desire",          "CAUSES",     "impulsive_action"),
            ("impulsive_action","LEADS_TO",   "regret"),
            ("regret",          "LEADS_TO",   "relief_seeking"),
            ("relief_seeking",  "REINFORCES", "desire"),
        ],
    },
]
