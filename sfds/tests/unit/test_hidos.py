"""
Unit Tests — HIDOS Orchestrator v3.5

All tests run without any database connection (all subsystems mocked or offline).
Tests validate:
  - 6-step orchestration pipeline produces HIDOSOutput
  - Dynamic subsystem activation logic
  - Contradiction resolution logic
  - SystemState computation
  - Integration synthesis
  - Reflective intervention output
  - Safety invariants (no identity labels, no directives, confidence cap)
  - Graceful degradation on all-offline subsystems
"""

import asyncio
import pytest
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ai.orchestrator.hidos import (
    HIDOSOrchestrator, HIDOSOutput, SystemState,
    SubsystemActivation, ActivationReason, ContradictionResolution,
    LayerOutput,
)
from ai.formation.fmm import FormationVector


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def hidos_offline():
    """HIDOS with all subsystems offline (pattern library + FMM only)."""
    from ai.formation.fmm import FormationMathematicsModel
    return HIDOSOrchestrator(
        gqe=None, fmm=FormationMathematicsModel(),
        formation_engine=None, vector_service=None, time_series_service=None,
    )


@pytest.fixture
def fear_emotions():
    return [{"type": "fear", "intensity": 7.5, "trigger": "overwork"}]


@pytest.fixture
def shame_emotions():
    return [{"type": "shame", "intensity": 6.0, "trigger": "social_exposure"}]


# ── 6-Step Pipeline Output ────────────────────────────────────────────────────

class TestOrchestrationPipeline:
    @pytest.mark.asyncio
    async def test_orchestrate_returns_hidos_output(self, hidos_offline, fear_emotions):
        out = await hidos_offline.orchestrate(
            user_id="u1", description="I keep overworking",
            emotions=fear_emotions, dominant_motive="control_drive",
            category="fear",
        )
        assert isinstance(out, HIDOSOutput)
        assert out.schema == "hidos_v3.5"
        assert out.user_id == "u1"

    @pytest.mark.asyncio
    async def test_output_dict_has_all_required_keys(self, hidos_offline, fear_emotions):
        out = await hidos_offline.orchestrate(
            user_id="u1", description="test",
            emotions=fear_emotions, dominant_motive="fear", category="fear",
        )
        d = out.to_dict()
        required = {
            "schema", "user_id", "context", "activation", "layers",
            "contradiction_resolution", "system_state", "integrated",
            "intervention", "reflective_insight", "confidence", "disclaimer",
        }
        assert required <= set(d.keys()), f"Missing: {required - set(d.keys())}"

    @pytest.mark.asyncio
    async def test_integrated_has_all_4_layers(self, hidos_offline, fear_emotions):
        out = await hidos_offline.orchestrate(
            user_id="u1", description="test",
            emotions=fear_emotions, dominant_motive="control_drive", category="fear",
        )
        d = out.to_dict()
        integrated = d.get("integrated", {})
        for layer in ("structural_layer", "temporal_layer", "semantic_layer", "formation_layer"):
            assert layer in integrated, f"Missing integrated layer: {layer}"

    @pytest.mark.asyncio
    async def test_formation_layer_has_state_vector(self, hidos_offline, fear_emotions):
        out = await hidos_offline.orchestrate(
            user_id="u2", description="recurring fear pattern",
            emotions=fear_emotions, dominant_motive="control_drive",
            category="fear",
        )
        form = out.to_dict()["integrated"]["formation_layer"]
        assert "state_vector" in form or "trajectory" in form


# ── Step 1: Context Classification ───────────────────────────────────────────

class TestContextClassification:
    @pytest.mark.asyncio
    async def test_high_intensity_classified(self, hidos_offline):
        emotions = [{"type": "fear", "intensity": 9.0}]
        out = await hidos_offline.orchestrate(
            user_id="u1", description="", emotions=emotions,
            dominant_motive="fear", category="fear",
        )
        assert out.emotional_intensity >= 9.0

    @pytest.mark.asyncio
    async def test_drift_increases_instability(self, hidos_offline):
        emotions = [{"type": "fear", "intensity": 5.0}]
        drifted_vector = {
            "fear_tendency": 0.80, "pride_tendency": 0.75,
            "emotional_stability": 0.20, "truth_alignment": 0.25,
            "relational_health": 0.50, "resilience": 0.50,
            "spiritual_clarity": 0.50, "desire_tendency": 0.50,
        }
        out = await hidos_offline.orchestrate(
            user_id="u1", description="", emotions=emotions,
            dominant_motive="control_drive", category="fear",
            formation_vector=drifted_vector,
        )
        assert out.instability_level > 0.20


