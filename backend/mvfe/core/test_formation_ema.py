"""
Tests for Formation EMA cross-session tracking and Critic feedback loop.
"""
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from .formation import FormationEngine, FormationResult, EMA_ALPHA
from .reflection import ReflectionOutput


# ── helpers ───────────────────────────────────────────────────────────────────

@dataclass
class _Emotion:
    intensity: float = 0.6
    uncertainty: float = 0.2

@dataclass
class _Drivers:
    fear: float = 0.5
    ego: float = 0.3
    love: float = 0.2

@dataclass
class _Attention:
    fixation_score: float = 0.4

@dataclass
class _Decision:
    type: str = "avoidance"
    drivers: _Drivers = None
    def __post_init__(self):
        if self.drivers is None:
            self.drivers = _Drivers()


# ── Formation EMA tests ────────────────────────────────────────────────────────

def test_first_session_seeds_ema():
    engine = FormationEngine()
    result = engine.compute("u1", _Emotion(), _Attention(), _Decision(),
                            previous_ema=0.0, previous_session_count=0)
    assert result.formation_score_ema == result.formation_score, (
        "First session: EMA should equal instantaneous score (seed)"
    )
    assert result.session_count == 1


def test_ema_smooths_across_sessions():
    engine = FormationEngine()
    # Session 1
    r1 = engine.compute("u2", _Emotion(intensity=0.8), _Attention(), _Decision(),
                        previous_ema=0.0, previous_session_count=0)
    ema1 = r1.formation_score_ema

    # Session 2 with lower intensity — EMA should lag behind
    r2 = engine.compute("u2", _Emotion(intensity=0.2), _Attention(fixation_score=0.1),
                        _Decision(type="approach"),
                        previous_ema=ema1, previous_session_count=1)
    assert r2.formation_score < r2.formation_score_ema, (
        "EMA should be above instantaneous score when score dropped sharply"
    )
    assert r2.session_count == 2
    expected_ema = EMA_ALPHA * r2.formation_score + (1 - EMA_ALPHA) * ema1
    assert abs(r2.formation_score_ema - round(expected_ema, 4)) < 1e-4


def test_ema_in_process_cache_overrides_db_seed():
    """Within a server process the in-process cache should win over the DB seed."""
    engine = FormationEngine()
    r1 = engine.compute("u3", _Emotion(intensity=0.5), _Attention(), _Decision(),
                        previous_ema=0.0, previous_session_count=0)
    # Simulate a second call in same process but passing stale DB values
    r2 = engine.compute("u3", _Emotion(intensity=0.5), _Attention(), _Decision(),
                        previous_ema=0.0, previous_session_count=0)  # stale DB values
    # In-process cache should still have advanced EMA
    assert r2.session_count == 2, "In-process cache should increment session count"


def test_drift_uses_ema_not_raw_previous():
    engine = FormationEngine()
    # Seed with high EMA
    r1 = engine.compute("u4", _Emotion(intensity=0.9), _Attention(fixation_score=0.8),
                        _Decision(), previous_ema=0.0, previous_session_count=0)
    # Large drop — drift measured against EMA, not raw score
    r2 = engine.compute("u4", _Emotion(intensity=0.1), _Attention(fixation_score=0.1),
                        _Decision(type="approach"),
                        previous_ema=r1.formation_score_ema, previous_session_count=1)
    expected_drift = abs(r2.formation_score - r1.formation_score_ema)
    assert abs(r2.drift_score - round(min(1.0, max(0.0, expected_drift)), 4)) < 1e-4


# ── Critic confidence wired into ReflectionOutput ─────────────────────────────

def test_reflection_output_has_confidence_field():
    ro = ReflectionOutput(
        state_interpretation="test",
        loop_detection="none",
        risk_assessment="low",
        reflective_question="?",
        bible_verse_hint="约翰福音 3:16",
        disclaimer="disclaimer",
    )
    assert hasattr(ro, "confidence"), "ReflectionOutput must have confidence field"
    assert ro.confidence == 1.0, "Default confidence should be 1.0"


def test_reflection_confidence_can_be_set():
    ro = ReflectionOutput(
        state_interpretation="s", loop_detection="l", risk_assessment="r",
        reflective_question="q", bible_verse_hint="v", disclaimer="d",
        confidence=0.65,
    )
    assert ro.confidence == 0.65


def test_formation_result_has_ema_fields():
    r = FormationResult(
        formation_score=0.5, drift_score=0.1, stability_score=0.9,
        emotion_contribution=0.2, attention_contribution=0.15,
        decision_contribution=0.15,
    )
    assert hasattr(r, "formation_score_ema")
    assert hasattr(r, "session_count")
    assert r.formation_score_ema == 0.0
    assert r.session_count == 0
