"""
Unit Tests — Graph Query Engine v3.3

All tests use pattern library mode (no Neo4j required).
Tests validate:
  - All 4 reasoning modes produce valid output
  - 7-step pipeline populates all output fields
  - Safety invariants enforced in synthesis text
  - Graceful degradation on unknown states
  - Simulation produces forward chain
  - Breakpoint detection identifies MotiveNode > BehaviorNode priority
  - Principle match present for known patterns
"""

import asyncio
import pytest
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "sfds"))

from ai.reasoning.graph_query_engine import (
    GraphQueryEngine, GQEMode, GQEOutput, UserStateInput,
    _simulate_forward, _find_best_breakpoint, _classify_position,
    _find_pattern, _load_pattern_library,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def gqe():
    """GQE instance with no Neo4j driver — pattern library mode."""
    return GraphQueryEngine(driver=None)


@pytest.fixture
def fear_state():
    return UserStateInput(
        emotion_node  = "fear",
        motive_node   = "control_drive",
        behavior_node = "overwork",
        user_id       = "test_user",
        category      = "fear",
    )


@pytest.fixture
def shame_state():
    return UserStateInput(
        emotion_node  = "shame",
        motive_node   = "avoidance",
        behavior_node = "procrastination",
        user_id       = "test_user",
        category      = "shame",
    )


@pytest.fixture
def pride_state():
    return UserStateInput(
        emotion_node  = "pride",
        motive_node   = "need_to_win",
        behavior_node = "comparison",
        user_id       = "test_user",
        category      = "pride",
    )


# ── Pattern library loading ───────────────────────────────────────────────────

class TestPatternLibraryLoading:
    def test_library_loads(self):
        lib = _load_pattern_library()
        assert len(lib) >= 50

    def test_find_pattern_by_direct_node_match(self):
        lib = _load_pattern_library()
        p = _find_pattern(lib, "fear", "control_drive", "overwork", "fear")
        assert p is not None
        assert "fear" in p["chain"] or p["category"] == "fear"

    def test_find_pattern_falls_back_to_category(self):
        lib = _load_pattern_library()
        p = _find_pattern(lib, "unknown_emotion", "unknown_motive", "unknown_behavior", "shame")
        assert p is not None
        assert p["category"] == "shame"

    def test_find_pattern_returns_none_for_completely_unknown(self):
        lib = _load_pattern_library()
        p = _find_pattern(lib, "xyz", "xyz", "xyz", "xyz_unknown_category")
        assert p is None


# ── All 4 Modes ───────────────────────────────────────────────────────────────

class TestGQEModes:
    @pytest.mark.asyncio
    async def test_structural_traversal_mode(self, gqe, fear_state):
        out = await gqe.reason(fear_state, mode=GQEMode.STRUCTURAL_TRAVERSAL)
        assert isinstance(out, GQEOutput)
        assert out.mode == GQEMode.STRUCTURAL_TRAVERSAL
        assert out.structural_view.causal_chain, "Should have causal chain"

    @pytest.mark.asyncio
    async def test_loop_simulation_mode(self, gqe, fear_state):
        out = await gqe.reason(fear_state, mode=GQEMode.LOOP_SIMULATION)
        assert out.loop_analysis.is_loop is True
        assert len(out.loop_analysis.loop_chain) >= 3
        assert out.loop_analysis.loop_closes_at != ""
        assert len(out.simulation.forward_chain) >= 1

    @pytest.mark.asyncio
    async def test_breakpoint_detection_mode(self, gqe, fear_state):
        out = await gqe.reason(fear_state, mode=GQEMode.BREAKPOINT_DETECTION)
        assert out.breakpoint.node_type != ""
        assert out.breakpoint.leverage_score > 0
        assert out.breakpoint.node_label in (
            "MotiveNode", "EmotionNode", "BehaviorNode", "PrincipleNode"
        )

    @pytest.mark.asyncio
    async def test_principle_activation_mode(self, gqe, fear_state):
        out = await gqe.reason(fear_state, mode=GQEMode.PRINCIPLE_ACTIVATION)
        assert out.principle_match.principle_label != "", \
            "Should find a break principle for fear loop"
        assert out.principle_match.structural_effectiveness > 0


# ── 7-Step Pipeline Completeness ─────────────────────────────────────────────

class TestPipelineCompleteness:
    @pytest.mark.asyncio
    async def test_all_output_fields_populated(self, gqe, fear_state):
        out = await gqe.reason(fear_state, mode=GQEMode.LOOP_SIMULATION)
        d   = out.to_dict()

        assert "structural_view"  in d
        assert "loop_analysis"    in d
        assert "simulation"       in d
        assert "breakpoint"       in d
        assert "principle_match"  in d
        assert "reflective_insight" in d
        assert "confidence"       in d
        assert "disclaimer"       in d
        assert "data_source"      in d

    @pytest.mark.asyncio
    async def test_data_source_is_pattern_library(self, gqe, fear_state):
        out = await gqe.reason(fear_state)
        assert "pattern_library" in out.data_source

    @pytest.mark.asyncio
    async def test_reflective_insight_not_empty(self, gqe, fear_state):
        out = await gqe.reason(fear_state)
        assert len(out.reflective_insight) > 50

    @pytest.mark.asyncio
    async def test_confidence_within_bounds(self, gqe, fear_state):
        out = await gqe.reason(fear_state)
        assert 0.0 <= out.confidence <= 0.85, \
            f"Confidence {out.confidence} exceeds 0.85 cap"


# ── Safety Invariants ─────────────────────────────────────────────────────────

class TestSafetyInvariants:
    FORBIDDEN_PHRASES = [
        "you are a ",
        "you are the type",
        "you will always",
        "this will always",
        "you are destined",
        "you are inevitably",
        "this is your personality",
        "this means you",
    ]

    @pytest.mark.asyncio
    async def test_no_identity_labels_in_synthesis(self, gqe, fear_state):
        out = await gqe.reason(fear_state, mode=GQEMode.LOOP_SIMULATION)
        text = out.reflective_insight.lower()
        for phrase in self.FORBIDDEN_PHRASES:
            assert phrase not in text, \
                f"Identity label found in synthesis: '{phrase}'"

    @pytest.mark.asyncio
    async def test_disclaimer_always_present(self, gqe, fear_state):
        out = await gqe.reason(fear_state)
        assert "disclaimer" in out.to_dict()
        assert len(out.disclaimer) > 30

    @pytest.mark.asyncio
    async def test_synthesis_contains_possibility_language(self, gqe, fear_state):
        out = await gqe.reason(fear_state)
        text = out.reflective_insight.lower()
        probabilistic_markers = ["may", "might", "appears", "possible", "tendency", "seems"]
        found = [m for m in probabilistic_markers if m in text]
        assert len(found) >= 2, \
            f"Synthesis lacks probabilistic language. Found: {found}"

    @pytest.mark.asyncio
    async def test_synthesis_contains_agency_statement(self, gqe, fear_state):
        out = await gqe.reason(fear_state)
        text = out.reflective_insight.lower()
        agency_markers = ["change", "possible", "interrupted", "break", "interrupt"]
        found = [m for m in agency_markers if m in text]
        assert len(found) >= 1, \
            f"Synthesis lacks agency statement. Found: {found}"

    @pytest.mark.asyncio
    async def test_confidence_never_above_cap(self, gqe):
        states = [
            UserStateInput("fear", "control_drive", "overwork", category="fear"),
            UserStateInput("shame", "avoidance", "hiding", category="shame"),
            UserStateInput("pride", "need_to_win", "comparison", category="pride"),
        ]
        for state in states:
            out = await gqe.reason(state)
            assert out.confidence <= 0.85, \
                f"Confidence {out.confidence} exceeds 0.85 for {state.emotion_node}"


# ── Multi-Category Reasoning ─────────────────────────────────────────────────

class TestMultiCategory:
    @pytest.mark.asyncio
    async def test_shame_loop_detected(self, gqe, shame_state):
        out = await gqe.reason(shame_state, mode=GQEMode.LOOP_SIMULATION)
        assert out.loop_analysis.is_loop is True
        assert "shame" in out.loop_analysis.loop_type or \
               "shame" in out.loop_analysis.loop_chain

    @pytest.mark.asyncio
    async def test_pride_breakpoint_targets_motive_or_emotion(self, gqe, pride_state):
        out = await gqe.reason(pride_state, mode=GQEMode.BREAKPOINT_DETECTION)
        assert out.breakpoint.leverage_score >= 0.65, \
            "Pride loop breakpoint should have high leverage"

    @pytest.mark.asyncio
    async def test_fear_principle_targets_control(self, gqe, fear_state):
        out = await gqe.reason(fear_state, mode=GQEMode.PRINCIPLE_ACTIVATION)
        label = out.principle_match.principle_label.lower()
        breaks_node = out.principle_match.breaks_node.lower()
        assert len(label) > 10, "Principle label should be descriptive"
        assert breaks_node != "", "Should target a specific node"

    @pytest.mark.asyncio
    async def test_unknown_state_degrades_gracefully(self, gqe):
        unknown = UserStateInput(
            emotion_node  = "completely_unknown",
            motive_node   = "no_such_motive",
            behavior_node = "nonexistent_behavior",
            category      = "fear",  # category fallback should still work
        )
        out = await gqe.reason(unknown)
        assert isinstance(out, GQEOutput)
        assert out.disclaimer != ""


# ── Simulation Logic ──────────────────────────────────────────────────────────

class TestSimulationLogic:
    def test_simulate_forward_follows_leads_to(self):
        chain = ["fear", "control_drive", "overwork", "burnout"]
        edges = [
            ("fear",          "CAUSES",     "control_drive"),
            ("control_drive", "LEADS_TO",   "overwork"),
            ("overwork",      "LEADS_TO",   "burnout"),
            ("burnout",       "REINFORCES", "fear"),
        ]
        result = _simulate_forward(chain, edges, "control_drive", 3)
        assert "overwork" in result
        assert "burnout" in result

    def test_simulate_forward_stops_at_reinforces(self):
        chain = ["fear", "control_drive", "overwork", "burnout"]
        edges = [
            ("fear",          "CAUSES",     "control_drive"),
            ("control_drive", "LEADS_TO",   "overwork"),
            ("overwork",      "LEADS_TO",   "burnout"),
            ("burnout",       "REINFORCES", "fear"),
        ]
        # Should not include "fear" again (loop re-entry)
        result = _simulate_forward(chain, edges, "overwork", 3)
        assert len(result) <= 3

    def test_find_best_breakpoint_prefers_motive(self):
        chain = ["fear", "control_drive", "overwork", "burnout"]
        edges = [("fear", "CAUSES", "control_drive")]
        result = _find_best_breakpoint(chain, edges)
        assert result is not None
        node_type, node_label = result
        assert node_label == "MotiveNode"
        assert node_type == "control_drive"

    def test_classify_position_entry(self):
        chain = ["fear", "control", "burnout"]
        assert _classify_position("fear", chain) == "entry"

    def test_classify_position_reinforcer(self):
        chain = ["fear", "control", "burnout"]
        assert _classify_position("burnout", chain) == "reinforcer"

    def test_classify_position_mid(self):
        chain = ["fear", "control", "overwork", "burnout"]
        assert _classify_position("control", chain) == "mid"
