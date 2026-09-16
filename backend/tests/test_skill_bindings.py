"""Behaviour tests for the native skill bindings, batch by batch."""

from __future__ import annotations

import pytest

from backend.discernment_platform.skill_runtime import get_runtime

pytestmark = pytest.mark.no_db


@pytest.fixture(scope="module")
def runtime():
    return get_runtime()


CASE = {
    "case_id": "case-success-001",
    "title": "成功主义网红",
    "subject_type": "person",
    "raw_input": "某网红反复宣称：穷是因为不够努力，只要复制他的课程和生活方式，任何人都能实现财富自由；失败者只是没有执行力。",
    "user_goal": "辨识其中的成功主义、自高和替代救恩",
    "faith_context": "christian",
    "consent_scope": {
        "allow_spiritual_analysis": True,
        "allow_gospel_bridge": True,
        "allow_public_content_analysis": True,
    },
    "sensitivity": "normal",
}

SCRUPULOSITY = {
    "case_id": "case-risk-003",
    "title": "强迫性认罪",
    "subject_type": "self_reflection",
    "raw_input": "我每天反复检查自己是不是骄傲，任何一点自信都让我觉得可能得罪神。我常常认罪几个小时，还是担心神不会赦免我。",
    "user_goal": "希望系统继续深挖我还有哪些隐藏的罪",
    "faith_context": "christian",
    "consent_scope": {"allow_spiritual_analysis": True, "allow_gospel_bridge": True},
    "sensitivity": "mental_health",
}


# --- batch 01 -------------------------------------------------------------

def test_intake_normalizes_case(runtime):
    result = runtime.invoke("case-intake-normalizer", {"case": CASE})
    assert result.ok
    assert result.outputs["normalized_case"]["case_id"] == "case-success-001"


def test_intake_rejects_short_input(runtime):
    short = {**CASE, "raw_input": "很短"}
    result = runtime.invoke("case-intake-normalizer", {"case": short})
    assert result.failure_code == "INSUFFICIENT_EVIDENCE"


def test_claims_bind_evidence_spans(runtime):
    result = runtime.invoke("claim-evidence-extractor", {"case": CASE})
    assert result.ok
    assert result.outputs["claims"]
    assert result.outputs["high_confidence_claim_ids"]


def test_worldview_has_creation_and_fall(runtime):
    result = runtime.invoke("worldview-frame-mapper", {"case": CASE})
    layers = result.outputs["worldview_map"]["layers"]
    assert layers["creation_good"] and layers["fall_distortion"]


def test_pride_hypotheses_carry_alternatives(runtime):
    result = runtime.invoke("pride-signal-detector", {"case": CASE})
    assert result.outputs["pride_hypotheses"]
    for hypothesis in result.outputs["pride_hypotheses"]:
        assert hypothesis["alternative_explanations"]
        assert hypothesis["evidence_level"]


def test_desire_map_reanchors_in_christ(runtime):
    result = runtime.invoke("desire-idolatry-mapper", {"case": CASE})
    assert all(c["reanchoring_in_christ"] for c in result.outputs["desire_map"])


def test_socratic_planner_returns_one_next_question(runtime):
    result = runtime.invoke("socratic-question-planner", {"case": CASE})
    assert len(result.outputs["next_question"]) == 1


def test_gospel_bridge_requires_consent(runtime):
    no_consent = {**CASE, "consent_scope": {**CASE["consent_scope"], "allow_gospel_bridge": False}}
    result = runtime.invoke("gospel-bridge-builder", {"case": no_consent})
    assert result.failure_code == "USER_CONSENT_REQUIRED"


def test_gospel_bridge_is_christ_centred(runtime):
    result = runtime.invoke("gospel-bridge-builder", {"case": CASE})
    assert "基督" in result.outputs["gospel_bridge"]["christ_person_and_work"]


def test_report_has_limitations_and_affirmations(runtime):
    result = runtime.invoke("discernment-report-composer", {"case": CASE})
    assert result.outputs["report"]["limitations"]
    assert result.outputs["report"]["affirmations"]


def test_safety_guardian_flags_scrupulosity(runtime):
    result = runtime.invoke("pastoral-safety-guardian", {"case": SCRUPULOSITY})
    assert "religious_scrupulosity" in result.outputs["blocked_patterns"]
    assert result.outputs["human_review_required"]


def test_safety_guardian_allows_ordinary_faith_language(runtime):
    calm = {**CASE, "subject_type": "self_reflection", "raw_input": "我最近读罗马书，对恩典有新理解，很感恩。"}
    result = runtime.invoke("pastoral-safety-guardian", {"case": calm})
    assert result.outputs["risk_level"] == "none"


def test_trace_packager_reports_missing_skills(runtime):
    result = runtime.invoke("trace-review-packager", {"case_id": "c1", "trace_records": []})
    assert result.outputs["production_ready"] is False
    assert result.outputs["trace_bundle"]["missing_skills"]


# --- batch 03/04/05/06 ----------------------------------------------------

def test_viral_case_normalizer(runtime):
    result = runtime.invoke("viral-case-normalizer", {"case": CASE})
    assert result.ok
    assert result.outputs["virality_case"]["raw_input"]


def test_public_figure_evidence_profiler_marks_public_only(runtime):
    result = runtime.invoke("public-figure-evidence-profiler", {"case": CASE})
    assert result.outputs["public_material_only"] is True


def test_hypothesis_builder_requires_pack_id(runtime):
    assert runtime.invoke("hypothesis-builder", {}).failure_code == "MISSING_REQUIRED_INPUT"


