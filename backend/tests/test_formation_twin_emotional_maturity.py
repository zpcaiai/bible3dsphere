from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from formation_twin.emotional_maturity import (
    CONSENT_SCOPES,
    DIMENSION_CODES,
    PUBLISHED_EVENTS,
    PROHIBITED_KEYS,
    STAGE_RANK,
    WORKFLOW_NODES,
    ConsentRequest,
    EvidenceItem,
    UnsafeContentError,
    apply_correction,
    audit_response_validity,
    build_intake,
    describe_module,
    emd_data_quality,
    normalize_evidence,
    plan_growth_route,
    run_consent_gate,
    run_safety_triage,
    sanitize_event,
    sanitize_payload,
    schedule_reassessment,
    score_dimension,
    select_next_items,
    synthesize_profile,
    validate_safe_text,
    withdraw_consent,
)
from routers.formation_twin_emotional_maturity import router


pytestmark = pytest.mark.no_db
NOW = datetime(2026, 7, 28, 12, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[2]
ALL_SCOPES = list(CONSENT_SCOPES)


def evidence(
    dimension="D2",
    kind="SELF_DESCRIPTION",
    stage="E3",
    *,
    ident=None,
    context="FAMILY",
    group=None,
    days_ago=3,
    self_rated=False,
    summary="",
):
    if kind in {"RECENT_BEHAVIOR", "REAL_LIFE_EVENT"} and not summary:
        summary = "我先离开房间十分钟，回来后把话说完。"
    occurred = NOW - timedelta(days=days_ago)
    return EvidenceItem(
        evidence_id=ident or f"{dimension}-{kind}-{stage}-{days_ago}-{context}",
        dimension_code=dimension,
        evidence_kind=kind,
        context=context,
        stage_signal=stage,
        occurred_at=occurred,
        recorded_at=occurred + timedelta(minutes=5),
        independence_group=group,
        self_rated=self_rated,
        behavior_summary=summary,
        references=[{"reference_type": "CHECKIN", "reference_id": f"ref-{dimension}-{kind}-{days_ago}"}],
    )


def consent(**updates):
    values = {
        "requested_scopes": ALL_SCOPES,
        "granted_scopes": ALL_SCOPES,
        "user_acknowledged_limits": True,
    }
    values.update(updates)
    return ConsentRequest(**values)


# ── EM-01 consent gate ───────────────────────────────────────────────────────

def test_consent_gate_grants_and_lists_withdrawable_scopes():
    result = run_consent_gate(consent(), now=NOW)
    assert result["decision"] == "GRANTED"
    assert set(result["withdrawable_scopes"]) == set(CONSENT_SCOPES)
    assert result["next_action"] == "SAFETY_TRIAGE"


def test_consent_gate_blocks_without_core_scope_or_acknowledgement():
    blocked = run_consent_gate(
        consent(requested_scopes=["EMD_SELF_ASSESSMENT"], granted_scopes=[]), now=NOW
    )
    assert blocked["decision"] == "BLOCKED"
    assert "REQUIRED_CONSENT_MISSING" in blocked["blocks"]
    assert blocked["granted_scopes"] == []

    unacknowledged = run_consent_gate(consent(user_acknowledged_limits=False), now=NOW)
    assert "LIMITS_NOT_ACKNOWLEDGED" in unacknowledged["blocks"]


def test_minor_requires_separate_certification():
    result = run_consent_gate(consent(is_minor=True), now=NOW)
    assert result["decision"] == "BLOCKED"
    assert "MINOR_REQUIRES_SEPARATE_CERTIFICATION" in result["blocks"]


def test_granted_scope_must_have_been_requested():
    with pytest.raises(ValueError):
        ConsentRequest(requested_scopes=["EMD_SELF_ASSESSMENT"], granted_scopes=["EMD_PASTORAL_SHARE"])


def test_withdrawing_sharing_keeps_private_core():
    result = withdraw_consent(ALL_SCOPES, "EMD_PASTORAL_SHARE")
    assert result["private_core_still_available"] is True
    assert "EMD_PASTORAL_SHARE" not in result["remaining_scopes"]


def test_withdrawing_behavior_consent_forces_recompute():
    result = withdraw_consent(ALL_SCOPES, "EMD_BEHAVIOR_EVIDENCE")
    assert result["recompute_required"] is True
    assert result["next_action"] == "RECOMPUTE_PROFILE"


# ── EM-02 safety triage ──────────────────────────────────────────────────────

def test_triage_blocks_assessment_on_self_reported_life_risk():
    result = run_safety_triage(self_reported_flags=["SUICIDAL_IDEATION"], now=NOW)
    assert result["safety_level"] == "IMMINENT"
    assert result["assessment_allowed"] is False
    assert result["next_action"] == "ROUTE_TO_CRISIS_CARE"


def test_triage_marks_relationship_caution_and_forbids_confrontation():
    result = run_safety_triage(free_text="他昨天又动手打我，还不让我出门。", now=NOW)
    assert result["relationship_safety"] == "CAUTION"
    assert any("对质" in item for item in result["restrictions"])


def test_triage_never_lowers_a_prior_risk_level():
    result = run_safety_triage(free_text="今天还好", prior_safety_level="ELEVATED", now=NOW)
    assert result["safety_level"] == "ELEVATED"
    assert result["assessment_allowed"] is False


def test_medical_red_flag_is_not_explained_as_emotion():
    result = run_safety_triage(free_text="这两天一直胸痛，喘不上气。", now=NOW)
    assert any("身体安全" in item for item in result["restrictions"])


# ── EM-03 intake ─────────────────────────────────────────────────────────────

def test_intake_is_blocked_while_safety_route_is_open():
    triage = run_safety_triage(self_reported_flags=["SELF_HARM"], now=NOW)
    result = build_intake(triage=triage, submitted={"life_season": "压力较大"}, now=NOW)
    assert result["status"] == "BLOCKED_BY_SAFETY"
    assert result["accepted"] == {}


def test_intake_rejects_forbidden_fields_and_allows_skipping():
    triage = run_safety_triage(free_text="最近工作压力大", now=NOW)
    result = build_intake(
        triage=triage,
        submitted={"life_season": "压力较大", "medication": "舍曲林", "third_party_name": "张牧师"},
        now=NOW,
    )
    assert result["status"] == "READY"
    assert result["rejected_fields"] == ["medication", "third_party_name"]
    assert "sleep_recent" in result["skipped_fields"]


# ── EM-04 evidence normalizer ────────────────────────────────────────────────

def test_behavior_evidence_requires_its_own_consent():
    raw = [evidence(kind="REAL_LIFE_EVENT").model_dump(mode="json")]
    result = normalize_evidence(raw, consented_scopes=["EMD_SELF_ASSESSMENT"], now=NOW)
    assert result["accepted"] == []
    assert result["rejected"][0]["reason"] == "BEHAVIOR_CONSENT_MISSING"


def test_normalizer_dedupes_and_drops_forbidden_bodies():
    raw = evidence(ident="dup-1", group="conflict-2026-07-20").model_dump(mode="json")
    raw["journal_text"] = "长长的日记正文"
    duplicate = dict(raw, evidence_id="dup-2")
    result = normalize_evidence([raw, duplicate], consented_scopes=ALL_SCOPES, now=NOW)
    assert len(result["accepted"]) == 1
    assert result["rejected"][0]["reason"] == "DUPLICATE"
    assert all("journal_text" not in item for item in result["accepted"])


def test_real_behavior_evidence_needs_an_observable_summary():
    with pytest.raises(ValueError):
        EvidenceItem(
            evidence_id="no-summary",
            dimension_code="D2",
            evidence_kind="REAL_LIFE_EVENT",
            context="WORK",
            stage_signal="E4",
            occurred_at=NOW - timedelta(days=1),
            recorded_at=NOW,
        )


# ── EM-05 adaptive assessor ──────────────────────────────────────────────────

def test_assessor_prioritises_dimensions_missing_the_most_evidence_kinds():
    items = [
        evidence(dimension="D2", kind="SELF_DESCRIPTION"),
        evidence(dimension="D2", kind="RECENT_BEHAVIOR"),
    ]
    result = select_next_items(evidence=items, focus_dimensions=["D2", "D9"])
    assert result["selected"][0]["dimension_code"] == "D9"
    assert result["skippable"] is True


def test_assessor_stops_on_fatigue():
    result = select_next_items(evidence=[], fatigue_reported=True)
    assert result["stop"] is True
    assert "USER_FATIGUE" in result["stop_reasons"]
    assert result["selected"] == []


def test_conflict_items_are_restricted_when_relationship_is_unsafe():
    triage = run_safety_triage(free_text="他昨天又动手打我。", now=NOW)
    result = select_next_items(evidence=[], focus_dimensions=["D9"], restrictions=triage["restrictions"])
    assert result["selected"][0]["scenario_restriction"]


# ── EM-06 scorer ─────────────────────────────────────────────────────────────

def test_insufficient_evidence_yields_stage_e0_not_a_low_score():
    snapshot = score_dimension("D2", [evidence()], now=NOW)
    assert snapshot.confidence == "INSUFFICIENT"
    assert snapshot.stage == "E0"
    assert "证据不足" in snapshot.uncertainty[0]


def test_self_report_only_is_capped_at_e2():
    items = [
        evidence(kind="SELF_DESCRIPTION", stage="E5", ident="s1", group="g1"),
        evidence(kind="SELF_DESCRIPTION", stage="E5", ident="s2", group="g2", days_ago=4),
        evidence(kind="SCENARIO_RESPONSE", stage="E5", ident="s3", group="g3", days_ago=5),
    ]
    snapshot = score_dimension("D2", items, now=NOW)
    assert snapshot.stage == "E2"
    assert "SELF_REPORT_ONLY" in snapshot.caps_applied


def test_scenario_success_without_real_event_cannot_reach_e4():
    items = [
        evidence(kind="SCENARIO_RESPONSE", stage="E5", ident="c1", group="g1"),
        evidence(kind="SCENARIO_RESPONSE", stage="E5", ident="c2", group="g2", days_ago=4),
        evidence(kind="RECENT_BEHAVIOR", stage="E5", ident="c3", group="g3", days_ago=6),
        evidence(kind="RECENT_BEHAVIOR", stage="E5", ident="c4", group="g4", days_ago=8),
    ]
    snapshot = score_dimension("D2", items, now=NOW)
    assert STAGE_RANK[snapshot.stage] <= STAGE_RANK["E3"]
    assert "NO_REAL_LIFE_EVENT" in snapshot.caps_applied


def test_single_success_does_not_prove_a_stable_stage():
    items = [
        evidence(kind="REAL_LIFE_EVENT", stage="E5", ident="r1", group="g1"),
        evidence(kind="SELF_DESCRIPTION", stage="E1", ident="r2", group="g2", days_ago=4),
        evidence(kind="SCENARIO_RESPONSE", stage="E1", ident="r3", group="g3", days_ago=5),
    ]
    snapshot = score_dimension("D2", items, now=NOW)
    assert snapshot.stage != "E5"


def test_higher_confidence_requires_two_real_events_across_contexts():
    items = [
        evidence(kind="REAL_LIFE_EVENT", stage="E4", ident="h1", group="g1", context="FAMILY"),
        evidence(kind="REAL_LIFE_EVENT", stage="E4", ident="h2", group="g2", context="WORK", days_ago=9),
        evidence(kind="RECENT_BEHAVIOR", stage="E4", ident="h3", group="g3", context="WORK", days_ago=12),
        evidence(kind="SCENARIO_RESPONSE", stage="E4", ident="h4", group="g4", days_ago=13),
        evidence(kind="SELF_DESCRIPTION", stage="E4", ident="h5", group="g5", days_ago=14),
    ]
    snapshot = score_dimension("D2", items, now=NOW)
    assert snapshot.confidence == "HIGHER"
    assert snapshot.stage == "E4"


def test_stale_evidence_does_not_keep_a_stage_alive():
    items = [
        evidence(kind="REAL_LIFE_EVENT", stage="E4", ident="old1", group="g1", days_ago=400),
        evidence(kind="REAL_LIFE_EVENT", stage="E4", ident="old2", group="g2", days_ago=420),
    ]
    snapshot = score_dimension("D2", items, now=NOW)
    assert snapshot.stage == "E0"


def test_context_differences_are_reported_rather_than_averaged_away():
    items = [
        evidence(kind="REAL_LIFE_EVENT", stage="E4", ident="w1", group="g1", context="WORK"),
        evidence(kind="REAL_LIFE_EVENT", stage="E4", ident="w2", group="g2", context="WORK", days_ago=6),
        evidence(kind="RECENT_BEHAVIOR", stage="E1", ident="f1", group="g3", context="FAMILY", days_ago=7),
        evidence(kind="SELF_DESCRIPTION", stage="E1", ident="f2", group="g4", context="FAMILY", days_ago=8),
    ]
    snapshot = score_dimension("D2", items, now=NOW)
    contexts = {entry["context"] for entry in snapshot.context_differences}
    assert contexts == {"WORK", "FAMILY"}
    assert any("场景" in note for note in snapshot.uncertainty)


# ── EM-07 validity auditor ───────────────────────────────────────────────────

def test_all_high_self_ratings_without_behavior_flag_social_desirability():
    responses = [{"self_rating": 0.95, "duration_ms": 5000} for _ in range(6)]
    result = audit_response_validity(responses, [evidence(kind="SELF_DESCRIPTION")], now=NOW)
    assert "SOCIAL_DESIRABILITY" in result["flag_codes"]
    assert result["cap_stage_required"] is True


def test_self_report_behavior_gap_is_flagged_high():
    items = [
        evidence(kind="SELF_DESCRIPTION", stage="E5", ident="g1", self_rated=True),
        evidence(kind="REAL_LIFE_EVENT", stage="E1", ident="g2", days_ago=4),
    ]
    result = audit_response_validity([], items, now=NOW)
    assert "SELF_REPORT_BEHAVIOR_GAP" in result["flag_codes"]


def test_short_answers_are_never_penalised_by_the_auditor():
    responses = [{"text": "我先走开，等冷静再说。", "duration_ms": 9000}]
    result = audit_response_validity(responses, [evidence(kind="RECENT_BEHAVIOR")], now=NOW)
    assert result["flag_codes"] == []
    assert any("字少" in note for note in result["user_visible_notes"])


def test_copying_rubric_wording_is_detected():
    responses = [{"text": "我会先暂停，命名情绪，再选择回应", "duration_ms": 4000}]
    result = audit_response_validity(responses, [], now=NOW)
    assert "RUBRIC_LANGUAGE_COPIED" in result["flag_codes"]


# ── EM-08 profile ────────────────────────────────────────────────────────────

def _rich_snapshots():
    strong = [
        evidence(dimension="D2", kind="REAL_LIFE_EVENT", stage="E4", ident="p1", group="g1", context="WORK"),
        evidence(dimension="D2", kind="REAL_LIFE_EVENT", stage="E4", ident="p2", group="g2", context="FAMILY", days_ago=9),
        evidence(dimension="D2", kind="RECENT_BEHAVIOR", stage="E4", ident="p3", group="g3", days_ago=11),
    ]
    weak = [
        evidence(dimension="D9", kind="REAL_LIFE_EVENT", stage="E1", ident="p4", group="g4", context="FAMILY"),
        evidence(dimension="D9", kind="RECENT_BEHAVIOR", stage="E1", ident="p5", group="g5", days_ago=6),
        evidence(dimension="D9", kind="SELF_DESCRIPTION", stage="E1", ident="p6", group="g6", days_ago=7),
    ]
    items = strong + weak
    return [score_dimension(code, items, now=NOW) for code in DIMENSION_CODES]


def test_profile_never_contains_a_total_score_or_ranking():
    profile = synthesize_profile(_rich_snapshots(), now=NOW)
    assert profile["total_score"] is None
    assert not set(profile) & PROHIBITED_KEYS
    assert profile["spiritual_maturity_claim"] is None


def test_profile_picks_lowest_supported_dimension_as_growth_invitation():
    profile = synthesize_profile(_rich_snapshots(), now=NOW)
    assert profile["growth_invitations"][0]["dimension_code"] == "D9"
    assert profile["current_strengths"][0]["dimension_code"] == "D2"


def test_profile_lists_insufficient_dimensions_instead_of_guessing():
    profile = synthesize_profile(_rich_snapshots(), now=NOW)
    assert "D5" in profile["insufficient_evidence_dimensions"]


# ── EM-09 growth route ───────────────────────────────────────────────────────

def test_route_targets_existing_training_modules_only():
    profile = synthesize_profile(_rich_snapshots(), now=NOW)
    route = plan_growth_route(profile, now=NOW)
    assert route["route_type"] == "TRAINING"
    assignment = route["assignments"][0]
    assert assignment["dimension_code"] == "D9"
    assert "forgiveness" in assignment["training_modules"]
    assert [item["day"] for item in route["checkpoints"]] == [14, 30, 90]


def test_route_is_care_first_when_safety_blocks_assessment():
    profile = synthesize_profile(
        _rich_snapshots(),
        triage=run_safety_triage(self_reported_flags=["SUICIDAL_IDEATION"], now=NOW),
        now=NOW,
    )
    route = plan_growth_route(profile, now=NOW)
    assert route["route_type"] == "CARE_FIRST"
    assert route["assignments"] == []
    assert route["next_action"] == "ROUTE_TO_CRISIS_CARE"


def test_unsafe_relationship_blocks_repair_actions_but_keeps_the_dimension():
    # Coercive control raises relationship caution without blocking the assessment itself.
    profile = synthesize_profile(
        _rich_snapshots(),
        triage=run_safety_triage(free_text="他会查我手机，也不准我联系以前的朋友。", now=NOW),
        now=NOW,
    )
    route = plan_growth_route(profile, now=NOW)
    assignment = next(item for item in route["assignments"] if item["dimension_code"] == "D9")
    assert assignment["restrictions"]


# ── EM-10 correction and reassessment ────────────────────────────────────────

def test_disputed_stage_is_not_written_into_the_twin():
    items = [
        evidence(kind="REAL_LIFE_EVENT", stage="E4", ident="d1", group="g1"),
        evidence(kind="RECENT_BEHAVIOR", stage="E4", ident="d2", group="g2", days_ago=5),
        evidence(kind="SELF_DESCRIPTION", stage="E4", ident="d3", group="g3", days_ago=6),
    ]
    snapshot = score_dimension("D2", items, now=NOW)
    result = apply_correction(snapshot, items, {"correction_type": "DISPUTE_STAGE", "user_note": "这不像我。"}, now=NOW)
    assert result["snapshot"]["user_review_status"] == "USER_DISPUTED"
    assert result["twin_update_allowed"] is False
    assert result["user_note_retained"] is True


def test_excluding_evidence_recomputes_the_snapshot():
    items = [
        evidence(kind="REAL_LIFE_EVENT", stage="E4", ident="x1", group="g1"),
        evidence(kind="REAL_LIFE_EVENT", stage="E4", ident="x2", group="g2", days_ago=5),
        evidence(kind="SELF_DESCRIPTION", stage="E4", ident="x3", group="g3", days_ago=6),
    ]
    snapshot = score_dimension("D2", items, now=NOW)
    result = apply_correction(snapshot, items, {"correction_type": "EXCLUDE_EVIDENCE", "evidence_id": "x1"}, now=NOW)
    assert STAGE_RANK[result["snapshot"]["stage"]] <= STAGE_RANK[snapshot.stage]
    assert result["superseded_snapshot"]["stage"] == snapshot.stage


def test_declining_a_dimension_clears_it_without_penalty():
    snapshot = score_dimension("D6", [evidence(dimension="D6")], now=NOW)
    result = apply_correction(snapshot, [], {"correction_type": "DECLINE_DIMENSION"}, now=NOW)
    assert result["snapshot"]["stage"] == "E0"
    assert result["snapshot"]["user_review_status"] == "USER_CORRECTED"


def test_reassessment_requires_longitudinal_consent():
    profile = synthesize_profile(_rich_snapshots(), now=NOW)
    without = schedule_reassessment(profile, consented_scopes=["EMD_SELF_ASSESSMENT"], now=NOW)
    assert without["status"] == "NOT_SCHEDULED"
    with_consent = schedule_reassessment(profile, consented_scopes=ALL_SCOPES, now=NOW)
    assert with_consent["status"] == "SCHEDULED"
    assert [item["day"] for item in with_consent["checkpoints"]] == [14, 30, 90]


# ── output safety, events and data quality ───────────────────────────────────

@pytest.mark.parametrize("text", [
    "你的情感成熟总分是 78 分",
    "神正在告诉你回到这段关系",
    "你就是回避型人格",
    "你必须立刻原谅他",
    "你小时候一定曾经被父亲抛弃",
])
def test_prohibited_output_is_blocked(text):
    with pytest.raises(UnsafeContentError):
        validate_safe_text(text)


def test_safe_behavioral_description_passes():
    assert validate_safe_text("你记录了三次在争执后先离开再回来把话说完。")


def test_sanitize_payload_strips_forbidden_keys():
    cleaned = sanitize_payload({"stage": "E3", "spiritual_rank": 2, "nested": {"clinical_diagnosis": "x", "ok": 1}})
    assert "spiritual_rank" not in cleaned
    assert "clinical_diagnosis" not in cleaned["nested"]
    assert cleaned["nested"]["ok"] == 1


def test_events_are_registered_and_carry_no_content():
    payload = sanitize_event("emd.profile_synthesized", {"profile_id": "p1", "raw_narrative": "正文", "stage": "E3"})
    assert payload == {"profile_id": "p1", "stage": "E3"}
    with pytest.raises(ValueError):
        sanitize_event("emd.unknown_event", {})


def test_data_quality_blocks_on_consentless_behavior_evidence():
    report = emd_data_quality(
        consent_records=[{"granted_scopes": ["EMD_SELF_ASSESSMENT"]}],
        evidence=[{"evidence_id": "e1", "dimension_code": "D2", "evidence_kind": "REAL_LIFE_EVENT", "references": [{"a": 1}]}],
        snapshots=[],
    )
    assert report["status"] == "BLOCKED"
    assert report["release_allowed"] is False
    assert any(item["code"] == "BEHAVIOR_EVIDENCE_WITHOUT_CONSENT" for item in report["findings"])


def test_data_quality_blocks_stage_without_evidence():
    report = emd_data_quality(
        consent_records=[{"granted_scopes": list(CONSENT_SCOPES)}],
        evidence=[],
        snapshots=[{"dimension_code": "D2", "stage": "E4", "confidence": "INSUFFICIENT"}],
    )
    assert any(item["code"] == "STAGE_WITHOUT_EVIDENCE" for item in report["findings"])


def test_module_description_declares_its_boundaries():
    described = describe_module()
    assert described["short_name"] == "EMD-OS"
    assert len(described["skills"]) == len(WORKFLOW_NODES) == 10
    assert len(described["dimensions"]) == 10
    assert any("得救" in item for item in described["does_not"])
    assert set(described["published_events"]) == set(PUBLISHED_EVENTS)


# ── wiring ───────────────────────────────────────────────────────────────────

def test_router_exposes_the_batch_one_surface():
    paths = {route.path for route in router.routes}
    for suffix in (
        "consent", "consent/withdraw", "triage", "intake", "evidence", "next-items",
        "score", "route", "corrections", "reassessment", "profile", "data-quality", "data",
    ):
        assert f"/api/v1/formation-twin/emotional-maturity/{suffix}" in paths


def test_migration_and_rollback_files_exist():
    migration = ROOT / "backend/migrations/0223_formation_twin_emotional_maturity.sql"
    rollback = ROOT / "backend/migrations/rollback/0223_formation_twin_emotional_maturity_down.sql"
    assert migration.exists() and rollback.exists()
    sql = migration.read_text(encoding="utf-8")
    assert "formation_twin_emd_dimension_snapshots" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql
    # a stage may never be persisted without supporting evidence
    assert "confidence <> 'INSUFFICIENT' OR stage = 'E0'" in sql


def test_main_registers_the_router():
    main = (ROOT / "backend/main.py").read_text(encoding="utf-8")
    assert "init_formation_twin_emotional_maturity_router(" in main
    assert "app.include_router(formation_twin_emotional_maturity_router)" in main
