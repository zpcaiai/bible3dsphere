"""
Formation Engine — Dimension Metadata Registry

Used by /v3/formation/dimensions API endpoint and the frontend
Formation Profile UI renderer.
"""

from typing import List, Dict, Any

DIMENSION_METADATA: List[Dict[str, Any]] = [
    {
        "key":         "humility",
        "label":       "Humility",
        "description": "Tendency toward truth-seeking vs self-protection",
        "direction":   "higher = more truth-seeking",
        "category":    "clarity",
        "reflective_question": (
            "What might be driving the need to protect your own perspective right now?"
        ),
    },
    {
        "key":         "fear_tendency",
        "label":       "Fear Tendency",
        "description": "Fear-driven response loop activity",
        "direction":   "higher = more active fear loop (signal, not judgment)",
        "category":    "loop",
        "reflective_question": (
            "What might you be trying to control that you actually can't — "
            "and what would it feel like to release it?"
        ),
    },
    {
        "key":         "pride_tendency",
        "label":       "Pride Tendency",
        "description": "Pride-driven comparison and self-protection loop",
        "direction":   "higher = more active pride loop (signal, not judgment)",
        "category":    "loop",
        "reflective_question": (
            "Where might the need to be right or seen as capable "
            "be creating distance from others?"
        ),
    },
    {
        "key":         "emotional_stability",
        "label":       "Emotional Stability",
        "description": "Regulated response vs reactive volatility tendency",
        "direction":   "higher = more regulated",
        "category":    "stability",
        "reflective_question": (
            "What patterns seem to trigger reactions before "
            "reflection has a chance to engage?"
        ),
    },
    {
        "key":         "truth_alignment",
        "label":       "Truth Alignment",
        "description": "Alignment with honest self-perception and principle",
        "direction":   "higher = more aligned",
        "category":    "clarity",
        "reflective_question": (
            "Where might there be a gap between what you believe "
            "and how you're actually responding?"
        ),
    },
    {
        "key":         "relational_health",
        "label":       "Relational Health",
        "description": "Other-oriented vs self-absorbed relational pattern",
        "direction":   "higher = more other-oriented",
        "category":    "relational",
        "reflective_question": (
            "Whose perspective or needs might you be finding it "
            "difficult to hold alongside your own?"
        ),
    },
    {
        "key":         "resilience",
        "label":       "Resilience",
        "description": "Recovery tendency after adversity vs avoidance",
        "direction":   "higher = more recovery-oriented",
        "category":    "stability",
        "reflective_question": (
            "What would recovery look like for you after a setback — "
            "not avoidance, but actual return?"
        ),
    },
    {
        "key":         "spiritual_clarity",
        "label":       "Spiritual Clarity",
        "description": "Clarity of inner values and reduction of dryness",
        "direction":   "higher = more clarity",
        "category":    "clarity",
        "reflective_question": (
            "What has been making it harder to access your "
            "own inner sense of clarity recently?"
        ),
    },
]

DOMINANT_LOOPS = [
    {
        "key":         "fear_control_loop",
        "label":       "Fear–Control Loop",
        "description": "fear → control → overwork → burnout → fear",
        "primary_dim": "fear_tendency",
    },
    {
        "key":         "shame_avoidance_loop",
        "label":       "Shame–Avoidance Loop",
        "description": "shame → avoidance → procrastination → anxiety",
        "primary_dim": "truth_alignment",
    },
    {
        "key":         "pride_comparison_loop",
        "label":       "Pride–Comparison Loop",
        "description": "pride → comparison → anxiety → instability",
        "primary_dim": "pride_tendency",
    },
    {
        "key":         "desire_impulse_loop",
        "label":       "Desire–Impulse Loop",
        "description": "desire → impulsive action → regret → desire",
        "primary_dim": "emotional_stability",
    },
    {
        "key":         "truth_stability_loop",
        "label":       "Truth–Stability Loop",
        "description": "truth-facing → reflection → stability (healthy)",
        "primary_dim": "truth_alignment",
    },
]
