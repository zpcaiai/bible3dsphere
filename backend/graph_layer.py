#!/usr/bin/env python3
"""
SFDS Graph Layer — PostgreSQL structural reasoning module (V2).

Answers: WHY does this pattern keep happening?

Provides:
- PostgreSQL connection management via PostgresGraphModule
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
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from mvfe.core.postgres_graph import PostgresGraphModule

logger = logging.getLogger(__name__)

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
# ──────────────────────────────────────────────────────────────────────────────

KNOWN_PATTERNS: List[Dict[str, Any]] = [
    # ── 恐惧类 (FEAR CLUSTER) ────────────────────────────────────────────────────────
    {
        "id": "fear_control_burnout",
        "category": "fear",
        "chain": ["fear", "control_impulse", "overwork", "burnout", "spiritual_dryness"],
        "label": "恐惧 → 控制 → 过度工作 → 枯竭 → 灵性干渴",
        "intervention": {
            "node": "control_impulse",
            "suggestion": "在控制冲动转化为行动前察觉它。放下这种控制感会是什么感觉？",
            "scripture": "马太福音 6:25-27",
        },
        "reflective_question": "如果你停止尝试控制这件事，你最担心会发生什么？",
    },
    {
        "id": "fear_avoidance_stagnation",
        "category": "fear",
        "chain": ["fear", "avoidance", "stagnation", "regret", "deeper_fear"],
        "label": "恐惧 → 回避 → 停滞 → 后悔 → 更深的恐惧（循环）",
        "intervention": {
            "node": "avoidance",
            "suggestion": "回避往往会随时间放大恐惧。面对所恐惧的事，你能迈出的最小一步是什么？",
            "scripture": "提摩太后书 1:7",
        },
        "reflective_question": "如果恐惧不是考量因素，在这种情况下你会怎么做？",
    },
    {
        "id": "fear_people_pleasing_resentment",
        "category": "fear",
        "chain": ["fear_of_rejection", "people_pleasing", "self_suppression", "resentment", "isolation"],
        "label": "拒绝恐惧 → 讨好行为 → 自我压抑 → 苦毒怨恨 → 孤立",
        "intervention": {
            "node": "people_pleasing",
            "suggestion": "当你想说‘不’却说‘好’时，每一次微小的妥协都会侵蚀你的正直。此时什么边界需要被确立？",
            "scripture": "加拉太书 1:10",
        },
        "reflective_question": "你最想获得谁的认可？为什么这种认可对你如此必要？",
    },
    {
        "id": "fear_urgency_poor_decision",
        "category": "fear",
        "chain": ["fear", "urgency_feeling", "rushed_decision", "poor_outcome", "anxiety_spike"],
        "label": "恐惧 → 紧迫感 → 仓促决策 → 糟糕结果 → 焦虑增加",
        "intervention": {
            "node": "urgency_feeling",
            "suggestion": "紧迫感可能只是一种感觉，而非事实。这个决策真的有时效性，还是仅仅感觉如此？",
            "scripture": "以赛亚书 28:16",
        },
        "reflective_question": "如果你在决定前等待 48 小时，会发生什么？",
    },

    # ── 骄傲类 (PRIDE CLUSTER) ────────────────────────────────────────────────────────
    {
        "id": "pride_comparison_anxiety",
        "category": "pride",
        "chain": ["pride", "comparison", "anxiety", "performance_addiction", "emptiness"],
        "label": "骄傲 → 比较 → 焦虑 → 表现成瘾 → 空虚",
        "intervention": {
            "node": "comparison",
            "suggestion": "比较的衡量标准往往是错误的。当没有人在看时，什么对你真正重要？",
            "scripture": "加拉太书 6:4",
        },
        "reflective_question": "如果没人知道这个决策的结果，你还会做出同样的选择吗？",
    },
    {
        "id": "pride_self_sufficiency_isolation",
        "category": "pride",
        "chain": ["pride", "self_sufficiency", "refusing_help", "isolation", "crisis"],
        "label": "骄傲 → 自我中心 → 拒绝帮助 → 孤立 → 危机",
        "intervention": {
            "node": "self_sufficiency",
            "suggestion": "寻求帮助不是软弱，而是智慧。谁可以受邀参与到这个决策中？",
            "scripture": "箴言 11:2",
        },
        "reflective_question": "承认你需要在这里获得支持，对你来说代价是什么？",
    },
    {
        "id": "pride_defensiveness_conflict",
        "category": "pride",
        "chain": ["pride", "defensiveness", "escalating_conflict", "broken_relationship", "loneliness"],
        "label": "骄傲 → 防卫心理 → 冲突升级 → 关系破裂 → 孤独",
        "intervention": {
            "node": "defensiveness",
            "suggestion": "防卫往往信号着深处的伤口。此时受威胁的是真理，还是你的形象？",
            "scripture": "箴言 13:10",
        },
        "reflective_question": "关于这个情况，你最抗拒听到的真理是什么？",
    },
    {
        "id": "ambition_shortcuts_integrity_loss",
        "category": "pride",
        "chain": ["ambition", "impatience", "shortcuts", "integrity_erosion", "shame"],
        "label": "野心 → 焦躁 → 捷径 → 正直侵蚀 → 羞耻",
        "intervention": {
            "node": "impatience",
            "suggestion": "建立在妥协之上的快速增长往往根基脆弱。什么样的速度在此刻是可持续的？",
            "scripture": "箴言 21:5",
        },
        "reflective_question": "你的匆忙是因为呼召，还是因为与他人的比较？",
    },

    # ── 羞耻类 (SHAME CLUSTER) ────────────────────────────────────────────────────────
    {
        "id": "shame_avoidance_procrastination",
        "category": "shame",
        "chain": ["shame", "avoidance", "procrastination", "accumulating_pressure", "anxiety_loop"],
        "label": "羞耻 → 回避 → 拖延 → 压力累积 → 焦虑循环",
        "intervention": {
            "node": "avoidance",
            "suggestion": "被回避的事物会在黑暗中滋长。什么是你一直没去做的那件事？",
            "scripture": "约翰一书 1:9",
        },
        "reflective_question": "你在回避什么？你认为这反映了关于你的什么信息？",
    },
    {
        "id": "shame_self_punishment_paralysis",
        "category": "shame",
        "chain": ["shame", "self_condemnation", "worthlessness", "paralysis", "missed_calling"],
        "label": "羞耻 → 自我定罪 → 无价值感 → 瘫痪停滞 → 错失呼召",
        "intervention": {
            "node": "self_condemnation",
            "suggestion": "内疚指向行为，羞耻攻击人格。此时运作的是哪一个？",
            "scripture": "罗马书 8:1",
        },
        "reflective_question": "如果有位密友犯了你正在定罪自己的错误，你会如何对他说话？",
    },
    {
        "id": "shame_overcompensation_exhaustion",
        "category": "shame",
        "chain": ["shame", "overcompensation", "hyperactivity", "exhaustion", "shame_spike"],
        "label": "羞耻 → 过度补偿 → 过度活跃 → 枯竭 → 羞耻高峰（循环）",
        "intervention": {
            "node": "overcompensation",
            "suggestion": "通过做更多事来获得价值感是不可持续的。价值并不来源于产出。",
            "scripture": "以弗所书 2:8-9",
        },
        "reflective_question": "如果你已经被完全接纳，你会停止做什么？",
    },

    # ── 欲望/依恋类 (DESIRE / ATTACHMENT CLUSTER) ──────────────────────────────────────────
    {
        "id": "loneliness_attachment_impulse",
        "category": "desire",
        "chain": ["loneliness", "attachment_seeking", "impulsive_bonding", "regret", "deeper_loneliness"],
        "label": "孤独 → 寻求依恋 → 冲动联结 → 后悔 → 更深的孤独",
        "intervention": {
            "node": "attachment_seeking",
            "suggestion": "孤独是真实且正当的。问题在于，这个行动是在解决根源，还是仅仅暂时麻痹它？",
            "scripture": "诗篇 62:1",
        },
        "reflective_question": "这个决策试图满足你什么样的深层需求？",
    },
    {
        "id": "desire_gratification_debt",
        "category": "desire",
        "chain": ["desire", "immediate_gratification", "overpromising", "debt_of_consequence", "regret"],
        "label": "欲望 → 即时满足 → 过度承诺 → 后果债 → 后悔",
        "intervention": {
            "node": "immediate_gratification",
            "suggestion": "短期缓解往往推迟了长期代价。这个决策在两年后看起来会是怎样的？",
            "scripture": "希伯来书 11:25",
        },
        "reflective_question": "为了此刻想要的东西，你愿意放弃什么？",
    },
    {
        "id": "escapism_numbing_drift",
        "category": "desire",
        "chain": ["pain", "escapism", "numbing_behavior", "spiritual_drift", "emptiness"],
        "label": "痛苦 → 逃避主义 → 麻木行为 → 灵性漂移 → 空虚",
        "intervention": {
            "node": "numbing_behavior",
            "suggestion": "麻木推迟了痛苦，但也推迟了医治。什么痛苦正需要被倾听？",
            "scripture": "诗篇 34:18",
        },
        "reflective_question": "你在尝试不去感受什么？如果你坐下来面对它会发生什么？",
    },

    # ── 关系类 (RELATIONAL CLUSTER) ───────────────────────────────────────────────────
    {
        "id": "unforgiveness_bitterness_isolation",
        "category": "relational",
        "chain": ["hurt", "unforgiveness", "bitterness", "relational_withdrawal", "spiritual_hardening"],
        "label": "受伤 → 不饶恕 → 苦毒 → 关系退缩 → 灵性硬化",
        "intervention": {
            "node": "unforgiveness",
            "suggestion": "饶恕不是开脱伤害，而是释放不再被伤害所控制的权利。",
            "scripture": "马太福音 18:21-22",
        },
        "reflective_question": "你正在紧抓谁或什么，而这正让你付出平安的代价？",
    },
    {
        "id": "codependency_enabling_resentment",
        "category": "relational",
        "chain": ["fear_of_abandonment", "codependency", "enabling", "resentment", "relational_collapse"],
        "label": "遗弃恐惧 → 相互依赖 → 纵容行为 → 苦毒怨恨 → 关系崩塌",
        "intervention": {
            "node": "codependency",
            "suggestion": "真爱包含适当的边界。你正在承担谁的本不属于你的责任？",
            "scripture": "加拉太书 6:2-5",
        },
        "reflective_question": "在这段关系中，哪里你是因为恐惧而非真正的关怀在做事？",
    },
    {
        "id": "comparison_envy_sabotage",
        "category": "relational",
        "chain": ["comparison", "envy", "passive_aggression", "relationship_damage", "guilt"],
        "label": "比较 → 嫉妒 → 隐性攻击 → 关系受损 → 内疚",
        "intervention": {
            "node": "envy",
            "suggestion": "嫉妒信号着未被满足的愿望——它可以是一种信息，而非敌人。",
            "scripture": "雅各书 3:14-16",
        },
        "reflective_question": "你在别人身上看到了什么你希望自己也能拥有的特质？",
    },

    # ── 灵性形成类 (SPIRITUAL FORMATION CLUSTER) ──────────────────────────────────────────
    {
        "id": "spiritual_dryness_duty_exhaustion",
        "category": "spiritual",
        "chain": ["spiritual_dryness", "duty_driven_service", "joyless_obedience", "exhaustion", "deeper_dryness"],
        "label": "灵性干渴 → 责任驱动的服事 → 无乐的顺服 → 枯竭 → 更深的干渴",
        "intervention": {
            "node": "duty_driven_service",
            "suggestion": "从匮乏中服事是不可持续的。安息不是逃避，而是形成过程的一部分。",
            "scripture": "马可福音 6:31",
        },
        "reflective_question": "你服事是因为你想，还是因为你觉得必须这样做？",
    },
    {
        "id": "calling_fear_inaction",
        "category": "spiritual",
        "chain": ["sense_of_calling", "fear_of_inadequacy", "delay", "missed_seasons", "deeper_regret"],
        "label": "呼召感 → 乏力感 → 拖延 → 错过时机 → 后悔",
        "intervention": {
            "node": "fear_of_inadequacy",
            "suggestion": "不足感是呼召的特征，而非取消资格的理由。圣经中谁在说‘是’之前是完全预备好的？",
            "scripture": "出埃及记 4:10-12",
        },
        "reflective_question": "如果你相信你的不足并非终局，你会尝试什么？",
    },
    {
        "id": "truth_humility_peace",
        "category": "growth",
        "chain": ["truth_exposure", "humility", "peace", "clarity", "fruit"],
        "label": "真理显露 → 谦卑 → 平安 → 清晰 → 果子",
        "intervention": {
            "node": "truth_exposure",
            "suggestion": "倾向于面对不舒服的真理。谦卑不是自我贬低，而是对现实的精准把握。",
            "scripture": "约翰福音 8:32",
        },
        "reflective_question": "关于这个情况，你一直不愿完全面对的真理是什么？",
    },
    {
        "id": "suffering_patience_character",
        "category": "growth",
        "chain": ["suffering", "endurance", "character_formation", "hope", "stability"],
        "label": "受苦 → 忍耐 → 性情形成 → 盼望 → 稳定",
        "intervention": {
            "node": "endurance",
            "suggestion": "以信心面对苦难会产生形成作用。这个季节正在你里面塑造什么？",
            "scripture": "罗马书 5:3-5",
        },
        "reflective_question": "这种困难正在你里面塑造什么安逸环境无法塑造的特质？",
    },
    {
        "id": "gratitude_peace_generosity",
        "category": "growth",
        "chain": ["gratitude", "contentment", "peace", "generosity", "flourishing"],
        "label": "感恩 → 知足 → 平安 → 慷慨 → 繁盛",
        "intervention": {
            "node": "gratitude",
            "suggestion": "感恩是一种操练，而不仅仅是一种感觉。此时此刻，有什么你尚未命名的真实而美好的事物？",
            "scripture": "腓立比书 4:6-7",
        },
        "reflective_question": "如果你从感激而非匮乏的姿态开始，情况会有什么转变？",
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
# ──────────────────────────────────────────────────────────────────────────────

PATTERN_SUBGRAPHS: List[PatternSubgraph] = [

    # ── 模式 1: 恐惧 → 控制 → 枯竭 循环 ─────────────────────────────
    PatternSubgraph(
        pattern_id  = "fear_control_burnout",
        label       = "恐惧 → 控制 → 枯竭 循环",
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
        reflective_question    = "如果你停止尝试控制这件事，你最担心会发生什么？",
        scripture              = "马太福音 6:25-27",
    ),

    # ── 模式 2: 骄傲 → 比较 → 焦虑 循环 ─────────────────────────
    PatternSubgraph(
        pattern_id  = "pride_comparison_anxiety",
        label       = "骄傲 → 比较 → 焦虑 循环",
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
        reflective_question    = "如果没人知道这个决策的结果，你还会做出同样的选择吗？",
        scripture              = "加拉太书 6:4",
    ),

    # ── 模式 3: 羞耻 → 回避 → 延迟 循环 ────────────────────────────
    PatternSubgraph(
        pattern_id  = "shame_avoidance_procrastination",
        label       = "羞耻 → 回避 → 延迟 循环",
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
        reflective_question    = "你在回避什么？你认为这反映了关于你的什么信息？",
        scripture              = "约翰一书 1:9",
    ),

    # ── 模式 4: 孤独 → 依恋 → 冲动决策 循环 ─────────
    PatternSubgraph(
        pattern_id  = "loneliness_attachment_impulse",
        label       = "孤独 → 依恋 → 冲动决策 循环",
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
        reflective_question    = "这个决策试图满足你什么样的深层需求？",
        scripture              = "诗篇 62:1",
    ),

    # ── 模式 5: 成功 → 骄傲膨胀 → 崩溃 ─────────────────────
    PatternSubgraph(
        pattern_id  = "pride_inflation_collapse",
        label       = "成功 → 骄傲膨胀 → 过度自信 → 纠正 → 羞耻崩溃",
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
        reflective_question    = "你做出这个决策是基于真正的清晰，还是仅仅因为赢了一次后的过度自信？",
        scripture              = "箴言 16:18",
    ),

    # ── 模式 6: 灵性干渴 → 补偿 → 过度活跃 循环 ──────
    PatternSubgraph(
        pattern_id  = "spiritual_dryness_compensation",
        label       = "灵性干渴 → 补偿 → 过度活跃 → 更深干渴 循环",
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
        reflective_question    = "你服事是因为你想，还是因为你觉得必须这样做？",
        scripture              = "马可福音 6:31",
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
# Graph Service — structural reasoning + write-back
# ──────────────────────────────────────────────────────────────────────────────

class GraphService:
    """
    V2 Graph Service — structural pattern reasoning + PostgreSQL write-back.

    Pipeline role: WHY does this pattern keep appearing?

    Works in two modes:
    - Live mode: queries PostgreSQL for user-specific historical paths.
    - Offline mode: static rule-based pattern matching (no DB required).

    Design principle: output is always framed as *possibility*, never *verdict*.
    The system is a mirror, not a judge.
    """

    def __init__(self, db_pool: Optional[Any] = None):
        self._pg = PostgresGraphModule(db_pool)

    @property
    def store(self) -> PostgresGraphModule:
        """The unified PostgreSQL graph store used by APIs and GraphRAG."""
        return self._pg

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
        Main entry point.  Returns a GraphInsight regardless of DB availability.

        Args:
            user_id:              UUID string — used for live lookups.
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
        if self._pg.enabled:
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
        belief: Optional[str] = None,
    ) -> None:
        """
        Persist this decision event into PostgreSQL as a graph update.
        Called at the end of the pipeline after guidance is generated.
        """
        if not self._pg.enabled:
            return
        try:
            if hasattr(self._pg, "persist_formation_chain"):
                persisted = self._pg.persist_formation_chain(
                    user_id=user_id,
                    event_id=decision_id,
                    emotion_name=dominant_emotion,
                    desire_name=dominant_motive,
                    behavior_name=behavior_type,
                    decision_category=decision_category,
                    outcome_name=outcome,
                    belief_name=belief,
                    matched_patterns=matched_pattern_ids or [],
                )
                if not persisted:
                    logger.warning("[graph] atomic formation write_back was not persisted")
                return

            # Compatibility path for injected stores used by extensions/tests.
            e_id = self._pg._upsert_node(user_id, "Emotion", dominant_emotion, {
                "category": decision_category, "last_decision_id": decision_id,
                "evidence_status": "observed",
            })
            d_id = self._pg._upsert_node(user_id, "Desire", dominant_motive, {
                "last_decision_id": decision_id, "evidence_status": "inferred",
            })
            b_id = self._pg._upsert_node(user_id, "Behavior", behavior_type, {
                "last_decision_id": decision_id, "evidence_status": "observed",
            })

            self._pg._upsert_edge(
                user_id, e_id, d_id, "CAUSES", properties={"evidence_status": "inferred"}
            )
            self._pg._upsert_edge(
                user_id, d_id, b_id, "DRIVES", properties={"evidence_status": "observed"}
            )

            if outcome:
                belief_name = belief or f"reflection:{dominant_motive}"
                o_id = self._pg._upsert_node(user_id, "Outcome", outcome, {
                    "last_decision_id": decision_id, "evidence_status": "reviewed",
                })
                belief_id = self._pg._upsert_node(user_id, "Belief", belief_name, {
                    "last_decision_id": decision_id,
                    "evidence_status": "user_reviewed" if belief else "hypothesis",
                })
                self._pg._upsert_edge(
                    user_id, b_id, o_id, "LEADS_TO", properties={"evidence_status": "reviewed"}
                )
                self._pg._upsert_edge(
                    user_id, o_id, belief_id, "REINFORCES",
                    properties={"evidence_status": "reviewed" if belief else "inferred"},
                )
                self._pg._upsert_edge(
                    user_id, belief_id, e_id, "AMPLIFIES",
                    weight=0.7 if belief else 0.4,
                    properties={"evidence_status": "reviewed" if belief else "inferred"},
                )

            if matched_pattern_ids:
                user_node = self._pg._upsert_node(user_id, "UserState", user_id, {})
                for pid in matched_pattern_ids:
                    p_id = self._pg._upsert_node(user_id, "PatternMatch", pid, {"decision_id": decision_id})
                    self._pg._upsert_edge(user_id, user_node, p_id, "MATCHED_PATTERN")

            self._pg.record_event(
                user_id, decision_id,
                emotion_name=dominant_emotion,
                desire_name=dominant_motive,
                behavior_name=behavior_type,
                outcome_name=outcome,
                belief_name=belief,
                matched_patterns=matched_pattern_ids or [],
                properties={"decision_category": decision_category},
            )
        except Exception as exc:
            logger.warning("[graph] write_back failed: %s", exc)

    def complete_formation_event(
        self,
        user_id: str,
        decision_id: str,
        outcome: str,
        belief: Optional[str] = None,
    ) -> bool:
        """Complete a previously observed chain after the user's own review."""
        event = self._pg.get_event(user_id, decision_id)
        if not event:
            return False
        self.write_back(
            user_id=user_id,
            decision_id=decision_id,
            dominant_emotion=event.get("emotion_name") or "unknown",
            dominant_motive=event.get("desire_name") or "unknown",
            decision_category=(event.get("properties") or {}).get("decision_category", "other"),
            behavior_type=event.get("behavior_name") or "unknown",
            matched_pattern_ids=event.get("matched_patterns") or [],
            outcome=outcome,
            belief=belief,
        )
        return True

    def get_user_pattern_history(
        self, user_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Return the patterns this user has most frequently matched."""
        if not self._pg.enabled:
            return []
        conn = self._pg._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT p.node_name AS pattern_id, e.traversal_count AS count, e.updated_at AS last_seen
                    FROM mvfe_graph_nodes p
                    JOIN mvfe_graph_edges e ON p.id = e.target_id
                        AND e.edge_type = 'MATCHED_PATTERN' AND e.user_id = p.user_id
                    WHERE p.user_id = %s AND p.node_type = 'PatternMatch'
                    ORDER BY e.traversal_count DESC, e.updated_at DESC
                    LIMIT %s
                    """,
                    (user_id, limit)
                )
                rows = cur.fetchall()
                return [
                    {"pattern_id": r[0], "count": r[1], "last_seen": r[2]}
                    for r in rows
                ]
        except Exception as e:
            logger.warning(f"[graph] get_user_pattern_history failed: {e}")
            return []
        finally:
            self._pg._pool.putconn(conn)

    # ── Graph Intelligence Queries (v2.1 use cases) ───────────────────────────

    def detect_loop(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Use case 1 — "Which loop is the user currently inside?"

        Returns list of {pattern_id, loop_description, confidence}.
        """
        if not self._pg.enabled:
            return self._detect_loop_offline(user_id)

        loops = self._pg.detect_loops(user_id)
        if not loops:
            return self._detect_loop_offline(user_id)

        results = []
        for lp in loops:
            results.append({
                "motive": lp.get("desires", [""])[0] if lp.get("desires") else "",
                "behavior": lp["loop_anchor"],
                "outcome": lp.get("beliefs", [""])[0] if lp.get("beliefs") else "",
                "frequency": lp["loop_count"],
                "loop_description": f"Loop around {lp['loop_anchor']} (depth {lp['loop_depth']})",
                "note": "This pattern has appeared multiple times — it may indicate an active loop.",
            })
        return results

    def trace_root_cause(self, behavior_type: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Use case 2 — "What emotion originally triggered this behavior chain?"

        Traverses backwards from a BehaviorNode through MotiveNode to EmotionNode.

        Returns list of {emotion, motive, behavior, path_description}.
        """
        if not self._pg.enabled:
            return self._trace_root_offline(behavior_type)

        conn = self._pg._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT e_node.node_name as emotion, m_node.node_name as motive, b_node.node_name as behavior
                    FROM mvfe_graph_nodes b_node
                    JOIN mvfe_graph_edges m_b ON m_b.target_id = b_node.id
                        AND m_b.edge_type IN ('LEADS_TO', 'DRIVES')
                        AND m_b.user_id = b_node.user_id
                    JOIN mvfe_graph_nodes m_node ON m_node.id = m_b.source_id
                        AND m_node.node_type IN ('Motive', 'Desire')
                        AND m_node.user_id = b_node.user_id
                    JOIN mvfe_graph_edges e_m ON e_m.target_id = m_node.id
                        AND e_m.edge_type = 'CAUSES' AND e_m.user_id = b_node.user_id
                    JOIN mvfe_graph_nodes e_node ON e_node.id = e_m.source_id
                        AND e_node.node_type = 'Emotion' AND e_node.user_id = b_node.user_id
                    WHERE b_node.node_name = %s
                      AND (%s IS NULL OR b_node.user_id = %s)
                    LIMIT 5
                    """, (behavior_type, user_id, user_id)
                )
                rows = cur.fetchall()
                if not rows:
                    return self._trace_root_offline(behavior_type)
                return [
                    {
                        "root_emotion": r[0],
                        "motive": r[1],
                        "behavior": r[2],
                        "path_labels": [r[0], r[1], r[2]],
                        "path_description": f"{r[0]} → {r[1]} → {r[2]}",
                    } for r in rows
                ]
        except Exception as e:
            logger.warning(f"trace_root_cause failed: {e}")
            return self._trace_root_offline(behavior_type)
        finally:
            self._pg._pool.putconn(conn)

    def find_intervention_points(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Use case 3 — "Where can this loop be broken?"

        Identifies BehaviorNodes that have BREAKS edges from PrincipleNodes,
        intersected with the user's active behavior history.

        Returns list of {behavior, principle, intervention_text, scripture}.
        """
        if not self._pg.enabled:
            return self._find_interventions_offline(user_id)

        conn = self._pg._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT b.node_name as behavior,
                           p.node_name as principle_id,
                           p.properties->>'text' as principle_text,
                           p.properties->>'scripture' as scripture
                    FROM mvfe_graph_edges e
                    JOIN mvfe_graph_nodes p ON p.id = e.source_id AND p.node_type = 'Principle'
                    JOIN mvfe_graph_nodes b ON b.id = e.target_id AND b.node_type IN ('Behavior', 'Motive', 'Desire')
                    WHERE e.edge_type = 'BREAKS'
                      AND e.user_id = '__system__'
                      AND EXISTS (
                          SELECT 1 FROM mvfe_graph_nodes active
                          WHERE active.user_id = %s
                            AND active.node_type IN ('Behavior', 'Motive', 'Desire')
                            AND active.node_name = b.node_name
                      )
                    ORDER BY e.weight DESC, e.traversal_count DESC
                    LIMIT 6
                    """, (user_id,)
                )
                rows = cur.fetchall()
                if not rows:
                    return self._find_interventions_offline(user_id)
                return [
                    {
                        "behavior": r[0],
                        "principle_id": r[1],
                        "principle_text": r[2] or r[1],
                        "scripture": r[3] or "",
                        "break_description": f"Principle '{r[1]}' can interrupt the '{r[0]}' behavior.",
                    } for r in rows
                ]
        except Exception as e:
            logger.warning(f"find_intervention_points failed: {e}")
            return self._find_interventions_offline(user_id)
        finally:
            self._pg._pool.putconn(conn)

    def activate_principles(self, motive_type: str) -> List[Dict[str, Any]]:
        """
        Use case 4 — "Which spiritual truth breaks this pattern?"

        Finds PrincipleNodes that either INFLUENCES or BREAKS paths involving
        a given MotiveNode type.

        Returns list of {principle_id, principle_text, action_type, scripture}.
        """
        if not self._pg.enabled:
            return self._activate_principles_offline(motive_type)

        conn = self._pg._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT p.node_name as principle_id, p.properties->>'text' as principle_text, e.edge_type as action_type
                    FROM mvfe_graph_edges e
                    JOIN mvfe_graph_nodes p ON p.id = e.source_id AND p.node_type = 'Principle'
                    JOIN mvfe_graph_nodes m ON m.id = e.target_id AND m.node_type IN ('Motive', 'Desire')
                    WHERE e.edge_type IN ('INFLUENCES', 'BREAKS')
                      AND e.user_id = '__system__' AND m.node_name = %s
                    LIMIT 5
                    """, (motive_type,)
                )
                rows = cur.fetchall()
                if not rows:
                    return self._activate_principles_offline(motive_type)
                return [
                    {
                        "principle_id": r[0],
                        "principle_text": r[1] or r[0],
                        "action_type": r[2],
                        "note": f"This principle {r[2].lower()}s patterns driven by '{motive_type}'.",
                    } for r in rows
                ]
        except Exception as e:
            logger.warning(f"activate_principles failed: {e}")
            return self._activate_principles_offline(motive_type)
        finally:
            self._pg._pool.putconn(conn)

    # ── Offline fallbacks (when DB is not connected) ───────────────────────

    def _detect_loop_offline(self, user_id: str) -> List[Dict[str, Any]]:
        """Rule-based loop detection using PATTERN_SUBGRAPHS when offline."""
        results = []
        for sg in PATTERN_SUBGRAPHS:
            if sg.reinforces_edges:
                out, mot = sg.reinforces_edges[0]
                results.append({
                    "pattern_id":   sg.pattern_id,
                    "motive":       mot,
                    "outcome":      out,
                    "loop_description": f"{sg.label} (offline inference)",
                    "note": "DB offline — loop detected from known pattern library.",
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
        if not self._pg.enabled:
            return []
        conn = self._pg._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT b.node_name as behavior, sum(e.traversal_count) as freq
                    FROM mvfe_graph_nodes b
                    JOIN mvfe_graph_edges e ON e.target_id = b.id AND e.edge_type = 'LEADS_TO'
                    WHERE b.user_id = %s AND b.node_type = 'Behavior'
                      AND e.updated_at > NOW() - INTERVAL '%s days'
                    GROUP BY b.node_name
                    HAVING sum(e.traversal_count) >= 2
                    ORDER BY freq DESC
                    """, (user_id, window_days)
                )
                return [{"behavior": r[0], "freq": r[1]} for r in cur.fetchall()]
        except Exception as e:
            logger.warning(f"_query_repeat_behaviors failed: {e}")
            return []
        finally:
            self._pg._pool.putconn(conn)

    def _query_user_paths(self, user_id: str) -> List[List[Dict[str, Any]]]:
        if not self._pg.enabled:
            return []
        conn = self._pg._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT e_node.node_name, m_node.node_name, b_node.node_name
                    FROM mvfe_graph_edges m_b
                    JOIN mvfe_graph_nodes b_node ON b_node.id = m_b.target_id AND b_node.node_type = 'Behavior'
                    JOIN mvfe_graph_nodes m_node ON m_node.id = m_b.source_id AND m_node.node_type IN ('Motive', 'Desire')
                    JOIN mvfe_graph_edges e_m ON e_m.target_id = m_node.id AND e_m.edge_type = 'CAUSES'
                    JOIN mvfe_graph_nodes e_node ON e_node.id = e_m.source_id AND e_node.node_type = 'Emotion'
                    WHERE b_node.user_id = %s
                    ORDER BY b_node.updated_at DESC
                    LIMIT 10
                    """, (user_id,)
                )
                rows = cur.fetchall()
                return [
                    [
                        {"label": "EmotionNode", "type": r[0]},
                        {"label": "MotiveNode", "type": r[1]},
                        {"label": "BehaviorNode", "type": r[2]}
                    ] for r in rows
                ]
        except Exception as e:
            logger.warning(f"_query_user_paths failed: {e}")
            return []
        finally:
            self._pg._pool.putconn(conn)

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


# ──────────────────────────────────────────────────────────────────────────────
# Module Singletons & Aliases
# ──────────────────────────────────────────────────────────────────────────────

_db_pool = None
_graph_service: Optional[GraphService] = None

# Backward-compat alias so existing imports of GraphEngine still work
GraphEngine = GraphService

def get_graph_service() -> GraphService:
    global _graph_service
    if _graph_service is None:
        _graph_service = GraphService(_db_pool)
    return _graph_service

def init_graph_db_pool(db_pool):
    global _db_pool, _graph_service
    _db_pool = db_pool
    _graph_service = GraphService(db_pool)
    return _graph_service

def seed_patterns_to_postgres(db_pool):
    """
    Seed canonical patterns and principles into the Postgres graph schema.
    Creates nodes and edges for all PATTERN_SUBGRAPHS under a '__system__' user.
    """
    if db_pool is None:
        return {"nodes": 0, "edges": 0}
    import json
    user_id = '__system__'
    conn = db_pool.getconn()
    node_count = edge_count = 0
    try:
        with conn.cursor() as cur:
            def upsert_node(node_type: str, name: str, props: Dict[str, Any]) -> str:
                nonlocal node_count
                cur.execute(
                    """
                    INSERT INTO mvfe_graph_nodes (user_id, node_type, node_name, properties)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, node_type, node_name) DO UPDATE
                    SET properties=mvfe_graph_nodes.properties || EXCLUDED.properties,
                        updated_at=NOW()
                    RETURNING id
                    """,
                    (user_id, node_type, name, json.dumps(props)),
                )
                node_count += 1
                return str(cur.fetchone()[0])

            def upsert_edge(source_id: str, target_id: str, edge_type: str, props: Dict[str, Any]) -> None:
                nonlocal edge_count
                cur.execute(
                    """
                    INSERT INTO mvfe_graph_edges
                        (user_id, source_id, target_id, edge_type, properties)
                    VALUES (%s, %s::uuid, %s::uuid, %s, %s)
                    ON CONFLICT (user_id, source_id, target_id, edge_type) DO UPDATE
                    SET properties=mvfe_graph_edges.properties || EXCLUDED.properties,
                        updated_at=NOW()
                    """,
                    (user_id, source_id, target_id, edge_type, json.dumps(props)),
                )
                edge_count += 1

            for sg in PATTERN_SUBGRAPHS:
                common = {
                    "pattern_id": sg.pattern_id, "category": sg.category,
                    "pattern_label": sg.label, "scripture": sg.scripture,
                }
                e_ids = {name: upsert_node("Emotion", name, common) for name in sg.emotion_nodes}
                m_ids = {name: upsert_node("Motive", name, common) for name in sg.motive_nodes}
                b_ids = {name: upsert_node("Behavior", name, common) for name in sg.behavior_nodes}
                o_ids = {name: upsert_node("Outcome", name, common) for name in sg.outcome_nodes}
                p_ids = {
                    name: upsert_node("Principle", name, {**common, "principle_id": name, "text": name})
                    for name in sg.principle_nodes
                }
                edge_props = {"pattern_id": sg.pattern_id, "category": sg.category}
                for source, target in sg.causes_edges:
                    if source in e_ids and target in m_ids:
                        upsert_edge(e_ids[source], m_ids[target], "CAUSES", edge_props)
                all_ids = {**m_ids, **b_ids, **o_ids}
                for source, target in sg.leads_to_edges:
                    if source in all_ids and target in all_ids:
                        upsert_edge(all_ids[source], all_ids[target], "LEADS_TO", edge_props)
                for source, target in sg.reinforces_edges:
                    if source in o_ids and target in m_ids:
                        upsert_edge(o_ids[source], m_ids[target], "REINFORCES", edge_props)
                for source, target in sg.breaks_edges:
                    if source in p_ids and target in b_ids:
                        upsert_edge(p_ids[source], b_ids[target], "BREAKS", edge_props)
                for source, target in sg.influences_edges:
                    if source in p_ids and target in m_ids:
                        upsert_edge(p_ids[source], m_ids[target], "INFLUENCES", edge_props)
        conn.commit()
        logger.info("[graph] seeded canonical PostgreSQL graph nodes=%s edges=%s", node_count, edge_count)
        return {"nodes": node_count, "edges": edge_count}
    except Exception:
        conn.rollback()
        raise
    finally:
        db_pool.putconn(conn)
