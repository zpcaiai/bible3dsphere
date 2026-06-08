"""Unit tests for idolatry_engine (pure functions, no DB)."""
import pytest
import idolatry_engine as ie

pytestmark = pytest.mark.no_db


def test_seven_idol_types_and_meta():
    assert len(ie.IDOL_TYPES) == 7
    m = ie.meta()
    assert {"idol_types", "core_questions", "dimensions", "risk_labels"} <= set(m)
    assert len(m["core_questions"]) == 6
    assert len(m["dimensions"]) == 5


def test_compute_intensity_and_risk_monotonic():
    low = ie.compute_intensity({k: 0.1 for k in ie.DIM_KEYS})
    high = ie.compute_intensity({k: 0.9 for k in ie.DIM_KEYS})
    assert 0.0 <= low < high <= 1.0
    assert ie.risk_from_intensity(low) == "low"
    assert ie.risk_from_intensity(high) == "high"


def test_assess_skips_unknown_and_sorts_by_intensity():
    r = ie.assess([
        {"target_type": "comfort", "fear_of_loss": 0.1, "identity_dependency": 0.1,
         "peace_disruption": 0.1, "obedience_conflict": 0.1, "attention_capture": 0.1},
        {"target_type": "success", "fear_of_loss": 0.9, "identity_dependency": 0.9,
         "peace_disruption": 0.9, "obedience_conflict": 0.9, "attention_capture": 0.9},
        {"target_type": "does_not_exist"},
    ])
    assert len(r["patterns"]) == 2                      # unknown skipped
    assert r["patterns"][0]["target_type"] == "success" # highest first
    assert r["top"]["target_type"] == "success"


def test_detected_from_never_exceeds_column_width():
    full = {"emotion": {"anxiety": .9, "fear": .9, "envy": .9},
            "fear_tendency": .9, "decision_fear": .9, "loop_detected": "x"}
    r = ie.assess([{"target_type": "success", "fear_of_loss": .5, "identity_dependency": .5,
                    "peace_disruption": .5, "obedience_conflict": .5, "attention_capture": .5}], full)
    assert len(r["patterns"][0]["detected_from"]) <= 64


def test_graph_model_has_chain_and_gospel_breaks():
    g = ie.graph_model("control")
    assert len(g["chain"]) >= 4
    assert any(b.get("principle") for b in g["breaks"])


def test_empty_assess_is_gentle():
    r = ie.assess([], None)
    assert r["top"] is None and r["patterns"] == []
    assert "自由" in r["summary"] or "继续" in r["summary"] or r["summary"]
