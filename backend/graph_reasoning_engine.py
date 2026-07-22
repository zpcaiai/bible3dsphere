#!/usr/bin/env python3
"""
SFDS Graph Reasoning Fusion Engine — v2.2

Performs MULTI-LAYER STRUCTURED REASONING over human inner dynamics by
combining three knowledge sources:

  1. PostgreSQL Graph Structure   — causal patterns, loops, intervention points
  2. Vector DB Semantic Knowledge — spiritual principles, similar cases
  3. Structured Fusion           — deterministic synthesis across all layers

Architecture (6 reasoning layers):

  Layer 1 — Graph Structure Interpretation
            "Which pattern trajectory is the user currently on?"

  Layer 2 — Loop Dynamics Analysis
            "Is a self-reinforcing cycle active? What is its feedback mechanism?"

  Layer 3 — Breakpoint Detection
            "Where in the loop is intervention most leveraged?"

  Layer 4 — Vector Knowledge Alignment
            "Which spiritual principles match and can break this loop?"

  Layer 5 — Temporal Context (optional)
            "Is this pattern increasing? Is this a peak state? Third recurrence?"

  Layer 6 — Synthesis (final reasoning output)
            Combines all layers into a structured FormationReasoning output.

Design invariants (inherited from SFDS philosophy):
  - System is a MIRROR, not a judge.
  - All language is probabilistic — "may", "might", "possible".
  - NO identity labelling. NO moralising. NO guilt induction.
  - Every output preserves user autonomy and mystery.
  - All layers fail gracefully — never blocks the pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

from graph_layer import (
    GraphService, GraphInsight, CausalChain,
    KNOWN_PATTERNS, PATTERN_SUBGRAPHS, PatternSubgraph,
    get_graph_service,
    EdgeType, NodeLabel,
)


# ──────────────────────────────────────────────────────────────────────────────
# Output dataclasses
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class LoopDiagnosis:
    """Result of Layer 2: active loop identification."""
    loop_id:          str
    loop_label:       str
    is_active:        bool
    feedback_node:    str            # OutcomeNode reinforcing the loop
    feedback_target:  str            # MotiveNode being reinforced
    recurrence_count: int = 0        # from TimescaleDB if available
    confidence:       float = 0.5    # 0–1 probabilistic estimate
    note: str = ""


@dataclass
class BreakpointAnalysis:
    """Result of Layer 3: highest-leverage intervention point."""
    target_node:        str          # BehaviorNode or MotiveNode
    target_layer:       str          # "motive" | "behavior" | "emotion"
    edge_type:          str          # which edge to interrupt
    leverage_score:     float        # 0–1; higher = earlier in chain = more leverage
    principle_id:       str          # PrincipleNode that BREAKS this edge
    principle_text:     str
    reasoning:          str          # why this is the optimal breakpoint
    scripture:          str = ""


@dataclass
class PrincipleAlignment:
    """Result of Layer 4: aligned spiritual principles."""
    principle_id:    str
    principle_text:  str
    action_type:     str    # BREAKS | INFLUENCES
    alignment_score: float  # 0–1 relevance
    source:          str    # "graph" | "vector" | "both"
    scripture:       str = ""
    note:            str = ""


@dataclass
class FormationReasoning:
    """
    Full output of the 6-layer Graph Reasoning Fusion Engine.

    Represents STRUCTURED REASONING over human inner dynamics —
    not advice, not diagnosis, not verdict.
    """
    # Layer outputs
    structural_insight:   str = ""         # Layer 1 narrative
    loop_diagnosis:       Optional[LoopDiagnosis] = None    # Layer 2
    breakpoint:           Optional[BreakpointAnalysis] = None  # Layer 3
    principle_alignments: List[PrincipleAlignment] = field(default_factory=list)  # Layer 4
    temporal_context:     Optional[Dict[str, Any]] = None   # Layer 5
    synthesis:            Dict[str, Any] = field(default_factory=dict)  # Layer 6

    # Structural summary fields (flattened for API)
    pattern_labels:       List[str] = field(default_factory=list)
    active_loops:         List[str] = field(default_factory=list)
    root_drivers:         Dict[str, str] = field(default_factory=dict)  # {emotion, motive}
    reflective_guidance:  List[str] = field(default_factory=list)

    # Meta
    reasoning_layers_run: List[str] = field(default_factory=list)
    confidence_overall:   float = 0.5

    DISCLAIMER: str = field(default=(
        "This reasoning is a structural mirror — not a spiritual verdict. "
        "All patterns describe possible dynamics, not fixed identity. "
        "Human freedom, grace, and mystery always exceed what any model can capture. "
        "NEVER optimizes for: human behavior change, emotional outcome optimization, "
        "personality state improvement, or behavioral compliance rate."
    ), compare=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "structural_insight":  self.structural_insight,
            "loop_diagnosis": (
                {
                    "loop_id":         self.loop_diagnosis.loop_id,
                    "loop_label":      self.loop_diagnosis.loop_label,
                    "is_active":       self.loop_diagnosis.is_active,
                    "feedback_node":   self.loop_diagnosis.feedback_node,
                    "feedback_target": self.loop_diagnosis.feedback_target,
                    "recurrence":      self.loop_diagnosis.recurrence_count,
                    "confidence":      self.loop_diagnosis.confidence,
                    "note":            self.loop_diagnosis.note,
                }
                if self.loop_diagnosis else None
            ),
            "breakpoint": (
                {
                    "target_node":    self.breakpoint.target_node,
                    "target_layer":   self.breakpoint.target_layer,
                    "leverage_score": self.breakpoint.leverage_score,
                    "principle_id":   self.breakpoint.principle_id,
                    "principle_text": self.breakpoint.principle_text,
                    "reasoning":      self.breakpoint.reasoning,
                    "scripture":      self.breakpoint.scripture,
                }
                if self.breakpoint else None
            ),
            "principle_alignments": [
                {
                    "principle_id":    pa.principle_id,
                    "principle_text":  pa.principle_text,
                    "action_type":     pa.action_type,
                    "alignment_score": pa.alignment_score,
                    "source":          pa.source,
                    "scripture":       pa.scripture,
                    "note":            pa.note,
                }
                for pa in self.principle_alignments
            ],
            "temporal_context":   self.temporal_context,
            "synthesis":          self.synthesis,
            "pattern_labels":     self.pattern_labels,
            "active_loops":       self.active_loops,
            "root_drivers":       self.root_drivers,
            "reflective_guidance":self.reflective_guidance,
            "reasoning_layers_run": self.reasoning_layers_run,
            "confidence_overall": self.confidence_overall,
            "disclaimer":         self.DISCLAIMER,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Graph Reasoning Fusion Engine
# ──────────────────────────────────────────────────────────────────────────────

class GraphReasoningFusion:
    """
    Implements the 6-layer structured reasoning pipeline.

    Use via:
        engine = GraphReasoningFusion(graph_service)
        result = engine.reason(
            user_id="...",
            dominant_emotion="anxiety",
            dominant_motive="fear_driven_control",
            graph_insight=insight,         # from GraphService.analyze()
            vector_principles=[...],       # from pgvector retrieval
            temporal_context={...},        # from TemporalEngine (optional)
        )
    """

    # Node-type → layer name mapping for leverage scoring
    _LAYER_LEVERAGE: Dict[str, float] = {
        NodeLabel.EMOTION:   0.95,   # earliest in chain = highest leverage
        NodeLabel.MOTIVE:    0.90,   # second — structural root cause
        NodeLabel.BEHAVIOR:  0.65,   # visible — easier to observe, harder to change
        NodeLabel.OUTCOME:   0.30,   # consequence — low leverage (too late)
        NodeLabel.SPIRITUAL: 0.85,   # spiritual state — high formation leverage
        NodeLabel.PRINCIPLE: 1.00,   # principle injection — always maximum
    }

    def __init__(self, graph_service: Optional[GraphService] = None):
        self._graph = graph_service or get_graph_service()

    # ── Public entry point ────────────────────────────────────────────────────

    def reason(
        self,
        user_id:           str,
        dominant_emotion:  str,
        dominant_motive:   str,
        graph_insight:     Optional[GraphInsight],
        vector_principles: Optional[List[Dict[str, Any]]] = None,
        temporal_context:  Optional[Dict[str, Any]] = None,
    ) -> FormationReasoning:
        """
        Execute all 6 reasoning layers. Always returns a FormationReasoning.
        Individual layer failures are silently degraded.
        """
        result = FormationReasoning()
        layers_run: List[str] = []

        # ── Layer 1: Graph Structure Interpretation ───────────────────────────
        try:
            result.structural_insight, result.pattern_labels = \
                self._layer1_structural(dominant_emotion, dominant_motive, graph_insight)
            layers_run.append("layer1_structural")
        except Exception as exc:
            logger.warning("[reasoning] layer1 failed: %s", exc)
            result.structural_insight = "Structural analysis could not be completed."

        # ── Layer 2: Loop Dynamics Analysis ───────────────────────────────────
        try:
            result.loop_diagnosis, result.active_loops = \
                self._layer2_loops(dominant_motive, graph_insight, temporal_context)
            layers_run.append("layer2_loops")
        except Exception as exc:
            logger.warning("[reasoning] layer2 failed: %s", exc)

        # ── Layer 3: Breakpoint Detection ─────────────────────────────────────
        try:
            result.breakpoint = self._layer3_breakpoint(
                dominant_motive, dominant_emotion, graph_insight
            )
            layers_run.append("layer3_breakpoint")
        except Exception as exc:
            logger.warning("[reasoning] layer3 failed: %s", exc)

        # ── Layer 4: Vector Knowledge Alignment ───────────────────────────────
        try:
            result.principle_alignments = self._layer4_principles(
                dominant_motive, dominant_emotion,
                graph_insight, vector_principles or []
            )
            layers_run.append("layer4_principles")
        except Exception as exc:
            logger.warning("[reasoning] layer4 failed: %s", exc)

        # ── Layer 5: Temporal Context ─────────────────────────────────────────
        if temporal_context:
            try:
                result.temporal_context = self._layer5_temporal(
                    temporal_context, result.loop_diagnosis
                )
                layers_run.append("layer5_temporal")
            except Exception as exc:
                logger.warning("[reasoning] layer5 failed: %s", exc)

        # ── Layer 6: Synthesis ────────────────────────────────────────────────
        try:
            result.root_drivers = self._extract_root_drivers(
                dominant_emotion, dominant_motive, graph_insight
            )
            result.reflective_guidance = self._build_reflective_guidance(
                result.loop_diagnosis, result.breakpoint, result.principle_alignments,
                graph_insight
            )
            result.synthesis = self._layer6_synthesis(result)
            result.confidence_overall = self._estimate_confidence(result, graph_insight)
            layers_run.append("layer6_synthesis")
        except Exception as exc:
            logger.warning("[reasoning] layer6 failed: %s", exc)
            result.synthesis = {"narrative": "Synthesis layer could not complete."}

        result.reasoning_layers_run = layers_run
        return result

    # ── Layer 1: Structural Interpretation ───────────────────────────────────

    def _layer1_structural(
        self,
        emotion: str,
        motive: str,
        graph_insight: Optional[GraphInsight],
    ) -> Tuple[str, List[str]]:
        """
        Identify the current node in the user's graph trajectory and
        which causal chain is dominant.
        """
        if graph_insight and graph_insight.pattern_labels:
            labels = graph_insight.pattern_labels
            primary = labels[0]
            cycle_note = ""
            if graph_insight.cycles:
                cycle_note = (
                    f" A recurring loop may be active — "
                    f"'{graph_insight.cycles[0].description}' has been detected."
                )
            narrative = (
                f"The structural pattern most consistent with the current state is: "
                f"'{primary}'.{cycle_note} "
                f"The dominant emotional signal is '{emotion}', "
                f"which may be driving a '{motive}' motivational posture."
            )
            return narrative, labels

        # Offline fallback — match from KNOWN_PATTERNS
        matched = []
        for p in KNOWN_PATTERNS:
            chain = p.get("chain", [])
            if emotion in chain or motive in chain:
                matched.append(p["label"])
        if matched:
            narrative = (
                f"Based on the emotional signal '{emotion}' and motive '{motive}', "
                f"the following structural pattern may be active: '{matched[0]}'. "
                f"This is a pattern-match inference, not a confirmed trajectory."
            )
            return narrative, matched
        return (
            f"No specific structural pattern was matched for emotion='{emotion}' "
            f"and motive='{motive}'. The current state may be novel or transitional.",
            [],
        )

    # ── Layer 2: Loop Dynamics Analysis ──────────────────────────────────────

    def _layer2_loops(
        self,
        dominant_motive: str,
        graph_insight: Optional[GraphInsight],
        temporal_context: Optional[Dict[str, Any]],
    ) -> Tuple[Optional[LoopDiagnosis], List[str]]:
        """
        Detect whether a self-reinforcing feedback loop is currently active,
        and identify the REINFORCES edge (OutcomeNode → MotiveNode).
        """
        active_loops: List[str] = []

        # Try live cycles from graph insight first
        if graph_insight and graph_insight.cycles:
            cycle = graph_insight.cycles[0]
            active_loops = [c.description for c in graph_insight.cycles]

            # Find matching PatternSubgraph for REINFORCES edge detail
            sg = self._find_subgraph_by_motive(dominant_motive)
            feedback_node = "unknown_outcome"
            feedback_target = dominant_motive
            confidence = 0.75

            if sg and sg.reinforces_edges:
                feedback_node, feedback_target = sg.reinforces_edges[0]

            recurrence = 0
            if temporal_context:
                recurrence = temporal_context.get("recurrence_count", 0)

            return LoopDiagnosis(
                loop_id        = cycle.description.replace(" ", "_")[:40],
                loop_label     = cycle.description,
                is_active      = True,
                feedback_node  = feedback_node,
                feedback_target= feedback_target,
                recurrence_count=recurrence,
                confidence     = confidence,
                note           = (
                    f"The outcome '{feedback_node}' may be reinforcing the motive "
                    f"'{feedback_target}', sustaining the loop. "
                    + (f"This pattern may have recurred {recurrence} time(s) recently."
                       if recurrence > 1 else "")
                ),
            ), active_loops

        # Offline: check PatternSubgraphs for motive match
        sg = self._find_subgraph_by_motive(dominant_motive)
        if sg and sg.reinforces_edges:
            out_node, mot_node = sg.reinforces_edges[0]
            active_loops = [sg.label]
            recurrence = temporal_context.get("recurrence_count", 0) if temporal_context else 0
            return LoopDiagnosis(
                loop_id        = sg.pattern_id,
                loop_label     = sg.label,
                is_active      = True,
                feedback_node  = out_node,
                feedback_target= mot_node,
                recurrence_count=recurrence,
                confidence     = 0.50,
                note           = (
                    f"Pattern inferred from known library. "
                    f"The outcome '{out_node}' may be sustaining the '{mot_node}' motive "
                    f"through a REINFORCES feedback edge. Confidence is moderate — "
                    f"this is a structural possibility, not a confirmed state."
                ),
            ), active_loops

        return None, []

    # ── Layer 3: Breakpoint Detection ────────────────────────────────────────

    def _layer3_breakpoint(
        self,
        dominant_motive: str,
        dominant_emotion: str,
        graph_insight: Optional[GraphInsight],
    ) -> Optional[BreakpointAnalysis]:
        """
        Find the optimal intervention point — the earliest, highest-leverage
        node in the active chain. Motive layer is almost always highest leverage
        because it precedes behavior and has BREAKS + INFLUENCES principles.
        """
        # If graph insight has intervention points, use the first (most relevant)
        if graph_insight and graph_insight.intervention_points:
            iv = graph_insight.intervention_points[0]
            break_at = iv.get("break_at", dominant_motive)
            target_layer = self._classify_node_layer(break_at)
            leverage = self._LAYER_LEVERAGE.get(
                self._node_label_for_layer(target_layer), 0.65
            )
            return BreakpointAnalysis(
                target_node    = break_at,
                target_layer   = target_layer,
                edge_type      = EdgeType.LEADS_TO,
                leverage_score = leverage,
                principle_id   = iv.get("pattern_id", ""),
                principle_text = iv.get("suggestion", ""),
                reasoning      = (
                    f"The node '{break_at}' was identified as the highest-leverage "
                    f"intervention point. Acting at the {target_layer} layer is typically "
                    f"more effective than addressing behavior or outcome after the fact. "
                    f"The suggestion: \"{iv.get('suggestion', '')}\""
                ),
                scripture      = iv.get("scripture", ""),
            )

        # Fallback: use PatternSubgraph BREAKS edges
        sg = self._find_subgraph_by_motive(dominant_motive)
        if sg and sg.breaks_edges:
            principle_id, behavior_node = sg.breaks_edges[0]
            # Motive-layer intervention is always higher leverage than behavior
            return BreakpointAnalysis(
                target_node    = dominant_motive,
                target_layer   = "motive",
                edge_type      = EdgeType.LEADS_TO,
                leverage_score = self._LAYER_LEVERAGE[NodeLabel.MOTIVE],
                principle_id   = principle_id,
                principle_text = principle_id.replace("_", " "),
                reasoning      = (
                    f"The highest-leverage intervention is at the Motive layer "
                    f"('{dominant_motive}'), not the Behavior layer ('{behavior_node}'). "
                    f"Interrupting the motive before it generates behavior is structurally "
                    f"more effective. The principle '{principle_id}' may address this motive "
                    f"through the INFLUENCES edge."
                ),
            )

        # Last resort: emotion-layer recommendation
        return BreakpointAnalysis(
            target_node    = dominant_emotion,
            target_layer   = "emotion",
            edge_type      = EdgeType.CAUSES,
            leverage_score = self._LAYER_LEVERAGE[NodeLabel.EMOTION],
            principle_id   = "",
            principle_text = "",
            reasoning      = (
                f"No specific breakpoint was identified from graph patterns. "
                f"The earliest intervention remains at the emotional source "
                f"('{dominant_emotion}'). Addressing the root emotion may prevent "
                f"the full chain from activating."
            ),
        )

    # ── Layer 4: Principle Alignment ─────────────────────────────────────────

    def _layer4_principles(
        self,
        dominant_motive:   str,
        dominant_emotion:  str,
        graph_insight:     Optional[GraphInsight],
        vector_principles: List[Dict[str, Any]],
    ) -> List[PrincipleAlignment]:
        """
        Merge and rank spiritual principles from two sources:
        - Graph BREAKS/INFLUENCES edges (structural — always included if available)
        - Vector DB retrieval (semantic — scored by relevance)

        Each principle is tagged with source and action_type.
        """
        alignments: List[PrincipleAlignment] = []
        seen_ids: set = set()

        # 1. Graph-derived principles (from PatternSubgraph BREAKS + INFLUENCES)
        sg = self._find_subgraph_by_motive(dominant_motive)
        if sg:
            for (principle_id, _) in sg.breaks_edges:
                if principle_id not in seen_ids:
                    seen_ids.add(principle_id)
                    alignments.append(PrincipleAlignment(
                        principle_id    = principle_id,
                        principle_text  = principle_id.replace("_", " "),
                        action_type     = EdgeType.BREAKS,
                        alignment_score = 0.90,
                        source          = "graph",
                        note            = (
                            f"This principle has a BREAKS edge to behaviors in the "
                            f"'{sg.pattern_id}' pattern — structurally targeted."
                        ),
                        scripture       = sg.scripture,
                    ))
            for (principle_id, _) in sg.influences_edges:
                if principle_id not in seen_ids:
                    seen_ids.add(principle_id)
                    alignments.append(PrincipleAlignment(
                        principle_id    = principle_id,
                        principle_text  = principle_id.replace("_", " "),
                        action_type     = EdgeType.INFLUENCES,
                        alignment_score = 0.80,
                        source          = "graph",
                        note            = (
                            f"This principle INFLUENCES the motive layer of the "
                            f"'{sg.pattern_id}' pattern — formational rather than behavioral."
                        ),
                        scripture       = sg.scripture,
                    ))

        # 2. Graph intervention_points (from GraphInsight, already matched)
        if graph_insight and graph_insight.intervention_points:
            for iv in graph_insight.intervention_points:
                suggestion = iv.get("suggestion", "")
                if suggestion and suggestion not in seen_ids:
                    seen_ids.add(suggestion)
                    alignments.append(PrincipleAlignment(
                        principle_id    = iv.get("pattern_id", "graph_intervention"),
                        principle_text  = suggestion,
                        action_type     = EdgeType.BREAKS,
                        alignment_score = 0.85,
                        source          = "graph",
                        scripture       = iv.get("scripture", ""),
                        note            = f"Intervention suggested at '{iv.get('break_at', '')}' node.",
                    ))

        # 3. Vector DB principles (semantic retrieval)
        for vp in vector_principles:
            text = vp.get("principle_text", vp.get("text", ""))
            pid  = vp.get("id", text[:30])
            if pid not in seen_ids and text:
                seen_ids.add(pid)
                raw_score = float(
                    vp.get("relevance_score", vp.get("similarity", vp.get("score", 0.5)))
                )
                # Boost score if the text semantically overlaps with current motive label
                boost = 0.1 if dominant_motive.replace("_", " ") in text.lower() else 0.0
                alignments.append(PrincipleAlignment(
                    principle_id    = pid,
                    principle_text  = text,
                    action_type     = EdgeType.INFLUENCES,
                    alignment_score = min(1.0, raw_score + boost),
                    source          = "vector",
                    scripture       = vp.get("scripture_reference", vp.get("scripture", "")),
                    note            = "Retrieved by semantic similarity to current emotional state.",
                ))

        # Sort by alignment_score descending; cap at 5
        alignments.sort(key=lambda a: a.alignment_score, reverse=True)
        return alignments[:5]

    # ── Layer 5: Temporal Context Enrichment ─────────────────────────────────

    def _layer5_temporal(
        self,
        temporal_context: Dict[str, Any],
        loop_diagnosis: Optional[LoopDiagnosis],
    ) -> Dict[str, Any]:
        """
        Enrich the temporal data with loop-specific recurrence context.
        """
        trend     = temporal_context.get("trend", "stable")
        season    = temporal_context.get("season", "stable")
        patterns  = temporal_context.get("detected_patterns", [])
        recurrence= temporal_context.get("recurrence_count", 0)

        # Build narrative
        trend_narrative = temporal_context.get("trend_narrative", "")
        season_narrative = temporal_context.get("season_narrative", "")

        recurrence_note = ""
        if recurrence >= 3:
            recurrence_note = (
                f"This appears to be at least the {recurrence}rd recurrence of this pattern — "
                f"suggesting a potentially entrenched loop rather than a one-time state."
            )
        elif recurrence == 2:
            recurrence_note = (
                "This appears to be the second recurrence of this pattern. "
                "A recurring loop may be forming."
            )
        elif recurrence == 1:
            recurrence_note = "This is the first detected instance of this pattern."

        loop_note = ""
        if loop_diagnosis and loop_diagnosis.is_active:
            loop_note = (
                f"The active loop ('{loop_diagnosis.loop_label}') may be intensifying — "
                f"feedback is flowing from '{loop_diagnosis.feedback_node}' back to "
                f"'{loop_diagnosis.feedback_target}'."
            )

        return {
            "trend":              trend,
            "season":             season,
            "trend_narrative":    trend_narrative,
            "season_narrative":   season_narrative,
            "detected_patterns":  patterns,
            "recurrence_count":   recurrence,
            "recurrence_note":    recurrence_note,
            "loop_context_note":  loop_note,
            "is_peak_state":      temporal_context.get("is_peak_anxiety", False),
            "intervention_window":temporal_context.get("intervention_window", False),
        }

    # ── Layer 6: Synthesis ────────────────────────────────────────────────────

    def _layer6_synthesis(self, result: FormationReasoning) -> Dict[str, Any]:
        """
        Combine all layers into a structured, non-directive synthesis.
        Produces 6 output sections as specified in the v2.2 prompt.
        """
        # 1. STRUCTURAL INSIGHT
        structural = result.structural_insight or "Structural pattern not identified."

        # 2. LOOP DIAGNOSIS
        loop_section = "No active loop detected in the current data."
        if result.loop_diagnosis and result.loop_diagnosis.is_active:
            ld = result.loop_diagnosis
            loop_section = (
                f"A possible feedback loop may be active: '{ld.loop_label}'. "
                f"The outcome node '{ld.feedback_node}' may be REINFORCING the motive "
                f"'{ld.feedback_target}', creating a self-sustaining cycle. "
                f"Confidence: {int(ld.confidence * 100)}%. {ld.note}"
            )

        # 3. ROOT DRIVERS
        root_section = "Root drivers could not be fully traced."
        if result.root_drivers:
            emotion = result.root_drivers.get("emotion", "unknown")
            motive  = result.root_drivers.get("motive", "unknown")
            root_section = (
                f"The current pattern may originate from the emotion '{emotion}', "
                f"which could be generating a '{motive}' motivational response. "
                f"This emotion-to-motive pathway (CAUSES edge) is a potential root driver, "
                f"though other factors always remain possible."
            )

        # 4. BREAKPOINT
        break_section = "No specific breakpoint was identified."
        if result.breakpoint:
            bp = result.breakpoint
            break_section = (
                f"The most leveraged intervention point appears to be at the "
                f"'{bp.target_layer}' layer — specifically the node '{bp.target_node}'. "
                f"Leverage score: {int(bp.leverage_score * 100)}%. "
                f"{bp.reasoning}"
            )

        # 5. PRINCIPLE ALIGNMENT
        principle_section = "No aligned principles identified."
        if result.principle_alignments:
            top = result.principle_alignments[0]
            others = result.principle_alignments[1:3]
            principle_section = (
                f"Primary aligned principle: '{top.principle_text}' "
                f"(source: {top.source}, action: {top.action_type}). "
                + ("Additional relevant principles: "
                   + "; ".join(f"'{p.principle_text}'" for p in others)
                   if others else "")
            )

        # 6. REFLECTIVE GUIDANCE
        guidance_section = result.reflective_guidance or [
            "Take time to notice what is driving urgency in this decision.",
            "Consider what you would advise a trusted friend in the same situation.",
        ]

        return {
            "STRUCTURAL_INSIGHT":  structural,
            "LOOP_DIAGNOSIS":      loop_section,
            "ROOT_DRIVERS":        root_section,
            "BREAKPOINT":          break_section,
            "PRINCIPLE_ALIGNMENT": principle_section,
            "REFLECTION_GUIDANCE": guidance_section,
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _find_subgraph_by_motive(self, motive: str) -> Optional[PatternSubgraph]:
        """Find the first PatternSubgraph where `motive` is in motive_nodes."""
        for sg in PATTERN_SUBGRAPHS:
            if motive in sg.motive_nodes:
                return sg
        # Partial match fallback
        motive_key = motive.split("_")[0]  # e.g. "fear_driven_control" → "fear"
        for sg in PATTERN_SUBGRAPHS:
            if any(motive_key in m for m in sg.motive_nodes):
                return sg
        return None

    def _classify_node_layer(self, node_type: str) -> str:
        """
        Heuristically classify a node type string into a layer name.
        Checks against known node collections from PATTERN_SUBGRAPHS.
        """
        for sg in PATTERN_SUBGRAPHS:
            if node_type in sg.emotion_nodes:
                return "emotion"
            if node_type in sg.motive_nodes:
                return "motive"
            if node_type in sg.behavior_nodes:
                return "behavior"
            if node_type in sg.outcome_nodes:
                return "outcome"
            if node_type in sg.principle_nodes:
                return "principle"
        # Heuristic keywords
        keywords_to_layer = {
            "control": "motive", "fear": "emotion", "shame": "emotion",
            "pride": "emotion", "desire": "emotion", "avoid": "motive",
            "overwork": "behavior", "procrastin": "behavior",
            "burnout": "outcome", "exhaust": "outcome", "regret": "outcome",
        }
        nl = node_type.lower()
        for kw, layer in keywords_to_layer.items():
            if kw in nl:
                return layer
        return "behavior"  # safe default

    def _node_label_for_layer(self, layer: str) -> str:
        return {
            "emotion":   NodeLabel.EMOTION,
            "motive":    NodeLabel.MOTIVE,
            "behavior":  NodeLabel.BEHAVIOR,
            "outcome":   NodeLabel.OUTCOME,
            "spiritual": NodeLabel.SPIRITUAL,
            "principle": NodeLabel.PRINCIPLE,
        }.get(layer, NodeLabel.BEHAVIOR)

    def _extract_root_drivers(
        self,
        emotion: str,
        motive:  str,
        graph_insight: Optional[GraphInsight],
    ) -> Dict[str, str]:
        return {
            "emotion":    emotion,
            "motive":     motive,
            "chain_root": graph_insight.causal_chains[0].nodes[0]
                          if graph_insight and graph_insight.causal_chains else emotion,
        }

    def _build_reflective_guidance(
        self,
        loop: Optional[LoopDiagnosis],
        breakpoint: Optional[BreakpointAnalysis],
        principles: List[PrincipleAlignment],
        graph_insight: Optional[GraphInsight],
    ) -> List[str]:
        """
        Build non-directive reflective questions from:
        1. KNOWN_PATTERNS reflective_question fields (if matched)
        2. Breakpoint reasoning (softened to a question form)
        3. Top principle (as a question prompt)
        """
        guidance: List[str] = []

        # From graph insight intervention patterns
        if graph_insight and graph_insight.intervention_points:
            for iv in graph_insight.intervention_points[:2]:
                pid = iv.get("pattern_id", "")
                for p in KNOWN_PATTERNS:
                    if p["id"] == pid and "reflective_question" in p:
                        guidance.append(p["reflective_question"])
                        break

        # From PatternSubgraph reflective question
        if loop and loop.loop_id:
            for sg in PATTERN_SUBGRAPHS:
                if sg.pattern_id == loop.loop_id or sg.pattern_id in loop.loop_id:
                    if sg.reflective_question and sg.reflective_question not in guidance:
                        guidance.append(sg.reflective_question)
                    break

        # Fallback from KNOWN_PATTERNS reflective questions
        if len(guidance) < 2:
            for p in KNOWN_PATTERNS:
                rq = p.get("reflective_question", "")
                if rq and rq not in guidance:
                    guidance.append(rq)
                if len(guidance) >= 2:
                    break

        return guidance[:3]

    def _estimate_confidence(
        self, result: FormationReasoning, graph_insight: Optional[GraphInsight]
    ) -> float:
        """
        Estimate overall confidence of the reasoning output.
        Higher when: graph connected + patterns matched + loop confirmed.
        """
        score = 0.3  # baseline
        if graph_insight:
            score += 0.15
            if graph_insight.pattern_labels:
                score += 0.15
            if graph_insight.cycles:
                score += 0.10
        if result.loop_diagnosis and result.loop_diagnosis.is_active:
            score += 0.10
        if result.breakpoint:
            score += 0.10
        if result.principle_alignments:
            score += 0.05
        if result.temporal_context:
            score += 0.05
        return round(min(score, 0.90), 2)  # cap at 0.90 — never claim certainty


# ──────────────────────────────────────────────────────────────────────────────
# Module-level singleton
# ──────────────────────────────────────────────────────────────────────────────

_reasoning_engine: Optional[GraphReasoningFusion] = None


def get_reasoning_engine() -> GraphReasoningFusion:
    global _reasoning_engine
    if _reasoning_engine is None:
        _reasoning_engine = GraphReasoningFusion()
    return _reasoning_engine
