#!/usr/bin/env python3
"""
SFDS Graph Layer — Neo4j structural reasoning module (V2).

Answers: WHY does this pattern keep happening?

Provides:
- Neo4j connection management
- 20+ seeded human formation loop patterns
- GraphService: query, write-back, cycle detection
- PatternMatcher: emotion/motive → pattern lookup
- Intervention extraction

Design constraints:
- Graph is a MIRROR, not a diagnosis.
- Pattern matches surface possibilities, not certainties.
- Output language preserves human autonomy and uncertainty.
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Optional neo4j driver import
# ──────────────────────────────────────────────────────────────────────────────
try:
    from neo4j import GraphDatabase, Driver, Session
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    Driver = Any
    Session = Any

# ──────────────────────────────────────────────────────────────────────────────
# Node / Edge label constants
# ──────────────────────────────────────────────────────────────────────────────

class NodeLabel:
    USER_STATE   = "UserStateNode"
    EMOTION      = "EmotionNode"
    MOTIVE       = "MotiveNode"
    BEHAVIOR     = "BehaviorNode"
    SPIRITUAL    = "SpiritualStateNode"
    OUTCOME      = "OutcomeNode"
    PRINCIPLE    = "PrincipleNode"


class EdgeType:
    CAUSES      = "CAUSES"        # EmotionNode → MotiveNode
    LEADS_TO    = "LEADS_TO"      # MotiveNode → BehaviorNode; BehaviorNode → OutcomeNode
    INFLUENCES  = "INFLUENCES"    # PrincipleNode → Motive / Behavior / Emotion
    REINFORCES  = "REINFORCES"    # OutcomeNode → MotiveNode (feedback loop reinforcement)
    BREAKS      = "BREAKS"        # PrincipleNode → loop edge (intervention target)
    REPEATS     = "REPEATS"       # BehaviorNode → BehaviorNode (historical cycle)
    HAS_STATE   = "HAS_STATE"     # UserStateNode → SpiritualStateNode


# ──────────────────────────────────────────────────────────────────────────────
# Data models
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class PatternNode:
    label: str
    node_id: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PatternEdge:
    from_id: str
    to_id: str
    edge_type: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CausalChain:
    """A sequence of nodes forming a causal path."""
    nodes: List[str]          # ordered list of node_ids / labels
    edge_types: List[str]     # edges between nodes
    cycle_detected: bool = False
    cycle_start: Optional[str] = None
    description: str = ""


@dataclass
class GraphInsight:
    """Output from structural graph analysis."""
    causal_chains: List[CausalChain]
    cycles: List[CausalChain]
    pattern_labels: List[str]           # e.g. ["fear→control→burnout"]
    intervention_points: List[Dict[str, str]]
    structural_summary: str
    raw_paths: List[List[Dict[str, Any]]] = field(default_factory=list)
    reflective_questions: List[str] = field(default_factory=list)


@dataclass
class PatternSubgraph:
    """
    Typed subgraph representation of one canonical human formation loop.

    Captures the full node-type-aware structure used by the v2.1 schema:
      EmotionNode → (CAUSES) → MotiveNode
      MotiveNode  → (LEADS_TO) → BehaviorNode
      BehaviorNode → (LEADS_TO) → OutcomeNode
      OutcomeNode  → (REINFORCES) → MotiveNode   [loop edge]
      PrincipleNode → (BREAKS) → [loop edge]     [intervention]
      PrincipleNode → (INFLUENCES) → MotiveNode  [formational influence]
    """
    pattern_id:    str
    label:         str
    category:      str

    # Typed nodes
    emotion_nodes:   List[str]   = field(default_factory=list)  # EmotionNode.name values
    motive_nodes:    List[str]   = field(default_factory=list)  # MotiveNode.type values
    behavior_nodes:  List[str]   = field(default_factory=list)  # BehaviorNode.type values
    outcome_nodes:   List[str]   = field(default_factory=list)  # OutcomeNode.type values
    principle_nodes: List[str]   = field(default_factory=list)  # PrincipleNode.principle_id values

    # Typed edges
    causes_edges:     List[Tuple[str, str]] = field(default_factory=list)  # (emotion, motive)
    leads_to_edges:   List[Tuple[str, str]] = field(default_factory=list)  # (motive/behavior, behavior/outcome)
    reinforces_edges: List[Tuple[str, str]] = field(default_factory=list)  # (outcome, motive) — loop
    breaks_edges:     List[Tuple[str, str]] = field(default_factory=list)  # (principle, loop_target)
    influences_edges: List[Tuple[str, str]] = field(default_factory=list)  # (principle, node)

    # Intervention info
    intervention_node: str = ""
    intervention_principle: str = ""
    reflective_question: str = ""
    scripture: str = ""


# ──────────────────────────────────────────────────────────────────────────────
# 22 Seeded Human Formation Loop Patterns
#
# Each pattern is:
#   id         — machine key
#   chain      — ordered causal nodes (emotion/motive/behavior/outcome)
#   label      — human-readable chain (shown in UI)
#   category   — cluster: fear / pride / shame / desire / relational / growth
#   intervention — the highest-leverage break point
#   reflective_question — open question for the user (NOT directive)
#   scripture   — optional supporting reference
# ──────────────────────────────────────────────────────────────────────────────

KNOWN_PATTERNS: List[Dict[str, Any]] = [
    # ── FEAR CLUSTER ────────────────────────────────────────────────────────
    {
        "id": "fear_control_burnout",
        "category": "fear",
        "chain": ["fear", "control_impulse", "overwork", "burnout", "spiritual_dryness"],
        "label": "fear → control → overwork → burnout → spiritual dryness",
        "intervention": {
            "node": "control_impulse",
            "suggestion": "Notice the impulse to control outcomes before it becomes action. What would it feel like to release this?",
            "scripture": "Matthew 6:25-27",
        },
        "reflective_question": "What are you most afraid will happen if you stop trying to control this?",
    },
    {
        "id": "fear_avoidance_stagnation",
        "category": "fear",
        "chain": ["fear", "avoidance", "stagnation", "regret", "deeper_fear"],
        "label": "fear → avoidance → stagnation → regret → deeper fear (loop)",
        "intervention": {
            "node": "avoidance",
            "suggestion": "Avoidance often amplifies fear over time. What is the smallest possible step toward the feared thing?",
            "scripture": "2 Timothy 1:7",
        },
        "reflective_question": "What would you do in this situation if fear were not a factor?",
    },
    {
        "id": "fear_people_pleasing_resentment",
        "category": "fear",
        "chain": ["fear_of_rejection", "people_pleasing", "self_suppression", "resentment", "isolation"],
        "label": "fear of rejection → people-pleasing → self-suppression → resentment → isolation",
        "intervention": {
            "node": "people_pleasing",
            "suggestion": "Each small 'yes' when you mean 'no' erodes integrity over time. What boundary is asking to be named?",
            "scripture": "Galatians 1:10",
        },
        "reflective_question": "Whose approval are you most trying to secure, and why does it feel so necessary?",
    },
    {
        "id": "fear_urgency_poor_decision",
        "category": "fear",
        "chain": ["fear", "urgency_feeling", "rushed_decision", "poor_outcome", "anxiety_spike"],
        "label": "fear → urgency → rushed decision → poor outcome → anxiety",
        "intervention": {
            "node": "urgency_feeling",
            "suggestion": "The urgency may be a feeling, not a fact. Is this decision actually time-critical, or does it feel that way?",
            "scripture": "Isaiah 28:16",
        },
        "reflective_question": "What would happen if you waited 48 hours before deciding?",
    },

    # ── PRIDE CLUSTER ────────────────────────────────────────────────────────
    {
        "id": "pride_comparison_anxiety",
        "category": "pride",
        "chain": ["pride", "comparison", "anxiety", "performance_addiction", "emptiness"],
        "label": "pride → comparison → anxiety → performance addiction → emptiness",
        "intervention": {
            "node": "comparison",
            "suggestion": "Comparison measures the wrong thing. What matters to you when no one is watching?",
            "scripture": "Galatians 6:4",
        },
        "reflective_question": "If no one ever knew the outcome of this decision, would you still make the same choice?",
    },
    {
        "id": "pride_self_sufficiency_isolation",
        "category": "pride",
        "chain": ["pride", "self_sufficiency", "refusing_help", "isolation", "crisis"],
        "label": "pride → self-sufficiency → refusing help → isolation → crisis",
        "intervention": {
            "node": "self_sufficiency",
            "suggestion": "Asking for help is not weakness — it is wisdom. Who could you bring into this decision?",
            "scripture": "Proverbs 11:2",
        },
        "reflective_question": "What would it cost you to admit you need support here?",
    },
    {
        "id": "pride_defensiveness_conflict",
        "category": "pride",
        "chain": ["pride", "defensiveness", "escalating_conflict", "broken_relationship", "loneliness"],
        "label": "pride → defensiveness → conflict escalation → broken relationship → loneliness",
        "intervention": {
            "node": "defensiveness",
            "suggestion": "Defensiveness often signals a wound beneath the surface. What is being threatened here — truth, or image?",
            "scripture": "Proverbs 13:10",
        },
        "reflective_question": "What truth about this situation are you most resistant to hearing?",
    },
    {
        "id": "ambition_shortcuts_integrity_loss",
        "category": "pride",
        "chain": ["ambition", "impatience", "shortcuts", "integrity_erosion", "shame"],
        "label": "ambition → impatience → shortcuts → integrity erosion → shame",
        "intervention": {
            "node": "impatience",
            "suggestion": "Fast growth built on compromise creates fragile foundations. What speed is sustainable here?",
            "scripture": "Proverbs 21:5",
        },
        "reflective_question": "Are you in a hurry because of calling, or because of comparison with others?",
    },

    # ── SHAME CLUSTER ────────────────────────────────────────────────────────
    {
        "id": "shame_avoidance_procrastination",
        "category": "shame",
        "chain": ["shame", "avoidance", "procrastination", "accumulating_pressure", "anxiety_loop"],
        "label": "shame → avoidance → procrastination → accumulating pressure → anxiety loop",
        "intervention": {
            "node": "avoidance",
            "suggestion": "The avoided thing grows in the dark. What is the one thing you keep not doing?",
            "scripture": "1 John 1:9",
        },
        "reflective_question": "What are you avoiding, and what do you believe it says about you?",
    },
    {
        "id": "shame_self_punishment_paralysis",
        "category": "shame",
        "chain": ["shame", "self_condemnation", "worthlessness", "paralysis", "missed_calling"],
        "label": "shame → self-condemnation → worthlessness → paralysis → missed calling",
        "intervention": {
            "node": "self_condemnation",
            "suggestion": "Guilt points to an action; shame attacks the person. Which is operating here?",
            "scripture": "Romans 8:1",
        },
        "reflective_question": "How would you speak to a close friend who made the same mistake you are condemning yourself for?",
    },
    {
        "id": "shame_overcompensation_exhaustion",
        "category": "shame",
        "chain": ["shame", "overcompensation", "hyperactivity", "exhaustion", "shame_spike"],
        "label": "shame → overcompensation → hyperactivity → exhaustion → shame spike (loop)",
        "intervention": {
            "node": "overcompensation",
            "suggestion": "Doing more to feel worthy is unsustainable. Worth does not come from output.",
            "scripture": "Ephesians 2:8-9",
        },
        "reflective_question": "If you were already fully accepted, what would you stop doing?",
    },

    # ── DESIRE / ATTACHMENT CLUSTER ──────────────────────────────────────────
    {
        "id": "loneliness_attachment_impulse",
        "category": "desire",
        "chain": ["loneliness", "attachment_seeking", "impulsive_bonding", "regret", "deeper_loneliness"],
        "label": "loneliness → attachment seeking → impulsive bonding → regret → deeper loneliness",
        "intervention": {
            "node": "attachment_seeking",
            "suggestion": "Loneliness is real and valid. The question is whether this action addresses the root or numbs it temporarily.",
            "scripture": "Psalm 62:1",
        },
        "reflective_question": "What deeper need is this decision attempting to meet?",
    },
    {
        "id": "desire_gratification_debt",
        "category": "desire",
        "chain": ["desire", "immediate_gratification", "overpromising", "debt_of_consequence", "regret"],
        "label": "desire → immediate gratification → overpromising → consequence debt → regret",
        "intervention": {
            "node": "immediate_gratification",
            "suggestion": "Short-term relief often defers long-term cost. What does the 2-year version of this decision look like?",
            "scripture": "Hebrews 11:25",
        },
        "reflective_question": "What are you willing to give up for what you want right now?",
    },
    {
        "id": "escapism_numbing_drift",
        "category": "desire",
        "chain": ["pain", "escapism", "numbing_behavior", "spiritual_drift", "emptiness"],
        "label": "pain → escapism → numbing → spiritual drift → emptiness",
        "intervention": {
            "node": "numbing_behavior",
            "suggestion": "Numbing delays the pain but also delays healing. What is the pain that needs to be heard?",
            "scripture": "Psalm 34:18",
        },
        "reflective_question": "What are you trying not to feel, and what would happen if you sat with it?",
    },

    # ── RELATIONAL CLUSTER ───────────────────────────────────────────────────
    {
        "id": "unforgiveness_bitterness_isolation",
        "category": "relational",
        "chain": ["hurt", "unforgiveness", "bitterness", "relational_withdrawal", "spiritual_hardening"],
        "label": "hurt → unforgiveness → bitterness → withdrawal → spiritual hardening",
        "intervention": {
            "node": "unforgiveness",
            "suggestion": "Forgiveness is not excusing the harm — it is releasing the right to be controlled by it.",
            "scripture": "Matthew 18:21-22",
        },
        "reflective_question": "Who or what are you holding onto that is costing you peace?",
    },
    {
        "id": "codependency_enabling_resentment",
        "category": "relational",
        "chain": ["fear_of_abandonment", "codependency", "enabling", "resentment", "relational_collapse"],
        "label": "fear of abandonment → codependency → enabling → resentment → relational collapse",
        "intervention": {
            "node": "codependency",
            "suggestion": "True love includes appropriate boundaries. Whose responsibility are you carrying that is not yours?",
            "scripture": "Galatians 6:2-5",
        },
        "reflective_question": "Where in this relationship are you doing something out of fear rather than genuine care?",
    },
    {
        "id": "comparison_envy_sabotage",
        "category": "relational",
        "chain": ["comparison", "envy", "passive_aggression", "relationship_damage", "guilt"],
        "label": "comparison → envy → passive aggression → relationship damage → guilt",
        "intervention": {
            "node": "envy",
            "suggestion": "Envy signals an unmet desire — it can be information rather than an enemy.",
            "scripture": "James 3:14-16",
        },
        "reflective_question": "What do you see in others that you wish were true of yourself?",
    },

    # ── SPIRITUAL FORMATION CLUSTER ──────────────────────────────────────────
    {
        "id": "spiritual_dryness_duty_exhaustion",
        "category": "spiritual",
        "chain": ["spiritual_dryness", "duty_driven_service", "joyless_obedience", "exhaustion", "deeper_dryness"],
        "label": "spiritual dryness → duty-driven service → joyless obedience → exhaustion → deeper dryness",
        "intervention": {
            "node": "duty_driven_service",
            "suggestion": "Serving from depletion is not sustainable. Rest is not escape — it is formation.",
            "scripture": "Mark 6:31",
        },
        "reflective_question": "Are you serving because you want to, or because you feel you must?",
    },
    {
        "id": "calling_fear_inaction",
        "category": "spiritual",
        "chain": ["sense_of_calling", "fear_of_inadequacy", "delay", "missed_seasons", "deeper_regret"],
        "label": "sense of calling → fear of inadequacy → delay → missed seasons → regret",
        "intervention": {
            "node": "fear_of_inadequacy",
            "suggestion": "Inadequacy is a feature of calling, not a disqualifier. Who in Scripture was adequate for their calling before they said yes?",
            "scripture": "Exodus 4:10-12",
        },
        "reflective_question": "What would you attempt if you trusted that your inadequacy was not the final word?",
    },
    {
        "id": "truth_humility_peace",
        "category": "growth",
        "chain": ["truth_exposure", "humility", "peace", "clarity", "fruit"],
        "label": "truth exposure → humility → peace → clarity → fruit",
        "intervention": {
            "node": "truth_exposure",
            "suggestion": "Lean into the uncomfortable truth. Humility is not self-deprecation — it is accuracy about reality.",
            "scripture": "John 8:32",
        },
        "reflective_question": "What truth about this situation have you been reluctant to fully face?",
    },
    {
        "id": "suffering_patience_character",
        "category": "growth",
        "chain": ["suffering", "endurance", "character_formation", "hope", "stability"],
        "label": "suffering → endurance → character formation → hope → stability",
        "intervention": {
            "node": "endurance",
            "suggestion": "Suffering resisted with faith produces formation. What is this season forming in you?",
            "scripture": "Romans 5:3-5",
        },
        "reflective_question": "What is this difficulty trying to form in you that ease could not?",
    },
    {
        "id": "gratitude_peace_generosity",
        "category": "growth",
        "chain": ["gratitude", "contentment", "peace", "generosity", "flourishing"],
        "label": "gratitude → contentment → peace → generosity → flourishing",
        "intervention": {
            "node": "gratitude",
            "suggestion": "Gratitude is a discipline, not just a feeling. What is true and good right now that you have not named?",
            "scripture": "Philippians 4:6-7",
        },
        "reflective_question": "What would shift if you began from a posture of thankfulness rather than lack?",
    },
]

# ──────────────────────────────────────────────────────────────────────────────
# Lookup maps: emotion/motive → relevant pattern IDs
# ──────────────────────────────────────────────────────────────────────────────

MOTIVE_PATTERN_MAP: Dict[str, List[str]] = {
    "fear":    ["fear_control_burnout", "fear_avoidance_stagnation", "fear_people_pleasing_resentment", "fear_urgency_poor_decision"],
    "pride":   ["pride_comparison_anxiety", "pride_self_sufficiency_isolation", "pride_defensiveness_conflict", "ambition_shortcuts_integrity_loss"],
    "shame":   ["shame_avoidance_procrastination", "shame_self_punishment_paralysis", "shame_overcompensation_exhaustion"],
    "desire":  ["loneliness_attachment_impulse", "desire_gratification_debt", "escapism_numbing_drift"],
    "duty":    ["spiritual_dryness_duty_exhaustion"],
    "ambition":["ambition_shortcuts_integrity_loss", "pride_comparison_anxiety"],
    "love":    ["truth_humility_peace", "gratitude_peace_generosity"],
}

EMOTION_PATTERN_MAP: Dict[str, List[str]] = {
    "fear":       ["fear_control_burnout", "fear_avoidance_stagnation", "fear_urgency_poor_decision"],
    "anxiety":    ["fear_control_burnout", "pride_comparison_anxiety", "shame_avoidance_procrastination"],
    "shame":      ["shame_avoidance_procrastination", "shame_self_punishment_paralysis", "shame_overcompensation_exhaustion"],
    "loneliness": ["loneliness_attachment_impulse", "fear_people_pleasing_resentment"],
    "pride":      ["pride_comparison_anxiety", "pride_defensiveness_conflict"],
    "anger":      ["pride_defensiveness_conflict", "unforgiveness_bitterness_isolation"],
    "hurt":       ["unforgiveness_bitterness_isolation", "shame_self_punishment_paralysis"],
    "sadness":    ["escapism_numbing_drift", "spiritual_dryness_duty_exhaustion"],
    "confusion":  ["fear_urgency_poor_decision", "calling_fear_inaction"],
    "desire":     ["desire_gratification_debt", "loneliness_attachment_impulse"],
    "guilt":      ["shame_avoidance_procrastination", "shame_self_punishment_paralysis"],
    "doubt":      ["calling_fear_inaction", "fear_avoidance_stagnation"],
    "peace":      ["truth_humility_peace", "gratitude_peace_generosity"],
    "joy":        ["gratitude_peace_generosity", "suffering_patience_character"],
    "hope":       ["suffering_patience_character", "truth_humility_peace"],
}

# ──────────────────────────────────────────────────────────────────────────────
# PATTERN_SUBGRAPHS — 6 Canonical Human Formation Loop Subgraphs (v2.1)
#
# These are the typed, edge-correct subgraphs for Neo4j persistence.
# Each uses the strict node labels:
#   EmotionNode, MotiveNode, BehaviorNode, OutcomeNode, PrincipleNode
# And the 5 edge types:
#   CAUSES, LEADS_TO, REINFORCES, BREAKS, INFLUENCES
#
# These ARE NOT a replacement for KNOWN_PATTERNS (which drives the rule engine).
# They ARE the graph representation for Neo4j persistence and query.
# ──────────────────────────────────────────────────────────────────────────────

PATTERN_SUBGRAPHS: List[PatternSubgraph] = [

    # ── Pattern 1: FEAR → CONTROL → BURNOUT LOOP ─────────────────────────────
    PatternSubgraph(
        pattern_id  = "fear_control_burnout",
        label       = "fear → control → burnout loop",
        category    = "fear",
        emotion_nodes   = ["anxiety"],
        motive_nodes    = ["fear_driven_control"],
        behavior_nodes  = ["overworking", "micromanaging", "overplanning"],
        outcome_nodes   = ["burnout", "exhaustion"],
        principle_nodes = ["rest_before_decision", "trust_over_control", "surrender_uncertainty"],
        # Causal edges
        causes_edges    = [("anxiety", "fear_driven_control")],
        leads_to_edges  = [
            ("fear_driven_control", "overworking"),
            ("fear_driven_control", "micromanaging"),
            ("overworking",         "burnout"),
            ("burnout",             "exhaustion"),
        ],
        # Loop: exhaustion reinforces the fear-control motive
        reinforces_edges = [("exhaustion", "fear_driven_control")],
        # Principle breaks the overworking → burnout edge
        breaks_edges     = [
            ("rest_before_decision",   "overworking"),
            ("trust_over_control",     "micromanaging"),
        ],
        influences_edges = [("surrender_uncertainty", "fear_driven_control")],
        intervention_node      = "overworking",
        intervention_principle = "rest_before_decision",
        reflective_question    = "What are you most afraid will happen if you stop trying to control this?",
        scripture              = "Matthew 6:25-27",
    ),

    # ── Pattern 2: PRIDE → COMPARISON → ANXIETY LOOP ─────────────────────────
    PatternSubgraph(
        pattern_id  = "pride_comparison_anxiety",
        label       = "pride → comparison → anxiety loop",
        category    = "pride",
        emotion_nodes   = ["insecurity"],
        motive_nodes    = ["pride_driven_self_evaluation"],
        behavior_nodes  = ["comparison_seeking", "performance_chasing"],
        outcome_nodes   = ["anxiety_spike", "shame"],
        principle_nodes = ["identity_not_in_performance", "humility_restores_clarity"],
        causes_edges    = [("insecurity", "pride_driven_self_evaluation")],
        leads_to_edges  = [
            ("pride_driven_self_evaluation", "comparison_seeking"),
            ("pride_driven_self_evaluation", "performance_chasing"),
            ("comparison_seeking",           "anxiety_spike"),
            ("performance_chasing",          "anxiety_spike"),
            ("anxiety_spike",                "shame"),
        ],
        reinforces_edges = [("shame", "pride_driven_self_evaluation")],
        breaks_edges     = [
            ("identity_not_in_performance", "comparison_seeking"),
            ("identity_not_in_performance", "performance_chasing"),
        ],
        influences_edges = [("humility_restores_clarity", "pride_driven_self_evaluation")],
        intervention_node      = "comparison_seeking",
        intervention_principle = "identity_not_in_performance",
        reflective_question    = "If no one ever knew the outcome of this decision, would you still make the same choice?",
        scripture              = "Galatians 6:4",
    ),

    # ── Pattern 3: SHAME → AVOIDANCE → DELAY LOOP ────────────────────────────
    PatternSubgraph(
        pattern_id  = "shame_avoidance_procrastination",
        label       = "shame → avoidance → delay loop",
        category    = "shame",
        emotion_nodes   = ["shame"],
        motive_nodes    = ["avoidance_driven"],
        behavior_nodes  = ["procrastination", "withdrawal"],
        outcome_nodes   = ["accumulated_pressure", "anxiety_spike"],
        principle_nodes = ["truth_brings_freedom", "small_obedience_breaks_shame"],
        causes_edges    = [("shame", "avoidance_driven")],
        leads_to_edges  = [
            ("avoidance_driven",    "procrastination"),
            ("avoidance_driven",    "withdrawal"),
            ("procrastination",     "accumulated_pressure"),
            ("accumulated_pressure","anxiety_spike"),
        ],
        reinforces_edges = [("anxiety_spike", "avoidance_driven")],
        breaks_edges     = [
            ("truth_brings_freedom",          "procrastination"),
            ("small_obedience_breaks_shame",  "withdrawal"),
        ],
        influences_edges = [("truth_brings_freedom", "avoidance_driven")],
        intervention_node      = "procrastination",
        intervention_principle = "truth_brings_freedom",
        reflective_question    = "What are you avoiding, and what do you believe it says about you?",
        scripture              = "1 John 1:9",
    ),

    # ── Pattern 4: LONELINESS → ATTACHMENT → IMPULSIVE DECISION LOOP ─────────
    PatternSubgraph(
        pattern_id  = "loneliness_attachment_impulse",
        label       = "loneliness → attachment → impulsive decision loop",
        category    = "desire",
        emotion_nodes   = ["loneliness"],
        motive_nodes    = ["emotional_dependency"],
        behavior_nodes  = ["impulsive_bonding"],
        outcome_nodes   = ["regret", "relational_instability"],
        principle_nodes = ["identity_stability_first", "avoid_void_decisions"],
        causes_edges    = [("loneliness", "emotional_dependency")],
        leads_to_edges  = [
            ("emotional_dependency", "impulsive_bonding"),
            ("impulsive_bonding",    "regret"),
            ("regret",               "relational_instability"),
        ],
        reinforces_edges = [("relational_instability", "emotional_dependency")],
        breaks_edges     = [("identity_stability_first", "impulsive_bonding")],
        influences_edges = [("avoid_void_decisions", "emotional_dependency")],
        intervention_node      = "impulsive_bonding",
        intervention_principle = "identity_stability_first",
        reflective_question    = "What deeper need is this decision attempting to meet?",
        scripture              = "Psalm 62:1",
    ),

    # ── Pattern 5: SUCCESS → PRIDE INFLATION → COLLAPSE ─────────────────────
    PatternSubgraph(
        pattern_id  = "pride_inflation_collapse",
        label       = "success → pride inflation → overconfidence → correction → shame collapse",
        category    = "pride",
        emotion_nodes   = ["high_confidence"],
        motive_nodes    = ["pride_amplification"],
        behavior_nodes  = ["overconfident_decisions"],
        outcome_nodes   = ["failure_event", "shame_collapse"],
        principle_nodes = ["humility_in_success", "identity_stability"],
        causes_edges    = [("high_confidence", "pride_amplification")],
        leads_to_edges  = [
            ("pride_amplification",     "overconfident_decisions"),
            ("overconfident_decisions", "failure_event"),
            ("failure_event",           "shame_collapse"),
        ],
        reinforces_edges = [("shame_collapse", "pride_amplification")],
        breaks_edges     = [("humility_in_success", "overconfident_decisions")],
        influences_edges = [("identity_stability", "pride_amplification")],
        intervention_node      = "overconfident_decisions",
        intervention_principle = "humility_in_success",
        reflective_question    = "Are you making this decision from a place of genuine clarity, or from elevated confidence after a win?",
        scripture              = "Proverbs 16:18",
    ),

    # ── Pattern 6: SPIRITUAL DRYNESS → COMPENSATION → OVERACTIVITY LOOP ──────
    PatternSubgraph(
        pattern_id  = "spiritual_dryness_compensation",
        label       = "spiritual dryness → compensation → overactivity → deeper dryness loop",
        category    = "spiritual",
        emotion_nodes   = ["emptiness"],
        motive_nodes    = ["compensation_behavior"],
        behavior_nodes  = ["overactivity", "over_spiritual_performance"],
        outcome_nodes   = ["exhaustion", "deeper_dryness"],
        principle_nodes = ["rest_in_being", "presence_over_performance"],
        causes_edges    = [("emptiness", "compensation_behavior")],
        leads_to_edges  = [
            ("compensation_behavior",       "overactivity"),
            ("compensation_behavior",       "over_spiritual_performance"),
            ("overactivity",                "exhaustion"),
            ("over_spiritual_performance",  "exhaustion"),
            ("exhaustion",                  "deeper_dryness"),
        ],
        reinforces_edges = [("deeper_dryness", "compensation_behavior")],
        breaks_edges     = [
            ("rest_in_being",          "overactivity"),
            ("presence_over_performance", "over_spiritual_performance"),
        ],
        influences_edges = [("rest_in_being", "compensation_behavior")],
        intervention_node      = "overactivity",
        intervention_principle = "rest_in_being",
        reflective_question    = "Are you serving because you want to, or because you feel you must?",
        scripture              = "Mark 6:31",
    ),
]


def format_subgraph_for_api(sg: PatternSubgraph) -> Dict[str, Any]:
    """
    Serialize a PatternSubgraph for API / frontend consumption.
    Returns a node-link format readable by graph visualisation libraries.
    """
    nodes = []
    for e in sg.emotion_nodes:
        nodes.append({"id": e, "label": NodeLabel.EMOTION, "type": e})
    for m in sg.motive_nodes:
        nodes.append({"id": m, "label": NodeLabel.MOTIVE, "type": m})
    for b in sg.behavior_nodes:
        nodes.append({"id": b, "label": NodeLabel.BEHAVIOR, "type": b})
    for o in sg.outcome_nodes:
        nodes.append({"id": o, "label": NodeLabel.OUTCOME, "type": o})
    for p in sg.principle_nodes:
        nodes.append({"id": p, "label": NodeLabel.PRINCIPLE, "type": p})

    edges = []
    for (s, t) in sg.causes_edges:
        edges.append({"from": s, "to": t, "type": EdgeType.CAUSES})
    for (s, t) in sg.leads_to_edges:
        edges.append({"from": s, "to": t, "type": EdgeType.LEADS_TO})
    for (s, t) in sg.reinforces_edges:
        edges.append({"from": s, "to": t, "type": EdgeType.REINFORCES, "loop": True})
    for (s, t) in sg.breaks_edges:
        edges.append({"from": s, "to": t, "type": EdgeType.BREAKS})
    for (s, t) in sg.influences_edges:
        edges.append({"from": s, "to": t, "type": EdgeType.INFLUENCES})

    return {
        "pattern_id":            sg.pattern_id,
        "label":                 sg.label,
        "category":              sg.category,
        "nodes":                 nodes,
        "edges":                 edges,
        "intervention_node":     sg.intervention_node,
        "intervention_principle":sg.intervention_principle,
        "reflective_question":   sg.reflective_question,
        "scripture":             sg.scripture,
    }


CATEGORY_PATTERN_MAP: Dict[str, List[str]] = {
    "career":       ["fear_control_burnout", "ambition_shortcuts_integrity_loss", "calling_fear_inaction", "pride_comparison_anxiety"],
    "relationship": ["unforgiveness_bitterness_isolation", "codependency_enabling_resentment", "fear_people_pleasing_resentment", "loneliness_attachment_impulse"],
    "temptation":   ["desire_gratification_debt", "escapism_numbing_drift", "shame_avoidance_procrastination"],
    "calling":      ["calling_fear_inaction", "fear_avoidance_stagnation", "spiritual_dryness_duty_exhaustion"],
    "financial":    ["desire_gratification_debt", "fear_control_burnout", "ambition_shortcuts_integrity_loss"],
    "health":       ["escapism_numbing_drift", "shame_self_punishment_paralysis", "fear_control_burnout"],
    "ministry":     ["spiritual_dryness_duty_exhaustion", "pride_self_sufficiency_isolation", "shame_overcompensation_exhaustion"],
}


# ──────────────────────────────────────────────────────────────────────────────
# Neo4j connection manager
# ──────────────────────────────────────────────────────────────────────────────

class Neo4jConnection:
    """Thread-safe Neo4j driver wrapper."""

    def __init__(self):
        self._driver: Optional[Driver] = None
        self._uri     = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
        self._user    = os.getenv("NEO4J_USER",     "neo4j")
        self._password = os.getenv("NEO4J_PASSWORD", "")

    def connect(self) -> bool:
        if not NEO4J_AVAILABLE:
            logger.warning("[graph] neo4j driver not installed — graph persistence disabled.")
            return False
        if not self._password:
            logger.warning("[graph] NEO4J_PASSWORD not set — graph persistence disabled.")
            return False
        try:
            self._driver = GraphDatabase.driver(self._uri, auth=(self._user, self._password))
            self._driver.verify_connectivity()
            logger.info("[graph] Neo4j connected: %s", self._uri)
            return True
        except Exception as exc:
            logger.warning("[graph] Neo4j connection failed: %s", exc)
            self._driver = None
            return False

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None

    @property
    def is_connected(self) -> bool:
        return self._driver is not None

    def run(self, cypher: str, **params) -> List[Dict[str, Any]]:
        if not self._driver:
            return []
        with self._driver.session() as session:
            result = session.run(cypher, **params)
            return [dict(record) for record in result]

    def ensure_constraints(self):
        """Idempotent schema constraints (v2.1 — all 6 node types)."""
        if not self._driver:
            return
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:EmotionNode)       REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:MotiveNode)        REQUIRE n.type IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:BehaviorNode)      REQUIRE n.type IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:OutcomeNode)       REQUIRE n.type IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:SpiritualStateNode) REQUIRE n.type IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:PrincipleNode)     REQUIRE n.principle_id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:UserStateNode)     REQUIRE n.user_id IS UNIQUE",
        ]
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (n:EmotionNode)   ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:BehaviorNode)  ON (n.type)",
            "CREATE INDEX IF NOT EXISTS FOR (n:OutcomeNode)   ON (n.type)",
            "CREATE INDEX IF NOT EXISTS FOR (n:UserStateNode) ON (n.user_id)",
        ]
        with self._driver.session() as session:
            for stmt in constraints + indexes:
                try:
                    session.run(stmt)
                except Exception as exc:
                    logger.debug("[graph] schema stmt: %s — %s", stmt[:60], exc)

    def seed_known_patterns(self):
        """
        Persist the canonical human formation loop patterns into Neo4j as
        fully-typed subgraphs using the v2.1 strict schema.

        Node types used:
          EmotionNode  — emotional state (name property)
          MotiveNode   — inner driver    (type property)
          BehaviorNode — observable act  (type property)
          OutcomeNode  — consequence     (type property)
          PrincipleNode— spiritual truth (principle_id, text properties)

        Edge types used:
          CAUSES      EmotionNode → MotiveNode
          LEADS_TO    MotiveNode  → BehaviorNode; BehaviorNode → OutcomeNode
          REINFORCES  OutcomeNode → MotiveNode  (loop feedback)
          BREAKS      PrincipleNode → BehaviorNode (intervention target)
          INFLUENCES  PrincipleNode → MotiveNode
        """
        if not self._driver:
            return
        with self._driver.session() as session:
            for sg in PATTERN_SUBGRAPHS:
                pid = sg.pattern_id

                # 1. Seed emotion nodes
                for e in sg.emotion_nodes:
                    session.run(
                        "MERGE (n:EmotionNode {name: $name}) SET n.pattern_id = $pid",
                        name=e, pid=pid,
                    )

                # 2. Seed motive nodes
                for m in sg.motive_nodes:
                    session.run(
                        "MERGE (n:MotiveNode {type: $t}) SET n.pattern_id = $pid",
                        t=m, pid=pid,
                    )

                # 3. Seed behavior nodes
                for b in sg.behavior_nodes:
                    session.run(
                        "MERGE (n:BehaviorNode {type: $t}) SET n.pattern_id = $pid",
                        t=b, pid=pid,
                    )

                # 4. Seed outcome nodes
                for o in sg.outcome_nodes:
                    session.run(
                        "MERGE (n:OutcomeNode {type: $t}) SET n.pattern_id = $pid",
                        t=o, pid=pid,
                    )

                # 5. Seed principle nodes
                for p in sg.principle_nodes:
                    session.run(
                        "MERGE (n:PrincipleNode {principle_id: $pid_val}) "
                        "SET n.text = $pid_val, n.pattern_id = $pid",
                        pid_val=p, pid=pid,
                    )

                # 6. CAUSES edges: EmotionNode → MotiveNode
                for (e, m) in sg.causes_edges:
                    session.run(
                        "MATCH (a:EmotionNode {name: $e}), (b:MotiveNode {type: $m}) "
                        "MERGE (a)-[:CAUSES {pattern_id: $pid}]->(b)",
                        e=e, m=m, pid=pid,
                    )

                # 7. LEADS_TO edges (motive→behavior, behavior→outcome)
                for (src, dst) in sg.leads_to_edges:
                    session.run(
                        """
                        MATCH (a {type: $src}), (b {type: $dst})
                        MERGE (a)-[:LEADS_TO {pattern_id: $pid}]->(b)
                        """,
                        src=src, dst=dst, pid=pid,
                    )

                # 8. REINFORCES edges: OutcomeNode → MotiveNode (loop)
                for (o, m) in sg.reinforces_edges:
                    session.run(
                        "MATCH (a:OutcomeNode {type: $o}), (b:MotiveNode {type: $m}) "
                        "MERGE (a)-[:REINFORCES {pattern_id: $pid}]->(b)",
                        o=o, m=m, pid=pid,
                    )

                # 9. BREAKS edges: PrincipleNode → BehaviorNode (intervention)
                for (p, b) in sg.breaks_edges:
                    session.run(
                        "MATCH (pr:PrincipleNode {principle_id: $p}), (bh:BehaviorNode {type: $b}) "
                        "MERGE (pr)-[:BREAKS {pattern_id: $pid}]->(bh)",
                        p=p, b=b, pid=pid,
                    )

                # 10. INFLUENCES edges: PrincipleNode → MotiveNode
                for (p, m) in sg.influences_edges:
                    session.run(
                        "MATCH (pr:PrincipleNode {principle_id: $p}), (mo:MotiveNode {type: $m}) "
                        "MERGE (pr)-[:INFLUENCES {pattern_id: $pid}]->(mo)",
                        p=p, m=m, pid=pid,
                    )

                logger.debug("[graph] seeded pattern subgraph: %s", pid)


# Singleton
_neo4j = Neo4jConnection()


def get_neo4j() -> Neo4jConnection:
    return _neo4j


# ──────────────────────────────────────────────────────────────────────────────
# Graph Service — structural reasoning + write-back
# ──────────────────────────────────────────────────────────────────────────────

class GraphService:
    """
    V2 Graph Service — structural pattern reasoning + Neo4j write-back.

    Pipeline role: WHY does this pattern keep appearing?

    Works in two modes:
    - Live mode: queries Neo4j for user-specific historical paths.
    - Offline mode: static rule-based pattern matching (no Neo4j required).

    Design principle: output is always framed as *possibility*, never *verdict*.
    The system is a mirror, not a judge.
    """

    def __init__(self, neo4j: Optional[Neo4jConnection] = None):
        self.neo4j = neo4j or _neo4j

    # ── Pipeline entry point ──────────────────────────────────────────────────

    def analyze(
        self,
        user_id: str,
        dominant_motive: str,
        emotions: List[Dict[str, Any]],
        decision_category: str,
        past_behavior_types: Optional[List[str]] = None,
    ) -> GraphInsight:
        """
        Main entry point.  Returns a GraphInsight regardless of Neo4j availability.

        Args:
            user_id:              UUID string — used for live Neo4j lookups.
            dominant_motive:      Highest-scoring motive (fear/pride/shame/desire/duty/love).
            emotions:             List of {type, intensity} dicts from current snapshot.
            decision_category:    career/relationship/temptation/calling/financial/health/ministry.
            past_behavior_types:  Optional list of behaviour strings from user history.
        """
        matched = self._match_patterns(dominant_motive, emotions, decision_category)
        chains, cycles = self._build_chains(matched, past_behavior_types or [])
        interventions = self._extract_interventions(matched)
        questions = self._extract_questions(matched)
        pattern_labels = [p["label"] for p in matched]
        summary = self._build_summary(chains, cycles, interventions)

        raw_paths: List[List[Dict[str, Any]]] = []
        repeat_behaviors: List[Dict[str, Any]] = []
        if self.neo4j.is_connected:
            raw_paths = self._query_user_paths(user_id)
            repeat_behaviors = self._query_repeat_behaviors(user_id)

        # Enrich insight with repeat behavior data from live graph
        if repeat_behaviors:
            for rb in repeat_behaviors[:3]:
                btype = rb.get("behavior", "")
                freq = rb.get("freq", 0)
                if freq >= 3:
                    summary += (
                        f"\n\nLive graph data: the behavior '{btype}' has appeared "
                        f"{freq} times in recent history — this may indicate a repeating loop."
                    )

        return GraphInsight(
            causal_chains=chains,
            cycles=cycles,
            pattern_labels=pattern_labels,
            intervention_points=interventions,
            structural_summary=summary,
            raw_paths=raw_paths,
            reflective_questions=questions,
        )

    # ── Write-back (called after decision is submitted) ───────────────────────

    def write_back(
        self,
        user_id: str,
        decision_id: str,
        dominant_emotion: str,
        dominant_motive: str,
        decision_category: str,
        behavior_type: str,
        matched_pattern_ids: Optional[List[str]] = None,
        outcome: Optional[str] = None,
    ) -> None:
        """
        Persist this decision event into Neo4j as a graph update.
        Called at the end of the pipeline after guidance is generated.
        """
        if not self.neo4j.is_connected:
            return
        try:
            self.neo4j.run(
                """
                MERGE (u:UserStateNode {user_id: $uid})
                MERGE (e:EmotionNode   {type: $emotion})
                MERGE (m:MotiveNode    {type: $motive})
                MERGE (b:BehaviorNode  {type: $behavior})
                MERGE (u)-[r:HAS_STATE {decision_id: $did}]->(e)
                  ON CREATE SET r.recorded_at = datetime(), r.category = $cat
                MERGE (e)-[:CAUSES     {decision_id: $did}]->(m)
                MERGE (m)-[:LEADS_TO   {decision_id: $did}]->(b)
                """,
                uid=user_id, emotion=dominant_emotion, motive=dominant_motive,
                behavior=behavior_type, did=decision_id, cat=decision_category,
            )
            if outcome:
                self.neo4j.run(
                    """
                    MERGE (b:BehaviorNode {type: $behavior})
                    MERGE (o:BehaviorNode {type: $outcome})
                    MERGE (b)-[:LEADS_TO {decision_id: $did, is_outcome: true}]->(o)
                    """,
                    behavior=behavior_type, outcome=outcome, did=decision_id,
                )
            if matched_pattern_ids:
                for pid in matched_pattern_ids:
                    self.neo4j.run(
                        """
                        MATCH (u:UserStateNode {user_id: $uid})
                        MERGE (p:PatternNode {pattern_id: $pid})
                        MERGE (u)-[r:MATCHED_PATTERN]->(p)
                          ON CREATE SET r.first_seen = datetime(), r.count = 1
                          ON MATCH  SET r.count = r.count + 1, r.last_seen = datetime()
                        """,
                        uid=user_id, pid=pid,
                    )
        except Exception as exc:
            logger.warning("[graph] write_back failed: %s", exc)

    def get_user_pattern_history(
        self, user_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Return the patterns this user has most frequently matched."""
        if not self.neo4j.is_connected:
            return []
        return self.neo4j.run(
            """
            MATCH (u:UserStateNode {user_id: $uid})-[r:MATCHED_PATTERN]->(p:PatternNode)
            RETURN p.pattern_id AS pattern_id, r.count AS count, r.last_seen AS last_seen
            ORDER BY r.count DESC LIMIT $lim
            """,
            uid=user_id, lim=limit,
        )

    # ── Graph Intelligence Queries (v2.1 use cases) ───────────────────────────

    def detect_loop(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Use case 1 — "Which loop is the user currently inside?"

        Looks for OutcomeNode → REINFORCES → MotiveNode paths in the user's
        recent history, indicating an active feedback loop.

        Returns list of {pattern_id, loop_description, confidence}.
        """
        if not self.neo4j.is_connected:
            return self._detect_loop_offline(user_id)
        rows = self.neo4j.run(
            """
            MATCH (u:UserStateNode {user_id: $uid})-[:HAS_STATE]->(e:EmotionNode)
                  -[:CAUSES]->(m:MotiveNode)-[:LEADS_TO]->(b:BehaviorNode)
                  -[:LEADS_TO]->(o:OutcomeNode)-[:REINFORCES]->(m)
            WITH m.type AS motive, b.type AS behavior, o.type AS outcome,
                 count(*) AS frequency
            WHERE frequency >= 2
            RETURN motive, behavior, outcome, frequency
            ORDER BY frequency DESC
            """,
            uid=user_id,
        )
        return [
            {
                "motive":      r["motive"],
                "behavior":    r["behavior"],
                "outcome":     r["outcome"],
                "frequency":   r["frequency"],
                "loop_description": f"{r['motive']} → {r['behavior']} → {r['outcome']} → (reinforces) → {r['motive']}",
                "note": "This pattern has appeared multiple times — it may indicate an active loop.",
            }
            for r in rows
        ]

    def trace_root_cause(self, behavior_type: str) -> List[Dict[str, Any]]:
        """
        Use case 2 — "What emotion originally triggered this behavior chain?"

        Traverses backwards from a BehaviorNode through MotiveNode to EmotionNode.

        Returns list of {emotion, motive, behavior, path_description}.
        """
        if not self.neo4j.is_connected:
            return self._trace_root_offline(behavior_type)
        rows = self.neo4j.run(
            """
            MATCH path = (e:EmotionNode)-[:CAUSES]->(m:MotiveNode)
                          -[:LEADS_TO]->(b:BehaviorNode {type: $btype})
            RETURN e.name AS emotion, m.type AS motive, b.type AS behavior,
                   [n in nodes(path) | coalesce(n.name, n.type)] AS path_labels
            LIMIT 5
            """,
            btype=behavior_type,
        )
        return [
            {
                "root_emotion":      r["emotion"],
                "motive":            r["motive"],
                "behavior":          r["behavior"],
                "path_labels":       r["path_labels"],
                "path_description":  " → ".join(r["path_labels"]),
            }
            for r in rows
        ]

    def find_intervention_points(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Use case 3 — "Where can this loop be broken?"

        Identifies BehaviorNodes that have BREAKS edges from PrincipleNodes,
        intersected with the user's active behavior history.

        Returns list of {behavior, principle, intervention_text, scripture}.
        """
        if not self.neo4j.is_connected:
            return self._find_interventions_offline(user_id)
        rows = self.neo4j.run(
            """
            MATCH (u:UserStateNode {user_id: $uid})-[:HAS_STATE*1..3]->(e)
                  -[:CAUSES|LEADS_TO*1..3]->(b:BehaviorNode)
            MATCH (pr:PrincipleNode)-[:BREAKS]->(b)
            RETURN b.type AS behavior,
                   pr.principle_id AS principle_id,
                   pr.text AS principle_text
            LIMIT 6
            """,
            uid=user_id,
        )
        return [
            {
                "behavior":      r["behavior"],
                "principle_id":  r["principle_id"],
                "principle_text":r.get("principle_text", r["principle_id"]),
                "break_description": (
                    f"Principle '{r['principle_id']}' can interrupt the '{r['behavior']}' behavior."
                ),
            }
            for r in rows
        ]

    def activate_principles(self, motive_type: str) -> List[Dict[str, Any]]:
        """
        Use case 4 — "Which spiritual truth breaks this pattern?"

        Finds PrincipleNodes that either INFLUENCES or BREAKS paths involving
        a given MotiveNode type.

        Returns list of {principle_id, principle_text, action_type, scripture}.
        """
        if not self.neo4j.is_connected:
            return self._activate_principles_offline(motive_type)
        rows = self.neo4j.run(
            """
            MATCH (pr:PrincipleNode)-[r:INFLUENCES|BREAKS]->(n)
            WHERE (n:MotiveNode AND n.type = $mtype)
               OR (n:BehaviorNode AND EXISTS {
                    MATCH (:MotiveNode {type: $mtype})-[:LEADS_TO]->(n)
                 })
            RETURN pr.principle_id AS principle_id,
                   pr.text AS principle_text,
                   type(r) AS action_type
            LIMIT 5
            """,
            mtype=motive_type,
        )
        return [
            {
                "principle_id":  r["principle_id"],
                "principle_text":r.get("principle_text", r["principle_id"]),
                "action_type":   r["action_type"],
                "note": (
                    f"This principle {r['action_type'].lower()}s patterns driven by '{motive_type}'."
                ),
            }
            for r in rows
        ]

    # ── Offline fallbacks (when Neo4j is not connected) ───────────────────────

    def _detect_loop_offline(self, user_id: str) -> List[Dict[str, Any]]:
        """Rule-based loop detection using PATTERN_SUBGRAPHS when Neo4j is offline."""
        results = []
        for sg in PATTERN_SUBGRAPHS:
            if sg.reinforces_edges:
                out, mot = sg.reinforces_edges[0]
                results.append({
                    "pattern_id":   sg.pattern_id,
                    "motive":       mot,
                    "outcome":      out,
                    "loop_description": f"{sg.label} (offline inference)",
                    "note": "Neo4j offline — loop detected from known pattern library.",
                })
        return results[:3]

    def _trace_root_offline(self, behavior_type: str) -> List[Dict[str, Any]]:
        results = []
        for sg in PATTERN_SUBGRAPHS:
            if behavior_type in sg.behavior_nodes:
                emotion = sg.emotion_nodes[0] if sg.emotion_nodes else "unknown"
                motive  = sg.motive_nodes[0]  if sg.motive_nodes  else "unknown"
                results.append({
                    "root_emotion":    emotion,
                    "motive":          motive,
                    "behavior":        behavior_type,
                    "path_description":f"{emotion} → {motive} → {behavior_type}",
                })
        return results

    def _find_interventions_offline(self, user_id: str) -> List[Dict[str, Any]]:
        results = []
        for sg in PATTERN_SUBGRAPHS:
            for (principle, behavior) in sg.breaks_edges:
                results.append({
                    "behavior":          behavior,
                    "principle_id":      principle,
                    "principle_text":    principle.replace("_", " "),
                    "break_description": f"Principle '{principle}' can interrupt '{behavior}'.",
                })
        return results[:4]

    def _activate_principles_offline(self, motive_type: str) -> List[Dict[str, Any]]:
        results = []
        for sg in PATTERN_SUBGRAPHS:
            if motive_type in sg.motive_nodes:
                for (principle, _) in sg.influences_edges:
                    results.append({
                        "principle_id":  principle,
                        "principle_text":principle.replace("_", " "),
                        "action_type":   EdgeType.INFLUENCES,
                        "note": f"This principle influences patterns driven by '{motive_type}'.",
                    })
                for (principle, _) in sg.breaks_edges:
                    results.append({
                        "principle_id":  principle,
                        "principle_text":principle.replace("_", " "),
                        "action_type":   EdgeType.BREAKS,
                        "note": f"This principle breaks behavior in '{motive_type}' loops.",
                    })
        seen = set()
        deduped = []
        for r in results:
            if r["principle_id"] not in seen:
                seen.add(r["principle_id"])
                deduped.append(r)
        return deduped[:5]

    def _query_repeat_behaviors(self, user_id: str, window_days: int = 90) -> List[Dict[str, Any]]:
        return self.neo4j.run(
            """
            MATCH (u:UserStateNode {user_id: $uid})-[r:HAS_STATE]->(e:EmotionNode)
                  -[:CAUSES]->(m:MotiveNode)-[:LEADS_TO]->(b:BehaviorNode)
            WHERE r.recorded_at > datetime() - duration({days: $days})
            WITH b.type AS behavior, count(*) AS freq
            WHERE freq >= 2
            RETURN behavior, freq ORDER BY freq DESC
            """,
            uid=user_id, days=window_days,
        )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _match_patterns(
        self,
        dominant_motive: str,
        emotions: List[Dict[str, Any]],
        decision_category: str,
    ) -> List[Dict[str, Any]]:
        matched_ids: set[str] = set()

        # Motive-based
        for pid in MOTIVE_PATTERN_MAP.get(dominant_motive.lower(), []):
            matched_ids.add(pid)

        # Emotion-based (cap at top-3 highest-intensity emotions)
        sorted_emos = sorted(emotions, key=lambda e: e.get("intensity", 0), reverse=True)
        for emo in sorted_emos[:3]:
            etype = emo.get("type", emo.get("emotion_type", "")).lower()
            for pid in EMOTION_PATTERN_MAP.get(etype, []):
                matched_ids.add(pid)

        # Category-based (at most 2 additions to avoid over-matching)
        cat_pids = CATEGORY_PATTERN_MAP.get(decision_category.lower(), [])
        for pid in cat_pids[:2]:
            matched_ids.add(pid)

        # Cap total at 4 most relevant patterns to keep output focused
        pattern_index = {p["id"]: p for p in KNOWN_PATTERNS}
        result = [pattern_index[pid] for pid in matched_ids if pid in pattern_index]
        return result[:4]

    def _build_chains(
        self,
        patterns: List[Dict[str, Any]],
        past_behaviors: List[str],
    ) -> Tuple[List[CausalChain], List[CausalChain]]:
        chains: List[CausalChain] = []
        cycles: List[CausalChain] = []
        past_set = set(pb.lower() for pb in past_behaviors)

        for p in patterns:
            chain_nodes = p["chain"]
            edges = [EdgeType.LEADS_TO] * (len(chain_nodes) - 1)

            # Structural cycle: last node reappears earlier in chain
            cycle = False
            cycle_start = None
            last = chain_nodes[-1]
            if last in chain_nodes[:-1]:
                cycle = True
                cycle_start = last

            # Behavioral cycle: user has done this before
            if not cycle:
                for node in chain_nodes:
                    if node.lower() in past_set:
                        cycle = True
                        cycle_start = node
                        break

            cc = CausalChain(
                nodes=chain_nodes,
                edge_types=edges,
                cycle_detected=cycle,
                cycle_start=cycle_start,
                description=p["label"],
            )
            chains.append(cc)
            if cycle:
                cycles.append(cc)

        return chains, cycles

    def _extract_interventions(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        out = []
        for p in patterns:
            if "intervention" in p:
                iv = p["intervention"]
                out.append({
                    "pattern_id":  p["id"],
                    "pattern":     p["label"],
                    "category":    p.get("category", ""),
                    "break_at":    iv["node"],
                    "suggestion":  iv["suggestion"],
                    "scripture":   iv.get("scripture", ""),
                })
        return out

    def _extract_questions(self, patterns: List[Dict[str, Any]]) -> List[str]:
        return [p["reflective_question"] for p in patterns if "reflective_question" in p]

    def _build_summary(
        self,
        chains: List[CausalChain],
        cycles: List[CausalChain],
        interventions: List[Dict[str, str]],
    ) -> str:
        if not chains:
            return (
                "No structural patterns were matched for the current profile. "
                "This may reflect a genuinely novel situation, or insufficient signal."
            )

        parts: List[str] = []
        for c in chains:
            parts.append(f"Pattern observed: {c.description}")
            if c.cycle_detected:
                parts.append(
                    f"  Possible recurring loop at '{c.cycle_start}' — "
                    "this may not be the first time this sequence has appeared."
                )

        if interventions:
            parts.append("")
            parts.append("Highest-leverage reflection points:")
            for iv in interventions[:2]:
                parts.append(
                    f"  [{iv['break_at']}] — {iv['suggestion']}"
                    + (f" ({iv['scripture']})" if iv.get("scripture") else "")
                )

        return "\n".join(parts)

    def _query_user_paths(self, user_id: str) -> List[List[Dict[str, Any]]]:
        rows = self.neo4j.run(
            """
            MATCH path = (u:UserStateNode {user_id: $uid})-[:HAS_STATE]->
                         (e:EmotionNode)-[:CAUSES]->(m:MotiveNode)-[:LEADS_TO]->(b:BehaviorNode)
            RETURN [node in nodes(path) | {label: labels(node)[0], type: node.type}] AS path_nodes
            ORDER BY e.recorded_at DESC LIMIT 10
            """,
            uid=user_id,
        )
        return [r.get("path_nodes", []) for r in rows]


# Backward-compat alias so existing imports of GraphEngine still work
GraphEngine = GraphService

# Module-level singleton
_graph_service = GraphService(_neo4j)


def get_graph_service() -> GraphService:
    return _graph_service


# ──────────────────────────────────────────────────────────────────────────────
# Cypher schema bootstrap (call once on startup)
# ──────────────────────────────────────────────────────────────────────────────

NEO4J_SCHEMA_CYPHER = """
// ── SFDS Neo4j Schema Bootstrap v2.1 ─────────────────────────────────
// Idempotent — safe to re-run.
// Node types : EmotionNode · MotiveNode · BehaviorNode · OutcomeNode
//              SpiritualStateNode · PrincipleNode · UserStateNode
// Edge types : CAUSES · LEADS_TO · REINFORCES · BREAKS · INFLUENCES
//              HAS_STATE
// ─────────────────────────────────────────────────────────────────────

// Constraints
CREATE CONSTRAINT IF NOT EXISTS FOR (n:EmotionNode)        REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:MotiveNode)         REQUIRE n.type IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:BehaviorNode)       REQUIRE n.type IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:OutcomeNode)        REQUIRE n.type IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:SpiritualStateNode) REQUIRE n.type IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:PrincipleNode)      REQUIRE n.principle_id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:UserStateNode)      REQUIRE n.user_id IS UNIQUE;

// Indexes
CREATE INDEX IF NOT EXISTS FOR (n:EmotionNode)   ON (n.name);
CREATE INDEX IF NOT EXISTS FOR (n:BehaviorNode)  ON (n.type);
CREATE INDEX IF NOT EXISTS FOR (n:OutcomeNode)   ON (n.type);
CREATE INDEX IF NOT EXISTS FOR (n:UserStateNode) ON (n.user_id);

// EmotionNodes
MERGE (:EmotionNode {name: 'anxiety'});
MERGE (:EmotionNode {name: 'shame'});
MERGE (:EmotionNode {name: 'insecurity'});
MERGE (:EmotionNode {name: 'loneliness'});
MERGE (:EmotionNode {name: 'high_confidence'});
MERGE (:EmotionNode {name: 'emptiness'});
MERGE (:EmotionNode {name: 'peace'});
MERGE (:EmotionNode {name: 'joy'});

// MotiveNodes
MERGE (:MotiveNode {type: 'fear_driven_control'});
MERGE (:MotiveNode {type: 'pride_driven_self_evaluation'});
MERGE (:MotiveNode {type: 'avoidance_driven'});
MERGE (:MotiveNode {type: 'emotional_dependency'});
MERGE (:MotiveNode {type: 'pride_amplification'});
MERGE (:MotiveNode {type: 'compensation_behavior'});
MERGE (:MotiveNode {type: 'truth_driven'});

// BehaviorNodes
MERGE (:BehaviorNode {type: 'overworking'});
MERGE (:BehaviorNode {type: 'micromanaging'});
MERGE (:BehaviorNode {type: 'comparison_seeking'});
MERGE (:BehaviorNode {type: 'performance_chasing'});
MERGE (:BehaviorNode {type: 'procrastination'});
MERGE (:BehaviorNode {type: 'withdrawal'});
MERGE (:BehaviorNode {type: 'impulsive_bonding'});
MERGE (:BehaviorNode {type: 'overconfident_decisions'});
MERGE (:BehaviorNode {type: 'overactivity'});
MERGE (:BehaviorNode {type: 'over_spiritual_performance'});

// OutcomeNodes
MERGE (:OutcomeNode {type: 'burnout'});
MERGE (:OutcomeNode {type: 'exhaustion'});
MERGE (:OutcomeNode {type: 'anxiety_spike'});
MERGE (:OutcomeNode {type: 'accumulated_pressure'});
MERGE (:OutcomeNode {type: 'regret'});
MERGE (:OutcomeNode {type: 'relational_instability'});
MERGE (:OutcomeNode {type: 'failure_event'});
MERGE (:OutcomeNode {type: 'shame_collapse'});
MERGE (:OutcomeNode {type: 'deeper_dryness'});
MERGE (:OutcomeNode {type: 'peace'});
MERGE (:OutcomeNode {type: 'spiritual_growth'});

// SpiritualStateNodes
MERGE (:SpiritualStateNode {type: 'dry'});
MERGE (:SpiritualStateNode {type: 'stable'});
MERGE (:SpiritualStateNode {type: 'growing'});
MERGE (:SpiritualStateNode {type: 'confused'});
MERGE (:SpiritualStateNode {type: 'restoring'});

// PrincipleNodes
MERGE (:PrincipleNode {principle_id: 'rest_before_decision',        text: 'Do not make major decisions from a depleted state'});
MERGE (:PrincipleNode {principle_id: 'trust_over_control',          text: 'Trust is the antidote to the compulsion to control'});
MERGE (:PrincipleNode {principle_id: 'surrender_uncertainty',       text: 'Surrender uncertainty rather than resolving it through force'});
MERGE (:PrincipleNode {principle_id: 'identity_not_in_performance', text: 'Identity is not located in achievement or output'});
MERGE (:PrincipleNode {principle_id: 'humility_restores_clarity',   text: 'Humility is not self-deprecation — it is accuracy about reality'});
MERGE (:PrincipleNode {principle_id: 'truth_brings_freedom',        text: 'Truth, however uncomfortable, is the beginning of freedom'});
MERGE (:PrincipleNode {principle_id: 'small_obedience_breaks_shame',text: 'One small faithful act can break the avoidance loop'});
MERGE (:PrincipleNode {principle_id: 'identity_stability_first',    text: 'Decisions from an unstable identity tend to compound instability'});
MERGE (:PrincipleNode {principle_id: 'avoid_void_decisions',        text: 'Avoid making permanent decisions from a temporary emotional void'});
MERGE (:PrincipleNode {principle_id: 'humility_in_success',         text: 'Success is a particularly dangerous time for pride inflation'});
MERGE (:PrincipleNode {principle_id: 'identity_stability',          text: 'Stable identity is the foundation of sustainable decision-making'});
MERGE (:PrincipleNode {principle_id: 'rest_in_being',               text: 'Being precedes doing — rest is not escape, it is formation'});
MERGE (:PrincipleNode {principle_id: 'presence_over_performance',   text: 'Presence with God is not measurable by output'});

// ── Pattern 1: FEAR → CONTROL → BURNOUT LOOP ─────────────────────────
MATCH (e:EmotionNode {name:'anxiety'}),      (m:MotiveNode  {type:'fear_driven_control'})      MERGE (e)-[:CAUSES {pattern_id:'fear_control_burnout'}]->(m);
MATCH (m:MotiveNode  {type:'fear_driven_control'}), (b:BehaviorNode {type:'overworking'})      MERGE (m)-[:LEADS_TO {pattern_id:'fear_control_burnout'}]->(b);
MATCH (m:MotiveNode  {type:'fear_driven_control'}), (b:BehaviorNode {type:'micromanaging'})    MERGE (m)-[:LEADS_TO {pattern_id:'fear_control_burnout'}]->(b);
MATCH (b:BehaviorNode{type:'overworking'}),  (o:OutcomeNode {type:'burnout'})                  MERGE (b)-[:LEADS_TO {pattern_id:'fear_control_burnout'}]->(o);
MATCH (o:OutcomeNode {type:'burnout'}),      (o2:OutcomeNode{type:'exhaustion'})               MERGE (o)-[:LEADS_TO {pattern_id:'fear_control_burnout'}]->(o2);
MATCH (o:OutcomeNode {type:'exhaustion'}),   (m:MotiveNode  {type:'fear_driven_control'})      MERGE (o)-[:REINFORCES {pattern_id:'fear_control_burnout'}]->(m);
MATCH (pr:PrincipleNode{principle_id:'rest_before_decision'}), (b:BehaviorNode{type:'overworking'})   MERGE (pr)-[:BREAKS {pattern_id:'fear_control_burnout'}]->(b);
MATCH (pr:PrincipleNode{principle_id:'trust_over_control'}),   (b:BehaviorNode{type:'micromanaging'}) MERGE (pr)-[:BREAKS {pattern_id:'fear_control_burnout'}]->(b);
MATCH (pr:PrincipleNode{principle_id:'surrender_uncertainty'}),(m:MotiveNode  {type:'fear_driven_control'}) MERGE (pr)-[:INFLUENCES {pattern_id:'fear_control_burnout'}]->(m);

// ── Pattern 2: PRIDE → COMPARISON → ANXIETY LOOP ─────────────────────
MATCH (e:EmotionNode {name:'insecurity'}),   (m:MotiveNode  {type:'pride_driven_self_evaluation'}) MERGE (e)-[:CAUSES {pattern_id:'pride_comparison_anxiety'}]->(m);
MATCH (m:MotiveNode  {type:'pride_driven_self_evaluation'}), (b:BehaviorNode{type:'comparison_seeking'})  MERGE (m)-[:LEADS_TO {pattern_id:'pride_comparison_anxiety'}]->(b);
MATCH (m:MotiveNode  {type:'pride_driven_self_evaluation'}), (b:BehaviorNode{type:'performance_chasing'}) MERGE (m)-[:LEADS_TO {pattern_id:'pride_comparison_anxiety'}]->(b);
MATCH (b:BehaviorNode{type:'comparison_seeking'}),  (o:OutcomeNode{type:'anxiety_spike'})              MERGE (b)-[:LEADS_TO {pattern_id:'pride_comparison_anxiety'}]->(o);
MATCH (o:OutcomeNode {type:'anxiety_spike'}),        (o2:OutcomeNode{type:'accumulated_pressure'})     MERGE (o)-[:LEADS_TO {pattern_id:'pride_comparison_anxiety'}]->(o2);
MATCH (o:OutcomeNode {type:'accumulated_pressure'}), (m:MotiveNode{type:'pride_driven_self_evaluation'}) MERGE (o)-[:REINFORCES {pattern_id:'pride_comparison_anxiety'}]->(m);
MATCH (pr:PrincipleNode{principle_id:'identity_not_in_performance'}),(b:BehaviorNode{type:'comparison_seeking'})  MERGE (pr)-[:BREAKS {pattern_id:'pride_comparison_anxiety'}]->(b);
MATCH (pr:PrincipleNode{principle_id:'identity_not_in_performance'}),(b:BehaviorNode{type:'performance_chasing'}) MERGE (pr)-[:BREAKS {pattern_id:'pride_comparison_anxiety'}]->(b);
MATCH (pr:PrincipleNode{principle_id:'humility_restores_clarity'}),  (m:MotiveNode{type:'pride_driven_self_evaluation'}) MERGE (pr)-[:INFLUENCES {pattern_id:'pride_comparison_anxiety'}]->(m);

// ── Pattern 3: SHAME → AVOIDANCE → DELAY LOOP ────────────────────────
MATCH (e:EmotionNode {name:'shame'}),  (m:MotiveNode{type:'avoidance_driven'})               MERGE (e)-[:CAUSES {pattern_id:'shame_avoidance_procrastination'}]->(m);
MATCH (m:MotiveNode  {type:'avoidance_driven'}),(b:BehaviorNode{type:'procrastination'})      MERGE (m)-[:LEADS_TO {pattern_id:'shame_avoidance_procrastination'}]->(b);
MATCH (m:MotiveNode  {type:'avoidance_driven'}),(b:BehaviorNode{type:'withdrawal'})           MERGE (m)-[:LEADS_TO {pattern_id:'shame_avoidance_procrastination'}]->(b);
MATCH (b:BehaviorNode{type:'procrastination'}), (o:OutcomeNode{type:'accumulated_pressure'}) MERGE (b)-[:LEADS_TO {pattern_id:'shame_avoidance_procrastination'}]->(o);
MATCH (o:OutcomeNode {type:'accumulated_pressure'}),(o2:OutcomeNode{type:'anxiety_spike'})    MERGE (o)-[:LEADS_TO {pattern_id:'shame_avoidance_procrastination'}]->(o2);
MATCH (o:OutcomeNode {type:'anxiety_spike'}),(m:MotiveNode{type:'avoidance_driven'})          MERGE (o)-[:REINFORCES {pattern_id:'shame_avoidance_procrastination'}]->(m);
MATCH (pr:PrincipleNode{principle_id:'truth_brings_freedom'}),         (b:BehaviorNode{type:'procrastination'}) MERGE (pr)-[:BREAKS {pattern_id:'shame_avoidance_procrastination'}]->(b);
MATCH (pr:PrincipleNode{principle_id:'small_obedience_breaks_shame'}), (b:BehaviorNode{type:'withdrawal'})      MERGE (pr)-[:BREAKS {pattern_id:'shame_avoidance_procrastination'}]->(b);
MATCH (pr:PrincipleNode{principle_id:'truth_brings_freedom'}),(m:MotiveNode{type:'avoidance_driven'}) MERGE (pr)-[:INFLUENCES {pattern_id:'shame_avoidance_procrastination'}]->(m);

// ── Pattern 4: LONELINESS → ATTACHMENT → IMPULSIVE DECISION ──────────
MATCH (e:EmotionNode {name:'loneliness'}),(m:MotiveNode{type:'emotional_dependency'})               MERGE (e)-[:CAUSES {pattern_id:'loneliness_attachment_impulse'}]->(m);
MATCH (m:MotiveNode  {type:'emotional_dependency'}),(b:BehaviorNode{type:'impulsive_bonding'})      MERGE (m)-[:LEADS_TO {pattern_id:'loneliness_attachment_impulse'}]->(b);
MATCH (b:BehaviorNode{type:'impulsive_bonding'}),   (o:OutcomeNode {type:'regret'})                 MERGE (b)-[:LEADS_TO {pattern_id:'loneliness_attachment_impulse'}]->(o);
MATCH (o:OutcomeNode {type:'regret'}),(o2:OutcomeNode{type:'relational_instability'})               MERGE (o)-[:LEADS_TO {pattern_id:'loneliness_attachment_impulse'}]->(o2);
MATCH (o:OutcomeNode {type:'relational_instability'}),(m:MotiveNode{type:'emotional_dependency'})   MERGE (o)-[:REINFORCES {pattern_id:'loneliness_attachment_impulse'}]->(m);
MATCH (pr:PrincipleNode{principle_id:'identity_stability_first'}),(b:BehaviorNode{type:'impulsive_bonding'}) MERGE (pr)-[:BREAKS {pattern_id:'loneliness_attachment_impulse'}]->(b);
MATCH (pr:PrincipleNode{principle_id:'avoid_void_decisions'}),(m:MotiveNode{type:'emotional_dependency'})    MERGE (pr)-[:INFLUENCES {pattern_id:'loneliness_attachment_impulse'}]->(m);

// ── Pattern 5: PRIDE INFLATION → COLLAPSE ────────────────────────────
MATCH (e:EmotionNode {name:'high_confidence'}),(m:MotiveNode{type:'pride_amplification'})             MERGE (e)-[:CAUSES {pattern_id:'pride_inflation_collapse'}]->(m);
MATCH (m:MotiveNode  {type:'pride_amplification'}),(b:BehaviorNode{type:'overconfident_decisions'})   MERGE (m)-[:LEADS_TO {pattern_id:'pride_inflation_collapse'}]->(b);
MATCH (b:BehaviorNode{type:'overconfident_decisions'}),(o:OutcomeNode{type:'failure_event'})           MERGE (b)-[:LEADS_TO {pattern_id:'pride_inflation_collapse'}]->(o);
MATCH (o:OutcomeNode {type:'failure_event'}),(o2:OutcomeNode{type:'shame_collapse'})                   MERGE (o)-[:LEADS_TO {pattern_id:'pride_inflation_collapse'}]->(o2);
MATCH (o:OutcomeNode {type:'shame_collapse'}),(m:MotiveNode{type:'pride_amplification'})               MERGE (o)-[:REINFORCES {pattern_id:'pride_inflation_collapse'}]->(m);
MATCH (pr:PrincipleNode{principle_id:'humility_in_success'}),  (b:BehaviorNode{type:'overconfident_decisions'}) MERGE (pr)-[:BREAKS {pattern_id:'pride_inflation_collapse'}]->(b);
MATCH (pr:PrincipleNode{principle_id:'identity_stability'}),(m:MotiveNode{type:'pride_amplification'}) MERGE (pr)-[:INFLUENCES {pattern_id:'pride_inflation_collapse'}]->(m);

// ── Pattern 6: SPIRITUAL DRYNESS → OVERACTIVITY LOOP ─────────────────
MATCH (e:EmotionNode {name:'emptiness'}),(m:MotiveNode{type:'compensation_behavior'})                    MERGE (e)-[:CAUSES {pattern_id:'spiritual_dryness_compensation'}]->(m);
MATCH (m:MotiveNode  {type:'compensation_behavior'}),(b:BehaviorNode{type:'overactivity'})               MERGE (m)-[:LEADS_TO {pattern_id:'spiritual_dryness_compensation'}]->(b);
MATCH (m:MotiveNode  {type:'compensation_behavior'}),(b:BehaviorNode{type:'over_spiritual_performance'}) MERGE (m)-[:LEADS_TO {pattern_id:'spiritual_dryness_compensation'}]->(b);
MATCH (b:BehaviorNode{type:'overactivity'}),               (o:OutcomeNode{type:'exhaustion'})            MERGE (b)-[:LEADS_TO {pattern_id:'spiritual_dryness_compensation'}]->(o);
MATCH (b:BehaviorNode{type:'over_spiritual_performance'}), (o:OutcomeNode{type:'exhaustion'})            MERGE (b)-[:LEADS_TO {pattern_id:'spiritual_dryness_compensation'}]->(o);
MATCH (o:OutcomeNode {type:'exhaustion'}),(o2:OutcomeNode{type:'deeper_dryness'})                        MERGE (o)-[:LEADS_TO {pattern_id:'spiritual_dryness_compensation'}]->(o2);
MATCH (o:OutcomeNode {type:'deeper_dryness'}),(m:MotiveNode{type:'compensation_behavior'})               MERGE (o)-[:REINFORCES {pattern_id:'spiritual_dryness_compensation'}]->(m);
MATCH (pr:PrincipleNode{principle_id:'rest_in_being'}),            (b:BehaviorNode{type:'overactivity'})               MERGE (pr)-[:BREAKS {pattern_id:'spiritual_dryness_compensation'}]->(b);
MATCH (pr:PrincipleNode{principle_id:'presence_over_performance'}),(b:BehaviorNode{type:'over_spiritual_performance'}) MERGE (pr)-[:BREAKS {pattern_id:'spiritual_dryness_compensation'}]->(b);
MATCH (pr:PrincipleNode{principle_id:'rest_in_being'}),(m:MotiveNode{type:'compensation_behavior'}) MERGE (pr)-[:INFLUENCES {pattern_id:'spiritual_dryness_compensation'}]->(m);
"""
