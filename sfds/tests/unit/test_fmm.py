"""
Unit Tests — Formation Mathematics Model v3.4 (FMM)

All tests run without any database connection.
Tests validate:
  - FormationVector bounds and operations
  - Dynamics equation: ΔX = α·G + β·E + γ·P + δ·N
  - Loop reinforcement R and breaking B coefficients
  - Stability analysis
  - Trajectory classification (all 6 directions)
  - Intervention score computation
  - Safety invariants (no identity labels, confidence cap)
  - FMM.step() end-to-end
"""

import pytest
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ai.formation.fmm import (
    FormationVector, LoopDynamics, StabilityAnalysis,
    FormationMathematicsModel, TrajectoryDirection, AccelerationDirection,
    compute_delta, apply_delta, compute_stability, compute_trajectory,
    compute_intervention_score, _compute_G, _compute_E, _compute_P, _compute_N,
    build_loop_dynamics_from_pattern,
    SCORE_MIN, SCORE_MAX, CONFIDENCE_CAP, ALPHA, BETA, GAMMA, DELTA,
)


# ── FormationVector ───────────────────────────────────────────────────────────

class TestFormationVector:
    def test_default_all_midpoint(self):
        v = FormationVector()
        for k, val in v.to_dict().items():
            assert val == 0.50, f"{k} should start at 0.50"

    def test_clamp_enforces_bounds(self):
        v = FormationVector(fear_tendency=2.0, truth_alignment=-1.0)
        v.clamp()
        assert v.fear_tendency  == SCORE_MAX
        assert v.truth_alignment == SCORE_MIN

    def test_from_dict_roundtrip(self):
        d = {"fear_tendency": 0.70, "resilience": 0.30}
        v = FormationVector.from_dict(d)
        assert v.fear_tendency == 0.70
        assert v.resilience    == 0.30
        assert v.truth_alignment == 0.50  # unchanged

    def test_zero_vector_all_zero(self):
        z = FormationVector.zero()
        for k, val in z.__dict__.items():
            assert val == 0.0, f"{k} should be 0.0"

    def test_distance_from_baseline(self):
        v = FormationVector(fear_tendency=0.80)
        d = v.distance_from_baseline()
        assert d["fear_tendency"] == pytest.approx(0.30, abs=0.001)
        assert d["truth_alignment"] == pytest.approx(0.00, abs=0.001)

    def test_never_zero_or_one_after_clamp(self):
        v = FormationVector()
        for k in v.__dataclass_fields__:
            setattr(v, k, 0.0)
        v.clamp()
        for k, val in v.to_dict().items():
            assert val >= SCORE_MIN, f"{k} should not go below SCORE_MIN"


# ── Loop Dynamics Coefficients ────────────────────────────────────────────────

class TestLoopDynamics:
    def test_R_increases_with_repetition(self):
        ld1 = LoopDynamics("p1", "fear_control_loop", repetition_count=1,
                           emotional_intensity=5.0, recency_weight=1.0)
        ld5 = LoopDynamics("p1", "fear_control_loop", repetition_count=5,
                           emotional_intensity=5.0, recency_weight=1.0)
        assert ld5.R > ld1.R

    def test_R_capped_at_095(self):
        ld = LoopDynamics("p1", "fear", repetition_count=1000,
                          emotional_intensity=10.0, recency_weight=1.0)
        assert ld.R <= 0.95

    def test_B_zero_without_principle_or_awareness(self):
        ld = LoopDynamics("p1", "fear", principle_strength=0.0,
                          awareness_level=0.0, interruption_action=0.0)
        assert ld.B == 0.0

    def test_B_increases_with_reflection_and_principle(self):
        ld_base = LoopDynamics("p1", "fear",
                               principle_strength=0.0, awareness_level=0.0, interruption_action=0.0)
        ld_full = LoopDynamics("p1", "fear",
                               principle_strength=0.80, awareness_level=1.0, interruption_action=0.80)
        assert ld_full.B > ld_base.B

    def test_net_momentum_positive_when_loop_active(self):
        ld = LoopDynamics("p1", "fear", repetition_count=3,
                          emotional_intensity=7.0, recency_weight=1.0,
                          principle_strength=0.0, awareness_level=0.0)
        assert ld.net_momentum > 0

    def test_net_momentum_negative_when_loop_breaking(self):
        ld = LoopDynamics("p1", "fear", repetition_count=1,
                          emotional_intensity=3.0, recency_weight=0.5,
                          principle_strength=0.90, awareness_level=1.0, interruption_action=0.90)
        assert ld.net_momentum < 0

    def test_build_from_pattern_reflection_active(self):
        pattern = {"id": "A01", "loop_type": "fear_control_loop"}
        ld = build_loop_dynamics_from_pattern(pattern, reflection=True, loop_broken=True)
        assert ld.awareness_level == 1.0
        assert ld.interruption_action == 0.80


