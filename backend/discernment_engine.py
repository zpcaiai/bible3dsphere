#!/usr/bin/env python3
"""
Discernment Engine Module - SFDS
Acts as a "spiritual mirror" rather than an oracle.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
from datetime import datetime
import random


class SourceType(Enum):
    HOLY_SPIRIT = "holy_spirit"
    CONSCIENCE = "conscience"
    FEAR = "fear"
    PRIDE = "pride"
    TRAUMA = "trauma"
    WORLDLY = "worldly"
    FLESH = "flesh"
    MIXED = "mixed"
    UNCERTAIN = "uncertain"


class ConfidenceLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskLevel(Enum):
    LOW = "low"
    MODERATE = "moderate"
    ELEVATED = "elevated"
    HIGH = "high"


@dataclass
class EmotionalState:
    emotions: List[Dict[str, Any]]
    stress_level: int
    anxiety_level: int
    fatigue_level: int
    spiritual_dryness: int
    emotional_stability: int


@dataclass
class MotiveProfile:
    fear_driven_score: float
    pride_driven_score: float
    love_driven_score: float
    desire_driven_score: float
    duty_driven_score: float = 0.0
    ambition_driven_score: float = 0.0


@dataclass
class SpiritualPrinciple:
    id: str
    principle_text: str
    scripture_reference: str
    category: str
    relevance_score: float


@dataclass
class DecisionEvent:
    id: str
    user_id: str
    title: str
    description: str
    category: str
    urgency_level: int
    importance_level: int
    created_at: datetime


@dataclass
class DiscernmentResult:
    primary_source: SourceType
    secondary_source: Optional[SourceType]
    confidence_level: ConfidenceLevel
    confidence_score: float
    primary_explanation: str
    alternative_interpretations: List[str]
    humility_statement: str
    risk_level: RiskLevel
    risk_factors: List[Dict[str, str]]
    recommended_reflections: List[str]
    suggested_questions: List[str]
    suggested_timeline: str
    supporting_principles: List[SpiritualPrinciple]
    analysis_version: str = "1.0.0"
    generated_at: datetime = field(default_factory=datetime.utcnow)
    disclaimer: str = "本分析仅供参考，不构成权威属灵指导。"


class DiscernmentEngine:
    """Spiritual discernment engine - acts as a mirror, not an oracle."""
    
    def __init__(self, version: str = "1.0.0"):
        self.version = version
    
    def discern(
        self,
        decision: DecisionEvent,
        emotional_state: EmotionalState,
        motive_profile: MotiveProfile,
        spiritual_principles: List[SpiritualPrinciple],
        past_cases: Optional[List] = None,
    ) -> DiscernmentResult:
        """Main discernment method."""
        
        # Calculate source scores
        scores = self._calculate_scores(emotional_state, motive_profile)
        
        # Determine sources
        primary, secondary, confidence = self._determine_sources(scores, emotional_state)
        
        # Map confidence
        conf_level = self._map_confidence(confidence)
        
        # Generate outputs
        explanation = self._generate_explanation(primary, secondary, motive_profile)
        alternatives = self._generate_alternatives(primary)
        humility = self._generate_humility(conf_level)
        risk_level, risks = self._assess_risks(emotional_state, primary, decision)
        reflections, questions, timeline = self._generate_steps(primary, risk_level)
        
        return DiscernmentResult(
            primary_source=primary,
            secondary_source=secondary,
            confidence_level=conf_level,
            confidence_score=confidence,
            primary_explanation=explanation,
            alternative_interpretations=alternatives,
            humility_statement=humility,
            risk_level=risk_level,
            risk_factors=risks,
            recommended_reflections=reflections,
            suggested_questions=questions,
            suggested_timeline=timeline,
            supporting_principles=spiritual_principles[:5],
        )
    
    def _calculate_scores(self, state: EmotionalState, motive: MotiveProfile) -> Dict[SourceType, float]:
        """Calculate alignment scores for each source type."""
        scores = {}
        
        # Holy Spirit: love, peace, stability
        hs_score = (
            motive.love_driven_score * 0.8 +
            (state.emotional_stability / 10) * 0.4 +
            (1 - state.anxiety_level / 10) * 0.3
        )
        scores[SourceType.HOLY_SPIRIT] = min(1.0, hs_score)
        
        # Fear: fear motive + anxiety + stress
        fear_score = (
            motive.fear_driven_score * 0.9 +
            (state.anxiety_level / 10) * 0.8 +
            (state.stress_level / 10) * 0.6
        )
        scores[SourceType.FEAR] = min(1.0, fear_score)
        
        # Pride: pride motive + instability
        pride_score = (
            motive.pride_driven_score * 0.9 +
            (1 - state.emotional_stability / 10) * 0.4
        )
        scores[SourceType.PRIDE] = min(1.0, pride_score)
        
        # Trauma: fear + spiritual dryness + instability
        trauma_score = (
            motive.fear_driven_score * 0.5 +
            (state.spiritual_dryness / 10) * 0.7 +
            (1 - state.emotional_stability / 10) * 0.6
        )
        scores[SourceType.TRAUMA] = min(1.0, trauma_score)
        
        # Worldly: desire + ambition
        worldly_score = (
            motive.desire_driven_score * 0.7 +
            motive.ambition_driven_score * 0.6
        )
        scores[SourceType.WORLDLY] = min(1.0, worldly_score)
        
        # Flesh: desire + fatigue
        flesh_score = (
            motive.desire_driven_score * 0.8 +
            (state.fatigue_level / 10) * 0.4
        )
        scores[SourceType.FLESH] = min(1.0, flesh_score)
        
        # Conscience: duty + stability
        conscience_score = (
            motive.duty_driven_score * 0.7 +
            (state.emotional_stability / 10) * 0.4
        )
        scores[SourceType.CONSCIENCE] = min(1.0, conscience_score)
        
        return scores
    
    def _determine_sources(
        self,
        scores: Dict[SourceType, float],
        state: EmotionalState
    ) -> Tuple[SourceType, Optional[SourceType], float]:
        """Determine primary and secondary sources."""
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        primary = sorted_scores[0][0]
        primary_score = sorted_scores[0][1]
        
        secondary = None
        if len(sorted_scores) >= 2:
            gap = primary_score - sorted_scores[1][1]
            if gap < 0.15:
                secondary = sorted_scores[1][0]
        
        # Low score = uncertain
        if primary_score < 0.3:
            return SourceType.UNCERTAIN, None, primary_score
        
        # Mixed signals
        if primary_score < 0.5 and secondary and sorted_scores[1][1] > 0.35:
            return SourceType.MIXED, None, primary_score
        
        # Adjust for stability
        stability_factor = state.emotional_stability / 10.0
        adjusted = primary_score * (0.7 + 0.3 * stability_factor)
        
        return primary, secondary, min(1.0, adjusted)
    
    def _map_confidence(self, score: float) -> ConfidenceLevel:
        if score >= 0.7:
            return ConfidenceLevel.HIGH
        elif score >= 0.5:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW
    
    def _generate_explanation(
        self,
        primary: SourceType,
        secondary: Optional[SourceType],
        motive: MotiveProfile
    ) -> str:
        """Generate reflective explanation."""
        
        explanations = {
            SourceType.HOLY_SPIRIT: [
                "从动机分析来看，决策展现出较高的爱与平安导向。情绪相对稳定，这与属灵感动的特征相符。但这仍需您在祷告中亲自确认。",
                "这个方向似乎与爱的原则一致，长期果实预测积极。不过，任何感动都需要在圣经、时间和群体中验证。",
            ],
            SourceType.FEAR: [
                f"动机分析显示，恐惧因素占有较大比重（{motive.fear_driven_score:.0%}）。这很常见，人在不确定时自然寻求安全。",
                '这个决定很大程度上受"避免损失"的心理驱动。这种动机本身并非错误，但可能限制看见其他可能性的视野。',
                "情绪状态显示焦虑较高，这可能影响判断清晰度。或许值得先处理焦虑，再看这个决定是否依然合适。",
            ],
            SourceType.PRIDE: [
                "动机分析显示出对外在认可的一定需求。这是很普遍的人性弱点，无需自责，但值得觉察。",
                "这个决定似乎与维护某种形象有关。这种动机往往带来短期满足，但长期可能导致疲惫。",
                '坦诚面对"被人如何看待"的影响，或许能帮助您做出更真实的选择。',
            ],
            SourceType.TRAUMA: [
                "灵性状态显示一定程度的干涸，情绪也较为波动。这种状态下做出的决定，可能受过去未愈伤痛的影响。",
                "情绪反应强度似乎与当下情境不完全匹配。这可能是过往经历被触发的信号。",
            ],
            SourceType.WORLDLY: [
                "决策似乎较多考虑社会标准或物质回报。这些考量很实际，但可能掩盖更深层的价值。",
                "问问自己：这是神衡量成功的标准，还是世界的？",
            ],
            SourceType.FLESH: [
                "决策与即时满足或欲望有较强关联。肉体的声音往往很急迫，但不代表正确。",
                "问问自己：如果没有任何舒适考量，我会怎么选？",
            ],
            SourceType.MIXED: [
                "动机分析显示出复杂的混合——既有值得肯定的面向，也有需要警觉的因素。这种复杂性是人性常态。",
                "没有单一主导动机，这种情况更需要谨慎和时间的检验。",
            ],
            SourceType.UNCERTAIN: [
                "基于当前信息，难以对来源做出有信心的判断。这并非坏事，不确定性本身就是分辨过程的一部分。",
                '不确定性邀请更深的寻求。与其匆忙结论，不如拥抱"尚未清楚"的状态。',
            ],
        }
        
        exp = random.choice(explanations.get(primary, ["分析正在进行..."]))
        
        if secondary:
            secondary_names = {
                SourceType.FEAR: "恐惧因素",
                SourceType.PRIDE: "骄傲因素",
                SourceType.HOLY_SPIRIT: "圣灵感动",
                SourceType.WORLDLY: "世俗影响",
                SourceType.TRAUMA: "创伤反应",
                SourceType.FLESH: "肉体欲望",
                SourceType.CONSCIENCE: "良心/理性",
            }
            sec_name = secondary_names.get(secondary, secondary.value)
            exp += f"\n\n同时，{sec_name}也可能在影响这个决定。"
        
        return exp
    
    def _generate_alternatives(self, primary: SourceType) -> List[str]:
        """Generate alternative interpretations."""
        alts = {
            SourceType.FEAR: [
                "另一种可能：这不是危险信号，而是信心成长的邀请。恐惧可能是需要跨越的边界。",
                "也值得考虑：如果完全不怕，您会如何选择？恐惧有时是价值重估的信号。",
            ],
            SourceType.PRIDE: [
                "另一种视角：对成就的追求也可能是神赋予的使命感和管家忠心。",
                '追求优秀本身并非罪，关键是对"谁得荣耀"的觉察。',
            ],
            SourceType.HOLY_SPIRIT: [
                '但也要小心：有时"爱"的动机可能掩盖了边界问题。',
                "另一个角度：爱驱动的决定也需要智慧执行，否则可能好心办坏事。",
            ],
            SourceType.TRAUMA: [
                "但也可以理解为：过往经历给了您独特的洞察力。",
                "另一个可能：这次情况与过去不同，您的警觉可能过度了。",
            ],
        }
        
        general = [
            "从另一角度看：这个决定的时机是否合适？或许需要更多准备。",
            '也可以理解为：这不是"对vs错"，而是"好vs更好"的排序。',
            "值得考虑：如果5年后回头看，现在的顾虑还重要吗？",
            "另一个视角：神在意的是您如何做决定，而非决定本身。",
        ]
        
        result = alts.get(primary, [])
        result.extend(random.sample(general, 2))
        return result[:3]
    
    def _generate_humility(self, confidence: ConfidenceLevel) -> str:
        humility = {
            ConfidenceLevel.HIGH: [
                "分析显示了相对清晰的方向，但这只是基于有限信息的推断。真正的确据需要来自神的话语、祷告中的平安，以及属灵群体的印证。",
            ],
            ConfidenceLevel.MEDIUM: [
                "目前的信号是混合的，没有单一来源明确主导。其他解释也合理存在，值得同等认真考虑。",
            ],
            ConfidenceLevel.LOW: [
                "基于当前信息，难以做出有信心的判断。不确定性本身就是分辨过程的一部分，等待和寻求可能比匆忙决定更明智。",
            ],
        }
        return random.choice(humility.get(confidence, humility[ConfidenceLevel.LOW]))
    
    def _assess_risks(
        self,
        state: EmotionalState,
        primary: SourceType,
        decision: DecisionEvent
    ) -> Tuple[RiskLevel, List[Dict[str, str]]]:
        """Assess decision risks."""
        risks = []
        score = 0
        
        if state.stress_level >= 7:
            risks.append({
                "factor": "高压力状态",
                "message": "当前压力水平较高，可能影响判断的客观性。",
                "recommendation": "考虑推迟重大决定，或先建立压力管理机制。",
            })
            score += 2
        
        if state.anxiety_level >= 7:
            risks.append({
                "factor": "高焦虑状态",
                "message": "焦虑水平显著升高，决策可能过度聚焦于风险规避。",
                "recommendation": "在焦虑平复前，避免做出不可逆的决定。",
            })
            score += 2
        
        if state.spiritual_dryness >= 6:
            risks.append({
                "factor": "灵性干涸",
                "message": "灵性状态显示一定干涸，可能导致依赖感觉而非信心。",
                "recommendation": "重建基本灵修习惯可能比做这个决定更紧迫。",
            })
            score += 1
        
        if state.emotional_stability < 4:
            risks.append({
                "factor": "情绪不稳定",
                "message": "情绪稳定性较低，决策可能受近期情绪波动的不当影响。",
                "recommendation": "建议等待情绪平复，或寻求辅导支持。",
            })
            score += 1
        
        if primary in [SourceType.FEAR, SourceType.TRAUMA]:
            risks.append({
                "factor": "恐惧/创伤驱动",
                "message": "恐惧驱动的决定往往过度保守，可能错失成长机会。",
                "recommendation": "列出如果不害怕，您会怎么选择，比较两个选项。",
            })
            score += 1
        
        if decision.importance_level >= 4 and primary == SourceType.UNCERTAIN:
            risks.append({
                "factor": "重要但方向不明",
                "message": "这是重要决定，但目前方向尚不清晰。",
                "recommendation": "考虑推迟决定，或缩小决策范围。",
            })
            score += 1
        
        if score >= 5:
            return RiskLevel.HIGH, risks
        elif score >= 3:
            return RiskLevel.ELEVATED, risks
        elif score >= 1:
            return RiskLevel.MODERATE, risks
        return RiskLevel.LOW, risks
    
    def _generate_steps(
        self,
        primary: SourceType,
        risk: RiskLevel
    ) -> Tuple[List[str], List[str], str]:
        """Generate non-directive next steps."""
        reflections = [
            "给自己24-48小时，期间不做任何相关决定，观察内心变化。",
            "写下这个决定最好和最坏的结果，评估自己是否都能承受。",
            "与一位您最尊重的属灵导师分享这个分析，听听他们的观察。",
            '在祷告中，不是求神"同意"您的决定，而是求祂显出您看不见的角度。',
        ]
        
        if primary == SourceType.FEAR:
            reflections.append("写下您最害怕的具体是什么。恐惧往往在真理的光中消散。")
        elif primary == SourceType.PRIDE:
            reflections.append('练习说出"我不知道"和"我需要帮助"，打破自我证明的循环。')
        elif primary == SourceType.UNCERTAIN:
            reflections.append('不要急于"制造"确定性。拥抱"尚未清楚"也是一种信心操练。')
        
        if risk in [RiskLevel.ELEVATED, RiskLevel.HIGH]:
            reflections.append("由于当前风险因素，建议优先考虑情绪/灵性健康，而非急于做决定。")
        
        questions = [
            "如果10年后的自己回看今天，会希望现在的我怎么选择？",
            "我能否在神面前完全坦诚这个决定的动机？",
            "如果我完全不需要考虑他人怎么看，我会怎么选？",
            "这个决定会让我的心与神更近，还是更远？",
        ]
        
        if risk == RiskLevel.HIGH or primary in [SourceType.FEAR, SourceType.TRAUMA]:
            timeline = "强烈建议等待24-72小时，待情绪平复后再重新评估。"
        else:
            timeline = "可以较快决定，但仍建议与至少一位信任的人分享您的想法。"
        
        return reflections[:3], questions, timeline


def format_result(result: DiscernmentResult) -> Dict[str, Any]:
    """Format for API response."""
    names = {
        SourceType.HOLY_SPIRIT: "圣灵感动",
        SourceType.CONSCIENCE: "良心/理性",
        SourceType.FEAR: "恐惧反应",
        SourceType.PRIDE: "骄傲反应",
        SourceType.TRAUMA: "创伤反应",
        SourceType.WORLDLY: "世俗价值观",
        SourceType.FLESH: "肉体欲望",
        SourceType.MIXED: "混合动机",
        SourceType.UNCERTAIN: "方向不明",
    }
    
    return {
        "source": {
            "primary": {"type": result.primary_source.value, "name": names.get(result.primary_source)},
            "secondary": {"type": result.secondary_source.value, "name": names.get(result.secondary_source)} if result.secondary_source else None,
            "confidence": result.confidence_level.value,
            "score": round(result.confidence_score, 2),
        },
        "explanation": result.primary_explanation,
        "alternatives": result.alternative_interpretations,
        "humility": result.humility_statement,
        "risk": {
            "level": result.risk_level.value,
            "factors": result.risk_factors,
        },
        "next_steps": {
            "reflections": result.recommended_reflections,
            "questions": result.suggested_questions,
            "timeline": result.suggested_timeline,
        },
        "principles": [
            {"text": p.principle_text, "scripture": p.scripture_reference}
            for p in result.supporting_principles
        ],
        "disclaimer": result.disclaimer,
    }


# ══════════════════════════════════════════════════════════════════════════════
# V2 DISCERNMENT ENGINE
# Integrates: V1 source analysis + Neo4j graph layer + TimescaleDB temporal layer
# ══════════════════════════════════════════════════════════════════════════════

from graph_layer import GraphEngine, GraphInsight, KNOWN_PATTERNS
from temporal_engine import TemporalEngine, TemporalInsight, TrendDirection


@dataclass
class V2DiscernmentResult:
    """
    Full V2 output combining structural, temporal, spiritual-alignment,
    and intervention insights.
    """
    # ── V1 core (always present) ──────────────────────────────────────────────
    v1_result: DiscernmentResult

    # ── 1. STRUCTURAL INSIGHT (Graph) ─────────────────────────────────────────
    structural_insight: str          # narrative
    causal_patterns: List[str]       # e.g. ["fear → control → burnout"]
    cycle_warning: Optional[str]     # non-None if cycle detected
    intervention_points: List[Dict[str, str]]

    # ── 2. TEMPORAL INSIGHT (Time-series) ────────────────────────────────────
    temporal_insight: str            # narrative
    trend_direction: str             # improving / declining / stable / volatile
    spiritual_season: str            # dry / growing / confused / etc.
    is_peak_anxiety: bool
    is_burnout_risk: bool
    temporal_patterns: List[str]     # human-readable pattern descriptions

    # ── 3. SPIRITUAL ALIGNMENT INSIGHT ───────────────────────────────────────
    alignment_trend: str             # narrative on alignment over time
    alignment_declining: bool

    # ── 4. INTERVENTION SUGGESTION ───────────────────────────────────────────
    intervention_suggestion: str     # non-directive suggestion
    reflective_questions: List[str]  # open mirror questions for the user
    is_high_risk_window: bool        # combined flag
    pause_recommended: bool

    # ── Meta ──────────────────────────────────────────────────────────────────
    analysis_version: str = "2.0.0"
    generated_at: datetime = field(default_factory=datetime.utcnow)
    disclaimer: str = (
        "This analysis is offered as a reflective mirror, not a directive. "
        "Please bring these observations to prayer, Scripture, and trusted community."
    )


class DiscernmentEngineV2:
    """
    Spiritual Formation & Discernment System — Version 2.

    Combines:
    - V1 rule-based source analysis (DiscernmentEngine)
    - Neo4j structural pattern reasoning (GraphEngine)
    - TimescaleDB temporal formation analysis (TemporalEngine)
    """

    def __init__(
        self,
        graph_engine: Optional[GraphEngine] = None,
        temporal_engine: Optional[TemporalEngine] = None,
    ):
        self._v1 = DiscernmentEngine(version="1.0.0")
        self._graph = graph_engine or GraphEngine()
        self._temporal = temporal_engine or TemporalEngine()

    def discern_v2(
        self,
        decision: DecisionEvent,
        emotional_state: EmotionalState,
        motive_profile: MotiveProfile,
        spiritual_principles: List[SpiritualPrinciple],
        user_id: str = "",
        current_snapshot: Optional[Dict[str, Any]] = None,
        past_behavior_types: Optional[List[str]] = None,
    ) -> V2DiscernmentResult:
        """
        Full V2 analysis.

        Args:
            decision:              The decision event.
            emotional_state:       Current emotional metrics.
            motive_profile:        Computed motive scores.
            spiritual_principles:  Relevant principles (pgvector results).
            user_id:               User UUID — used for historical DB queries.
            current_snapshot:      Dict of current spiritual metrics for temporal engine.
            past_behavior_types:   List of behavior type strings from user history.
        """

        # ── Step 1: V1 analysis ──────────────────────────────────────────────
        v1 = self._v1.discern(decision, emotional_state, motive_profile, spiritual_principles)

        # ── Step 2: Graph structural analysis ───────────────────────────────
        dominant_motive = self._dominant_motive(motive_profile)
        emotions_list = [
            {"type": e.get("type", ""), "intensity": e.get("intensity", 5)}
            for e in emotional_state.emotions
        ]
        graph_insight: GraphInsight = self._graph.analyze(
            user_id=user_id,
            dominant_motive=dominant_motive,
            emotions=emotions_list,
            decision_category=decision.category,
            past_behavior_types=past_behavior_types or [],
        )

        # ── Step 3: Temporal analysis ────────────────────────────────────────
        snapshot = current_snapshot or {
            "anxiety_level":      emotional_state.anxiety_level,
            "peace_level":        max(0, 10 - emotional_state.anxiety_level),
            "clarity_level":      emotional_state.emotional_stability,
            "spiritual_dryness":  emotional_state.spiritual_dryness,
            "emotional_stability":emotional_state.emotional_stability,
            "decision_confidence":max(0, 10 - emotional_state.fatigue_level),
        }
        temporal_insight: TemporalInsight = self._temporal.analyze(
            user_id=user_id,
            current_snapshot=snapshot,
        )

        # ── Step 4: Build V2 output ──────────────────────────────────────────
        return self._build_v2_result(v1, graph_insight, temporal_insight, motive_profile, decision.category)

    # ── Internal builders ─────────────────────────────────────────────────────

    def _dominant_motive(self, motive: MotiveProfile) -> str:
        scores = {
            "fear":      motive.fear_driven_score,
            "pride":     motive.pride_driven_score,
            "love":      motive.love_driven_score,
            "desire":    motive.desire_driven_score,
            "duty":      motive.duty_driven_score,
            "ambition":  motive.ambition_driven_score,
        }
        return max(scores, key=scores.get)

    def _get_reflective_questions(self, pattern_labels: List[str]) -> List[str]:
        pid_map = {p["label"]: p.get("reflective_question") for p in KNOWN_PATTERNS}
        return [q for lbl, q in pid_map.items() if lbl in pattern_labels and q][:3]

    def _build_v2_result(
        self,
        v1: DiscernmentResult,
        graph: GraphInsight,
        temporal: TemporalInsight,
        motive: MotiveProfile,
        category: str = "other",
    ) -> V2DiscernmentResult:

        # ── Structural insight ────────────────────────────────────────────────
        structural_narrative = graph.structural_summary or "No structural patterns matched."
        causal_patterns = graph.pattern_labels
        cycle_warning: Optional[str] = None
        if graph.cycles:
            cycle_desc = "; ".join(c.description for c in graph.cycles[:2])
            cycle_warning = (
                f"A possible recurring loop may be present: {cycle_desc}. "
                "This is offered as a mirror — it may or may not apply to your situation."
            )

        reflective_questions = self._get_reflective_questions(graph.pattern_labels)

        # ── Temporal insight ──────────────────────────────────────────────────
        temporal_narrative = temporal.temporal_summary
        temporal_pattern_descs = [p.description for p in temporal.detected_patterns]

        # ── Alignment trend ───────────────────────────────────────────────────
        alignment_declining = temporal.trend_direction == TrendDirection.DECLINING
        if alignment_declining:
            alignment_trend = (
                "Overall spiritual stability has been declining over the last observation period. "
                "Decisions made during decline phases tend to reflect anxiety more than faith."
            )
        elif temporal.trend_direction == TrendDirection.IMPROVING:
            alignment_trend = (
                "Spiritual formation indicators are trending upward. "
                "This is a relatively stronger window for aligned decision-making."
            )
        else:
            alignment_trend = (
                f"Spiritual alignment is broadly {temporal.trend_direction.value}. "
                "No strong trend signal in either direction."
            )

        # ── Intervention suggestion ───────────────────────────────────────────
        is_high_risk = (
            temporal.is_intervention_window
            or v1.risk_level.value in ("high", "elevated")
            or bool(graph.cycles)
        )
        pause_recommended = is_high_risk and (
            temporal.is_peak_anxiety or temporal.is_burnout_risk
        )

        intervention = self._compose_intervention(
            v1, graph, temporal, is_high_risk, pause_recommended
        )

        return V2DiscernmentResult(
            v1_result=v1,
            structural_insight=structural_narrative,
            causal_patterns=causal_patterns,
            cycle_warning=cycle_warning,
            intervention_points=graph.intervention_points,
            temporal_insight=temporal_narrative,
            trend_direction=temporal.trend_direction.value,
            spiritual_season=temporal.spiritual_season.value,
            is_peak_anxiety=temporal.is_peak_anxiety,
            is_burnout_risk=temporal.is_burnout_risk,
            temporal_patterns=temporal_pattern_descs,
            alignment_trend=alignment_trend,
            alignment_declining=alignment_declining,
            intervention_suggestion=intervention,
            reflective_questions=reflective_questions,
            is_high_risk_window=is_high_risk,
            pause_recommended=pause_recommended,
        )

    def _compose_intervention(
        self,
        v1: DiscernmentResult,
        graph: GraphInsight,
        temporal: TemporalInsight,
        is_high_risk: bool,
        pause: bool,
    ) -> str:
        parts: List[str] = []

        if pause:
            parts.append(
                "Multiple signals are present at once — elevated anxiety, possible burnout, "
                "and a recognised pattern. You might consider giving yourself 24–72 hours "
                "before deciding, if that is feasible."
            )
        elif is_high_risk:
            parts.append(
                "Several stress indicators are elevated right now. "
                "Slowing down or bringing a trusted person into this decision may be worth considering."
            )

        if graph.intervention_points:
            iv = graph.intervention_points[0]
            parts.append(
                f"Pattern reflection: {iv['suggestion']}"
                + (f" ({iv['scripture']})" if iv.get('scripture') else "")
            )

        if temporal.intervention_guidance:
            parts.append(temporal.intervention_guidance)

        if not parts:
            parts.append(
                "No acute risk signals were detected. "
                "Standard discernment practices — prayer, counsel, Scripture — remain relevant."
            )

        return "\n\n".join(parts)


def format_v2_result(result: V2DiscernmentResult) -> Dict[str, Any]:
    """Serialize V2DiscernmentResult for API response."""
    return {
        "version": result.analysis_version,
        "generated_at": result.generated_at.isoformat(),

        "1_structural_insight": {
            "summary": result.structural_insight,
            "causal_patterns": result.causal_patterns,
            "cycle_warning": result.cycle_warning,
            "intervention_points": result.intervention_points,
        },

        "2_temporal_insight": {
            "summary": result.temporal_insight,
            "trend_direction": result.trend_direction,
            "spiritual_season": result.spiritual_season,
            "is_peak_anxiety": result.is_peak_anxiety,
            "is_burnout_risk": result.is_burnout_risk,
            "patterns_detected": result.temporal_patterns,
        },

        "3_spiritual_alignment": {
            "trend_narrative": result.alignment_trend,
            "alignment_declining": result.alignment_declining,
        },

        "4_intervention": {
            "suggestion": result.intervention_suggestion,
            "reflective_questions": result.reflective_questions,
            "is_high_risk_window": result.is_high_risk_window,
            "pause_recommended": result.pause_recommended,
        },

        "v1_analysis": format_result(result.v1_result),

        "disclaimer": result.disclaimer,
    }
