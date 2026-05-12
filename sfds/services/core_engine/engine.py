"""
Core Engine — SFDS v3 Brain Coordinator

Responsibilities:
  - Orchestrates all 5 subsystem services
  - Runs LLM fusion reasoning
  - Produces final integrated discernment output
  - Routes to FormationEngine for long-term update

This is the ONLY place that fuses inputs from:
  graph_service, vector_service, time_series_service, formation_engine.

v3.5 upgrade: HIDOS Orchestrator is the primary coordinator.
  analyze_hidos() → HIDOSOrchestrator.orchestrate() → unified multi-layer output
  analyze()       → legacy 5-layer pipeline (kept as fallback)

It does NOT contain DB logic (delegated to services).
It does NOT contain LLM prompt templates (in packages/prompts).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from packages.shared_types.decision import DecisionRequest
from services.graph_service.service import GraphService
from services.vector_service.service import VectorService
from services.time_series_service.service import TimeSeriesService
from services.formation_engine.engine import FormationEngine

logger = logging.getLogger(__name__)

_core_engine: Optional["CoreEngine"] = None


def get_core_engine() -> "CoreEngine":
    global _core_engine
    if _core_engine is None:
        _core_engine = CoreEngine()
    return _core_engine


class CoreEngine:
    """
    The central coordinator of SFDS v3.

    Data flow:
        DecisionRequest
            → [1] VectorService  (semantic context: principles, similar cases)
            → [2] GraphService   (structural context: loops, causal chains)
            → [3] TimeSeriesService (temporal context: trends, cycles)
            → [4] LLM Fusion     (integrated discernment reasoning)
            → [5] FormationEngine (long-term trajectory update)
            → AnalysisResponse

    Design contract:
        - All layers fail gracefully (never raise to the user)
        - Output is always non-authoritative and probabilistic
        - No identity labels, no moral scoring, no divine certainty
    """

    def __init__(
        self,
        graph:   Optional[GraphService]      = None,
        vector:  Optional[VectorService]     = None,
        timeseries: Optional[TimeSeriesService] = None,
        formation: Optional[FormationEngine]  = None,
    ):
        self.graph      = graph      or GraphService()
        self.vector     = vector     or VectorService()
        self.timeseries = timeseries or TimeSeriesService()
        self.formation  = formation  or FormationEngine()
        self._hidos     = self._build_hidos()

    def _build_hidos(self):
        """Lazily construct HIDOS Orchestrator with all subsystems."""
        try:
            from ai.orchestrator.hidos import HIDOSOrchestrator
            from ai.reasoning.graph_query_engine import GraphQueryEngine
            from ai.formation.fmm import FormationMathematicsModel
            return HIDOSOrchestrator(
                gqe               = GraphQueryEngine(driver=getattr(self.graph, '_driver', None)),
                fmm               = FormationMathematicsModel(),
                formation_engine  = self.formation,
                vector_service    = self.vector,
                time_series_service=self.timeseries,
            )
        except Exception as exc:
            logger.warning("[core-engine] HIDOS init failed, will use legacy pipeline: %s", exc)
            return None

    async def analyze_hidos(self, req: DecisionRequest) -> Dict[str, Any]:
        """
        v3.5 primary analysis path — HIDOS Orchestrator.

        Replaces the sequential 5-layer pipeline with dynamic subsystem
        activation, contradiction resolution, and unified formation math.

        Falls back to analyze() (v3.1) on HIDOS failure.
        """
        if self._hidos is None:
            logger.warning("[core-engine] HIDOS unavailable, falling back to v3.1")
            result = await self.analyze(req)
            result["schema"] = "v3.1_fallback"
            return result

        try:
            output = await self._hidos.orchestrate(
                user_id         = req.user_id,
                description     = req.description or "",
                emotions        = req.emotions or [],
                dominant_motive = req.dominant_motive or "unknown",
                category        = req.category or "general",
                urgency         = int(req.urgency or 3),
                reflection_notes= req.reflection_notes or "",
            )
            result = output.to_dict()
            result["decision_id"] = req.decision_id
            return result
        except Exception as exc:
            logger.error("[core-engine] HIDOS orchestration failed: %s", exc)
            fallback = await self.analyze(req)
            fallback["schema"]        = "v3.1_hidos_fallback"
            fallback["hidos_error"]   = str(exc)
            return fallback

    async def analyze(self, req: DecisionRequest) -> Dict[str, Any]:
        """v3.1 legacy 5-layer analysis pipeline. Called as HIDOS fallback."""
        result: Dict[str, Any] = {
            "user_id":     req.user_id,
            "decision_id": req.decision_id,
            "schema":      "v3.1",
        }

        # Layer 1 — Semantic
        try:
            semantic = await self.vector.get_principles(req.description, top_k=5)
            result["semantic"] = semantic
        except Exception as exc:
            logger.warning("[core-engine] semantic layer failed: %s", exc)
            result["semantic"] = {}

        # Layer 2 — Structural
        try:
            graph = await self.graph.analyze(
                user_id          = req.user_id,
                dominant_motive  = req.dominant_motive or "unknown",
                emotions         = req.emotions or [],
                decision_category= req.category,
                past_behaviors   = req.past_behavior_types or [],
            )
            result["structural"] = graph
        except Exception as exc:
            logger.warning("[core-engine] structural layer failed: %s", exc)
            result["structural"] = {}

        # Layer 3 — Temporal
        try:
            temporal = await self.timeseries.analyze(req.user_id)
            result["temporal"] = temporal
        except Exception as exc:
            logger.warning("[core-engine] temporal layer failed: %s", exc)
            result["temporal"] = {}

        # Layer 4 — LLM Reasoning Fusion
        try:
            from ai.reasoning.fusion import run_fusion_reasoning
            reasoning = await run_fusion_reasoning(req, result)
            result["reasoning"] = reasoning
        except Exception as exc:
            logger.warning("[core-engine] reasoning layer failed: %s", exc)
            result["reasoning"] = {"summary": "Reasoning layer unavailable."}

        # Layer 5 — Formation
        try:
            pattern_categories = result.get("structural", {}).get("pattern_categories", [])
            loop_broken        = result.get("structural", {}).get("loop_broken", False)
            intensity          = max(
                (e.get("intensity", 5) for e in (req.emotions or [])), default=5.0
            )
            formation = self.formation.analyze_sync(
                user_id            = req.user_id,
                pattern_categories = pattern_categories,
                loop_broken        = loop_broken,
                decision_category  = req.category,
                session_id         = req.decision_id,
                emotional_intensity= float(intensity),
                reflection_active  = bool(req.reflection_notes),
            )
            result["formation"] = formation.to_dict()
        except Exception as exc:
            logger.warning("[core-engine] formation layer failed: %s", exc)
            result["formation"] = {}

        return result

    async def write_back(self, decision_id: str) -> None:
        """
        Persist confirmed decision to all data stores.
        Called only after user confirms guidance was shown.
        """
        logger.info("[core-engine] write_back for decision: %s", decision_id)
