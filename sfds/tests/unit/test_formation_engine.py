"""
Unit Tests — Formation Engine

Tests the 5-layer computation engine without any DB dependencies.
All tests use preloaded_history=[] (baseline mode) for isolation.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.formation_engine import (
    FormationEngine,
    CharacterDimension,
    DominantLoop,
    TrajectoryDirection,
)


@pytest.fixture
def engine():
    return FormationEngine(db_pool=None)


class TestFormationStateVector:
    def test_baseline_scores_are_midpoint(self, engine):
        insight = engine.analyze_sync("user1", [], False)
        v = insight.state_vector.to_dict()
        for key, val in v.items():
            assert val == 0.50, f"Baseline {key} should be 0.50, got {val}"

    def test_fear_pattern_raises_fear_tendency(self, engine):
        insight = engine.analyze_sync("user1", ["fear"], False)
        v = insight.state_vector.to_dict()
        assert v["fear_tendency"] > 0.50, "fear pattern should raise fear_tendency"

    def test_growth_pattern_raises_positive_dims(self, engine):
        insight = engine.analyze_sync("user1", ["growth"], False)
        v = insight.state_vector.to_dict()
        assert v["resilience"] > 0.50
        assert v["truth_alignment"] > 0.50

    def test_scores_always_bounded(self, engine):
        for categories in [["fear"] * 10, ["growth"] * 10, ["pride", "shame"]]:
            insight = engine.analyze_sync("user1", categories[:3], False)
            for k, v in insight.state_vector.to_dict().items():
                assert 0.05 <= v <= 0.95, f"{k}={v} out of bounds"

    def test_loop_break_reduces_fear_tendency(self, engine):
        insight_no_break  = engine.analyze_sync("user1", ["fear"], False)
        insight_with_break= engine.analyze_sync("user1", ["fear"], True)
        assert (
            insight_with_break.state_vector.fear_tendency
            < insight_no_break.state_vector.fear_tendency
        )


class TestTrajectoryDirection:
    def test_improving_clarity_on_growth(self, engine):
        insight = engine.analyze_sync("user1", ["growth"], False)
        assert insight.trajectory_direction in (
            TrajectoryDirection.IMPROVING_CLARITY.value,
            TrajectoryDirection.STABILIZING.value,
            TrajectoryDirection.UNKNOWN.value,
        )

    def test_dominant_loop_fear_on_fear_pattern(self, engine):
        insight = engine.analyze_sync("user1", ["fear"], False)
        assert insight.dominant_loop == DominantLoop.FEAR_CONTROL.value


class TestFormationArc:
    def test_deepening_loops_on_fear_pattern(self, engine):
        insight = engine.analyze_sync("user1", ["fear", "pride"], False,
                                      emotional_intensity=8.0)
        assert insight.formation_arc in ("deepening_loops", "unknown")

    def test_breaking_through_on_growth(self, engine):
        insight = engine.analyze_sync("user1", ["growth"], True,
                                      emotional_intensity=8.0)
        assert insight.formation_arc in ("breaking_through", "unknown")


class TestWeighting:
    def test_high_intensity_amplifies_deltas(self, engine):
        low  = engine.analyze_sync("user1", ["fear"], False, emotional_intensity=2.0)
        high = engine.analyze_sync("user1", ["fear"], False, emotional_intensity=9.0)
        low_fear  = low.state_vector.fear_tendency
        high_fear = high.state_vector.fear_tendency
        assert high_fear > low_fear, "Higher intensity should amplify fear_tendency delta"

    def test_reflection_dampens_negative_impact(self, engine):
        no_reflect = engine.analyze_sync("user1", ["fear"], False, reflection_active=False)
        with_reflect = engine.analyze_sync("user1", ["fear"], False, reflection_active=True)
        assert (
            with_reflect.state_vector.emotional_stability
            >= no_reflect.state_vector.emotional_stability
        ), "Reflection should reduce negative impact on stability"


class TestDesignInvariants:
    def test_no_identity_label_in_output(self, engine):
        insight = engine.analyze_sync("user1", ["fear", "shame"], False)
        d = insight.to_dict()
        narrative = str(d.get("trajectory_narrative", ""))
        forbidden_phrases = ["you are a ", "you are the ", "you are someone who"]
        for phrase in forbidden_phrases:
            assert phrase not in narrative.lower(), f"Found identity label: '{phrase}'"

    def test_disclaimer_present(self, engine):
        insight = engine.analyze_sync("user1", ["fear"], False)
        d = insight.to_dict()
        assert "disclaimer" in d
        assert len(d["disclaimer"]) > 20

    def test_confidence_never_exceeds_cap(self, engine):
        for i in range(1, 31):
            history = [{"fear_tendency_delta": 0.1} for _ in range(i)]
            insight = engine.analyze_sync("user1", ["fear"], False,
                                          preloaded_history=history)
            dims = insight.current_snapshot.dimensions
            for dim_name, sc in dims.items():
                assert sc.confidence <= 0.90, (
                    f"Confidence {sc.confidence} exceeds 0.90 for {dim_name} at history={i}"
                )