# ── Step 2: Subsystem Activation ─────────────────────────────────────────────

class TestSubsystemActivation:
    def _activate(self, hidos, category, intensity, instab):
        from ai.orchestrator.hidos import HIDOSOutput
        out = HIDOSOutput(user_id="u1")
        out.decision_type = category
        out.emotional_intensity = intensity
        out.instability_level = instab
        hidos._step2_activate(out)
        return out.activation

    def test_fear_category_activates_graph(self, hidos_offline):
        act = self._activate(hidos_offline, "fear", 5.0, 0.10)
        assert act.graph_active
        assert ActivationReason.LOOP_DETECTED in act.reasons

    def test_high_intensity_activates_time_series(self, hidos_offline):
        act = self._activate(hidos_offline, "general", 7.0, 0.10)
        assert act.time_active
        assert ActivationReason.EMOTIONAL_VOLATILITY in act.reasons

    def test_high_instability_activates_formation(self, hidos_offline):
        act = self._activate(hidos_offline, "general", 4.0, 0.40)
        assert act.formation_active
        assert ActivationReason.LONG_TERM_DRIFT in act.reasons

    def test_vector_always_active(self, hidos_offline):
        act = self._activate(hidos_offline, "general", 3.0, 0.05)
        assert act.vector_active

    def test_llm_always_active(self, hidos_offline):
        act = self._activate(hidos_offline, "general", 3.0, 0.05)
        assert act.llm_active


# ── Step 4: Contradiction Resolution ─────────────────────────────────────────

class TestContradictionResolution:
    def _make_output(self, hidos, loop_detected, time_improving, principles_present):
        out = HIDOSOutput(user_id="u1")
        layers = []
        if loop_detected:
            layers.append(LayerOutput(
                layer="graph",
                data={"loop_analysis": {"is_loop": True}},
                confidence=0.70, available=True,
            ))
        if time_improving:
            layers.append(LayerOutput(
                layer="time_series",
                data={"trend_direction": "improving"},
                confidence=0.65, available=True,
            ))
        if principles_present:
            layers.append(LayerOutput(
                layer="vector",
                data={"principles": [{"label": "Truth sets free"}]},
                confidence=0.75, available=True,
            ))
        out.layers = layers
        hidos._step4_resolve(out)
        return out

    def test_graph_loop_plus_improving_time_flags_conflict(self, hidos_offline):
        out = self._make_output(hidos_offline, True, True, False)
        assert out.resolution.conflict_detected
        assert "graph" in out.resolution.conflict_layers
        assert "time_series" in out.resolution.conflict_layers

    def test_conflict_preserves_ambiguity(self, hidos_offline):
        out = self._make_output(hidos_offline, True, True, False)
        assert out.resolution.preserved_ambiguity is True

    def test_no_conflict_when_no_loop(self, hidos_offline):
        out = self._make_output(hidos_offline, False, True, True)
        assert not out.resolution.conflict_detected

    def test_notes_populated_on_conflict(self, hidos_offline):
        out = self._make_output(hidos_offline, True, True, False)
        assert len(out.resolution.notes) > 0


# ── Step 5: Integration Synthesis ────────────────────────────────────────────

class TestIntegrationSynthesis:
    @pytest.mark.asyncio
    async def test_system_state_computed(self, hidos_offline, fear_emotions):
        out = await hidos_offline.orchestrate(
            user_id="u1", description="test",
            emotions=fear_emotions, dominant_motive="control", category="fear",
        )
        ss = out.system_state
        assert isinstance(ss, SystemState)
        assert 0.0 <= ss.overall_uncertainty <= 1.0

    @pytest.mark.asyncio
    async def test_overall_uncertainty_in_bounds(self, hidos_offline, fear_emotions):
        out = await hidos_offline.orchestrate(
            user_id="u1", description="test",
            emotions=fear_emotions, dominant_motive="control", category="fear",
        )
        assert 0.0 <= out.system_state.overall_uncertainty <= 1.0


# ── Step 6: Reflective Intervention ──────────────────────────────────────────

