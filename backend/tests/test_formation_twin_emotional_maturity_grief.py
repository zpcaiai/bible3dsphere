from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from formation_twin.emotional_maturity import UnsafeContentError
from formation_twin.emotional_maturity_grief import (
    BYPASSING_CODES,
    GI_RANK,
    GRIEF_INTEGRATION_LEVELS,
    REST_MEASURES,
    WORKFLOW_NODES,
    accompany_grief,
    build_rest_rhythm,
    calibrate_control,
    describe_grief_engine,
    design_ritual,
    discern_spiritual_bypassing,
    evaluate_integration,
    map_loss,
    process_ambiguous_loss,
)


pytestmark = pytest.mark.no_db
NOW = datetime(2026, 7, 28, 12, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[2]


# ── EM-54 loss mapping ───────────────────────────────────────────────────────

def test_naming_the_loss_and_its_secondary_losses_raises_the_level():
    named_only = map_loss(loss_type="DEATH", what_was_lost="父亲", now=NOW)
    assert named_only["integration_level"] == "GI1"
    with_secondary = map_loss(
        loss_type="DEATH", what_was_lost="父亲",
        secondary_losses=["DAILY_ROUTINE", "ROLE"], now=NOW,
    )
    assert with_secondary["integration_level"] == "GI2"


def test_no_timeline_is_imposed_on_grief():
    result = map_loss(loss_type="RELATIONSHIP_END", what_was_lost="十年的婚姻", now=NOW)
    assert "没有标准时长" in result["no_timeline_expected"]


def test_ambiguous_loss_routes_to_its_own_processor():
    result = map_loss(loss_type="UNCERTAIN_OUTCOME" if False else "OTHER",
                      what_was_lost="失联的家人", is_ambiguous=True, now=NOW)
    assert result["next_action"] == "AMBIGUOUS_LOSS_PROCESSOR"


def test_days_since_is_computed_when_the_date_is_known():
    result = map_loss(
        loss_type="HEALTH", what_was_lost="以前的体力",
        occurred_at=NOW - timedelta(days=45), now=NOW,
    )
    assert result["days_since"] == 45


def test_unknown_loss_or_secondary_domain_is_rejected():
    with pytest.raises(ValueError):
        map_loss(loss_type="NOT_A_TYPE", what_was_lost="x", now=NOW)
    with pytest.raises(ValueError):
        map_loss(loss_type="DEATH", what_was_lost="x", secondary_losses=["SOMETHING"], now=NOW)


# ── EM-55 grief companion ────────────────────────────────────────────────────

def test_all_grief_emotions_are_allowed_including_relief_and_anger():
    result = accompany_grief(named_emotions=["愤怒", "解脱"])
    assert result["all_emotions_allowed"] is True
    assert "愤怒" in result["common_grief_emotions"]
    assert "解脱" in result["common_grief_emotions"]


def test_grief_is_never_treated_as_spiritual_failure():
    result = accompany_grief(named_emotions=["迷惘"])
    assert any("缺乏信心" in note for note in result["never_says"])
    assert any("意义" in note for note in result["never_says"])


def test_lament_is_optional_and_may_end_unresolved():
    with_lament = accompany_grief(named_emotions=["悲痛"], wants_lament=True)
    assert [item["code"] for item in with_lament["lament_structure"]][-1] == "TRUST_OR_UNRESOLVED"
    assert with_lament["lament_may_end_unresolved"] is True
    assert accompany_grief(named_emotions=["悲痛"])["lament_structure"] == []


def test_neutral_framework_gets_no_lament_structure():
    result = accompany_grief(named_emotions=["悲痛"], wants_lament=True, spiritual_framework="neutral")
    assert result["lament_structure"] == []


# ── EM-56 control calibration ────────────────────────────────────────────────

def test_five_buckets_separate_responsibility_from_uncontrollable():
    result = calibrate_control(buckets={
        "MY_RESPONSIBILITY": ["按时吃药"],
        "MY_INFLUENCE": ["和医生沟通"],
        "NOT_CONTROLLABLE": ["最终的治疗结果"],
    })
    codes = [item["code"] for item in result["buckets"]]
    assert codes == ["MY_RESPONSIBILITY", "MY_CHOICE", "MY_INFLUENCE", "SHARED", "NOT_CONTROLLABLE"]
    assert result["integration_level"] == "GI3"


def test_passive_surrender_disguised_as_faith_is_blocked():
    with pytest.raises(UnsafeContentError):
        calibrate_control(buckets={}, surrender_statement="一切交给神就不用去治疗了")


def test_outstanding_responsibilities_are_flagged():
    result = calibrate_control(
        buckets={"MY_RESPONSIBILITY": ["预约复诊"]},
        still_owed_actions=["预约复诊", "回复律师的邮件"],
    )
    assert result["outstanding_responsibilities"]
    assert "交托不应该被用来跳过它们" in result["warning"]


def test_acceptance_is_explicitly_not_approval():
    result = calibrate_control(buckets={})
    assert "仍然认为它是错的" in result["acceptance_is_not_approval"]


# ── EM-57 ambiguous loss ─────────────────────────────────────────────────────

def test_closure_is_never_manufactured():
    result = process_ambiguous_loss(
        kind="NO_ANSWER_EVER", what_is_unresolved="我永远不会知道他为什么离开",
    )
    assert "没有「结案」" in result["closure_not_required"]
    assert "不要求你原谅" in result["not_required"]


def test_symbolic_goodbye_is_offered_only_when_requested():
    without = process_ambiguous_loss(kind="NO_FORMAL_GOODBYE", what_is_unresolved="没能见最后一面")
    assert not any("象征性的告别" in option for option in without["options"])
    with_goodbye = process_ambiguous_loss(
        kind="NO_FORMAL_GOODBYE", what_is_unresolved="没能见最后一面", wants_symbolic_goodbye=True,
    )
    assert "象征性的告别" in with_goodbye["options"][0]


def test_anniversary_rebound_is_normalised():
    result = process_ambiguous_loss(kind="UNRESOLVED_ESTRANGEMENT", what_is_unresolved="断联三年")
    assert "不代表退步" in result["anniversary_note"]


def test_contact_option_appears_only_when_contact_is_safe():
    unsafe = process_ambiguous_loss(kind="UNRESOLVED_ESTRANGEMENT", what_is_unresolved="x")
    assert not any("联系尝试" in option for option in unsafe["options"])
    safe = process_ambiguous_loss(
        kind="UNRESOLVED_ESTRANGEMENT", what_is_unresolved="x", contact_is_safe=True,
    )
    assert any("联系尝试" in option for option in safe["options"])


# ── EM-58 spiritual bypassing ────────────────────────────────────────────────

def test_premature_meaning_and_emotion_suppression_are_flagged():
    result = discern_spiritual_bypassing("这件事一定有神的美意，基督徒不该难过。")
    codes = {item["code"] for item in result["flags"]}
    assert {"PREMATURE_MEANING", "EMOTION_SUPPRESSION"} <= codes


def test_responsibility_avoidance_and_forced_forgiveness_are_flagged():
    result = discern_spiritual_bypassing("交给神就不用沟通了，你必须立刻原谅他。")
    codes = {item["code"] for item in result["flags"]}
    assert {"RESPONSIBILITY_AVOIDANCE", "FORCED_FORGIVENESS"} <= codes


def test_divine_certainty_claims_are_flagged():
    result = discern_spiritual_bypassing("神就是为了让你学功课才允许这件事。")
    assert any(item["code"] == "DIVINE_CERTAINTY_CLAIM" for item in result["flags"])


def test_each_flag_comes_with_an_honest_reframe():
    result = discern_spiritual_bypassing("只要祷告就够了，不用看医生。")
    assert result["reframes"]
    assert "不替代医疗" in " ".join(item["reframe"] for item in result["reframes"])


def test_faith_practices_are_not_banned():
    result = discern_spiritual_bypassing("我想安静祷告")
    assert result["flags"] == []
    assert "诗篇默想（包括哀歌类诗篇）" in result["healthy_spiritual_options"]
    assert "不是禁止属灵操练" in result["faith_is_not_banned"]


def test_neutral_framework_gets_no_spiritual_options():
    result = discern_spiritual_bypassing("我很难过", spiritual_framework="neutral")
    assert result["healthy_spiritual_options"] == []


def test_all_documented_bypassing_codes_exist():
    assert len(BYPASSING_CODES) == 7


# ── EM-59 rituals ────────────────────────────────────────────────────────────

def test_rituals_are_optional_user_authored_and_not_magic():
    result = design_ritual(kind="RELEASE", what_it_marks="放下我无法决定的治疗结果")
    assert result["optional"] is True
    assert result["user_authored"] is True
    assert any("不产生超自然效力" in note for note in result["not_magic"])
    assert any("哀伤结束" in note for note in result["not_magic"])


def test_transactional_or_magical_ritual_language_is_blocked():
    with pytest.raises(UnsafeContentError):
        design_ritual(kind="RELEASE", what_it_marks="做完这个仪式神就一定会让他回来")
    with pytest.raises(UnsafeContentError):
        design_ritual(kind="MEMORIAL", what_it_marks="纪念父亲", elements=["献上这个换取平安"])


def test_each_ritual_kind_has_default_elements():
    for kind in ("RELEASE", "MEMORIAL", "FAREWELL", "GRATITUDE", "BOUNDARY_MARKER"):
        assert design_ritual(kind=kind, what_it_marks="x")["elements"]


# ── EM-60 rest rhythm ────────────────────────────────────────────────────────

def test_rest_is_measured_on_six_axes():
    result = build_rest_rhythm(available_slots=["MORNING_PAUSE", "WEEKLY_SABBATH"])
    assert len(result["rest_measures"]) == 6
    assert {item["code"] for item in result["rest_measures"]} == {code for code, _ in REST_MEASURES}


def test_stopping_work_alone_is_not_counted_as_recovery():
    result = build_rest_rhythm(
        available_slots=["WEEKLY_SABBATH"],
        current_measures={"BEHAVIOR_STOPPED": True},
    )
    assert result["stopping_is_not_recovery"] is True
    assert "注意力和情绪还没有真正休息" in result["stopping_note"]


def test_high_rest_guilt_is_marked_as_a_concern():
    result = build_rest_rhythm(
        available_slots=["MORNING_PAUSE"],
        current_measures={"BEHAVIOR_STOPPED": True, "REST_GUILT": 8, "BODY_RECOVERED": True},
    )
    guilt = next(item for item in result["rest_measures"] if item["code"] == "REST_GUILT")
    assert guilt["status"] == "CONCERN"


def test_rest_is_explicitly_not_irresponsibility():
    result = build_rest_rhythm(available_slots=["WEEKLY_SABBATH"])
    assert "更自由地承担该承担的" in result["rest_is_not_irresponsibility"]


def test_unknown_rhythm_slot_is_rejected():
    with pytest.raises(ValueError):
        build_rest_rhythm(available_slots=["ALL_DAY_NOTHING"])


# ── EM-61 integration evaluation ─────────────────────────────────────────────

def test_integration_is_not_grief_completion():
    result = evaluate_integration(day=30, loss_named=True)
    assert "不是「哀伤完成度」" in result["is_not_grief_completion"]
    assert result["grief_may_fluctuate"] is True


def test_levels_require_the_documented_evidence():
    result = evaluate_integration(
        day=30, loss_named=True, secondary_losses_named=2, responsibility_separated=True,
        grief_expressed_events=1, real_actions_taken=1, rest_slots_kept=2,
    )
    assert result["integration_level"] == "GI5"
    assert GI_RANK[result["integration_level"]] == 5


def test_gi6_requires_day_ninety_and_comparable_events():
    args = dict(
        loss_named=True, secondary_losses_named=2, responsibility_separated=True,
        grief_expressed_events=2, real_actions_taken=1, rest_slots_kept=3, comparable_event_count=2,
    )
    assert evaluate_integration(day=30, **args)["integration_level"] == "GI5"
    assert evaluate_integration(day=90, **args)["integration_level"] == "GI6"


def test_busyness_replacing_grief_is_flagged():
    result = evaluate_integration(
        day=30, loss_named=True, secondary_losses_named=1, responsibility_separated=True,
        grief_expressed_events=0, real_actions_taken=3,
    )
    assert any("忙碌代替哀伤" in concern for concern in result["concerns"])


def test_anniversary_reaction_is_not_counted_as_regression():
    result = evaluate_integration(day=90, loss_named=True, anniversary_reaction=True)
    assert "不计为退步" in result["anniversary_note"]


def test_evaluation_states_its_attribution_limits():
    result = evaluate_integration(day=14, loss_named=True)
    assert any("不能证明是操练造成的" in note for note in result["attribution_limits"])


def test_unknown_checkpoint_day_is_rejected():
    with pytest.raises(ValueError):
        evaluate_integration(day=60, loss_named=True)


# ── module description and wiring ────────────────────────────────────────────

def test_module_description_lists_the_eight_distinctions():
    described = describe_grief_engine()
    assert len(described["skills"]) == len(WORKFLOW_NODES) == 8
    assert len(described["eight_distinctions"]) == 8
    assert set(described["integration_levels"]) == set(GRIEF_INTEGRATION_LEVELS)
    refusals = " ".join(described["does_not"])
    assert "不代神宣告这件事的理由" in refusals
    assert "不把停止工作直接当作已经恢复" in refusals


def test_router_exposes_the_batch_seven_surface():
    from routers.formation_twin_emotional_maturity import router

    paths = {route.path for route in router.routes}
    for suffix in (
        "grief/overview", "grief/loss-map", "grief/companion", "grief/control-calibration",
        "grief/ambiguous-loss", "grief/bypassing-check", "grief/ritual",
        "grief/rest-rhythm", "grief/integration",
    ):
        assert f"/api/v1/formation-twin/emotional-maturity/{suffix}" in paths


def test_migration_file_exists_for_batch_seven():
    migration = ROOT / "backend/migrations/0229_formation_twin_emd_grief_rest.sql"
    rollback = ROOT / "backend/migrations/rollback/0229_formation_twin_emd_grief_rest_down.sql"
    assert migration.exists() and rollback.exists()
    sql = migration.read_text(encoding="utf-8")
    assert "formation_twin_emd_losses" in sql
    assert "formation_twin_emd_rest_rhythms" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql


def test_erasure_covers_every_batch_seven_table():
    source = (ROOT / "backend/routers/formation_twin_emotional_maturity.py").read_text(encoding="utf-8")
    erase_block = source.split("def emotional_maturity_erase")[1]
    for table in (
        "formation_twin_emd_losses", "formation_twin_emd_grief_sessions",
        "formation_twin_emd_control_calibrations", "formation_twin_emd_bypassing_checks",
        "formation_twin_emd_rituals", "formation_twin_emd_rest_rhythms",
        "formation_twin_emd_grief_integrations",
    ):
        assert table in erase_block