# ── Influence Terms ───────────────────────────────────────────────────────────

class TestInfluenceTerms:
    def test_G_increases_fear_tendency_on_active_loop(self):
        ld = LoopDynamics("A01_fear", "fear_control_loop",
                          repetition_count=3, emotional_intensity=7.0, recency_weight=1.0)
        pdims = {"A01_fear": {"fear_tendency": "+", "emotional_stability": "-"}}
        G = _compute_G([ld], pdims)
        assert G.fear_tendency > 0, "Active fear loop should push fear_tendency positive"
        assert G.emotional_stability < 0, "Active fear loop should push stability negative"

    def test_G_reverses_on_breaking_loop(self):
        ld = LoopDynamics("A01_fear", "fear_control_loop",
                          repetition_count=1, emotional_intensity=3.0,
                          principle_strength=0.90, awareness_level=1.0,
                          interruption_action=0.90)
        assert ld.net_momentum < 0   # loop breaking
        G = _compute_G([ld], {"A01_fear": {"fear_tendency": "+"}})
        assert G.fear_tendency < 0, "Breaking loop should reduce fear_tendency"

    def test_E_high_volatility_reduces_stability(self):
        E = _compute_E(emotional_volatility=9.0, stress_spikes=3, stability_trend=0.0)
        assert E.emotional_stability < 0
        assert E.fear_tendency > 0

    def test_E_improving_trend_increases_resilience(self):
        E = _compute_E(emotional_volatility=2.0, stress_spikes=0, stability_trend=0.8)
        assert E.resilience > 0

    def test_P_humility_principle_reduces_pride(self):
        P = _compute_P([{"score": 0.90, "category": "humility"}])
        assert P.pride_tendency < 0
        # humility dim is in FormationVector as just "humility" → not a field, but no error

    def test_P_rest_principle_reduces_fear(self):
        P = _compute_P([{"score": 0.85, "category": "rest"}])
        assert P.fear_tendency < 0
        assert P.resilience > 0

    def test_N_is_nonzero(self):
        N = _compute_N()
        vals = list(N.__dict__.values())
        assert any(abs(v) > 1e-10 for v in vals), "Noise term must never be all zeros"

    def test_N_different_calls_differ(self):
        N1 = _compute_N()
        N2 = _compute_N()
        diffs = [abs(getattr(N1, k) - getattr(N2, k))
                 for k in N1.__dataclass_fields__]
        assert any(d > 1e-10 for d in diffs), "Noise must be non-deterministic"


# ── Dynamics Equation ─────────────────────────────────────────────────────────

class TestDynamicsEquation:
    def test_delta_composition(self):
        G = FormationVector.zero()
        E = FormationVector.zero()
        P = FormationVector.zero()
        N = FormationVector.zero()
        dx = compute_delta(G, E, P, N)
        for k, v in dx.__dict__.items():
            assert v == pytest.approx(0.0, abs=1e-10), f"{k} should be 0 with all-zero inputs"

    def test_delta_respects_weights(self):
        G = FormationVector.zero(); G.fear_tendency = 1.0
        E = FormationVector.zero()
        P = FormationVector.zero()
        N = FormationVector.zero()
        dx = compute_delta(G, E, P, N)
        assert dx.fear_tendency == pytest.approx(ALPHA * 1.0, abs=1e-6)

    def test_apply_delta_clamps(self):
        X  = FormationVector(fear_tendency=0.90)
        dx = FormationVector.zero(); dx.fear_tendency = 0.20
        X2 = apply_delta(X, dx)
        assert X2.fear_tendency <= SCORE_MAX

    def test_apply_delta_does_not_go_below_min(self):
        X  = FormationVector(truth_alignment=0.10)
        dx = FormationVector.zero(); dx.truth_alignment = -0.20
        X2 = apply_delta(X, dx)
        assert X2.truth_alignment >= SCORE_MIN


# ── Stability Analysis ────────────────────────────────────────────────────────

