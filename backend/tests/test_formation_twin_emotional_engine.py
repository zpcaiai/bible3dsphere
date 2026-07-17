from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from formation_twin.emotion_inference import EmotionInferenceOutput, InferredCandidate, EvidenceSpan, infer_candidates
from formation_twin.emotion_ontology import EmotionLabel, normalize_emotion_label
from formation_twin.emotional_engine import build_snapshot, extract_user_reported, numeric_trend

pytestmark = pytest.mark.no_db


def test_open_ontology_preserves_custom_chinese_label():
    assert normalize_emotion_label("焦虑") == ("ANXIETY", None)
    assert normalize_emotion_label("委屈") == ("OTHER", "委屈")
    assert EmotionLabel.UNKNOWN.value == "UNKNOWN"


def test_user_report_extraction_does_not_infer_missing_values_or_confidence():
    occurred = datetime.now(timezone.utc)
    observations, energy, body = extract_user_reported({
        "event_id": "event-1", "occurred_at": occurred,
        "self_report": {"emotions": [{"emotion": "失望", "intensity": 7}], "stress_level": 8,
                        "body_states": [{"body_label": "胸口发紧", "intensity": 6}]},
    })
    assert observations == [{
        "emotion_label": "DISAPPOINTMENT", "custom_label": None, "intensity": 7,
        "source_kind": "USER_REPORT", "statement_type": "USER_REPORTED_FACT", "confidence": None,
        "occurred_at": occurred, "life_event_id": "event-1", "user_review_status": "NOT_REQUIRED",
        "processing_status": "ACTIVE",
    }]
    assert energy["stress_level"] == 8
    assert "energy_level" not in energy
    assert body[0]["body_label"] == "胸口发紧"
    assert body[0]["statement_type"] == "USER_REPORTED_FACT"


def test_duplicate_emotion_in_same_event_keeps_highest_explicit_intensity():
    observations, _, _ = extract_user_reported({
        "event_id": "event-1", "occurred_at": datetime.now(timezone.utc),
        "self_report": {"emotions": [{"emotion": "ANGER", "intensity": 3}, {"emotion": "ANGER", "intensity": 8}]},
    })
    assert len(observations) == 1
    assert observations[0]["intensity"] == 8


def test_distinct_custom_emotion_words_are_not_collapsed_into_other():
    observations, _, _ = extract_user_reported({
        "event_id": "event-1", "occurred_at": datetime.now(timezone.utc),
        "self_report": {"emotions": [{"emotion": "委屈"}, {"emotion": "疲惫"}]},
    })
    assert {(item["emotion_label"], item["custom_label"]) for item in observations} == {
        ("OTHER", "委屈"), ("OTHER", "疲惫"),
    }


def test_deterministic_trend_requires_distinct_days():
    now = datetime.now(timezone.utc)
    assert numeric_trend([(now, 3), (now + timedelta(hours=1), 9)])["direction"] == "INSUFFICIENT_DATA"
    result = numeric_trend([(now - timedelta(days=3), 3), (now - timedelta(days=2), 4), (now, 8)])
    assert result["direction"] == "INCREASING"
    assert result["data_points"] == 3


def test_snapshot_keeps_user_rules_and_model_candidates_separate():
    now = datetime.now(timezone.utc)
    snapshot = build_snapshot(
        observations=[{"emotion_label":"PEACE","source_kind":"USER_REPORT","statement_type":"USER_REPORTED_FACT","occurred_at":now,"processing_status":"ACTIVE"}],
        energy_points=[{"stress_level":8,"occurred_at":now,"source_kind":"USER_REPORT"}],
        start=now-timedelta(hours=24), end=now,
        model_candidates=[{"emotion_label":"SHAME","source_kind":"MODEL","statement_type":"MODEL_INFERENCE","user_review_status":"PENDING"}],
    )
    assert snapshot["user_reported"]["emotions"][0]["emotion_label"] == "PEACE"
    assert snapshot["rule_derived"]["statement_type"] == "RULE_DERIVED_METRIC"
    assert snapshot["possible_model_candidates"][0]["emotion_label"] == "SHAME"
    assert "score" not in str(snapshot).lower()


def test_inference_is_disabled_by_default_and_never_calls_provider(monkeypatch):
    monkeypatch.delenv("FORMATION_TWIN_MODEL_INFERENCE_ENABLED", raising=False)
    candidates, meta = infer_candidates("synthetic: 我今天非常愤怒。")
    assert candidates == []
    assert meta["status"] == "DISABLED"


def test_inference_schema_rejects_bad_offsets_and_confidence():
    with pytest.raises(Exception):
        EvidenceSpan(start_offset=5, end_offset=2)
    with pytest.raises(Exception):
        InferredCandidate(label="ANGER", confidence=1.2, evidence_spans=[])


def test_red_team_terms_are_not_part_of_emotion_labels():
    forbidden = {"DEPRESSION", "BIPOLAR", "ATTACHMENT_DISORDER", "SPIRITUAL_LEVEL", "SALVATION_STATUS"}
    assert forbidden.isdisjoint({item.value for item in EmotionLabel})


def test_localized_ontology_and_snapshot_schema_match_runtime_contract():
    root = Path(__file__).parents[1] / "formation_twin"
    zh = json.loads((root / "emotion_ontology.zh-CN.json").read_text())
    en = json.loads((root / "emotion_ontology.en.json").read_text())
    schema = json.loads((root / "emotional-state.schema.json").read_text())
    runtime = {item.value for item in EmotionLabel}
    assert set(zh["labels"]) == runtime == set(en["labels"])
    assert zh["mapping_status"] == "NON_EXCLUSIVE"
    assert {"user_reported", "rule_derived", "possible_model_candidates"}.issubset(schema["required"])
