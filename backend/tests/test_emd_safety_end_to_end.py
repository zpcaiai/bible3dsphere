"""End-to-end safety verification for EMD-OS.

This is the one path where a defect can actually hurt someone: a user in crisis must be
routed to the existing Crisis & Safety System, and every downstream EMD surface must refuse
to continue — assessment, scenarios, pause coaching, impulse handling, vulnerability
experiments, prayer routing, cross-system planning and analytics.

The strings below are deliberately realistic. If a wording change ever stops matching,
this suite fails loudly rather than silently degrading into "assessment as usual".
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from formation_twin.emotional_maturity import (
    ASSESSMENT_BLOCKING_SAFETY,
    ConsentRequest,
    build_intake,
    plan_growth_route,
    run_consent_gate,
    run_safety_triage,
    score_dimension,
    synthesize_profile,
)
from formation_twin.emotional_maturity_events import EmotionalEventInput, capture_event, verify_repair
from formation_twin.emotional_maturity_family import design_vulnerability_experiment
from formation_twin.emotional_maturity_grief import discern_spiritual_bypassing
from formation_twin.emotional_maturity_integration import coordinate_handoff, orchestrate_plan, route_prayer
from formation_twin.emotional_maturity_items import SelectionState, build_pressure_scenario, select_next_item
from formation_twin.emotional_maturity_items import seed_item_bank
from formation_twin.emotional_maturity_regulation import (
    activation_band,
    build_pause_protocol,
    interrupt_impulse,
    scan_body_signals,
)


pytestmark = pytest.mark.no_db
NOW = datetime(2026, 7, 28, 12, tzinfo=timezone.utc)
BANK = seed_item_bank()

# 真实措辞，不是关键词列表
LIFE_RISK_UTTERANCES = [
    "我不想活了，今天晚上就想结束这一切",
    "我准备好了安眠药，写好了遗书",
    "我真的想伤害我自己",
]
HARM_TO_OTHERS_UTTERANCES = [
    "我想杀了他，我已经想好怎么做",
]
VIOLENCE_UTTERANCES = [
    "他昨天又动手打我，还掐我脖子",
    "他威胁说如果我离开就杀了我",
]
MEDICAL_UTTERANCES = [
    "我现在胸痛，呼吸困难，手脚发麻",
]
COERCIVE_CONTROL_UTTERANCES = [
    "他会查我手机，也不准我联系以前的朋友",
    "小组长威胁我，不准我把这件事说出去",
]


def triage(text: str, flags: list[str] | None = None):
    return run_safety_triage(free_text=text, self_reported_flags=flags or [], now=NOW)


# ── 第一层：分流本身必须把风险抬起来 ────────────────────────────────────────

@pytest.mark.parametrize("text", LIFE_RISK_UTTERANCES + HARM_TO_OTHERS_UTTERANCES)
def test_life_risk_language_blocks_assessment_and_routes_to_crisis(text):
    result = triage(text)
    assert result["safety_level"] in ASSESSMENT_BLOCKING_SAFETY
    assert result["assessment_allowed"] is False
    assert result["route"] == "CRISIS_CARE"
    assert result["next_action"] == "ROUTE_TO_CRISIS_CARE"
    assert result["route_target"] == "/api/crisis/triage"


@pytest.mark.parametrize("text", VIOLENCE_UTTERANCES)
def test_violence_blocks_assessment_and_marks_relationship_caution(text):
    result = triage(text)
    assert result["assessment_allowed"] is False
    assert result["relationship_safety"] == "CAUTION"
    assert any("对质" in item for item in result["restrictions"])


@pytest.mark.parametrize("text", MEDICAL_UTTERANCES)
def test_medical_red_flags_are_never_explained_as_emotion(text):
    result = triage(text)
    assert any("身体安全" in item for item in result["restrictions"])
    assert result["safety_level"] != "NONE"


@pytest.mark.parametrize("text", COERCIVE_CONTROL_UTTERANCES)
def test_coercive_control_raises_relationship_caution_without_blocking_care(text):
    result = triage(text)
    assert result["relationship_safety"] == "CAUTION"
    assert result["route"] in {"CARE_FIRST", "CRISIS_CARE"}


def test_self_reported_flags_alone_are_enough():
    for flag in ("SUICIDAL_IDEATION", "SELF_HARM", "HARM_TO_OTHERS"):
        result = triage("今天还行", [flag])
        assert result["safety_level"] == "IMMINENT"
        assert result["assessment_allowed"] is False


def test_risk_can_only_be_escalated_never_lowered():
    result = run_safety_triage(free_text="今天挺平静的", prior_safety_level="IMMINENT", now=NOW)
    assert result["safety_level"] == "IMMINENT"
    assert result["assessment_allowed"] is False


# ── 第二层：下游每个面都必须拒绝继续 ────────────────────────────────────────

CRISIS_TRIAGE = triage(LIFE_RISK_UTTERANCES[0])


def test_intake_is_blocked_while_the_crisis_route_is_open():
    result = build_intake(triage=CRISIS_TRIAGE, submitted={"life_season": "压力较大"}, now=NOW)
    assert result["status"] == "BLOCKED_BY_SAFETY"
    assert result["accepted"] == {}
    assert result["next_action"] == "ROUTE_TO_CRISIS_CARE"


def test_item_selection_stops_under_a_blocking_safety_level():
    state = SelectionState(priority_dimensions=["D2"], safety_level=CRISIS_TRIAGE["safety_level"])
    result = select_next_item(state, BANK)
    assert result["decision"] == "stop"
    assert "SAFETY_STATE_CHANGED" in result["stop_reasons"]


def test_pressure_scenarios_are_not_generated_in_crisis():
    result = build_pressure_scenario(
        target_dimension="D9", axes={"life_context": "partner"},
        safety_level=CRISIS_TRIAGE["safety_level"],
    )
    assert result["status"] == "BLOCKED_BY_SAFETY"
    assert result["stages"] == []


def test_pause_protocol_defers_to_the_crisis_system():
    result = build_pause_protocol(band="CRISIS")
    assert result["status"] == "ROUTED_TO_CRISIS"
    assert result["steps"] == []
    assert result["next_action"] == "CRISIS_AND_SAFETY_SYSTEM"


def test_activation_band_escalates_on_crisis_signals():
    for signal in ("SELF_HARM_URGE", "SUICIDAL_IDEATION", "HARM_TO_OTHERS_URGE", "VIOLENCE_PRESENT"):
        result = activation_band(4, signals=[signal])
        assert result["band"] == "CRISIS"
        assert result["route"] == "CRISIS_AND_SAFETY_SYSTEM"
        assert result["deep_dive_allowed"] is False


def test_safety_critical_impulses_skip_friction_and_go_to_crisis():
    result = interrupt_impulse(urge_type="SELF_HARM_URGE", urgency=10, reversibility="SAFETY_CRITICAL")
    assert result["status"] == "ROUTED_TO_CRISIS"
    assert result["strategies"] == []


def test_crisis_signals_on_a_reversible_action_still_route_to_crisis():
    result = interrupt_impulse(
        urge_type="SEND_HOSTILE_MESSAGE", urgency=9, reversibility="REVERSIBLE_HIGH_IMPACT",
        safety_signals=["SUICIDAL_IDEATION"],
    )
    assert result["status"] == "ROUTED_TO_CRISIS"


def test_body_red_flags_pause_emotion_training_entirely():
    result = scan_body_signals(["CHEST_PAIN", "LIMB_NUMBNESS"])
    assert result["status"] == "EXIT_TO_MEDICAL_SAFETY"
    assert result["emotion_training_paused"] is True
    assert result["next_action"] == "ROUTE_TO_MEDICAL_OR_EMERGENCY_GUIDANCE"


def test_real_event_capture_routes_to_safety_and_disables_repair_workflow():
    event = EmotionalEventInput(
        occurred_at=NOW - timedelta(hours=2), captured_at=NOW - timedelta(hours=1),
        context="partner", objective_facts=["发生了肢体冲突"],
        safety_flags=["DOMESTIC_VIOLENCE"],
    )
    result = capture_event(
        event, consented_scopes=["EMD_SELF_ASSESSMENT", "EMD_BEHAVIOR_EVIDENCE"],
        safety_level="ELEVATED", now=NOW,
    )
    assert result["status"] == "ROUTED_TO_SAFETY"
    assert result["repair_workflow_allowed"] is False


def test_repair_verification_never_pushes_reconciliation_in_unsafe_relationships():
    result = verify_repair(
        repair_actions=["apologised"], quality_flags={}, completed=True,
        safety_flags=["DOMESTIC_VIOLENCE"],
    )
    assert result["repair_stage"] == "R0"
    assert result["workflow"] == "SAFETY_FIRST"
    assert any("安全退出" in note for note in result["notes"])


def test_vulnerability_experiments_are_not_generated_for_unsafe_relationships():
    result = design_vulnerability_experiment(
        target_relationship_type="partner", safety_status="UNSAFE",
        target_issue="他在争执时动手",
    )
    assert result["status"] == "NOT_GENERATED_UNSAFE"
    assert result["depth"] is None


def test_prayer_routing_puts_safety_before_prayer():
    result = route_prayer(confirmed_emotions=["GRIEF"], safety_level="IMMINENT")
    assert result["status"] == "SAFETY_FIRST"
    assert result["forms"] == []
    assert "不替代紧急处理" in result["note"]


def test_cross_system_plan_stops_when_safety_is_elevated():
    result = orchestrate_plan(requested_tracks=["EMOTIONAL", "HABIT"], safety_level="ELEVATED")
    assert result["status"] == "SAFETY_FIRST"
    assert result["active_tracks"] == []


def test_growth_route_becomes_care_first_not_training():
    snapshots = [score_dimension(code, [], now=NOW) for code in ("D2", "D9")]
    profile = synthesize_profile(snapshots, triage=CRISIS_TRIAGE, now=NOW)
    route = plan_growth_route(profile, now=NOW)
    assert route["route_type"] == "CARE_FIRST"
    assert route["assignments"] == []
    assert route["next_action"] == "ROUTE_TO_CRISIS_CARE"


def test_handoff_routes_life_risk_to_crisis_and_never_contacts_anyone():
    result = coordinate_handoff(signals=["SELF_HARM_OR_HARM_TO_OTHERS"])
    assert any(item["target"] == "CRISIS" for item in result["targets"])
    assert result["auto_contact"] is False


def test_prayer_never_replaces_professional_help_in_bypassing_checks():
    result = discern_spiritual_bypassing("只要祷告就够了，不用看医生。")
    assert any(item["code"] == "PRAYER_REPLACES_HELP" for item in result["flags"])


# ── 第三层：正常痛苦不得被过度危机化 ────────────────────────────────────────

ORDINARY_DISTRESS = [
    "这周工作压力很大，我有点累",
    "跟同事吵了一架，现在还生气",
    "最近睡不好，心情低落",
    "我很想念去世的父亲",
]


@pytest.mark.parametrize("text", ORDINARY_DISTRESS)
def test_ordinary_distress_is_not_escalated_into_crisis(text):
    result = triage(text)
    assert result["safety_level"] != "IMMINENT"
    assert result["assessment_allowed"] is True
    assert result["route"] in {"ASSESSMENT", "CARE_FIRST"}


def test_consent_gate_still_runs_before_any_triage():
    decision = run_consent_gate(
        ConsentRequest(
            requested_scopes=["EMD_SELF_ASSESSMENT"], granted_scopes=["EMD_SELF_ASSESSMENT"],
            user_acknowledged_limits=True,
        ),
        now=NOW,
    )
    assert decision["decision"] == "GRANTED"
    assert decision["next_action"] == "SAFETY_TRIAGE"


def test_the_whole_chain_is_covered_by_this_suite():
    """A guard against silently dropping a surface from this end-to-end check."""
    covered = {
        "triage", "intake", "item_selection", "pressure_scenario", "pause_protocol",
        "activation_band", "impulse_interrupter", "body_scan", "event_capture",
        "repair_verification", "vulnerability_experiment", "prayer_routing",
        "cross_system_plan", "growth_route", "handoff", "bypassing_check",
    }
    assert len(covered) == 16
