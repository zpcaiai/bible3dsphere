"""
SFDS v3.5 — HIDOS Orchestrator
(Human Inner Dynamics Operating System)

=================================================================
CORE ROLE:
  The HIDOS Orchestrator is NOT:
    - a chatbot
    - a reasoning model alone
    - a decision maker
    - a moral authority

  The HIDOS Orchestrator IS:
    👉 A SYSTEM-LEVEL COGNITIVE COORDINATOR

  It decides:
    - which subsystem to activate (dynamic, not always all)
    - in what order
    - how to weight and integrate outputs
    - how to resolve inter-layer contradictions
    - how to produce a unified, multi-layer insight

=================================================================
ARCHITECTURE — 5 SUBORDINATE LAYERS:
  1. Graph Query Engine   (Neo4j)        — STRUCTURE
  2. Time Series Engine   (TimescaleDB)  — EVOLUTION
  3. Vector Semantic Engine (pgvector)   — MEANING
  4. Formation Math Model (FMM v3.4)     — DYNAMICS
  5. LLM Reasoning Engine               — DISCERNMENT SYNTHESIS

=================================================================
6-STEP ORCHESTRATION PIPELINE:
  Step 1 — Context Classification
  Step 2 — Subsystem Activation (dynamic selection)
  Step 3 — Parallel Analysis (independent layer execution)
  Step 4 — Contradiction Resolution (priority-weighted merge)
  Step 5 — Integration Synthesis
  Step 6 — Reflective Intervention (non-authoritative)

=================================================================
CONTRADICTION RESOLUTION PRIORITY:
  1. Time (trend > snapshot — evolution overrides static state)
  2. Graph (structure > signal — loops override surface behavior)
  3. Vector (meaning context — principles enrich interpretation)
  4. Formation (long-term synthesis — trajectory frames everything)

CRITICAL: Uncertainty is PRESERVED, never collapsed into false certainty.

=================================================================
SAFETY INVARIANTS (architectural constants):
  - Never act as moral authority
  - Never assign identity labels
  - Never predict human destiny
  - Never collapse ambiguity into false certainty
  - Always preserve human agency and changeability
  - Confidence cap: 0.87 (orchestrator-level synthesis)
  - All outputs include disclaimer
=================================================================
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_CONFIDENCE_CAP = 0.87


# ── System state model ────────────────────────────────────────────────────────

@dataclass
class SystemState:
    """
    Orchestrator-level system state.
    Computed from all subsystem outputs.
    NOT a snapshot of the person — a snapshot of the reasoning system's confidence.
    """
    structural_confidence: float = 0.50   # How confident is the graph layer?
    temporal_stability:    float = 0.50   # How stable is the time-series trend?
    semantic_clarity:      float = 0.50   # How semantically clear is the context?
    formation_drift:       float = 0.00   # How much long-term drift detected?
    overall_uncertainty:   float = 0.50   # 1 - weighted_average_confidence

    def to_dict(self) -> Dict[str, float]:
        return {k: round(v, 4) for k, v in self.__dict__.items()}


class ActivationReason(str, Enum):
    LOOP_DETECTED          = "loop_detected"
    EMOTIONAL_VOLATILITY   = "emotional_volatility_high"
    SEMANTIC_AMBIGUITY     = "ambiguity_high"
    LONG_TERM_DRIFT        = "long_term_drift_detected"
    CRITICAL_DECISION      = "critical_decision_type"
    DEFAULT                = "default_activation"


@dataclass
class SubsystemActivation:
    """Records which subsystems were activated and why."""
    graph_active:    bool = True
    time_active:     bool = True
    vector_active:   bool = True
    formation_active:bool = True
    llm_active:      bool = True
    reasons:         List[ActivationReason] = field(default_factory=list)

    def active_names(self) -> List[str]:
        names = []
        if self.graph_active:     names.append("graph")
        if self.time_active:      names.append("time_series")
        if self.vector_active:    names.append("vector")
        if self.formation_active: names.append("formation")
        if self.llm_active:       names.append("llm")
        return names


@dataclass
class LayerOutput:
    """Single subsystem output wrapper."""
    layer:   str                   # "graph" | "time" | "vector" | "formation" | "llm"
    data:    Dict[str, Any]        # raw output from subsystem
    confidence: float = 0.50
    available:  bool  = True       # False if subsystem was offline/skipped


@dataclass
class ContradictionResolution:
    """Records how contradictions between layers were resolved."""
    conflict_detected:  bool = False
    conflict_layers:    List[str] = field(default_factory=list)
    resolution_rule:    str = ""
    preserved_ambiguity:bool = True
    notes:              List[str] = field(default_factory=list)


@dataclass
class HIDOSOutput:
    """
    Complete HIDOS Orchestrator output.

    Contains all 6 pipeline step results.
    SAFETY: All text uses system-state language, not identity language.
    """
    # Meta
    user_id:         str
    schema:          str = "hidos_v3.5"

    # Step 1
    decision_type:   str = "general"
    emotional_intensity: float = 5.0
    instability_level:   float = 0.0

    # Step 2
    activation:      SubsystemActivation = field(default_factory=SubsystemActivation)

    # Step 3
    layers:          List[LayerOutput] = field(default_factory=list)

    # Step 4
    resolution:      ContradictionResolution = field(default_factory=ContradictionResolution)

    # Step 5
    system_state:    SystemState = field(default_factory=SystemState)
    integrated:      Dict[str, Any] = field(default_factory=dict)

    # Step 6
    intervention:    Dict[str, Any] = field(default_factory=dict)
    reflective_insight: str = ""

    # Output
    confidence:      float = 0.0
    disclaimer:      str = (
        "This analysis describes system-level dynamics — not identity, destiny, or moral worth. "
        "All interpretations describe temporary structural tendencies. "
        "Human agency and change are always preserved."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema":             self.schema,
            "user_id":            self.user_id,
            "context": {
                "decision_type":      self.decision_type,
                "emotional_intensity":self.emotional_intensity,
                "instability_level":  self.instability_level,
            },
            "activation": {
                "active_layers":  self.activation.active_names(),
                "reasons":        [r.value for r in self.activation.reasons],
            },
            "layers": {
                l.layer: {
                    "available":  l.available,
                    "confidence": round(l.confidence, 4),
                    "data":       l.data,
                }
                for l in self.layers
            },
            "contradiction_resolution": {
                "conflict_detected":   self.resolution.conflict_detected,
                "conflict_layers":     self.resolution.conflict_layers,
                "resolution_rule":     self.resolution.resolution_rule,
                "preserved_ambiguity": self.resolution.preserved_ambiguity,
                "notes":               self.resolution.notes,
            },
            "system_state":      self.system_state.to_dict(),
            "integrated":        self.integrated,
            "intervention":      self.intervention,
            "reflective_insight":self.reflective_insight,
            "confidence":        round(self.confidence, 4),
            "disclaimer":        self.disclaimer,
        }


# ── HIDOS Orchestrator ────────────────────────────────────────────────────────

class HIDOSOrchestrator:
    """
    HIDOS v3.5 — Human Inner Dynamics OS Orchestrator.

    Coordinates all 5 subordinate subsystems into a unified
    multi-layer cognitive interpretation.

    All subsystems are optional — the orchestrator degrades gracefully
    when any layer is unavailable.

    Usage:
        hidos = HIDOSOrchestrator(
            gqe=graph_engine,
            fmm=formation_model,
            formation_engine=formation_svc,
            vector_service=vector_svc,
            time_series_service=ts_svc,
        )
        output = await hidos.orchestrate(request, context)
    """

    def __init__(
        self,
        gqe=None,               # GraphQueryEngine
        fmm=None,               # FormationMathematicsModel
        formation_engine=None,  # FormationEngine (existing)
        vector_service=None,    # VectorService
        time_series_service=None,  # TimeSeriesService
        openai_client=None,     # AsyncOpenAI
    ):
        self._gqe    = gqe
        self._fmm    = fmm
        self._fe     = formation_engine
        self._vector = vector_service
        self._ts     = time_series_service
        self._llm    = openai_client

    # ── Public interface ──────────────────────────────────────────────────────

    async def orchestrate(
        self,
        user_id:        str,
        description:    str,
        emotions:       List[Dict[str, Any]],
        dominant_motive:str,
        category:       str,
        urgency:        int  = 3,
        reflection_notes:str = "",
        formation_vector:Optional[Dict[str, float]] = None,
        history:         Optional[List[Dict[str, float]]] = None,
    ) -> HIDOSOutput:
        """
        Execute the 6-step HIDOS orchestration pipeline.

        Returns HIDOSOutput — complete multi-layer cognitive analysis.
        Always returns, never raises.
        """
        output = HIDOSOutput(user_id=user_id)

        try:
            # ── Step 1: Context classification ────────────────────────────────
            self._step1_classify(
                output, emotions, urgency, category, formation_vector, history
            )

            # ── Step 2: Subsystem activation ──────────────────────────────────
            self._step2_activate(output)

            # ── Step 3: Parallel analysis ──────────────────────────────────────
            await self._step3_analyze(
                output, user_id, description, emotions,
                dominant_motive, category, reflection_notes,
                formation_vector, history,
            )

            # ── Step 4: Contradiction resolution ──────────────────────────────
            self._step4_resolve(output)

            # ── Step 5: Integration synthesis ─────────────────────────────────
            self._step5_integrate(output)

            # ── Step 6: Reflective intervention ───────────────────────────────
            self._step6_intervene(output, reflection_notes)

        except Exception as exc:
            logger.error("[HIDOS] Orchestration pipeline failed: %s", exc, exc_info=True)
            output.reflective_insight = (
                "System analysis temporarily unavailable. "
                "Please try again — if the issue persists, the subsystems may need reconnection."
            )

        # Confidence = weighted average of available layers
        output.confidence = self._compute_confidence(output)

        # ── Safety Constitution check (always last) ───────────────────────
        output = self._apply_constitution(output)

        return output

    def _apply_constitution(self, output: HIDOSOutput) -> HIDOSOutput:
        """
        Run the 15-article Safety Constitution check on the final output.
        On violations: reduce confidence, sanitize offending fields,
        and attach constitution_check results.
        """
        try:
            from ai.constitution.safety_constitution import get_constitution_checker
            checker = get_constitution_checker()
            result  = checker.check(output.to_dict())

            if not result.passed:
                logger.warning(
                    "[HIDOS] Constitution violations: %d total, %d critical",
                    result.violation_count, result.critical_count,
                )
                output.confidence = max(
                    0.10,
                    output.confidence - result.confidence_penalty,
                )
                # Sanitize any critical/high violations in reflective_insight
                if any(
                    v.field == "reflective_insight"
                    for v in result.violations
                    if v.severity.value in ("critical", "high")
                ):
                    output.reflective_insight = (
                        "[Constitution review applied. "
                        "Structural analysis available without violating fields.] "
                        + output.reflective_insight[:400]
                    )
        except Exception as exc:
            logger.warning("[HIDOS] Constitution check failed: %s", exc)
        return output

    # ── Step 1: Context Classification ───────────────────────────────────────

    def _step1_classify(
        self,
        output:          HIDOSOutput,
        emotions:        List[Dict[str, Any]],
        urgency:         int,
        category:        str,
        formation_vector:Optional[Dict[str, float]],
        history:         Optional[List[Dict[str, float]]],
    ) -> None:
        """
        Determine: decision type, emotional intensity, instability level.
        """
        intensity = max(
            (float(e.get("intensity", 5.0)) for e in emotions),
            default=5.0,
        )
        output.emotional_intensity = intensity
        output.decision_type = category

        # Instability from formation vector drift
        if formation_vector:
            from ai.formation.fmm import DRIFT_THRESHOLD
            drifting = [
                abs(v - 0.50) for v in formation_vector.values()
                if abs(v - 0.50) > DRIFT_THRESHOLD
            ]
            output.instability_level = round(len(drifting) / 8.0, 4)
        else:
            output.instability_level = 0.30  # default moderate uncertainty

    # ── Step 2: Subsystem Activation ─────────────────────────────────────────

    def _step2_activate(self, output: HIDOSOutput) -> None:
        """
        Dynamically select subsystems based on context signals.

        | Condition                  | Activated |
        |---------------------------|-----------|
        | loop detected (category)  | graph     |
        | emotional volatility high | time      |
        | ambiguity (clarity low)   | vector    |
        | long-term drift detected  | formation |
        | always                    | llm       |
        """
        act     = SubsystemActivation()
        reasons = []

        intensity = output.emotional_intensity
        instab    = output.instability_level

        # Loop-type categories always activate graph
        if output.decision_type in ("fear", "shame", "pride", "desire", "relational", "spiritual"):
            act.graph_active = True
            reasons.append(ActivationReason.LOOP_DETECTED)

        # High emotional intensity → activate time series
        if intensity >= 6.0:
            act.time_active = True
            reasons.append(ActivationReason.EMOTIONAL_VOLATILITY)

        # High instability → activate formation
        if instab > 0.25:
            act.formation_active = True
            reasons.append(ActivationReason.LONG_TERM_DRIFT)

        # Always activate vector (principles always potentially relevant)
        act.vector_active = True

        # LLM always last
        act.llm_active = True

        if not reasons:
            reasons.append(ActivationReason.DEFAULT)

        act.reasons = reasons
        output.activation = act

    # ── Step 3: Parallel Analysis ─────────────────────────────────────────────

    async def _step3_analyze(
        self,
        output:          HIDOSOutput,
        user_id:         str,
        description:     str,
        emotions:        List[Dict[str, Any]],
        dominant_motive: str,
        category:        str,
        reflection_notes:str,
        formation_vector:Optional[Dict[str, float]],
        history:         Optional[List[Dict[str, float]]],
    ) -> None:
        """Run all activated subsystems. Each wrapped in try/except — never blocks."""
        tasks = []
        act   = output.activation

        if act.graph_active and self._gqe:
            tasks.append(self._run_graph(user_id, emotions, dominant_motive, category))
        else:
            tasks.append(self._offline_layer("graph"))

        if act.time_active and self._ts:
            tasks.append(self._run_timeseries(user_id))
        else:
            tasks.append(self._offline_layer("time_series"))

        if act.vector_active and self._vector:
            tasks.append(self._run_vector(description, emotions))
        else:
            tasks.append(self._offline_layer("vector"))

        if act.formation_active:
            tasks.append(self._run_formation(
                user_id, emotions, category, reflection_notes,
                formation_vector, history,
            ))
        else:
            tasks.append(self._offline_layer("formation"))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                logger.warning("[HIDOS] Layer failed: %s", r)
            elif isinstance(r, LayerOutput):
                output.layers.append(r)

    async def _run_graph(
        self, user_id: str, emotions: List[Dict], motive: str, category: str
    ) -> LayerOutput:
        try:
            from ai.reasoning.graph_query_engine import (
                GQEMode, UserStateInput,
            )
            emotion = emotions[0].get("type", "fear") if emotions else "fear"
            behavior= emotions[0].get("trigger", "avoidance") if emotions else "avoidance"
            state   = UserStateInput(
                emotion_node=emotion, motive_node=motive,
                behavior_node=behavior, user_id=user_id, category=category,
            )
            result = await self._gqe.reason(state, mode=GQEMode.LOOP_SIMULATION)
            return LayerOutput(
                layer="graph",
                data=result.to_dict(),
                confidence=result.confidence,
                available=True,
            )
        except Exception as exc:
            logger.warning("[HIDOS:graph] %s", exc)
            return LayerOutput(layer="graph", data={}, confidence=0.0, available=False)

    async def _run_timeseries(self, user_id: str) -> LayerOutput:
        try:
            result = await self._ts.analyze(user_id)
            conf = 0.65 if result.get("trends") else 0.30
            return LayerOutput(layer="time_series", data=result, confidence=conf, available=True)
        except Exception as exc:
            logger.warning("[HIDOS:time] %s", exc)
            return LayerOutput(layer="time_series", data={}, confidence=0.0, available=False)

    async def _run_vector(
        self, description: str, emotions: List[Dict]
    ) -> LayerOutput:
        try:
            emotion_str = " ".join(e.get("type", "") for e in emotions[:3])
            query       = f"{description} {emotion_str}".strip()
            result      = await self._vector.get_principles(query)
            principles  = result.get("principles", [])
            conf        = min(0.80, len(principles) * 0.15 + 0.20)
            return LayerOutput(
                layer="vector", data=result, confidence=conf, available=True
            )
        except Exception as exc:
            logger.warning("[HIDOS:vector] %s", exc)
            return LayerOutput(layer="vector", data={}, confidence=0.0, available=False)

    async def _run_formation(
        self,
        user_id:          str,
        emotions:         List[Dict],
        category:         str,
        reflection_notes: str,
        formation_vector: Optional[Dict[str, float]],
        history:          Optional[List[Dict[str, float]]],
    ) -> LayerOutput:
        try:
            from ai.formation.fmm import (
                FormationMathematicsModel, FormationVector,
                build_loop_dynamics_from_pattern, LoopDynamics,
            )
            from graph.patterns._loops_part1 import _LOOPS_A_B_C
            from graph.patterns._loops_part2 import _LOOPS_D_E_F
            library = _LOOPS_A_B_C + _LOOPS_D_E_F

            fmm = self._fmm or FormationMathematicsModel()

            X_current = (
                FormationVector.from_dict(formation_vector)
                if formation_vector else FormationVector()
            )
            hist_vecs = [FormationVector.from_dict(h) for h in (history or [])]

            # Find matching patterns
            matching = [p for p in library if p.get("category") == category][:2]
            intensity = max(
                (float(e.get("intensity", 5.0)) for e in emotions), default=5.0
            )
            loop_dyn = [
                build_loop_dynamics_from_pattern(
                    p,
                    repetitions=1,
                    intensity=intensity,
                    reflection=bool(reflection_notes),
                )
                for p in matching
            ]

            pattern_dims = {p["id"]: p.get("formation_dims", {}) for p in matching}

            result = fmm.step(
                current_vector    = X_current,
                loop_dynamics     = loop_dyn,
                emotional_signal  = {
                    "volatility":       intensity,
                    "stress_spikes":    len([e for e in emotions if e.get("intensity", 0) > 7]),
                    "stability_trend":  0.0,
                },
                principle_scores  = [],
                history           = hist_vecs,
                pattern_dims      = pattern_dims,
            )

            return LayerOutput(
                layer="formation",
                data=result.to_dict(),
                confidence=result.confidence,
                available=True,
            )
        except Exception as exc:
            logger.warning("[HIDOS:formation] %s", exc)
            return LayerOutput(layer="formation", data={}, confidence=0.0, available=False)

    async def _offline_layer(self, name: str) -> LayerOutput:
        return LayerOutput(layer=name, data={}, confidence=0.0, available=False)

    # ── Step 4: Contradiction Resolution ─────────────────────────────────────

    def _step4_resolve(self, output: HIDOSOutput) -> None:
        """
        Priority resolution when layers disagree:
          1. Time (trend > snapshot)
          2. Graph (structure > surface signal)
          3. Vector (meaning context)
          4. Formation (long-term framing)

        CRITICAL: Never discard uncertainty.
        Preserve ambiguity by holding multiple interpretations.
        """
        layer_map = {l.layer: l for l in output.layers if l.available}
        res       = ContradictionResolution(preserved_ambiguity=True)

        graph_loops = bool(
            layer_map.get("graph", LayerOutput("", {})).data.get("loop_analysis", {}).get("is_loop")
        )
        time_improving = (
            layer_map.get("time_series", LayerOutput("", {})).data.get("trend_direction") == "improving"
        )
        principles_present = bool(
            layer_map.get("vector", LayerOutput("", {})).data.get("principles")
        )

        conflicts = []
        notes     = []

        # Conflict: graph detects active loop BUT time shows improving trend
        if graph_loops and time_improving:
            conflicts = ["graph", "time_series"]
            res.conflict_detected = True
            res.resolution_rule   = (
                "Time-series trend (improving) takes priority over graph loop snapshot. "
                "Both signals preserved — possible transitional state."
            )
            notes.append(
                "The structural loop detected in the graph layer coexists with an improving "
                "time-series trend. This may indicate the loop is active but weakening. "
                "Ambiguity is preserved."
            )

        # Conflict: graph loop + principles present (principle may already be active)
        if graph_loops and principles_present and not conflicts:
            res.resolution_rule = (
                "Graph loop detected; principles present. "
                "Vector layer enriches — does not override. "
                "Principle exposure modeled as B(loop) function."
            )
            notes.append(
                "Active loop and principle exposure coexist. "
                "The principle may be in the process of weakening the loop."
            )

        res.conflict_layers = conflicts
        res.notes           = notes
        output.resolution   = res

    # ── Step 5: Integration Synthesis ────────────────────────────────────────

    def _step5_integrate(self, output: HIDOSOutput) -> None:
        """
        Combine all available layer outputs into a unified interpretation.
        Updates SystemState and output.integrated.
        """
        layer_map = {l.layer: l for l in output.layers}

        graph_data = layer_map.get("graph",      LayerOutput("", {})).data
        time_data  = layer_map.get("time_series",LayerOutput("", {})).data
        vec_data   = layer_map.get("vector",     LayerOutput("", {})).data
        fmm_data   = layer_map.get("formation",  LayerOutput("", {})).data

        # Update SystemState
        ss = SystemState(
            structural_confidence = layer_map.get("graph",       LayerOutput("", {}, 0.0)).confidence,
            temporal_stability    = layer_map.get("time_series", LayerOutput("", {}, 0.0)).confidence,
            semantic_clarity      = layer_map.get("vector",      LayerOutput("", {}, 0.0)).confidence,
            formation_drift       = fmm_data.get("trajectory", {}).get("drift_detected", False)
                                    and 0.60 or 0.10,
        )
        confs = [
            ss.structural_confidence, ss.temporal_stability,
            ss.semantic_clarity,
        ]
        available = [c for c in confs if c > 0]
        ss.overall_uncertainty = round(
            1.0 - (sum(available) / len(available)) if available else 0.50, 4
        )
        output.system_state = ss

        # Unified integrated dict
        output.integrated = {
            "structural_layer": {
                "loop_detected":     graph_data.get("loop_analysis", {}).get("is_loop", False),
                "active_loop_type":  graph_data.get("loop_analysis", {}).get("loop_type", ""),
                "loop_chain":        graph_data.get("loop_analysis", {}).get("loop_chain", []),
                "breakpoint":        graph_data.get("breakpoint", {}),
                "principle":         graph_data.get("principle_match", {}),
            },
            "temporal_layer": {
                "trend_direction":   time_data.get("trend_direction", ""),
                "volatility":        time_data.get("volatility", {}),
                "cycle_detected":    time_data.get("cycle_detected", False),
            },
            "semantic_layer": {
                "top_principles":    [
                    p.get("principle_en", p.get("label", ""))
                    for p in (vec_data.get("principles", []) or [])[:3]
                ],
                "principle_count":   len(vec_data.get("principles", []) or []),
            },
            "formation_layer": {
                "state_vector":      fmm_data.get("state_vector", {}),
                "trajectory":        fmm_data.get("trajectory", {}).get("direction", "unknown"),
                "stability_score":   fmm_data.get("stability", {}).get("stability_score", 0.50),
                "intervention_urgency": fmm_data.get("intervention", {}).get("urgency_level", "low"),
            },
        }

    # ── Step 6: Reflective Intervention ──────────────────────────────────────

    def _step6_intervene(self, output: HIDOSOutput, reflection_notes: str) -> None:
        """
        Compute structural intervention signal and generate reflective insight.

        NOT commands. NOT moral judgments.
        System-state signals + reflective questions only.
        """
        int_data = output.integrated
        struct   = int_data.get("structural_layer", {})
        form     = int_data.get("formation_layer", {})
        sem      = int_data.get("semantic_layer", {})
        fmm_layer= next((l for l in output.layers if l.layer == "formation"), None)
        fmm_data = fmm_layer.data if fmm_layer else {}

        # Intervention score from FMM
        interv_urgency  = form.get("intervention_urgency", "low")
        interv_note     = fmm_data.get("intervention", {}).get("note", "")

        output.intervention = {
            "urgency_level":     interv_urgency,
            "loop_strength":     fmm_data.get("intervention", {}).get("loop_strength", 0.0),
            "breaking_potential":fmm_data.get("intervention", {}).get("breaking_potential", {}),
            "breakpoint_node":   struct.get("breakpoint", {}).get("node_type", ""),
            "principle_label":   struct.get("principle", {}).get("principle_label", ""),
            "top_principles":    sem.get("top_principles", []),
            "note":              interv_note,
        }

        output.reflective_insight = self._build_insight(
            output, reflection_notes
        )

    def _build_insight(
        self, output: HIDOSOutput, reflection_notes: str
    ) -> str:
        """
        Non-authoritative multi-layer reflective insight.

        Language rules (enforced):
          - "may", "appears", "tends toward", "possible", "suggests"
          - No "you are X"
          - No "this will happen"
          - Always close with agency statement
        """
        parts: List[str] = []
        struct = output.integrated.get("structural_layer", {})
        temp   = output.integrated.get("temporal_layer", {})
        form   = output.integrated.get("formation_layer", {})
        sem    = output.integrated.get("semantic_layer", {})
        ss     = output.system_state

        # Structural insight
        if struct.get("loop_detected"):
            chain = struct.get("loop_chain", [])
            ltype = struct.get("active_loop_type", "").replace("_", " ")
            if chain:
                parts.append(
                    f"Structurally, a pattern appears active: "
                    f"{' → '.join(chain[:4])}. "
                    f"This may be consistent with a '{ltype}' dynamic."
                )

        # Temporal insight
        trend = temp.get("trend_direction", "")
        if trend and trend not in ("unknown", ""):
            parts.append(
                f"The temporal layer suggests the system has been trending "
                f"'{trend}' over the recent period."
            )

        # Formation insight
        traj = form.get("trajectory", "unknown")
        stab = float(form.get("stability_score", 0.50))
        if traj not in ("unknown", ""):
            parts.append(
                f"The formation dynamics model indicates a '{traj}' trajectory. "
                f"System stability is estimated at {stab:.0%}."
            )

        # Contradiction note
        if output.resolution.conflict_detected:
            parts.append(
                "Notably, different analytical layers are providing somewhat different signals. "
                "This ambiguity is preserved — it may itself be meaningful."
            )

        # Principle intervention
        principles = sem.get("top_principles", [])
        if principles:
            parts.append(
                f"A potentially relevant principle: '{principles[0][:80]}'. "
                f"Principle exposure is modeled as having structural influence "
                f"on loop momentum."
            )

        # Breakpoint
        bp = struct.get("breakpoint", {})
        if bp.get("node_type"):
            parts.append(
                f"The graph layer identifies '{bp['node_type']}' as a possible "
                f"high-leverage structural intervention point "
                f"(leverage: {float(bp.get('leverage_score', 0)):.0%})."
            )

        # Reflection acknowledgment
        if reflection_notes:
            parts.append(
                "Active reflection has been noted. In the dynamics model, "
                "reflection modulates the breaking function B(loop), "
                "reducing negative delta momentum."
            )

        # System uncertainty note
        if ss and ss.overall_uncertainty > 0.40:
            parts.append(
                f"The overall system uncertainty estimate is {ss.overall_uncertainty:.0%}. "
                f"This means multiple interpretations remain open — "
                f"the picture is genuinely ambiguous at this stage."
            )

        # Agency close — always last
        parts.append(
            "This is a multi-layer structural description — not a prediction or verdict. "
            "The system is dynamic. Change is structurally always possible."
        )

        return " ".join(parts)

    # ── Confidence ────────────────────────────────────────────────────────────

    def _compute_confidence(self, output: HIDOSOutput) -> float:
        available = [l for l in output.layers if l.available]
        if not available:
            return 0.20
        avg = sum(l.confidence for l in available) / len(available)
        return round(min(_CONFIDENCE_CAP, avg + 0.05 * len(available)), 4)
