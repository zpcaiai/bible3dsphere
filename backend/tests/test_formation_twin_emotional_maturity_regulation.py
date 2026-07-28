from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from formation_twin.emotional_maturity import UnsafeContentError
from formation_twin.emotional_maturity_regulation import (
    ACTIVATION_BANDS,
    EMOTION_LEXICON,
    MEDICAL_RED_FLAGS,
    WORKFLOW_NODES,
    LabelingInput,
    SupportPerson,
    activation_band,
    build_pause_protocol,
    build_rehearsal,
    build_trigger_profile,
    confirm_emotions,
    describe_regulation_engine,
    interrupt_impulse,
    label_emotions,
    plan_recovery,
    route_coregulation,
    scan_body_signals,
)


pytestmark = pytest.mark.no_db
NOW = datetime(2026, 7, 28, 12, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[2]


def contact(**updates) -> SupportPerson:
    values = {
        "support_person_id": "sp_001",
        "relationship_role": "trusted_friend",
        "allowed_support_types": ["LISTEN", "DELAY_SUPPORT"],
        "available_now": True,
        "person_has_consented": True,
        "user_has_consented": True,
    }
    values.update(updates)
    return SupportPerson(**values)


# ── activation banding ───────────────────────────────────────────────────────

def test_bands_follow_the_documented_default_ranges():
    assert activation_band(2)["band"] == "GREEN"
    assert activation_band(5)["band"] == "AMBER"
    assert activation_band(8)["band"] == "RED"
    assert set(ACTIVATION_BANDS) == {"GREEN", "AMBER", "RED", "CRISIS", "UNKNOWN"}


def test_a_number_alone_never_decides_the_route():
    calm_number_unsafe_place = activation_band(3, environment_safe=False)
    assert calm_number_unsafe_place["band"] == "RED"
    pending = activation_band(4, irreversible_action_pending=True)
    assert pending["band"] == "RED"


def test_safety_signals_force_the_crisis_route():
    result = activation_band(5, signals=["SELF_HARM_URGE"])
    assert result["band"] == "CRISIS"
    assert result["route"] == "CRISIS_AND_SAFETY_SYSTEM"


def test_no_deep_dive_while_highly_activated():
    assert activation_band(9, signals=["VIOLENCE_PRESENT"])["deep_dive_allowed"] is False
    assert activation_band(8)["deep_dive_allowed"] is False
    assert activation_band(3)["deep_dive_allowed"] is True


# ── EM-28 emotion labelling ──────────────────────────────────────────────────

def test_labeling_separates_fact_interpretation_emotion_and_urge():
    result = label_emotions(LabelingInput(
        mode="REAL_TIME",
        raw_utterance="他当着所有人的面否定我，我觉得他就是故意羞辱我，我现在气炸了，想马上在群里骂回去。",
        known_facts=["对方在会议中否定了用户的方案"],
        user_activation_level=8,
    ))
    assert result["objective_facts"] == ["对方在会议中否定了用户的方案"]
    assert result["user_interpretations"]
    assert any(item["emotion_code"] == "ANGER" for item in result["emotion_candidates"])
    assert any(item["urge_code"] == "SEND_HOSTILE_MESSAGE" for item in result["action_urges"])


def test_candidate_emotions_are_never_written_as_facts():
    result = label_emotions(LabelingInput(raw_utterance="我很气", user_activation_level=6))
    assert result["confirmed_emotions"] == []
    assert all(item["status"] == "CANDIDATE_AWAITING_USER_CONFIRMATION" for item in result["emotion_candidates"])


def test_anger_is_not_automatically_reduced_to_a_secondary_emotion():
    result = label_emotions(LabelingInput(raw_utterance="我很气，他越界了。", user_activation_level=6))
    codes = [item["emotion_code"] for item in result["emotion_candidates"]]
    assert "ANGER" in codes
    assert any("合理反应" in note for note in result["principles"])


def test_at_most_three_candidates_are_offered():
    result = label_emotions(LabelingInput(
        raw_utterance="我又气又害怕又羞又孤单又失望又内疚。", user_activation_level=5,
    ))
    assert len(result["emotion_candidates"]) <= 3


def test_real_time_mode_uses_the_short_path():
    result = label_emotions(LabelingInput(mode="REAL_TIME", raw_utterance="我现在气炸了", user_activation_level=8))
    assert result["path"] == "SHORT_PATH"
    assert result["deep_dive_offered"] is False


def test_training_mode_offers_confusion_pairs():
    result = label_emotions(LabelingInput(mode="REHEARSAL", raw_utterance="", user_activation_level=1))
    assert any(pair["a"] == "GUILT" and pair["b"] == "SHAME" for pair in result["training_pairs"])


def test_only_the_user_confirms_an_emotion():
    labeled = label_emotions(LabelingInput(raw_utterance="我很气也很受伤", user_activation_level=5))
    confirmed = confirm_emotions(labeled, ["ANGER"], user_words=["说不上来的闷"])
    assert [item["emotion_code"] for item in confirmed["confirmed_emotions"]][0] == "ANGER"
    assert confirmed["confirmed_emotions"][-1]["localized_label"] == "说不上来的闷"
    assert all(item["emotion_code"] != "ANGER" for item in confirmed["emotion_candidates"])


def test_unknown_emotion_codes_are_rejected():
    labeled = label_emotions(LabelingInput(raw_utterance="我很气", user_activation_level=5))
    with pytest.raises(ValueError):
        confirm_emotions(labeled, ["NOT_A_CODE"])


def test_labeling_refuses_spiritually_coercive_input_text():
    with pytest.raises(UnsafeContentError):
        label_emotions(LabelingInput(raw_utterance="神正在告诉你回到这段关系", user_activation_level=3))


# ── EM-29 body signals ───────────────────────────────────────────────────────

def test_early_body_signals_are_recorded_without_diagnosis():
    result = scan_body_signals(["JAW_CLENCH", "SHALLOW_BREATH"], activation_level=6)
    assert result["status"] == "RECORDED"
    assert result["earliest_signal"] == "JAW_CLENCH"
    assert "不是心理或医学诊断" in result["note"]


def test_medical_red_flags_exit_emotion_training():
    result = scan_body_signals(["CHEST_PAIN"])
    assert result["status"] == "EXIT_TO_MEDICAL_SAFETY"
    assert result["emotion_training_paused"] is True
    assert "原因未知" in result["recorded_statement"]
    assert any("不得把这些身体信号解释为焦虑" in rule for rule in result["forbidden_interpretations"])


def test_every_documented_red_flag_is_covered():
    for code in MEDICAL_RED_FLAGS:
        assert scan_body_signals([code])["status"] == "EXIT_TO_MEDICAL_SAFETY"


# ── EM-30 trigger profile ────────────────────────────────────────────────────

def sample_trigger_events() -> list[dict]:
    return [
        {"trigger_codes": ["PUBLIC_CRITICISM"], "context": "workplace",
         "body_signals": ["JAW_CLENCH"], "urges": ["SEND_HOSTILE_MESSAGE"], "escalation_minutes": 4},
        {"trigger_codes": ["PUBLIC_CRITICISM"], "context": "church_service",
         "body_signals": ["JAW_CLENCH"], "urges": ["WITHDRAW"], "escalation_minutes": 6},
    ]


def test_trigger_profile_needs_at_least_two_events():
    result = build_trigger_profile(sample_trigger_events()[:1], now=NOW)
    assert result["status"] == "INSUFFICIENT_EVENTS"
    assert "不代表你没有模式" in result["note"]


def test_trigger_profile_waits_for_user_confirmation():
    result = build_trigger_profile(sample_trigger_events(), now=NOW)
    assert result["status"] == "DRAFT_AWAITING_USER_CONFIRMATION"
    assert result["trigger_signature"] == ["PUBLIC_CRITICISM"]
    assert result["earliest_body_signals"][0] == "JAW_CLENCH"
    assert result["median_escalation_minutes"] == 5.0
    assert any("不是对你人格的判断" in note for note in result["limitations"])


# ── EM-31 sacred pause ───────────────────────────────────────────────────────

def test_pause_has_six_steps_including_tell_and_return():
    result = build_pause_protocol(band="AMBER")
    codes = [step["code"] for step in result["steps"]]
    assert codes == ["STOP", "STEADY", "DISTINGUISH", "CHOOSE", "TELL", "RETURN"]
    assert result["return_commitment_required"] is True


def test_pause_level_scales_with_the_band():
    assert build_pause_protocol(band="GREEN")["pause_level"] == "P1"
    assert build_pause_protocol(band="AMBER")["pause_level"] == "P2"
    assert build_pause_protocol(band="RED")["pause_level"] == "P3"


def test_both_parties_activated_forces_an_extended_pause():
    result = build_pause_protocol(band="AMBER", both_parties_activated=True)
    assert result["pause_level"] == "P3"
    assert result["third_party_support_suggested"] is True


def test_unsafe_relationship_does_not_require_telling_the_other_party():
    result = build_pause_protocol(band="AMBER", relationship_safety="CAUTION")
    assert all(step["code"] != "TELL" for step in result["steps"])
    assert "先保护自己" in result["return_note"]


def test_crisis_band_skips_the_pause_protocol():
    result = build_pause_protocol(band="CRISIS")
    assert result["status"] == "ROUTED_TO_CRISIS"
    assert result["steps"] == []


# ── EM-32 impulse interrupter ────────────────────────────────────────────────

def test_hostile_message_is_draft_only_with_a_substitute_action():
    result = interrupt_impulse(
        urge_type="SEND_HOSTILE_MESSAGE", urgency=9,
        reversibility="IRREVERSIBLE_HIGH_IMPACT", activation_level=8,
    )
    assert result["send_blocked"] is True
    assert "DRAFT_ONLY" in result["strategies"]
    assert "不发送的信" in result["substitute_action"]
    assert result["delay_seconds"] >= 12 * 3600


def test_reversible_low_impact_gets_a_short_delay_only():
    result = interrupt_impulse(urge_type="WITHDRAW", urgency=4, reversibility="REVERSIBLE_LOW_IMPACT")
    assert result["delay_seconds"] == 600
    assert "ACCOUNTABILITY" not in result["strategies"]


def test_safety_critical_actions_go_to_crisis_not_to_friction():
    result = interrupt_impulse(urge_type="SELF_HARM_URGE", urgency=10, reversibility="SAFETY_CRITICAL")
    assert result["status"] == "ROUTED_TO_CRISIS"
    assert result["strategies"] == []


def test_the_user_can_always_override_the_guard():
    result = interrupt_impulse(urge_type="PUBLIC_ATTACK", urgency=8, reversibility="IRREVERSIBLE_HIGH_IMPACT")
    assert result["user_can_override"] is True
    assert "不替你做决定" in result["override_note"]


def test_unknown_reversibility_class_is_rejected():
    with pytest.raises(ValueError):
        interrupt_impulse(urge_type="WITHDRAW", urgency=3, reversibility="MAYBE")


# ── EM-33 coregulation ───────────────────────────────────────────────────────

def test_only_dual_consented_contacts_are_eligible():
    result = route_coregulation(
        requested_support=["LISTEN"],
        contacts=[contact(person_has_consented=False), contact(support_person_id="sp_002")],
        activation_level=8,
    )
    assert [item["support_person_id"] for item in result["eligible_contacts"]] == ["sp_002"]
    assert result["excluded_contacts"][0]["reason"] == "DUAL_CONSENT_MISSING"


def test_support_types_the_person_never_agreed_to_are_not_used():
    result = route_coregulation(
        requested_support=["PRACTICAL_HELP"], contacts=[contact()], activation_level=7,
    )
    assert result["status"] == "NO_ELIGIBLE_CONTACT"
    assert result["excluded_contacts"][0]["reason"] == "SUPPORT_TYPE_NOT_AGREED"
    assert result["fallback"]


def test_the_conflict_party_is_never_routed_as_support():
    result = route_coregulation(
        requested_support=["LISTEN"], contacts=[contact(is_conflict_party=True)], activation_level=8,
    )
    assert result["excluded_contacts"][0]["reason"] == "IS_CONFLICT_PARTY"


def test_only_minimum_content_is_shared_and_nothing_is_auto_sent():
    result = route_coregulation(requested_support=["LISTEN"], contacts=[contact()], activation_level=8)
    assert result["message_auto_sent"] is False
    assert result["shared_content"]["event_details_shared"] is False
    assert result["eligible_contacts"][0]["content_sharing_scope"].startswith("activation_level")


def test_prayer_support_is_dropped_for_a_neutral_framework():
    result = route_coregulation(
        requested_support=["LISTEN", "PRAYER"], contacts=[contact(allowed_support_types=["LISTEN", "PRAYER"])],
        spiritual_framework="neutral",
    )
    assert "PRAYER" not in result["requested_support"]


# ── EM-34 recovery planning ──────────────────────────────────────────────────

def test_recovery_plan_covers_three_horizons_and_four_recovery_kinds():
    plan = plan_recovery(activation_peak=8, activation_current=4)
    assert [item["code"] for item in plan["horizons"]] == ["NEXT_10_MIN", "NEXT_2_HOURS", "NEXT_24_72_HOURS"]
    assert set(plan["recovery_kinds"]) == {"behavioral", "functional", "emotional", "relational"}


def test_recovery_never_demands_instant_calm_or_instant_forgiveness():
    plan = plan_recovery(activation_peak=9, activation_current=6, relationship_repair_needed=True)
    assert any("不要求你立刻不难过" in note for note in plan["not_required"])
    assert any("立刻原谅" in note for note in plan["not_required"])


def test_unsafe_relationship_removes_repair_from_the_plan():
    plan = plan_recovery(
        activation_peak=8, activation_current=5, relationship_repair_needed=True, relationship_safety="CAUTION",
    )
    long_horizon = plan["horizons"][2]["actions"]
    assert any("优先保护自己" in action for action in long_horizon)
    assert not any("决定是否修复" in action for action in long_horizon)


def test_neutral_framework_gets_no_prayer_suggestions():
    plan = plan_recovery(activation_peak=6, activation_current=3, spiritual_framework="neutral")
    assert plan["optional_spiritual_support"] == []


def test_prayer_is_offered_as_optional_support_not_as_a_requirement():
    plan = plan_recovery(activation_peak=6, activation_current=3)
    text = " ".join(plan["optional_spiritual_support"])
    assert "可选" in text and "替代安全" in text


def test_harmful_action_adds_concrete_correction_not_just_an_apology():
    plan = plan_recovery(activation_peak=9, activation_current=4, harmful_action_occurred=True)
    assert any("具体更正" in action for action in plan["horizons"][2]["actions"])


# ── EM-35 rehearsal ──────────────────────────────────────────────────────────

def rehearsal(**updates):
    values = {
        "level": 2,
        "trigger_description": "在会议上被当众否定",
        "earliest_body_signal": "下颌咬紧",
        "planned_action": "先退出群聊十分钟，把想说的话写到私人草稿",
        "fallback_contact": "可信的同事",
        "changed_variable": "对方不接受边界",
    }
    values.update(updates)
    return build_rehearsal(**values)


def test_rehearsal_always_includes_a_pause_failed_and_already_happened_card():
    result = rehearsal()
    kinds = {card["kind"] for card in result["cards"]}
    assert {"PRIMARY", "PAUSE_FAILED", "ALREADY_HAPPENED"} <= kinds


def test_level_two_changes_exactly_one_listed_variable():
    with pytest.raises(ValueError):
        rehearsal(changed_variable="对方开始动手")
    assert rehearsal(changed_variable="对方延迟回应")["changed_variable"] == "对方延迟回应"


def test_violence_context_is_not_rehearsed():
    result = rehearsal(violence_context=True)
    assert result["status"] == "NOT_APPLICABLE_SAFETY"
    assert result["cards"] == []


def test_rehearsal_language_does_not_pathologise_the_user():
    result = rehearsal(level=3)
    text = " ".join(result["language_rules"])
    assert "不是把你标记为复发者" in text
    assert "复现一次不取消" in text


def test_high_pressure_level_adds_a_spiritualised_pressure_card():
    result = rehearsal(level=3, changed_variable=None)
    assert any(card["kind"] == "HIGH_PRESSURE" for card in result["cards"])


# ── module description and wiring ────────────────────────────────────────────

def test_module_description_lists_its_refusals():
    described = describe_regulation_engine()
    assert len(described["skills"]) == len(WORKFLOW_NODES) == 8
    assert set(described["emotion_lexicon"]) == set(EMOTION_LEXICON)
    assert any("不把候选情绪写成事实" in item for item in described["does_not"])
    assert any("不在高激活时做五层情绪深挖" in item for item in described["does_not"])
    assert any("不用经文或祷告要求用户停止悲伤" in item for item in described["does_not"])


def test_router_exposes_the_batch_four_surface():
    from routers.formation_twin_emotional_maturity import router

    paths = {route.path for route in router.routes}
    for suffix in (
        "regulation/overview", "regulation/label", "regulation/body-scan",
        "regulation/trigger-profile", "regulation/pause", "regulation/impulse-guard",
        "regulation/coregulation", "regulation/recovery-plan", "regulation/rehearsal",
    ):
        assert f"/api/v1/formation-twin/emotional-maturity/{suffix}" in paths


def test_migration_file_exists_for_batch_four():
    migration = ROOT / "backend/migrations/0226_formation_twin_emd_regulation.sql"
    rollback = ROOT / "backend/migrations/rollback/0226_formation_twin_emd_regulation_down.sql"
    assert migration.exists() and rollback.exists()
    sql = migration.read_text(encoding="utf-8")
    assert "formation_twin_emd_regulation_sessions" in sql
    assert "formation_twin_emd_support_persons" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql


def test_erasure_covers_every_batch_four_table():
    source = (ROOT / "backend/routers/formation_twin_emotional_maturity.py").read_text(encoding="utf-8")
    erase_block = source.split("def emotional_maturity_erase")[1]
    for table in (
        "formation_twin_emd_regulation_sessions", "formation_twin_emd_trigger_profiles",
        "formation_twin_emd_pause_protocols", "formation_twin_emd_impulse_guards",
        "formation_twin_emd_support_persons", "formation_twin_emd_coregulation_requests",
        "formation_twin_emd_recovery_plans", "formation_twin_emd_rehearsals",
    ):
        assert table in erase_block
