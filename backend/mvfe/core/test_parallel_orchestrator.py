"""
Tests for parallel extraction in Orchestrator (Task #6).
Verifies that emotion/attention/decision steps run concurrently and
that results are identical to sequential execution.
"""
import time
import unittest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import Optional


# ── Minimal stubs ────────────────────────────────────────────────────────────

@dataclass
class FakeEmotionState:
    primary_emotion: str = "peace"
    intensity: float = 0.7
    uncertainty: float = 0.1
    secondary_emotions: list = None
    def __post_init__(self):
        if self.secondary_emotions is None:
            self.secondary_emotions = []

@dataclass
class FakeAttentionState:
    focus: str = "present"
    breadth: float = 0.5
    depth: float = 0.6

@dataclass
class FakeDecisionState:
    type: str = "approach"
    drivers: dict = None
    def __post_init__(self):
        if self.drivers is None:
            self.drivers = {"fear": 0.1}

@dataclass
class FakeFormationResult:
    formation_score: float = 0.5
    formation_score_ema: float = 0.5
    session_count: int = 1
    drift_score: float = 0.1
    stability_score: float = 0.8

@dataclass
class FakeReflectionOutput:
    state_interpretation: str = "You are at peace."
    confidence: float = 1.0

@dataclass
class FakeCriticReport:
    overall_risk: str = "low"
    adjusted_confidence: float = 0.9

@dataclass
class FakeGovernanceReport:
    passed: bool = True
    violations: list = None
    warnings: list = None
    formation_danger_flag: bool = False
    categories: list = None
    risk_level: str = "none"
    def __post_init__(self):
        if self.violations is None: self.violations = []
        if self.warnings is None: self.warnings = []
        if self.categories is None: self.categories = []


def _make_slow_extractor(delay: float, state):
    """Returns a mock extractor whose .extract() sleeps `delay` seconds."""
    ext = MagicMock()
    def slow_extract(text):
        time.sleep(delay)
        return state
    ext.extract.side_effect = slow_extract
    ext.to_dict.return_value = {}
    return ext


def _build_orchestrator(emo_delay=0.1, att_delay=0.1, dec_delay=0.1):
    """Build a minimal Orchestrator with slow fake extractors."""
    from backend.mvfe.core.orchestrator import Orchestrator

    emo = _make_slow_extractor(emo_delay, FakeEmotionState())
    att = _make_slow_extractor(att_delay, FakeAttentionState())
    dec = _make_slow_extractor(dec_delay, FakeDecisionState())

    context = MagicMock()
    context.extract.return_value = MagicMock()
    context.to_dict.return_value = {}

    memory = None

    formation = MagicMock()
    formation.compute.return_value = FakeFormationResult()
    formation.to_dict.return_value = {
        "formation_score": 0.5, "drift_score": 0.1,
        "stability_score": 0.8, "formation_score_ema": 0.5, "session_count": 1
    }

    reflection = MagicMock()
    rout = FakeReflectionOutput()
    reflection.generate.return_value = rout
    reflection.to_dict.return_value = {}

    critic = MagicMock()
    critic.challenge.return_value = FakeCriticReport()
    critic.to_dict.return_value = {}
    critic.adjust_confidence.return_value = 0.9

    governance = MagicMock()
    gov = FakeGovernanceReport()
    governance.audit.return_value = gov
    governance.sanitize.return_value = "ok"

    graph = MagicMock()
    graph.update.return_value = None
    graph.update_rich.return_value = None
    graph.get_formation_insight.return_value = {"loop_detected": False}

    return Orchestrator(
        context_extractor=context,
        emotion_extractor=emo,
        attention_extractor=att,
        decision_classifier=dec,
        memory_store=memory,
        formation_engine=formation,
        critic_agent=critic,
        reflection_generator=reflection,
        governance_layer=governance,
        graph_module=graph,
        db_pool=None,
    )


class TestParallelExtraction(unittest.TestCase):

    def test_results_correct(self):
        """Orchestrator returns a ProcessResult with all expected keys."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

        with patch('backend.mvfe.core.orchestrator.tag_extractor'), \
             patch('backend.mvfe.core.orchestrator.get_tag_store', return_value=None):
            orch = _build_orchestrator()
            result = orch.process("user-1", "I feel peaceful today")

        self.assertEqual(result.input_text, "I feel peaceful today")
        self.assertIn("primary_emotion", str(result.emotion) or str(orch._emotion.to_dict.call_count >= 1))
        self.assertIsNotNone(result.event_id)
        self.assertIsNotNone(result.timestamp)

    def test_parallel_faster_than_sequential(self):
        """
        Three extractors each sleep 0.15s.
        Sequential would take ~0.45s; parallel should finish in ~0.15s (+overhead).
        We assert wall-time < 0.40s as a generous bound.
        """
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

        with patch('backend.mvfe.core.orchestrator.tag_extractor'), \
             patch('backend.mvfe.core.orchestrator.get_tag_store', return_value=None):
            orch = _build_orchestrator(emo_delay=0.15, att_delay=0.15, dec_delay=0.15)
            t0 = time.perf_counter()
            orch.process("user-2", "Testing parallelism")
            elapsed = time.perf_counter() - t0

        print(f"\n  [parallel test] wall-time: {elapsed*1000:.0f}ms (expect < 400ms)")
        # Sequential would be ≥ 0.45s; parallel should be ~0.15-0.25s
        self.assertLess(elapsed, 0.40,
            f"Parallel extraction took {elapsed:.3f}s — expected < 0.40s (sequential would be ~0.45s)")

    def test_each_extractor_called_once(self):
        """Each extractor's .extract() is called exactly once per process()."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

        with patch('backend.mvfe.core.orchestrator.tag_extractor'), \
             patch('backend.mvfe.core.orchestrator.get_tag_store', return_value=None):
            orch = _build_orchestrator()
            orch.process("user-3", "Hello world")

        self.assertEqual(orch._emotion.extract.call_count, 1)
        self.assertEqual(orch._attention.extract.call_count, 1)
        self.assertEqual(orch._decision.extract.call_count, 1)

    def test_extractor_exception_propagates(self):
        """If any extractor raises, process() re-raises immediately."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

        with patch('backend.mvfe.core.orchestrator.tag_extractor'), \
             patch('backend.mvfe.core.orchestrator.get_tag_store', return_value=None):
            orch = _build_orchestrator()
            orch._emotion.extract.side_effect = RuntimeError("LLM timeout")

            with self.assertRaises(RuntimeError):
                orch.process("user-4", "This should fail")


if __name__ == "__main__":
    # Run with: python3 backend/mvfe/core/test_parallel_orchestrator.py
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestParallelExtraction)
    result = runner.run(suite)
    import sys; sys.exit(0 if result.wasSuccessful() else 1)
