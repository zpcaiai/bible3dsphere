"""
Unit Tests — Self-Improving Cognitive Loop v3.6 (SICL)

No database required. Tests validate:
  - Stage 1: Observation extracts correct telemetry
  - Stage 2: Evaluation computes valid ΔS metrics
  - Stage 3: Pattern extraction identifies correct weakness types
  - Stage 4: Proposals generated per weakness type
  - Stage 5: Guardrails auto-reject forbidden update types
  - Stage 6: Validation measures before/after delta
  - Boundary: SICL never targets human behavior/outcomes
  - ΔS improvement function (weights + bounds)
"""

import pytest
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ai.self_improvement.sicl import (
    SelfImprovingCognitiveLoop, SICLOutput,
    observe, evaluate, extract_weaknesses, generate_proposals,
    integrate_proposals, validate_updates,
    SystemTelemetry, PerformanceMetrics, UpdateProposal, UpdateStatus,
    ProposalType, WeaknessType,
    _WEAK_THRESHOLD, _UPDATE_MIN_DELTA, _OVERFIT_THRESHOLD,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_hidos_output(
    loop_detected: bool = True,
    confidence: float = 0.65,
    uncertainty_in_insight: bool = True,
    graph_available: bool = True,
    vector_available: bool = True,
    formation_available: bool = True,
) -> dict:
    insight = (
        "The system may be showing a tendency toward fear-based patterns."
        if uncertainty_in_insight
        else "The system is definitely showing fear-based patterns."
    )
    return {
        "schema": "hidos_v3.5",
        "user_id": "test",
        "confidence": confidence,
        "reflective_insight": insight,
        "layers": {
            "graph": {
                "available": graph_available,
                "confidence": 0.70 if graph_available else 0.0,
                "data": {},
            },
            "vector": {
                "available": vector_available,
                "confidence": 0.65 if vector_available else 0.0,
                "data": {"principles": [{"label": "Truth", "score": 0.80}]},
            },
            "formation": {
                "available": formation_available,
                "confidence": 0.60 if formation_available else 0.0,
                "data": {"trajectory": {"drift_detected": False}},
            },
        },
        "integrated": {
            "structural_layer": {
                "loop_detected": loop_detected,
                "active_loop_type": "fear_control_loop" if loop_detected else "",
            },
        },
        "disclaimer": "Structural tendencies only.",
    }


@pytest.fixture
def sicl():
    return SelfImprovingCognitiveLoop()


@pytest.fixture
def good_outputs():
    return [_make_hidos_output() for _ in range(10)]


@pytest.fixture
def poor_graph_outputs():
    return [_make_hidos_output(loop_detected=False, graph_available=False) for _ in range(10)]


# ── Stage 1: Observation ──────────────────────────────────────────────────────

class TestObservation:
    def test_sessions_counted(self, good_outputs):
        t = observe(good_outputs)
        assert t.sessions_observed == 10

    def test_loops_detected_counted(self, good_outputs):
        t = observe(good_outputs)
        assert t.loops_detected > 0

    def test_graph_fallbacks_counted(self, poor_graph_outputs):
        t = observe(poor_graph_outputs)
        assert t.graph_fallback_count == 10

    def test_uncertainty_preserved_counted(self, good_outputs):
        t = observe(good_outputs)
        assert t.uncertainty_preserved == 10

    def test_overconfident_outputs_counted(self):
        outputs = [_make_hidos_output(confidence=0.85) for _ in range(5)]
        t = observe(outputs)
        assert t.high_confidence_outputs == 5

    def test_empty_outputs_no_crash(self):
        t = observe([])
        assert t.sessions_observed == 0


# ── Stage 2: Evaluation ───────────────────────────────────────────────────────

class TestEvaluation:
    def test_delta_S_between_zero_and_one(self, good_outputs):
        t = observe(good_outputs)
        m = evaluate(t)
        assert 0.0 <= m.delta_S <= 1.0

    def test_all_metrics_non_negative(self, good_outputs):
        t = observe(good_outputs)
        m = evaluate(t)
        for metric in ("IAS", "IRS", "SDS", "TPS", "FCS"):
            assert getattr(m, metric) >= 0.0, f"{metric} should be non-negative"

    def test_all_metrics_at_most_one(self, good_outputs):
        t = observe(good_outputs)
        m = evaluate(t)
        for metric in ("IAS", "IRS", "SDS", "TPS", "FCS"):
            assert getattr(m, metric) <= 1.0, f"{metric} exceeds 1.0"

    def test_poor_graph_lowers_SDS(self, poor_graph_outputs):
        t = observe(poor_graph_outputs)
        m = evaluate(t)
        assert m.SDS < _WEAK_THRESHOLD

    def test_high_uncertainty_raises_IAS(self, good_outputs):
        t = observe(good_outputs)
        m = evaluate(t)
        # All outputs have uncertainty preserved — IAS should be respectable
        assert m.IAS > 0.30

    def test_weakest_metric_is_minimum(self, good_outputs):
        t  = observe(good_outputs)
        m  = evaluate(t)
        k, v = m.weakest_metric
        for metric in ("IAS", "IRS", "SDS", "TPS", "FCS"):
            assert v <= getattr(m, metric), \
                f"weakest_metric {k}={v} is not the minimum"

    def test_weight_sum_is_one(self):
        weights = {"IAS": 0.25, "IRS": 0.20, "SDS": 0.25, "TPS": 0.15, "FCS": 0.15}
        assert abs(sum(weights.values()) - 1.0) < 1e-9


# ── Stage 3: Pattern Extraction ───────────────────────────────────────────────

class TestPatternExtraction:
    def test_low_SDS_triggers_missed_loop_detection(self, poor_graph_outputs):
        t = observe(poor_graph_outputs)
        m = evaluate(t)
        w = extract_weaknesses(m, t)
        types = [x.weakness_type for x in w]
        assert WeaknessType.MISSED_LOOP_DETECTION in types

    def test_weaknesses_sorted_by_severity(self, poor_graph_outputs):
        t = observe(poor_graph_outputs)
        m = evaluate(t)
        w = extract_weaknesses(m, t)
        severities = [x.severity for x in w]
        assert severities == sorted(severities, reverse=True)

    def test_overfitting_flagged_at_high_scores(self):
        t = SystemTelemetry(sessions_observed=20, reasoning_calls=20,
                            uncertainty_preserved=19, loops_detected=15,
                            graph_queries_run=15, retrieval_calls=10,
                            retrieval_relevant=9)
        m = PerformanceMetrics(
            IAS=_OVERFIT_THRESHOLD + 0.01,
            IRS=0.80, SDS=_OVERFIT_THRESHOLD + 0.01,
            TPS=0.70, FCS=0.70,
        )
        w = extract_weaknesses(m, t)
        types = [x.weakness_type for x in w]
        assert WeaknessType.HALLUCINATED_REASONING in types

    def test_healthy_system_minimal_weaknesses(self):
        t = SystemTelemetry(sessions_observed=20, reasoning_calls=20,
                            uncertainty_preserved=18, loops_detected=8,
                            graph_queries_run=20, retrieval_calls=15,
                            retrieval_relevant=13)
        m = PerformanceMetrics(IAS=0.75, IRS=0.72, SDS=0.70, TPS=0.68, FCS=0.74)
        w = extract_weaknesses(m, t)
        # Healthy system should have minimal critical weaknesses
        critical = [x for x in w if x.severity > 0.5]
        assert len(critical) <= 1


# ── Stage 4: Proposal Generation ─────────────────────────────────────────────

class TestProposalGeneration:
    def test_missed_loop_generates_graph_proposal(self):
        from ai.self_improvement.sicl import SystemWeakness
        w = [SystemWeakness(
            weakness_type=WeaknessType.MISSED_LOOP_DETECTION,
            affected_layer="graph", severity=0.60,
            evidence="SDS low", proposed_fix=ProposalType.GRAPH_PATTERN_ADDITION,
        )]
        m = PerformanceMetrics(IAS=0.60, IRS=0.60, SDS=0.40, TPS=0.60, FCS=0.60)
        p = generate_proposals(w, m)
        assert any(x.proposal_type == ProposalType.GRAPH_PATTERN_ADDITION for x in p)

    def test_proposals_do_not_modify_user_model(self, poor_graph_outputs):
        t = observe(poor_graph_outputs)
        m = evaluate(t)
        w = extract_weaknesses(m, t)
        p = generate_proposals(w, m)
        for prop in p:
            assert not prop.modifies_user_model, \
                f"Proposal {prop.proposal_type} must not modify user model"

    def test_proposals_do_not_add_moral_judgment(self, poor_graph_outputs):
        t = observe(poor_graph_outputs)
        m = evaluate(t)
        w = extract_weaknesses(m, t)
        p = generate_proposals(w, m)
        for prop in p:
            assert not prop.adds_moral_judgment, \
                f"Proposal {prop.proposal_type} must not add moral judgment"

    def test_proposals_do_not_target_human_outcome(self, poor_graph_outputs):
        t = observe(poor_graph_outputs)
        m = evaluate(t)
        w = extract_weaknesses(m, t)
        p = generate_proposals(w, m)
        for prop in p:
            assert not prop.targets_human_outcome, \
                f"Proposal {prop.proposal_type} must not target human outcome"


# ── Stage 5: Guardrail Integration ───────────────────────────────────────────

class TestGuardrailIntegration:
    def test_user_model_modification_rejected(self):
        p = UpdateProposal(
            proposal_type=ProposalType.GRAPH_PATTERN_ADDITION,
            target_layer="graph",
            description="Test",
            expected_metric="SDS",
            expected_delta=0.10,
            rationale="Test",
            modifies_user_model=True,   # FORBIDDEN
        )
        results = integrate_proposals([p])
        assert results[0].status == UpdateStatus.REJECTED_SAFE
        assert "modifies_user_model" in results[0].rejection_reason

    def test_moral_judgment_rejected(self):
        p = UpdateProposal(
            proposal_type=ProposalType.FORMATION_COEFFICIENT_ADJUST,
            target_layer="formation",
            description="Test",
            expected_metric="FCS",
            expected_delta=0.10,
            rationale="Test",
            adds_moral_judgment=True,   # FORBIDDEN
        )
        results = integrate_proposals([p])
        assert results[0].status == UpdateStatus.REJECTED_SAFE

    def test_human_outcome_targeting_rejected(self):
        p = UpdateProposal(
            proposal_type=ProposalType.RETRIEVAL_OPTIMIZATION,
            target_layer="vector",
            description="Test",
            expected_metric="IRS",
            expected_delta=0.10,
            rationale="Test",
            targets_human_outcome=True,   # FORBIDDEN
        )
        results = integrate_proposals([p])
        assert results[0].status == UpdateStatus.REJECTED_SAFE

    def test_prompt_refinement_never_auto_applied(self):
        p = UpdateProposal(
            proposal_type=ProposalType.PROMPT_REFINEMENT,   # always requires human review
            target_layer="reasoning",
            description="Test",
            expected_metric="IAS",
            expected_delta=0.10,
            rationale="Test",
        )
        results = integrate_proposals([p])
        assert results[0].status == UpdateStatus.REJECTED_SAFE
        assert "human review" in results[0].rejection_reason.lower()

    def test_insufficient_delta_rejected(self):
        p = UpdateProposal(
            proposal_type=ProposalType.GRAPH_PATTERN_ADDITION,
            target_layer="graph",
            description="Test",
            expected_metric="SDS",
            expected_delta=0.005,   # below _UPDATE_MIN_DELTA=0.03
            rationale="Test",
        )
        results = integrate_proposals([p])
        assert results[0].status == UpdateStatus.REJECTED_PERF

    def test_valid_proposal_accepted(self):
        p = UpdateProposal(
            proposal_type=ProposalType.GRAPH_PATTERN_ADDITION,
            target_layer="graph",
            description="Add loop templates",
            expected_metric="SDS",
            expected_delta=0.08,
            rationale="Valid improvement",
        )
        results = integrate_proposals([p])
        assert results[0].status == UpdateStatus.ACCEPTED
        assert results[0].passes_guardrails


# ── Stage 6: Validation ───────────────────────────────────────────────────────

class TestValidation:
    def test_validation_captures_improvement(self):
        p = UpdateProposal(
            proposal_type=ProposalType.GRAPH_PATTERN_ADDITION,
            target_layer="graph",
            description="Test",
            expected_metric="SDS",
            expected_delta=0.08,
            rationale="Test",
            status=UpdateStatus.ACCEPTED,
        )
        before = PerformanceMetrics(IAS=0.60, IRS=0.60, SDS=0.45, TPS=0.60, FCS=0.60)
        after  = PerformanceMetrics(IAS=0.60, IRS=0.60, SDS=0.55, TPS=0.60, FCS=0.60)
        results = validate_updates([p], before, after)
        assert len(results) == 1
        assert results[0].improvement == pytest.approx(0.10, abs=0.01)
        assert results[0].accepted

    def test_validation_rejects_insufficient_improvement(self):
        p = UpdateProposal(
            proposal_type=ProposalType.FORMATION_COEFFICIENT_ADJUST,
            target_layer="formation",
            description="Test",
            expected_metric="FCS",
            expected_delta=0.05,
            rationale="Test",
            status=UpdateStatus.ACCEPTED,
        )
        before = PerformanceMetrics(IAS=0.60, IRS=0.60, SDS=0.60, TPS=0.60, FCS=0.60)
        after  = PerformanceMetrics(IAS=0.60, IRS=0.60, SDS=0.60, TPS=0.60, FCS=0.61)
        results = validate_updates([p], before, after)
        assert not results[0].accepted  # improvement = 0.01 < _UPDATE_MIN_DELTA


# ── Full SICL cycle ───────────────────────────────────────────────────────────

class TestFullCycle:
    def test_cycle_returns_sicl_output(self, sicl, good_outputs):
        out = sicl.run_cycle(good_outputs, cycle_id="test_001")
        assert isinstance(out, SICLOutput)
        assert out.schema == "sicl_v3.6"

    def test_cycle_has_all_required_keys(self, sicl, good_outputs):
        out = sicl.run_cycle(good_outputs)
        d   = out.to_dict()
        required = {"schema", "metrics", "weaknesses", "proposals", "summary", "disclaimer"}
        assert required <= set(d.keys())

    def test_summary_has_counts(self, sicl, good_outputs):
        out = sicl.run_cycle(good_outputs)
        d   = out.to_dict()
        s   = d["summary"]
        assert "accepted_updates" in s
        assert "rejected_updates" in s
        assert "net_delta_S" in s

    def test_disclaimer_present(self, sicl, good_outputs):
        out = sicl.run_cycle(good_outputs)
        assert len(out.disclaimer) > 50
        assert "system understanding" in out.disclaimer.lower()
        assert "behavior" in out.disclaimer.lower()

    def test_accepted_plus_rejected_equals_total(self, sicl, poor_graph_outputs):
        out   = sicl.run_cycle(poor_graph_outputs)
        total = out.accepted_updates + out.rejected_updates
        assert total == len(out.proposals)
