"""Unit tests for waiting_engine (deterministic path, no DB / no AI)."""
import waiting_engine as we


def test_seven_day_plan_is_fixed_and_complete():
    plan = we.default_7_day_plan()
    assert [d["day_index"] for d in plan] == [1, 2, 3, 4, 5, 6, 7]
    assert all(d["practice_title"] and d["reflection_prompt"] for d in plan)


def test_godot_vs_god_classification():
    godot = we.analyze({"waiting_for": "x", "anxiety_level": 9, "hope_level": 3,
                         "passivity_level": 9, "fantasy_level": 9, "trust_level": 1,
                         "obedience_readiness": 1, "action_clarity": 1}, use_ai=False)
    god = we.analyze({"waiting_for": "x", "anxiety_level": 2, "hope_level": 8,
                      "passivity_level": 1, "fantasy_level": 1, "trust_level": 9,
                      "obedience_readiness": 9, "action_clarity": 8}, use_ai=False)
    assert godot["waiting_type"] == "godot_waiting"
    assert god["waiting_type"] == "god_waiting"
    assert godot["godot_waiting_score"] > god["godot_waiting_score"]


def test_unknown_when_no_input():
    r = we.analyze({"waiting_for": "x"}, use_ai=False)
    assert r["waiting_type"] == "unknown"


def test_scores_in_unit_range():
    r = we.analyze({"waiting_for": "x", "anxiety_level": 6, "hope_level": 6,
                    "passivity_level": 5, "fantasy_level": 5, "trust_level": 5,
                    "obedience_readiness": 5, "action_clarity": 5}, use_ai=False)
    for k in ("godot_waiting_score", "god_waiting_score", "idolatry_risk",
              "passivity_risk", "hope_stability"):
        assert 0.0 <= r[k] <= 1.0
    assert len(r["guidance"]) <= 3 and len(r["reflection_questions"]) >= 1


def test_crisis_detection_prepends_help_note():
    r = we.analyze({"waiting_for": "我撑不下去了，想死", "anxiety_level": 9, "hope_level": 1,
                    "passivity_level": 8, "fantasy_level": 5, "trust_level": 1,
                    "action_clarity": 1}, use_ai=False)
    assert r["crisis_flag"] is True
    assert r["summary"].startswith("⚠️")


def test_ai_json_coercion_clamps_and_falls_back():
    fallback = we.deterministic_analysis({"waiting_for": "x"}, we.score(
        {"anxiety_level": 5, "hope_level": 5, "passivity_level": 5, "fantasy_level": 5,
         "trust_level": 5, "obedience_readiness": 5, "action_clarity": 5}))
    bad_ai = {"waiting_type": "garbage", "godot_waiting_score": 7, "guidance": ["a"]}
    out = we._coerce_ai_result(bad_ai, fallback)
    assert out["waiting_type"] in we.WAITING_TYPE_LABELS      # invalid -> fallback type
    assert 0.0 <= out["godot_waiting_score"] <= 1.0           # 7 clamped
