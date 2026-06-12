"""Tests for the stateless Spiritual Formation engines and their endpoints.

These mirror the frontend recommendation and plan-generator behavior. They do
not touch the database, so they are marked ``no_db``.
"""
import pytest

from spiritual_formation_engine import (
    PATTERN_META,
    generate_transformation_plan,
    recommend_spiritual_response,
)

pytestmark = pytest.mark.no_db


# ── recommendation engine ─────────────────────────────────────────────────────
def test_recommend_emotion_maps_to_expected_patterns():
    result = recommend_spiritual_response(emotion="lust")
    assert "sexual_disorder" in result["likelySinPatterns"]
    assert result["likelySinPatterns"][0] == "sexual_disorder"
    assert result["suggestedGospelTruths"]
    assert "self_control" in result["suggestedFruits"]


def test_recommend_behavior_keywords_score_pattern():
    result = recommend_spiritual_response(behavior_text="I kept scrolling and watching video to escape")
    assert "entertainment_escapism" in result["likelySinPatterns"]


def test_recommend_money_keywords_detect_greed():
    result = recommend_spiritual_response(behavior_text="I obsess over money, shopping and my investment")
    assert "greed_consumerism" in result["likelySinPatterns"]


def test_recommend_selected_pattern_outranks_weak_signals():
    result = recommend_spiritual_response(selected_sin_pattern="pride", triggers=["loneliness"])
    assert result["likelySinPatterns"][0] == "pride"


def test_recommend_triggers_contribute_scores():
    result = recommend_spiritual_response(triggers=["sexual_temptation"])
    assert "sexual_disorder" in result["likelySinPatterns"]


def test_recommend_empty_input_defaults_gracefully():
    result = recommend_spiritual_response()
    assert result["likelySinPatterns"] == ["self_centeredness"]
    assert result["pastoralNote"]
    assert len(result["suggestedPractices"]) <= 4


def test_recommend_caps_collections():
    result = recommend_spiritual_response(
        emotion="anxiety", triggers=["pressure", "comparison"], behavior_text="money buy stock house"
    )
    assert len(result["possibleCoreLies"]) <= 5
    assert len(result["suggestedFruits"]) <= 5
    assert len(result["suggestedVirtues"]) <= 5
    assert len(result["likelySinPatterns"]) <= 3


# ── plan generator ────────────────────────────────────────────────────────────
def test_generate_plan_7_day_structure():
    plan = generate_transformation_plan(
        duration="7_days", intensity="normal", primary_sin_pattern="pride", start_date="2025-01-01"
    )
    assert plan["duration"] == "7_days"
    assert plan["endDate"] == "2025-01-08"
    assert plan["startDate"] == "2025-01-01"
    assert len(plan["reviewQuestions"]) == 5
    assert plan["dailyPractices"]
    assert plan["status"] == "active"
    assert "Pride" in plan["title"]


def test_generate_plan_light_intensity_trims_practices():
    plan = generate_transformation_plan(
        duration="30_days", intensity="light", primary_sin_pattern="idolatry"
    )
    assert len(plan["dailyPractices"]) <= 2
    assert len(plan["weeklyPractices"]) <= 2


def test_generate_plan_battle_adds_accountability():
    plan = generate_transformation_plan(
        duration="90_days", intensity="battle", primary_sin_pattern="sexual_disorder"
    )
    assert "accountability" in plan["progressSummary"].lower()
    assert "accountability" in plan["recommendedNextStep"].lower()
    # battle daily includes emergency practices
    assert len(plan["dailyPractices"]) > 4


def test_generate_plan_merges_secondary_pattern_targets():
    plan = generate_transformation_plan(
        duration="1_year",
        intensity="normal",
        primary_sin_pattern="pride",
        secondary_sin_pattern="greed_consumerism",
    )
    assert "generosity" in plan["targetVirtues"]
    assert plan["secondarySinPattern"] == "greed_consumerism"


def test_generate_plan_rejects_unknown_pattern():
    with pytest.raises(ValueError):
        generate_transformation_plan(duration="7_days", intensity="normal", primary_sin_pattern="nope")


def test_pattern_meta_has_all_thirteen():
    assert len(PATTERN_META) == 13


# ── endpoint contracts ────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    import main
    return TestClient(main.app)


def test_recommend_endpoint(client):
    res = client.post("/api/spiritual-formation/recommend", json={"emotion": "anger", "behaviorText": "I want revenge"})
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert "hatred_division" in body["recommendation"]["likelySinPatterns"]
    assert body["disclaimer"]


def test_generate_plan_endpoint(client):
    res = client.post(
        "/api/spiritual-formation/generate-plan",
        json={"duration": "30_days", "intensity": "normal", "primarySinPattern": "idolatry"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["plan"]["duration"] == "30_days"
    assert body["plan"]["primarySinPattern"] == "idolatry"


def test_generate_plan_endpoint_rejects_bad_duration(client):
    res = client.post(
        "/api/spiritual-formation/generate-plan",
        json={"duration": "bad", "intensity": "normal", "primarySinPattern": "idolatry"},
    )
    assert res.status_code == 422


def test_recommend_endpoint_rejects_bad_pattern(client):
    res = client.post(
        "/api/spiritual-formation/recommend",
        json={"selectedSinPattern": "not_a_pattern"},
    )
    assert res.status_code == 422