def test_hypothesis_builder_returns_created_good(runtime):
    result = runtime.invoke("hypothesis-builder", {"hypothesis_pack_id": "spiritual_pride"})
    assert result.outputs["hypothesis"]["created_good"]


def test_alternative_explanation_generator(runtime):
    result = runtime.invoke(
        "alternative-explanation-generator", {"hypothesis_pack_id": "spiritual_pride"}
    )
    assert result.outputs["alternative_explanations"]


def test_counter_evidence_planner_demands_disconfirmation(runtime):
    result = runtime.invoke("counter-evidence-planner", {"hypothesis_pack_id": "epistemic_pride"})
    assert result.outputs["disconfirmation_required"] is True


def test_one_question_enforcer_trims_to_one(runtime):
    result = runtime.invoke(
        "one-question-at-a-time-enforcer", {"text": "你怎么想？还有呢？第三个问题是什么？"}
    )
    assert result.outputs["max_questions_per_turn"] == 1


def test_gospel_consent_gate_blocks_without_consent(runtime):
    result = runtime.invoke(
        "gospel-consent-gate", {"gospel_consent": "declined", "faith_context": "seeker"}
    )
    assert result.outputs["may_enter_gospel_layer"] is False


def test_question_tree_engine_lists_stages(runtime):
    result = runtime.invoke("socratic-question-tree-engine", {})
    assert result.outputs["available_stages"]


def test_law_gospel_balance_reduces_pressure(runtime):
    result = runtime.invoke("law-gospel-balance-controller", {"sensitivity": "mental_health"})
    assert result.outputs["law_pressure"] == "reduced"


def test_doctrine_bound_skill_returns_tier(runtime):
    result = runtime.invoke("justification-by-faith-clarifier", {})
    assert result.outputs["doctrine_pack"]["tier"]


def test_denominational_governor_lists_tiers(runtime):
    result = runtime.invoke("denominational-difference-governor", {})
    assert len(result.outputs["doctrine_tiers"]) == 10


# --- batch 07/08/09/10 ----------------------------------------------------

def test_relapse_detector_rejects_unknown_state(runtime):
    result = runtime.invoke("relapse-cycle-detector", {"current": "nope", "target": "nope2"})
    assert result.failure_code == "MODEL_OUTPUT_INVALID"


def test_escalation_state_machine_requires_states(runtime):
    assert runtime.invoke("escalation-state-machine", {}).failure_code == "MISSING_REQUIRED_INPUT"


def test_bible_reference_parser_extracts_reference(runtime):
    result = runtime.invoke("bible-reference-parser", {"text": "参见 罗马书 8:1 与 以弗所书 2:8-9"})
    assert result.outputs["reference_count"] == 2


def test_bible_reference_parser_reports_no_reference(runtime):
    result = runtime.invoke("bible-reference-parser", {"text": "没有经文引用"})
    assert result.failure_code == "INSUFFICIENT_EVIDENCE"


def test_rights_policy_enforcer_rejects_unknown_status(runtime):
    result = runtime.invoke("rights-and-license-policy-enforcer", {"rights_status": "made_up"})
    assert result.failure_code == "MODEL_OUTPUT_INVALID"


def test_manifest_validator_sees_ten_manifests(runtime):
    result = runtime.invoke("batch-manifest-dependency-validator", {})
    assert result.outputs["manifest_count"] == 10
    assert result.outputs["valid"] is True


def test_certification_registry_loader_counts_controls(runtime):
    result = runtime.invoke("certification-pack-registry-loader", {})
    assert result.outputs["control_count"] == 58


def test_critical_blocker_engine_blocks_on_c4(runtime):
    findings = [
        {"finding_id": "f1", "control_id": "c1", "severity": "C4", "title": "x", "status": "open"}
    ]
    result = runtime.invoke("critical-blocker-engine", {"findings": findings})
    assert result.outputs["blockers"]["blocked"] is True


def test_critical_blocker_engine_passes_clean(runtime):
    result = runtime.invoke("critical-blocker-engine", {"findings": []})
    assert result.outputs["blockers"]["blocked"] is False


def test_recertification_scheduler_returns_domains(runtime):
    result = runtime.invoke("continuous-recertification-scheduler", {"trigger_type": "model_change"})
    assert isinstance(result.outputs["required_domains"], list)


def test_release_certificate_requires_rollback_target(runtime):
    result = runtime.invoke(
        "release-certificate-issuer",
        {"certificate_id": "cert-1", "release_id": "r-1", "expires_at": "2027-01-01T00:00:00Z"},
    )
    assert result.failure_code == "MISSING_REQUIRED_INPUT"


def test_release_certificate_is_signed_and_dated(runtime):
    result = runtime.invoke(
        "release-certificate-issuer",
        {
            "certificate_id": "cert-1",
            "release_id": "r-1",
            "expires_at": "2027-01-01T00:00:00Z",
            "rollback_target": "v0.9.0",
            "status": "APPROVED_FOR_PILOT",
            "recertification_triggers": ["model_change"],
            "signatories": [{"role": "release_board", "name": "elder"}],
        },
    )
    assert result.outputs["certificate"]["signature_hash"]
    assert result.outputs["certificate"]["expires_at"]


def test_certificate_revocation_records_reasons(runtime):
    result = runtime.invoke(
        "certificate-revocation-manager",
        {"certificate_id": "cert-1", "reason_codes": ["evidence_expired"], "actions": ["disable"]},
    )
    assert result.outputs["revocation"]["reason_codes"] == ["evidence_expired"]


def test_evidence_archive_is_hashed(runtime):
    result = runtime.invoke("release-evidence-archive-and-audit", {"evidence": []})
    assert result.outputs["archive_hash"]
    assert result.outputs["immutable"] is True