class TestStabilityAnalysis:
    def test_insufficient_history_returns_midpoint(self):
        s = compute_stability([FormationVector()])
        assert s.stability_score == 0.50
        assert "Insufficient" in s.coherence_note

    def test_stable_history_high_score(self):
        h = [FormationVector()] * 10  # identical → zero variance
        s = compute_stability(h)
        assert s.stability_score >= 0.90

    def test_volatile_history_low_score(self):
        h = [
            FormationVector(fear_tendency=0.80, emotional_stability=0.20),
            FormationVector(fear_tendency=0.20, emotional_stability=0.80),
        ] * 5
        s = compute_stability(h)
        assert s.stability_score < 0.80

    def test_critical_transition_flagged(self):
        # Alternate extremes to maximise variance per dimension (≥ CRITICAL_VARIANCE=0.04)
        # fear_tendency: alternates 0.95 / 0.05 → variance ≈ 0.2025 >> 0.04
        h = [
            FormationVector(fear_tendency=0.95, emotional_stability=0.05),
            FormationVector(fear_tendency=0.05, emotional_stability=0.95),
        ] * 5
        s = compute_stability(h)
        assert s.is_critical, (
            f"Expected is_critical=True for extreme swings, "
            f"got variance={s.overall_variance}, threshold=0.04"
        )


# ── Trajectory Analysis ───────────────────────────────────────────────────────

class TestTrajectoryAnalysis:
    def test_no_previous_returns_unknown(self):
        t = compute_trajectory(FormationVector(), None, [])
        assert t.direction == TrajectoryDirection.UNKNOWN

    def test_improving_clarity_detected(self):
        prev = FormationVector(truth_alignment=0.50, spiritual_clarity=0.50)
        curr = FormationVector(truth_alignment=0.56, spiritual_clarity=0.55)
        t = compute_trajectory(curr, prev, [prev])
        assert t.direction == TrajectoryDirection.IMPROVING_CLARITY

    def test_stabilizing_detected(self):
        prev = FormationVector(emotional_stability=0.44, fear_tendency=0.58, resilience=0.46)
        curr = FormationVector(emotional_stability=0.50, fear_tendency=0.53, resilience=0.48)
        t = compute_trajectory(curr, prev, [prev])
        assert t.direction == TrajectoryDirection.STABILIZING

    def test_increasing_volatility_detected(self):
        prev = FormationVector(emotional_stability=0.55, fear_tendency=0.50)
        curr = FormationVector(emotional_stability=0.45, fear_tendency=0.58)
        t = compute_trajectory(curr, prev, [prev])
        assert t.direction == TrajectoryDirection.INCREASING_VOLATILITY

    def test_drift_detected(self):
        curr = FormationVector(
            fear_tendency=0.72, pride_tendency=0.68,
            emotional_stability=0.30, truth_alignment=0.30,
        )
        t = compute_trajectory(curr, FormationVector(), [])
        assert t.drift_detected

    def test_narrative_uses_probabilistic_language(self):
        prev = FormationVector(truth_alignment=0.50)
        curr = FormationVector(truth_alignment=0.56, spiritual_clarity=0.55)
        t    = compute_trajectory(curr, prev, [prev])
        text = t.description.lower()
        markers = ["tends", "appears", "may", "possible", "structural"]
        assert any(m in text for m in markers), \
            f"Trajectory narrative must use probabilistic language. Got: {t.description}"


# ── Intervention Score ────────────────────────────────────────────────────────

class TestInterventionScore:
    def test_no_loops_returns_low_urgency(self):
        stab = StabilityAnalysis(stability_score=0.80)
        i    = compute_intervention_score([], stab, [])
        assert i.urgency_level == "low"
        assert i.score == 0.0

    def test_high_R_high_instability_yields_elevated(self):
        ld   = LoopDynamics("A01", "fear", repetition_count=5,
                            emotional_intensity=8.0, recency_weight=1.0)
        stab = StabilityAnalysis(stability_score=0.20)  # high instability
        i    = compute_intervention_score([ld], stab, [{"score": 0.10, "category": "general"}])
        assert i.urgency_level in ("elevated", "high")

    def test_high_principle_reduces_urgency(self):
        ld    = LoopDynamics("A01", "fear", repetition_count=2,
                             emotional_intensity=5.0, recency_weight=0.8)
        stab  = StabilityAnalysis(stability_score=0.60)
        princ = [{"score": 0.95, "category": "truth"}]
        i     = compute_intervention_score([ld], stab, princ)
        # Higher principle_alignment → lower I score
        assert i.score < 0.50

    def test_note_is_non_directive(self):
        ld   = LoopDynamics("A01", "fear", repetition_count=3, emotional_intensity=7.0)
        stab = StabilityAnalysis(stability_score=0.40)
        i    = compute_intervention_score([ld], stab, [])
        assert "signal" in i.note.lower() or "structural" in i.note.lower()
        forbidden = ["you must", "you should", "you need to"]
        for f in forbidden:
            assert f not in i.note.lower(), f"Note must not be directive: '{f}'"