class TestReflectiveIntervention:
    @pytest.mark.asyncio
    async def test_reflective_insight_not_empty(self, hidos_offline, fear_emotions):
        out = await hidos_offline.orchestrate(
            user_id="u1", description="recurring overwork cycle",
            emotions=fear_emotions, dominant_motive="control_drive", category="fear",
        )
        assert len(out.reflective_insight) > 50

    @pytest.mark.asyncio
    async def test_intervention_has_urgency_level(self, hidos_offline, fear_emotions):
        out = await hidos_offline.orchestrate(
            user_id="u1", description="test",
            emotions=fear_emotions, dominant_motive="control_drive", category="fear",
        )
        d = out.to_dict()
        assert "urgency_level" in d["intervention"]
        assert d["intervention"]["urgency_level"] in ("low", "moderate", "elevated", "high")

    @pytest.mark.asyncio
    async def test_reflection_notes_acknowledged(self, hidos_offline, fear_emotions):
        out = await hidos_offline.orchestrate(
            user_id="u1", description="test",
            emotions=fear_emotions, dominant_motive="control", category="fear",
            reflection_notes="I noticed I keep controlling outcomes out of fear",
        )
        text = out.reflective_insight.lower()
        reflection_markers = ["reflect", "b(loop)", "breaking", "dampen", "noted"]
        assert any(m in text for m in reflection_markers), \
            f"Reflection notes should be acknowledged. Got: {out.reflective_insight[:200]}"


# ── Safety Invariants ─────────────────────────────────────────────────────────

class TestSafetyInvariants:
    FORBIDDEN_IDENTITY = [
        "you are a ", "your personality", "you are the type",
        "this defines you", "you will always", "you are destined",
    ]
    FORBIDDEN_DIRECTIVE = [
        "you must", "you need to", "you should immediately",
        "stop doing", "you are required",
    ]

    @pytest.mark.asyncio
    async def test_no_identity_labels_in_insight(self, hidos_offline, fear_emotions):
        out = await hidos_offline.orchestrate(
            user_id="u1", description="test",
            emotions=fear_emotions, dominant_motive="control_drive", category="fear",
        )
        text = out.reflective_insight.lower()
        for phrase in self.FORBIDDEN_IDENTITY:
            assert phrase not in text, f"Identity label found: '{phrase}'"

    @pytest.mark.asyncio
    async def test_no_directive_commands_in_insight(self, hidos_offline, fear_emotions):
        out = await hidos_offline.orchestrate(
            user_id="u1", description="test",
            emotions=fear_emotions, dominant_motive="control_drive", category="fear",
        )
        text = out.reflective_insight.lower()
        for phrase in self.FORBIDDEN_DIRECTIVE:
            assert phrase not in text, f"Directive command found: '{phrase}'"

    @pytest.mark.asyncio
    async def test_disclaimer_always_present(self, hidos_offline, fear_emotions):
        out = await hidos_offline.orchestrate(
            user_id="u1", description="test",
            emotions=fear_emotions, dominant_motive="control_drive", category="fear",
        )
        assert len(out.disclaimer) > 50

    @pytest.mark.asyncio
    async def test_confidence_never_above_cap(self, hidos_offline, fear_emotions):
        out = await hidos_offline.orchestrate(
            user_id="u1", description="test",
            emotions=fear_emotions, dominant_motive="control_drive", category="fear",
        )
        assert out.confidence <= 0.87, \
            f"HIDOS confidence {out.confidence} exceeds 0.87 cap"

    @pytest.mark.asyncio
    async def test_insight_contains_agency_statement(self, hidos_offline, fear_emotions):
        out = await hidos_offline.orchestrate(
            user_id="u1", description="test",
            emotions=fear_emotions, dominant_motive="control_drive", category="fear",
        )
        text = out.reflective_insight.lower()
        agency = ["change", "possible", "dynamic", "agency", "always", "structurally"]
        found  = [m for m in agency if m in text]
        assert len(found) >= 1, \
            f"Agency statement missing from insight. Found: {found}"

    @pytest.mark.asyncio
    async def test_graceful_degradation_all_offline(self, hidos_offline):
        """All subsystems offline — should still return valid output with disclaimer."""
        out = await hidos_offline.orchestrate(
            user_id="u_unknown", description="",
            emotions=[], dominant_motive="", category="general",
        )
        assert isinstance(out, HIDOSOutput)
        assert out.disclaimer != ""
        assert out.schema == "hidos_v3.5"
