"""SFDS v3 — Pattern Library Part 2: Categories D (Desire) + E (Relational) + F (Spiritual)"""

_LOOPS_D_E_F = [

    # ══════════════════════════════════════════════════════════
    # CATEGORY D — DESIRE / IMPULSE LOOPS (31–38)
    # ══════════════════════════════════════════════════════════
    {   # D31
        "id": "D31_desire_impulse_regret", "label": "Desire → Impulse Decision → Regret Loop",
        "category": "desire", "loop_type": "desire_impulse_loop", "trigger_emotion": "desire",
        "break_principle": "Pause between impulse and action: 24 hours changes the trajectory",
        "description": "Unexamined desire → impulsive action → regret → relief seeking → desire.",
        "chain": ["desire", "impulsive_action", "regret", "relief_seeking"],
        "edges": [
            ("desire", "CAUSES", "impulsive_action"), ("impulsive_action", "LEADS_TO", "regret"),
            ("regret", "LEADS_TO", "relief_seeking"), ("relief_seeking", "REINFORCES", "desire"),
        ],
        "break_edges": [("principle_pause_before_action", "BREAKS", "impulsive_action")],
        "formation_dims": {"emotional_stability": "-", "truth_alignment": "-"},
    },
    {   # D32
        "id": "D32_desire_dopamine_seeking_emptiness", "label": "Desire → Dopamine Seeking → Emptiness Loop",
        "category": "desire", "loop_type": "desire_impulse_loop", "trigger_emotion": "desire",
        "break_principle": "Deeper desire cannot be satisfied by surface pleasure",
        "description": "Desire → dopamine seeking → transient satisfaction → emptiness → desire.",
        "chain": ["desire", "dopamine_seeking", "transient_satisfaction", "emptiness"],
        "edges": [
            ("desire", "CAUSES", "dopamine_seeking"),
            ("dopamine_seeking", "LEADS_TO", "transient_satisfaction"),
            ("transient_satisfaction", "LEADS_TO", "emptiness"),
            ("emptiness", "REINFORCES", "desire"),
        ],
        "break_edges": [("principle_deeper_desire", "BREAKS", "dopamine_seeking")],
        "formation_dims": {"spiritual_clarity": "-", "emotional_stability": "-"},
    },
    {   # D33
        "id": "D33_desire_short_term_reward_long_term_loss", "label": "Desire → Short-Term Reward → Long-Term Loss Loop",
        "category": "desire", "loop_type": "desire_impulse_loop", "trigger_emotion": "desire",
        "break_principle": "Visualize the long-term self before the short-term decision",
        "description": "Desire for immediate reward overrides long-term consideration → loss → compensation desire.",
        "chain": ["desire", "short_term_reward", "long_term_loss", "compensation_desire"],
        "edges": [
            ("desire", "CAUSES", "short_term_reward"),
            ("short_term_reward", "LEADS_TO", "long_term_loss"),
            ("long_term_loss", "LEADS_TO", "compensation_desire"),
            ("compensation_desire", "REINFORCES", "desire"),
        ],
        "break_edges": [("principle_future_self_visualization", "BREAKS", "short_term_reward")],
        "formation_dims": {"truth_alignment": "-", "resilience": "-"},
    },
    {   # D34
        "id": "D34_desire_emotional_dependency_instability", "label": "Desire → Emotional Dependency → Instability Loop",
        "category": "desire", "loop_type": "desire_impulse_loop", "trigger_emotion": "desire",
        "break_principle": "Emotional regulation from within reduces dependency pressure",
        "description": "Desire for emotional completion → dependency → relational instability → heightened desire.",
        "chain": ["desire", "emotional_dependency", "relational_instability", "heightened_desire"],
        "edges": [
            ("desire", "CAUSES", "emotional_dependency"),
            ("emotional_dependency", "LEADS_TO", "relational_instability"),
            ("relational_instability", "LEADS_TO", "heightened_desire"),
            ("heightened_desire", "REINFORCES", "desire"),
        ],
        "break_edges": [("principle_inner_regulation", "BREAKS", "emotional_dependency")],
        "formation_dims": {"relational_health": "-", "emotional_stability": "-"},
    },
    {   # D35
        "id": "D35_desire_relationship_attachment_anxiety", "label": "Desire → Relationship Attachment → Anxiety Loop",
        "category": "desire", "loop_type": "desire_impulse_loop", "trigger_emotion": "desire",
        "break_principle": "Secure attachment is built on self-stability, not possession",
        "description": "Desire for connection → anxious attachment → controlling behavior → relational threat → desire.",
        "chain": ["desire", "anxious_attachment", "controlling_behavior", "relational_threat"],
        "edges": [
            ("desire", "CAUSES", "anxious_attachment"),
            ("anxious_attachment", "LEADS_TO", "controlling_behavior"),
            ("controlling_behavior", "LEADS_TO", "relational_threat"),
            ("relational_threat", "REINFORCES", "desire"),
        ],
        "break_edges": [("principle_secure_self_stability", "BREAKS", "anxious_attachment")],
        "formation_dims": {"relational_health": "-", "emotional_stability": "-", "fear_tendency": "+"},
    },
    {   # D36
        "id": "D36_desire_consumption_addiction_dissatisfaction", "label": "Desire → Consumption Addiction → Dissatisfaction Loop",
        "category": "desire", "loop_type": "desire_impulse_loop", "trigger_emotion": "desire",
        "break_principle": "Sufficiency practice: naming what is already enough",
        "description": "Desire → consumption → threshold increase → dissatisfaction → desire.",
        "chain": ["desire", "consumption", "threshold_increase", "dissatisfaction"],
        "edges": [
            ("desire", "CAUSES", "consumption"), ("consumption", "LEADS_TO", "threshold_increase"),
            ("threshold_increase", "LEADS_TO", "dissatisfaction"),
            ("dissatisfaction", "REINFORCES", "desire"),
        ],
        "break_edges": [("principle_sufficiency", "BREAKS", "consumption")],
        "formation_dims": {"spiritual_clarity": "-", "truth_alignment": "-"},
    },
    {   # D37
        "id": "D37_desire_escalation_loss_of_control", "label": "Desire → Escalation → Loss of Control Loop",
        "category": "desire", "loop_type": "desire_impulse_loop", "trigger_emotion": "desire",
        "break_principle": "The escalation point is always before, not during",
        "description": "Desire → habituation → escalation → loss of control → shame → desire.",
        "chain": ["desire", "habituation", "escalation", "loss_of_control", "shame"],
        "edges": [
            ("desire", "CAUSES", "habituation"), ("habituation", "LEADS_TO", "escalation"),
            ("escalation", "LEADS_TO", "loss_of_control"),
            ("loss_of_control", "LEADS_TO", "shame"), ("shame", "REINFORCES", "desire"),
        ],
        "break_edges": [("principle_early_intervention", "BREAKS", "escalation")],
        "formation_dims": {"emotional_stability": "-", "truth_alignment": "-", "resilience": "-"},
    },
    {   # D38
        "id": "D38_desire_discipline_avoidance_chaos", "label": "Desire → Avoidance of Discipline → Chaos Loop",
        "category": "desire", "loop_type": "desire_impulse_loop", "trigger_emotion": "desire",
        "break_principle": "Small consistent structure reduces chaos without requiring willpower",
        "description": "Desire for comfort avoids discipline → accumulated chaos → crisis → desire for relief.",
        "chain": ["desire", "discipline_avoidance", "accumulated_chaos", "crisis"],
        "edges": [
            ("desire", "CAUSES", "discipline_avoidance"),
            ("discipline_avoidance", "LEADS_TO", "accumulated_chaos"),
            ("accumulated_chaos", "LEADS_TO", "crisis"), ("crisis", "REINFORCES", "desire"),
        ],
        "break_edges": [("principle_small_consistent_structure", "BREAKS", "discipline_avoidance")],
        "formation_dims": {"resilience": "-", "emotional_stability": "-", "truth_alignment": "-"},
    },

    # ══════════════════════════════════════════════════════════
    # CATEGORY E — RELATIONAL LOOPS (39–44)
    # ══════════════════════════════════════════════════════════
    {   # E39
        "id": "E39_loneliness_attachment_instability", "label": "Loneliness → Attachment → Instability Loop",
        "category": "relational", "loop_type": "shame_avoidance_loop", "trigger_emotion": "loneliness",
        "break_principle": "Healthy presence, not anxious possession",
        "description": "Loneliness → urgent attachment → relational instability → deeper loneliness.",
        "chain": ["loneliness", "urgent_attachment", "relational_instability", "deeper_loneliness"],
        "edges": [
            ("loneliness", "CAUSES", "urgent_attachment"),
            ("urgent_attachment", "LEADS_TO", "relational_instability"),
            ("relational_instability", "LEADS_TO", "deeper_loneliness"),
            ("deeper_loneliness", "REINFORCES", "loneliness"),
        ],
        "break_edges": [("principle_healthy_presence", "BREAKS", "urgent_attachment")],
        "formation_dims": {"relational_health": "-", "emotional_stability": "-"},
    },
    {   # E40
        "id": "E40_trust_betrayal_withdrawal", "label": "Trust → Betrayal Sensitivity → Withdrawal Loop",
        "category": "relational", "loop_type": "shame_avoidance_loop", "trigger_emotion": "fear",
        "break_principle": "Distinguish past betrayal from present reality",
        "description": "Past betrayal → hypervigilance → withdrawal → isolation → increased sensitivity.",
        "chain": ["past_betrayal", "hypervigilance", "withdrawal", "isolation", "sensitivity_increase"],
        "edges": [
            ("past_betrayal", "CAUSES", "hypervigilance"),
            ("hypervigilance", "LEADS_TO", "withdrawal"),
            ("withdrawal", "LEADS_TO", "isolation"),
            ("isolation", "LEADS_TO", "sensitivity_increase"),
            ("sensitivity_increase", "REINFORCES", "hypervigilance"),
        ],
        "break_edges": [("principle_past_present_distinction", "BREAKS", "hypervigilance")],
        "formation_dims": {"relational_health": "-", "fear_tendency": "+", "resilience": "-"},
    },
    {   # E41
        "id": "E41_conflict_avoidance_accumulated_breakdown", "label": "Conflict Avoidance → Accumulated Breakdown Loop",
        "category": "relational", "loop_type": "shame_avoidance_loop", "trigger_emotion": "fear",
        "break_principle": "Small honest conversation prevents large relational collapse",
        "description": "Conflict avoidance → unresolved issues → accumulated tension → breakdown.",
        "chain": ["conflict_avoidance", "unresolved_issues", "accumulated_tension", "breakdown"],
        "edges": [
            ("conflict_avoidance", "CAUSES", "unresolved_issues"),
            ("unresolved_issues", "LEADS_TO", "accumulated_tension"),
            ("accumulated_tension", "LEADS_TO", "breakdown"),
            ("breakdown", "REINFORCES", "conflict_avoidance"),
        ],
        "break_edges": [("principle_early_honest_conversation", "BREAKS", "conflict_avoidance")],
        "formation_dims": {"relational_health": "-", "truth_alignment": "-", "fear_tendency": "+"},
    },
    {   # E42
        "id": "E42_love_overgiving_burnout", "label": "Love → Overgiving → Burnout Loop",
        "category": "relational", "loop_type": "shame_avoidance_loop", "trigger_emotion": "love",
        "break_principle": "Sustainable love requires self-care as foundation",
        "description": "Genuine love distorts into overgiving → self-neglect → burnout → guilt → overgiving.",
        "chain": ["love", "overgiving", "self_neglect", "burnout", "guilt"],
        "edges": [
            ("love", "CAUSES", "overgiving"), ("overgiving", "LEADS_TO", "self_neglect"),
            ("self_neglect", "LEADS_TO", "burnout"), ("burnout", "LEADS_TO", "guilt"),
            ("guilt", "REINFORCES", "love"),
        ],
        "break_edges": [("principle_self_care_foundation", "BREAKS", "overgiving")],
        "formation_dims": {"relational_health": "-", "resilience": "-", "emotional_stability": "-"},
    },
    {   # E43
        "id": "E43_missing_boundaries_exploitation_resentment", "label": "Missing Boundaries → Exploitation → Resentment Loop",
        "category": "relational", "loop_type": "shame_avoidance_loop", "trigger_emotion": "fear",
        "break_principle": "Boundaries protect relationships; they do not end them",
        "description": "Missing boundaries → exploitation → resentment → relational rupture.",
        "chain": ["missing_boundaries", "exploitation", "resentment", "relational_rupture"],
        "edges": [
            ("missing_boundaries", "CAUSES", "exploitation"),
            ("exploitation", "LEADS_TO", "resentment"),
            ("resentment", "LEADS_TO", "relational_rupture"),
            ("relational_rupture", "REINFORCES", "missing_boundaries"),
        ],
        "break_edges": [("principle_boundary_setting", "BREAKS", "missing_boundaries")],
        "formation_dims": {"relational_health": "-", "truth_alignment": "-"},
    },
    {   # E44
        "id": "E44_miscommunication_assumption_conflict", "label": "Miscommunication → Assumption → Conflict Loop",
        "category": "relational", "loop_type": "shame_avoidance_loop", "trigger_emotion": "confusion",
        "break_principle": "Ask before assuming — curiosity replaces projection",
        "description": "Miscommunication → unverified assumption → conflict → damaged communication.",
        "chain": ["miscommunication", "unverified_assumption", "conflict", "damaged_communication"],
        "edges": [
            ("miscommunication", "CAUSES", "unverified_assumption"),
            ("unverified_assumption", "LEADS_TO", "conflict"),
            ("conflict", "LEADS_TO", "damaged_communication"),
            ("damaged_communication", "REINFORCES", "miscommunication"),
        ],
        "break_edges": [("principle_curiosity_not_assumption", "BREAKS", "unverified_assumption")],
        "formation_dims": {"relational_health": "-", "emotional_stability": "-"},
    },

    # ══════════════════════════════════════════════════════════
    # CATEGORY F — SPIRITUAL / MEANING LOOPS (45–50)
    # ══════════════════════════════════════════════════════════
    {   # F45
        "id": "F45_spiritual_dryness_performance_exhaustion", "label": "Spiritual Dryness → Performance → Exhaustion Loop",
        "category": "spiritual", "loop_type": "truth_stability_loop", "trigger_emotion": "spiritual_dryness",
        "break_principle": "Inward orientation over outward performance",
        "description": "Spiritual dryness → compensatory performance → exhaustion → deeper dryness.",
        "chain": ["spiritual_dryness", "compensatory_performance", "exhaustion", "deeper_dryness"],
        "edges": [
            ("spiritual_dryness", "CAUSES", "compensatory_performance"),
            ("compensatory_performance", "LEADS_TO", "exhaustion"),
            ("exhaustion", "LEADS_TO", "deeper_dryness"),
            ("deeper_dryness", "REINFORCES", "spiritual_dryness"),
        ],
        "break_edges": [("principle_inner_orientation", "BREAKS", "compensatory_performance")],
        "formation_dims": {"spiritual_clarity": "-", "emotional_stability": "-", "pride_tendency": "+"},
    },
    {   # F46
        "id": "F46_meaning_loss_distraction_emptiness", "label": "Meaning Loss → Distraction → Emptiness Loop",
        "category": "spiritual", "loop_type": "truth_stability_loop", "trigger_emotion": "confusion",
        "break_principle": "Stillness before distraction reveals the deeper question",
        "description": "Meaning loss → distraction → meaning work avoided → emptiness → meaning loss.",
        "chain": ["meaning_loss", "distraction", "meaning_work_avoided", "emptiness"],
        "edges": [
            ("meaning_loss", "CAUSES", "distraction"),
            ("distraction", "LEADS_TO", "meaning_work_avoided"),
            ("meaning_work_avoided", "LEADS_TO", "emptiness"),
            ("emptiness", "REINFORCES", "meaning_loss"),
        ],
        "break_edges": [("principle_stillness_before_distraction", "BREAKS", "distraction")],
        "formation_dims": {"spiritual_clarity": "-", "truth_alignment": "-"},
    },
    {   # F47
        "id": "F47_truth_encounter_resistance_confusion", "label": "Truth Encounter → Resistance → Confusion Loop",
        "category": "spiritual", "loop_type": "truth_stability_loop", "trigger_emotion": "confusion",
        "break_principle": "Confusion is often resistance — what is being protected?",
        "description": "Truth encounter → resistance → confusion → delayed integration → reinforced resistance.",
        "chain": ["truth_encounter", "resistance", "confusion", "delayed_integration"],
        "edges": [
            ("truth_encounter", "CAUSES", "resistance"),
            ("resistance", "LEADS_TO", "confusion"),
            ("confusion", "LEADS_TO", "delayed_integration"),
            ("delayed_integration", "REINFORCES", "resistance"),
        ],
        "break_edges": [("principle_name_the_resistance", "BREAKS", "resistance")],
        "formation_dims": {"truth_alignment": "-", "spiritual_clarity": "-", "humility": "-"},
    },
    {   # F48
        "id": "F48_conviction_guilt_avoidance", "label": "Conviction → Guilt → Avoidance Loop",
        "category": "spiritual", "loop_type": "shame_avoidance_loop", "trigger_emotion": "guilt",
        "break_principle": "Guilt that leads to avoidance is not repentance — it continues the loop",
        "description": "Conviction → guilt → avoidance of source → unresolved conviction → reinforced guilt.",
        "chain": ["conviction", "guilt", "avoidance_of_source", "unresolved_conviction"],
        "edges": [
            ("conviction", "CAUSES", "guilt"),
            ("guilt", "LEADS_TO", "avoidance_of_source"),
            ("avoidance_of_source", "LEADS_TO", "unresolved_conviction"),
            ("unresolved_conviction", "REINFORCES", "conviction"),
        ],
        "break_edges": [("principle_repentance_not_guilt_spiral", "BREAKS", "guilt")],
        "formation_dims": {"truth_alignment": "-", "spiritual_clarity": "-"},
    },
    {   # F49
        "id": "F49_rest_ignored_burnout_spiritual_fog", "label": "Rest Ignored → Burnout → Spiritual Fog Loop",
        "category": "spiritual", "loop_type": "fear_control_loop", "trigger_emotion": "drivenness",
        "break_principle": "Rest is a spiritual act, not a reward for productivity",
        "description": (
            "Ignoring the need for rest (driven by fear or pride) leads to burnout. "
            "Burnout produces spiritual fog — disconnection from clarity and values — "
            "which intensifies the driven, restless response."
        ),
        "chain": ["rest_ignored", "depletion", "burnout", "spiritual_fog", "driven_response"],
        "edges": [
            ("rest_ignored", "LEADS_TO", "depletion"),
            ("depletion", "LEADS_TO", "burnout"),
            ("burnout", "LEADS_TO", "spiritual_fog"),
            ("spiritual_fog", "LEADS_TO", "driven_response"),
            ("driven_response", "REINFORCES", "rest_ignored"),
        ],
        "break_edges": [("principle_rest_as_spiritual_act", "BREAKS", "rest_ignored")],
        "formation_dims": {"spiritual_clarity": "-", "resilience": "-", "emotional_stability": "-"},
    },
    {   # F50
        "id": "F50_reflection_avoidance_pattern_repetition", "label": "Reflection Avoidance → Pattern Repetition Loop",
        "category": "spiritual", "loop_type": "shame_avoidance_loop", "trigger_emotion": "discomfort",
        "break_principle": "Reflection is the only mechanism that interrupts unconscious repetition",
        "description": (
            "Avoidance of self-reflection (because it is uncomfortable) prevents the "
            "pattern recognition that would allow change. The same loops repeat "
            "with increasing entrenchment."
        ),
        "chain": ["reflection_avoidance", "pattern_repetition", "increased_entrenchment", "discomfort"],
        "edges": [
            ("reflection_avoidance", "LEADS_TO", "pattern_repetition"),
            ("pattern_repetition", "LEADS_TO", "increased_entrenchment"),
            ("increased_entrenchment", "LEADS_TO", "discomfort"),
            ("discomfort", "REINFORCES", "reflection_avoidance"),
        ],
        "break_edges": [("principle_reflection_as_interruption", "BREAKS", "reflection_avoidance")],
        "formation_dims": {"truth_alignment": "-", "spiritual_clarity": "-", "humility": "-"},
    },

    # ══════════════════════════════════════════════════════════
    # HEALTHY COUNTER-LOOPS (reference patterns for intervention)
    # ══════════════════════════════════════════════════════════
    {
        "id": "H51_truth_reflection_stability", "label": "Truth-Facing → Reflection → Stability Loop (Healthy)",
        "category": "growth", "loop_type": "truth_stability_loop", "trigger_emotion": "clarity",
        "break_principle": "N/A — this is the target state",
        "description": "Truth-facing → reflection → stability → clarity → more truth-facing. Virtuous cycle.",
        "chain": ["truth_facing", "reflection", "stability", "clarity"],
        "edges": [
            ("truth_facing", "LEADS_TO", "reflection"), ("reflection", "LEADS_TO", "stability"),
            ("stability", "LEADS_TO", "clarity"), ("clarity", "REINFORCES", "truth_facing"),
        ],
        "break_edges": [],
        "formation_dims": {"truth_alignment": "+", "spiritual_clarity": "+", "humility": "+", "resilience": "+"},
    },
    {
        "id": "H52_humility_learning_resilience", "label": "Humility → Learning → Resilience Loop (Healthy)",
        "category": "growth", "loop_type": "truth_stability_loop", "trigger_emotion": "openness",
        "break_principle": "N/A — this is the target state",
        "description": "Humility opens learning pathways → resilience from adversity → wisdom → deeper humility.",
        "chain": ["humility", "learning_openness", "resilience", "wisdom"],
        "edges": [
            ("humility", "LEADS_TO", "learning_openness"),
            ("learning_openness", "LEADS_TO", "resilience"),
            ("resilience", "LEADS_TO", "wisdom"), ("wisdom", "REINFORCES", "humility"),
        ],
        "break_edges": [],
        "formation_dims": {"humility": "+", "resilience": "+", "truth_alignment": "+"},
    },
]
