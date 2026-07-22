#!/usr/bin/env python3
"""
SFDS Formation Pipeline — unified evidence and formation engine.

Flow:
    User Input
    1. State Snapshot         (PostgreSQL — facts)
    2. Semantic Retrieval     (pgvector — meaning)
    3. GraphRAG               (pgvector + PostgreSQL graph paths)
    4. Graph Query            (PostgreSQL recursive CTE — structure / WHY)
    5. Time-Series Query      (TimescaleDB — time / WHEN)
    6. Discernment Fusion     (structured evidence — WHAT NOW)
       Guidance Output
       Write-back:
           graph update  (PostgreSQL)
           timeline      (TimescaleDB)
           decision log  (PostgreSQL)

Design principles:
  - Every layer is optional / gracefully degraded.
  - Output preserves awareness, reflection, autonomy.
  - System is a mirror, NOT a judge.
  - No guilt scoring. No divine certainty. No commands.
  - Human freedom and uncertainty built into every output.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from graph_layer import (
    GraphService, GraphInsight, get_graph_service, KNOWN_PATTERNS,
    MOTIVE_PATTERN_MAP, EMOTION_PATTERN_MAP,
)
from graph_reasoning_engine import (
    GraphReasoningFusion, FormationReasoning, get_reasoning_engine,
)
from formation_engine import (
    FormationEngine, FormationInsight, get_formation_engine, init_formation_engine,
)
from temporal_engine import (
    TemporalEngine, TemporalInsight, TemporalDataAccess,
    TrendDirection, SpiritualSeason,
)
from discernment_engine import (
    DiscernmentEngineV2,
    DecisionEvent as EngineDecision,
    EmotionalState as EngineEmotion,
    MotiveProfile as EngineMotive,
    SpiritualPrinciple as EnginePrinciple,
    format_v2_result,
)
from graph_rag import GraphRAGContext, GraphRAGEngine, get_rag_engine


# ──────────────────────────────────────────────────────────────────────────────
# Pipeline I/O dataclasses
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class PipelineInput:
    """All fields the pipeline needs. Safe defaults everywhere."""
    user_id:             str
    decision_id:         str   = field(default_factory=lambda: str(uuid.uuid4()))
    title:               str   = ""
    description:         str   = ""
    category:            str   = "other"
    urgency:             int   = 3
    importance:          int   = 3

    # Emotional state (0–10 scales)
    anxiety_level:       int   = 5
    peace_level:         int   = 5
    clarity_level:       int   = 5
    spiritual_dryness:   int   = 5
    emotional_stability: int   = 5
    decision_confidence: int   = 5
    stress_level:        int   = 5
    fatigue_level:       int   = 5

    # Active emotions: [{"type": "fear", "intensity": 7, "trigger": "..."}]
    emotions: List[Dict[str, Any]] = field(default_factory=list)

    # Motive scores (0–1): {"fear": 0.7, "pride": 0.2, ...}
    motive_scores: Optional[Dict[str, float]] = None

    # Prior behaviour strings for cycle detection
    past_behavior_types: List[str] = field(default_factory=list)

    # pgvector results passed in from semantic layer
    semantic_principles: List[Dict[str, Any]] = field(default_factory=list)

    # Optional reflection text — activates reflection_active damping in Formation Engine
    reflection_notes: str = ""


@dataclass
class LayerResult:
    layer:       str
    success:     bool
    data:        Any            = None
    error:       Optional[str]  = None
    duration_ms: float          = 0.0


@dataclass
class FormationOutput:
    """Final output of the multi-layer formation pipeline."""
    pipeline_id:  str = field(default_factory=lambda: str(uuid.uuid4()))
    generated_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    user_id:      str = ""
    decision_id:  str = ""

    # Four insight pillars
    structural:   Dict[str, Any] = field(default_factory=dict)
    temporal:     Dict[str, Any] = field(default_factory=dict)
    alignment:    Dict[str, Any] = field(default_factory=dict)
    intervention: Dict[str, Any] = field(default_factory=dict)

    # v3 — Formation Engine layer (character dimension tracking)
    formation:    Dict[str, Any] = field(default_factory=dict)

    # Auditable semantic matches + PostgreSQL paths used during fusion.
    graph_rag:     Dict[str, Any] = field(default_factory=dict)

    reflective_questions: List[str] = field(default_factory=list)
    v1_analysis:          Optional[Dict[str, Any]] = None

    pipeline_layers:      List[LayerResult] = field(default_factory=list)
    is_high_risk_window:  bool = False
    pause_recommended:    bool = False

    disclaimer: str = (
        "This system offers structured reflection — not spiritual authority. "
        "It is a mirror for awareness, not a verdict. "
        "All insights are probabilistic. Human freedom, grace, and mystery "
        "always exceed what any model can capture. "
        "NEVER optimizes for: human behavior change, emotional outcome optimization, "
        "personality state improvement, or behavioral compliance rate."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_id":     self.pipeline_id,
            "generated_at":    self.generated_at,
            "user_id":         self.user_id,
            "decision_id":     self.decision_id,
            "1_structural":    self.structural,
            "2_temporal":      self.temporal,
            "3_alignment":     self.alignment,
            "4_intervention":  self.intervention,
            "5_formation":     self.formation,
            "graph_rag":       self.graph_rag,
            "reflective_questions": self.reflective_questions,
            "v1_analysis":     self.v1_analysis,
            "is_high_risk_window": self.is_high_risk_window,
            "pause_recommended":   self.pause_recommended,
            "disclaimer":      self.disclaimer,
            "pipeline_meta": {
                "layers_run": [
                    {
                        "layer": lr.layer,
                        "success": lr.success,
                        "error": lr.error,
                        "duration_ms": round(lr.duration_ms, 1),
                    }
                    for lr in self.pipeline_layers
                ]
            },
        }


# ──────────────────────────────────────────────────────────────────────────────
# Formation Pipeline
# ──────────────────────────────────────────────────────────────────────────────

class FormationPipeline:
    """
    Unified V2 spiritual formation intelligence pipeline.

    Instantiate once at startup; reuse across requests.
    All layers fail gracefully — pipeline always returns a FormationOutput.
    """

    def __init__(
        self,
        graph_service:    Optional[GraphService]       = None,
        temporal_engine:  Optional[TemporalEngine]     = None,
        v2_engine:        Optional[DiscernmentEngineV2] = None,
        reasoning_engine: Optional[GraphReasoningFusion] = None,
        graph_rag_engine: Optional[GraphRAGEngine] = None,
        db_pool=None,
    ):
        self._db_pool   = db_pool
        self.graph      = graph_service  or get_graph_service()
        self.temporal   = temporal_engine or TemporalEngine(TemporalDataAccess(db_pool))
        self.v2         = v2_engine or DiscernmentEngineV2(
            graph_engine=self.graph,
            temporal_engine=self.temporal,
        )
        self.reasoning  = reasoning_engine or get_reasoning_engine()
        self.graph_rag  = graph_rag_engine or get_rag_engine()
        self.formation  = get_formation_engine(db_pool)

    # ── Main entry ────────────────────────────────────────────────────────────

    def run(self, inp: PipelineInput) -> FormationOutput:
        """Execute every pipeline layer. Returns FormationOutput always."""
        import time

        out = FormationOutput(user_id=inp.user_id, decision_id=inp.decision_id)
        layers: List[LayerResult] = []

        # Layer 1 — State snapshot (already materialised in inp)
        layers.append(LayerResult(
            layer="state_snapshot", success=True,
            data={
                "anxiety": inp.anxiety_level, "peace": inp.peace_level,
                "dryness": inp.spiritual_dryness, "stability": inp.emotional_stability,
            },
        ))

        # Layer 2 — Semantic retrieval (pgvector; passed in by caller)
        t = time.monotonic()
        principles: List[EnginePrinciple] = []
        try:
            principles = self._build_principles(inp.semantic_principles)
            layers.append(LayerResult(
                layer="semantic_retrieval", success=True,
                data={"principles_found": len(principles)},
                duration_ms=(time.monotonic() - t) * 1000,
            ))
        except Exception as exc:
            layers.append(LayerResult(
                layer="semantic_retrieval", success=False, error=str(exc)
            ))

        # Layer 3 — GraphRAG: semantic anchors + recursive PostgreSQL paths.
        # Context remains source-labelled and visible in the response.
        t = time.monotonic()
        rag_context = GraphRAGContext()
        try:
            query_parts = [inp.title, inp.description, inp.category]
            query_parts.extend(
                str(emotion.get("type", "")) for emotion in inp.emotions
            )
            query_text = " ".join(
                part.strip() for part in query_parts if part and part.strip()
            )
            rag_context = self.graph_rag.retrieve(
                user_id=inp.user_id,
                query_text=query_text or "spiritual formation reflection",
                top_k=5,
                graph_depth=2,
                precomputed_principles=inp.semantic_principles,
            )
            rag_context.ai_synthesis = self.graph_rag.synthesize(
                inp.user_id, query_text, rag_context
            )
            rag_context.source_stats["ai_synthesis"] = rag_context.ai_synthesis.get("status", "NOT_RUN")
            out.graph_rag = rag_context.to_dict()
            if not principles and rag_context.matched_principles:
                principles = self._build_principles(rag_context.matched_principles)
            layers.append(LayerResult(
                layer="graph_rag", success=True,
                data=rag_context.source_stats,
                duration_ms=(time.monotonic() - t) * 1000,
            ))
        except Exception as exc:
            logger.warning("[pipeline] GraphRAG layer failed: %s", exc)
            out.graph_rag = GraphRAGContext().to_dict()
            layers.append(LayerResult(layer="graph_rag", success=False, error=str(exc)))

        # Layer 4 — PostgreSQL graph query (WHY)
        t = time.monotonic()
        graph_insight: Optional[GraphInsight] = None
        matched_pattern_ids: List[str] = []
        try:
            dominant_motive = self._dominant_motive(inp.motive_scores)
            graph_insight = self.graph.analyze(
                user_id=inp.user_id,
                dominant_motive=dominant_motive,
                emotions=inp.emotions,
                decision_category=inp.category,
                past_behavior_types=inp.past_behavior_types,
            )
            matched_pattern_ids = [
                iv.get("pattern_id", "") for iv in graph_insight.intervention_points
            ]
            rqs = self._get_reflective_questions(matched_pattern_ids)

            # Run 6-layer graph reasoning fusion (v2.2)
            dominant_emotion = self._dominant_emotion(inp.emotions)
            dominant_motive  = self._dominant_motive(inp.motive_scores)
            formation_reasoning: Optional[FormationReasoning] = None
            try:
                formation_reasoning = self.reasoning.reason(
                    user_id          = inp.user_id,
                    dominant_emotion = dominant_emotion,
                    dominant_motive  = dominant_motive,
                    graph_insight    = graph_insight,
                    vector_principles= (
                        inp.semantic_principles or rag_context.matched_principles
                    ),
                    temporal_context = None,   # enriched after layer 4
                )
            except Exception as rexc:
                logger.warning("[pipeline] reasoning fusion failed: %s", rexc)

            out.structural = self._format_structural(
                graph_insight, rqs, formation_reasoning
            )
            out.reflective_questions.extend(
                formation_reasoning.reflective_guidance
                if formation_reasoning else rqs
            )
            layers.append(LayerResult(
                layer="graph_query", success=True,
                data={
                    "patterns_matched":   len(graph_insight.pattern_labels),
                    "cycles_detected":    len(graph_insight.cycles),
                    "reasoning_layers":   (
                        formation_reasoning.reasoning_layers_run
                        if formation_reasoning else []
                    ),
                },
                duration_ms=(time.monotonic() - t) * 1000,
            ))
        except Exception as exc:
            logger.warning("[pipeline] graph layer failed: %s", exc)
            layers.append(LayerResult(layer="graph_query", success=False, error=str(exc)))
            out.structural = {
                "summary": "Structural layer unavailable.",
                "patterns": [], "cycles": [], "interventions": [],
            }

        # Layer 4 — Time-series (TimescaleDB: WHEN)
        t = time.monotonic()
        temporal_insight: Optional[TemporalInsight] = None
        current_snapshot: Dict[str, Any] = {
            "anxiety_level":       inp.anxiety_level,
            "peace_level":         inp.peace_level,
            "clarity_level":       inp.clarity_level,
            "spiritual_dryness":   inp.spiritual_dryness,
            "emotional_stability": inp.emotional_stability,
            "decision_confidence": inp.decision_confidence,
        }
        try:
            temporal_insight = self.temporal.analyze(
                user_id=inp.user_id,
                current_snapshot=current_snapshot,
            )
            out.temporal = self._format_temporal(temporal_insight)
            layers.append(LayerResult(
                layer="timeseries_query", success=True,
                data={
                    "trend":    temporal_insight.trend_direction.value,
                    "season":   temporal_insight.spiritual_season.value,
                    "patterns": len(temporal_insight.detected_patterns),
                },
                duration_ms=(time.monotonic() - t) * 1000,
            ))
        except Exception as exc:
            logger.warning("[pipeline] temporal layer failed: %s", exc)
            layers.append(LayerResult(layer="timeseries_query", success=False, error=str(exc)))
            out.temporal = {"summary": "Temporal layer unavailable."}

        # Layer 6 — deterministic discernment fusion (GraphRAG AI is recorded above)
        t = time.monotonic()
        try:
            decision_obj = EngineDecision(
                id=inp.decision_id,
                user_id=inp.user_id,
                title=inp.title,
                description=inp.description,
                category=inp.category,
                urgency_level=inp.urgency,
                importance_level=inp.importance,
                created_at=datetime.utcnow(),
            )
            emotion_obj = EngineEmotion(
                emotions=inp.emotions,
                stress_level=inp.stress_level,
                anxiety_level=inp.anxiety_level,
                fatigue_level=inp.fatigue_level,
                spiritual_dryness=inp.spiritual_dryness,
                emotional_stability=inp.emotional_stability,
            )
            motive_obj = self._build_motive(inp.motive_scores)

            v2_result = self.v2.discern_v2(
                decision=decision_obj,
                emotional_state=emotion_obj,
                motive_profile=motive_obj,
                spiritual_principles=principles,
                user_id=inp.user_id,
                current_snapshot=current_snapshot,
                past_behavior_types=inp.past_behavior_types,
                graph_context=rag_context.context_text,
            )
            formatted = format_v2_result(v2_result)
            out.v1_analysis         = formatted.get("v1_analysis")
            out.alignment           = formatted.get("3_spiritual_alignment", {})
            out.intervention        = formatted.get("4_intervention", {})
            if rag_context.ai_synthesis.get("status") == "COMPLETED":
                out.intervention["graph_rag_reflection"] = rag_context.ai_synthesis
            out.is_high_risk_window = v2_result.is_high_risk_window
            out.pause_recommended   = v2_result.pause_recommended
            layers.append(LayerResult(
                layer="discernment_fusion", success=True,
                data={"high_risk_window": v2_result.is_high_risk_window},
                duration_ms=(time.monotonic() - t) * 1000,
            ))
        except Exception as exc:
            logger.warning("[pipeline] discernment layer failed: %s", exc)
            layers.append(LayerResult(layer="discernment_fusion", success=False, error=str(exc)))
            out.alignment    = {"narrative": "Discernment layer unavailable."}
            out.intervention = {
                "awareness_prompts": ["Take time to reflect before deciding."],
                "reflective_questions": out.reflective_questions,
            }

        # Determine global risk window
        out.is_high_risk_window = (
            out.is_high_risk_window
            or self._assess_risk_window(inp, graph_insight, temporal_insight)
        )
        out.pause_recommended = out.is_high_risk_window or out.pause_recommended

        # Layer 7 — Formation Engine (v3: character dimension tracking)
        t = time.monotonic()
        try:
            _loop_broken = out.is_high_risk_window and bool(out.structural.get("cycles_detected"))
            _pattern_categories = list({
                p.get("category", "")
                for p in KNOWN_PATTERNS
                if p["label"] in out.structural.get("patterns", [])
            } - {""})
            _emotional_intensity = max(
                (e.get("intensity", 5) for e in inp.emotions), default=5.0
            )
            formation_insight: Optional[FormationInsight] = self.formation.analyze_sync(
                user_id            = inp.user_id,
                pattern_categories = _pattern_categories,
                loop_broken        = _loop_broken,
                decision_category  = inp.category,
                session_id         = inp.decision_id,
                emotional_intensity= float(_emotional_intensity),
                reflection_active  = bool(inp.reflection_notes),
            )
            out.formation = formation_insight.to_dict()
            layers.append(LayerResult(
                layer="formation_engine", success=True,
                data={"arc": formation_insight.formation_arc, "trajectory": formation_insight.trajectory_direction},
                duration_ms=(time.monotonic() - t) * 1000,
            ))
        except Exception as exc:
            logger.warning("[pipeline] formation layer failed: %s", exc)
            layers.append(LayerResult(layer="formation_engine", success=False, error=str(exc)))
            out.formation = {"summary": "Formation layer unavailable."}

        out.pipeline_layers = layers
        return out

    # ── Write-back (call after user confirms / saves decision) ───────────────

    def write_back(
        self,
        inp:                 PipelineInput,
        matched_pattern_ids: List[str],
        outcome:             Optional[str] = None,
    ) -> None:
        """
        Persist this session into PostgreSQL graph storage and TimescaleDB.
        Call once after guidance is shown and user confirms.
        Failures are silent — never block the user.
        """
        dominant_motive   = self._dominant_motive(inp.motive_scores)
        dominant_emotion  = self._dominant_emotion(inp.emotions)

        # Graph write-back
        try:
            self.graph.write_back(
                user_id=inp.user_id,
                decision_id=inp.decision_id,
                dominant_emotion=dominant_emotion,
                dominant_motive=dominant_motive,
                decision_category=inp.category,
                behavior_type=inp.category,
                matched_pattern_ids=matched_pattern_ids,
                outcome=outcome,
            )
        except Exception as exc:
            logger.warning("[pipeline] graph write_back failed: %s", exc)

        # Timeline write-back
        try:
            snapshot = {
                "anxiety_level":       inp.anxiety_level,
                "peace_level":         inp.peace_level,
                "clarity_level":       inp.clarity_level,
                "spiritual_dryness":   inp.spiritual_dryness,
                "emotional_stability": inp.emotional_stability,
                "decision_confidence": inp.decision_confidence,
            }
            self.temporal.record_snapshot(
                user_id=inp.user_id,
                snapshot=snapshot,
                decision_id=inp.decision_id,
                context=inp.category,
            )
        except Exception as exc:
            logger.warning("[pipeline] temporal write_back failed: %s", exc)

        # Emotion series write-back
        try:
            for emo in inp.emotions:
                self.temporal.record_emotion(
                    user_id=inp.user_id,
                    emotion_type=emo.get("type", "unknown"),
                    intensity=emo.get("intensity", 5),
                    trigger=emo.get("trigger"),
                    decision_id=inp.decision_id,
                )
        except Exception as exc:
            logger.warning("[pipeline] emotion write_back failed: %s", exc)

        # Formation Engine write-back (v3)
        try:
            pattern_categories = list({
                p.get("category", "")
                for p in KNOWN_PATTERNS
                if any(pid in p.get("id", "") for pid in matched_pattern_ids)
            } - {""})
            loop_broken = bool(outcome and "break" in outcome.lower())
            _emotional_intensity = max(
                (e.get("intensity", 5) for e in inp.emotions), default=5.0
            )
            formation_insight = self.formation.analyze_sync(
                user_id            = inp.user_id,
                pattern_categories = pattern_categories,
                loop_broken        = loop_broken,
                decision_category  = inp.category,
                session_id         = inp.decision_id,
                emotional_intensity= float(_emotional_intensity),
                reflection_active  = bool(inp.reflection_notes),
            )
            dimension_deltas = {
                dim: sc.delta
                for dim, sc in formation_insight.current_snapshot.dimensions.items()
            }
            # Synchronous write path. The previous event-loop dispatch
            # (get_event_loop/ensure_future) silently no-op'd from this sync
            # threadpool code, dropping formation events. Write directly.
            from formation_bridge import record_formation_event_sync
            record_formation_event_sync(
                self.formation,
                user_id            = inp.user_id,
                session_id         = inp.decision_id,
                pattern_categories = pattern_categories,
                loop_broken        = loop_broken,
                dimension_deltas   = dimension_deltas,
                decision_category  = inp.category,
            )
        except Exception as exc:
            logger.warning("[pipeline] formation write_back failed: %s", exc)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _dominant_motive(self, scores: Optional[Dict[str, float]]) -> str:
        if not scores:
            return "fear"
        return max(scores, key=lambda k: scores[k])

    def _dominant_emotion(self, emotions: List[Dict[str, Any]]) -> str:
        if not emotions:
            return "anxiety"
        return max(emotions, key=lambda e: e.get("intensity", 0)).get("type", "anxiety")

    def _build_principles(self, raw: List[Dict[str, Any]]) -> List[EnginePrinciple]:
        out = []
        for r in raw:
            try:
                out.append(EnginePrinciple(
                    id=r.get("id", str(uuid.uuid4())),
                    principle_text=r.get("principle_text", r.get("text", "")),
                    scripture_reference=r.get("scripture_reference", r.get("scripture", "")),
                    category=r.get("category", "general"),
                    relevance_score=float(r.get(
                        "relevance_score", r.get("similarity", r.get("score", 0.5))
                    )),
                ))
            except Exception:
                continue
        return out

    def _build_motive(self, scores: Optional[Dict[str, float]]) -> EngineMotive:
        s = scores or {}
        dominant = self._dominant_motive(scores)
        secondary = None
        sorted_s = sorted(
            [(k, v) for k, v in s.items() if k != dominant],
            key=lambda x: x[1], reverse=True,
        )
        if sorted_s:
            secondary = sorted_s[0][0]
        return EngineMotive(
            fear_driven_score=s.get("fear", 0.5),
            pride_driven_score=s.get("pride", 0.2),
            love_driven_score=s.get("love", 0.3),
            desire_driven_score=s.get("desire", 0.3),
            dominant_motive=dominant,
            secondary_motive=secondary,
        )

    def _get_reflective_questions(self, pattern_ids: List[str]) -> List[str]:
        pid_set = set(pattern_ids)
        questions: List[str] = []
        for p in KNOWN_PATTERNS:
            if p["id"] in pid_set and "reflective_question" in p:
                questions.append(p["reflective_question"])
        return questions[:3]

    def _format_structural(
        self,
        insight: GraphInsight,
        questions: List[str],
        reasoning: Optional[FormationReasoning] = None,
    ) -> Dict[str, Any]:
        base = {
            "summary":         insight.structural_summary,
            "patterns":        insight.pattern_labels,
            "cycles_detected": len(insight.cycles) > 0,
            "cycle_labels":    [c.description for c in insight.cycles],
            "interventions": [
                {
                    "break_at":    iv.get("break_at"),
                    "suggestion":  iv.get("suggestion"),
                    "scripture":   iv.get("scripture"),
                    "category":    iv.get("category"),
                }
                for iv in insight.intervention_points
            ],
            "reflective_questions": questions,
        }
        if reasoning:
            base["reasoning_v22"] = reasoning.to_dict()
        return base

    def _format_temporal(self, insight: TemporalInsight) -> Dict[str, Any]:
        return {
            "trend":         insight.trend_direction.value,
            "season":        insight.spiritual_season.value,
            "season_narrative": insight.season_narrative,
            "trend_narrative":  insight.trend_narrative,
            "detected_patterns": [
                {
                    "type":        p.pattern_type.value,
                    "description": p.description,
                    "confidence":  round(p.confidence, 2),
                }
                for p in insight.detected_patterns
            ],
            "intervention_window": insight.intervention_window,
            "data_points_available": insight.data_points_available,
        }

    def _assess_risk_window(
        self,
        inp: PipelineInput,
        graph: Optional[GraphInsight],
        temporal: Optional[TemporalInsight],
    ) -> bool:
        """
        Heuristic: flag high-risk decision window when multiple stress signals align.
        This is advisory, not deterministic.
        """
        score = 0
        if inp.anxiety_level >= 7:   score += 1
        if inp.fatigue_level >= 7:   score += 1
        if inp.spiritual_dryness >= 7: score += 1
        if inp.clarity_level <= 3:   score += 1
        if inp.urgency >= 4:         score += 1

        if graph and len(graph.cycles) >= 2:
            score += 1
        if temporal and temporal.trend_direction == TrendDirection.DECLINING:
            score += 1
        if temporal and temporal.spiritual_season == SpiritualSeason.DRY:
            score += 1

        return score >= 4


# ──────────────────────────────────────────────────────────────────────────────
# Module-level singleton factory
# ──────────────────────────────────────────────────────────────────────────────

_pipeline: Optional[FormationPipeline] = None


def get_pipeline(db_pool=None) -> FormationPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = FormationPipeline(db_pool=db_pool)
    return _pipeline


def init_pipeline(db_pool) -> FormationPipeline:
    global _pipeline
    _pipeline = FormationPipeline(db_pool=db_pool)
    return _pipeline