# ── FMM.step() end-to-end ─────────────────────────────────────────────────────

class TestFMMStep:
    @pytest.fixture
    def fmm(self):
        return FormationMathematicsModel()

    @pytest.fixture
    def fear_loop(self):
        return LoopDynamics(
            pattern_id="A01_fear", loop_type="fear_control_loop",
            repetition_count=3, emotional_intensity=7.0, recency_weight=1.0,
        )

    def test_step_returns_fmmoutput(self, fmm, fear_loop):
        from ai.formation.fmm import FMMOutput
        out = fmm.step(
            current_vector    = FormationVector(),
            loop_dynamics     = [fear_loop],
            emotional_signal  = {"volatility": 7.0, "stress_spikes": 2, "stability_trend": -0.2},
            principle_scores  = [],
            history           = [],
            _noise_seed       = 42,
        )
        assert isinstance(out, FMMOutput)
        assert out.schema == "fmm_v3.4"

    def test_active_fear_loop_raises_fear_tendency(self, fmm, fear_loop):
        X0  = FormationVector(fear_tendency=0.50)
        out = fmm.step(
            current_vector   = X0,
            loop_dynamics    = [fear_loop],
            emotional_signal = {"volatility": 8.0, "stress_spikes": 0, "stability_trend": 0.0},
            principle_scores = [],
            history          = [],
            pattern_dims     = {"A01_fear": {"fear_tendency": "+", "emotional_stability": "-"}},
            _noise_seed      = 1,
        )
        assert out.state_vector.fear_tendency > 0.50, \
            "Active fear loop should increase fear_tendency"

    def test_reflection_with_principle_can_reduce_fear(self, fmm):
        ld = LoopDynamics("A01_fear", "fear_control_loop",
                          repetition_count=1, emotional_intensity=4.0,
                          principle_strength=0.85, awareness_level=1.0,
                          interruption_action=0.80)
        X0 = FormationVector(fear_tendency=0.65)
        out = fmm.step(
            current_vector   = X0,
            loop_dynamics    = [ld],
            emotional_signal = {"volatility": 3.0, "stress_spikes": 0, "stability_trend": 0.3},
            principle_scores = [{"score": 0.85, "category": "truth", "label": "Truth sets free"}],
            history          = [],
            pattern_dims     = {"A01_fear": {"fear_tendency": "+"}},
            _noise_seed      = 99,
        )
        assert out.state_vector.fear_tendency <= 0.65, \
            "Breaking function should not increase fear further"

    def test_confidence_bounded(self, fmm, fear_loop):
        out = fmm.step(
            current_vector   = FormationVector(),
            loop_dynamics    = [fear_loop],
            emotional_signal = {"volatility": 5.0, "stress_spikes": 0, "stability_trend": 0.0},
            principle_scores = [],
            history          = [FormationVector()] * 12,
            _noise_seed      = 7,
        )
        assert out.confidence <= CONFIDENCE_CAP, \
            f"FMM confidence {out.confidence} exceeds cap {CONFIDENCE_CAP}"

    def test_output_dict_has_all_keys(self, fmm, fear_loop):
        out = fmm.step(
            current_vector   = FormationVector(),
            loop_dynamics    = [fear_loop],
            emotional_signal = {"volatility": 5.0},
            principle_scores = [],
            history          = [],
            _noise_seed      = 0,
        )
        d = out.to_dict()
        required = {
            "schema", "state_vector", "delta_vector", "loop_dynamics",
            "stability", "trajectory", "intervention",
            "reflective_insight", "confidence", "disclaimer",
        }
        assert required <= set(d.keys()), f"Missing keys: {required - set(d.keys())}"

    def test_disclaimer_always_present(self, fmm):
        out = fmm.step(
            current_vector=FormationVector(), loop_dynamics=[],
            emotional_signal={}, principle_scores=[], history=[],
        )
        assert len(out.disclaimer) > 50

    def test_reflective_insight_no_identity_labels(self, fmm, fear_loop):
        out = fmm.step(
            current_vector   = FormationVector(fear_tendency=0.75),
            loop_dynamics    = [fear_loop],
            emotional_signal = {"volatility": 8.0, "stress_spikes": 3},
            principle_scores = [],
            history          = [],
            _noise_seed      = 55,
        )
        text     = out.reflective_insight.lower()
        forbidden = ["you are a ", "your personality", "you are the type", "this defines you"]
        for phrase in forbidden:
            assert phrase not in text, f"Identity label found: '{phrase}'"
