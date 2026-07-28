from __future__ import annotations

from pathlib import Path

import pytest

from production_governance.emd_assurance_profiles import (
    ASSURANCE_PROFILES,
    CHECKLIST_ITEMS,
    CHECKLIST_PRIORITIES,
    UNCHANGED_GATES,
    describe_profiles,
    fairness_thresholds,
    generate_checklist,
    profile_diff,
    psychometric_thresholds,
    required_signoffs,
    resolve_profile,
)
from production_governance.emd_certification import (
    RELEASE_GATES,
    CertificationDossier,
    audit_fairness,
    certify_release,
    govern_psychometric_evidence,
)


pytestmark = pytest.mark.no_db
ROOT = Path(__file__).resolve().parents[2]


# ── 配置档本身 ───────────────────────────────────────────────────────────────

def test_pilot_relaxes_only_psychometric_and_fairness():
    diff = profile_diff()
    gates = {item["gate"] for item in diff["relaxed"]}
    assert gates <= {"G1_PSYCHOMETRIC", "G3_FAIRNESS"}
    assert set(diff["unchanged_gates"]) == set(UNCHANGED_GATES)


def test_safety_privacy_and_security_gates_are_identical_in_both_profiles():
    for gate in ("G0_INTENDED_USE", "G4_DOMAIN_SAFETY", "G5_PRIVACY", "G6_LLM_SECURITY"):
        assert gate in UNCHANGED_GATES
    # 两档配置里没有任何一项设置以这些闸门命名，说明它们不可被配置放宽
    for profile in ASSURANCE_PROFILES.values():
        assert "domain_safety" not in profile["psychometric"]
        assert "privacy" not in profile["fairness"]


def test_pilot_ceiling_is_restricted_pilot():
    assert resolve_profile("PILOT")["max_certifiable_level"] == "RESTRICTED_PILOT"
    assert resolve_profile("PRODUCTION")["max_certifiable_level"] == "COMMUNITY_RESTRICTED"


def test_pilot_forbids_sharing_and_group_features():
    pilot = resolve_profile("PILOT")
    assert pilot["sharing_allowed"] is False
    assert pilot["group_features_allowed"] is False
    assert "exploratory" in pilot["required_labels"]


def test_pilot_thresholds_are_realistic_but_not_zero():
    thresholds = psychometric_thresholds("PILOT")
    assert thresholds["minimum_pilot_sample_per_primary_locale"] == 20
    assert thresholds["minimum_cognitive_interviews_per_locale"] == 5
    assert thresholds["open_response_inter_rater_default"] >= 0.70
    assert fairness_thresholds("PILOT")["minimum_group_sample"] == 5
    assert fairness_thresholds("PILOT")["accessibility_required"] is True


def test_pilot_still_requires_privacy_domain_safety_and_independent_review():
    roles = required_signoffs("PILOT")
    assert {"privacy", "domain_safety", "independent_reviewer"} <= set(roles)
    assert len(roles) < len(required_signoffs("PRODUCTION"))


def test_unknown_profile_is_rejected():
    with pytest.raises(ValueError):
        resolve_profile("WHATEVER")


# ── 阈值真的被引擎使用 ───────────────────────────────────────────────────────

SMALL_STUDY = dict(
    instrument_version="emd_v1",
    interpretation_claims=["私人探索性画像"],
    content_expert_agreement=0.85,
    inter_rater_agreement=0.72,
    pilot_sample_per_locale={"zh-CN": 25},
    cognitive_interviews_per_locale={"zh-CN": 6},
    retest_reliability=0.65,
)


def test_a_small_pilot_study_reaches_pm3_only_under_the_pilot_profile():
    pilot = govern_psychometric_evidence(**SMALL_STUDY, profile="PILOT")
    production = govern_psychometric_evidence(**SMALL_STUDY, profile="PRODUCTION")
    assert pilot["evidence_level"] == "PM3_PILOT_CALIBRATED"
    assert production["evidence_level"] == "PM1_EXPLORATORY_CONTENT"


def test_pilot_profile_caps_the_evidence_level_at_pm3():
    strong = govern_psychometric_evidence(
        instrument_version="emd_v1", interpretation_claims=[],
        content_expert_agreement=0.95, inter_rater_agreement=0.9,
        pilot_sample_per_locale={"zh-CN": 500}, cognitive_interviews_per_locale={"zh-CN": 40},
        retest_reliability=0.9, responsiveness_days=200, profile="PILOT",
    )
    assert strong["evidence_level"] == "PM3_PILOT_CALIBRATED"
    assert strong["release_recommendation"] == "RESTRICTED_PILOT"
    assert any("上限" in gap for gap in strong["evidence_gaps"])


def test_high_stakes_uses_stay_forbidden_in_the_pilot_profile_too():
    result = govern_psychometric_evidence(**SMALL_STUDY, profile="PILOT")
    assert "精神疾病诊断" in result["forbidden_interpretations"]
    assert "教会资格与纪律决定" in result["forbidden_interpretations"]


def test_fairness_minimum_group_sample_follows_the_profile():
    pilot = audit_fairness(release_id="r", group_samples={"zh-CN": 8}, profile="PILOT")
    production = audit_fairness(release_id="r", group_samples={"zh-CN": 8}, profile="PRODUCTION")
    assert pilot["insufficient_sample_groups"] == []
    assert production["insufficient_sample_groups"] == ["zh-CN"]


def test_fairness_hard_blocks_still_apply_in_the_pilot_profile():
    result = audit_fairness(
        release_id="r", group_samples={"zh-CN": 8},
        hard_block_codes=["CRISIS_MISS_BY_LOCALE"], profile="PILOT",
    )
    assert result["status"] == "BLOCKED"
    assert result["release_allowed"] is False


def test_accessibility_failure_still_blocks_in_the_pilot_profile():
    result = audit_fairness(
        release_id="r", group_samples={"zh-CN": 8}, accessibility_passed=False, profile="PILOT",
    )
    assert result["status"] == "BLOCKED"


# ── 认证受配置档约束 ─────────────────────────────────────────────────────────

def pilot_dossier(**updates) -> CertificationDossier:
    values = {
        "release_id": "release_0.1.0",
        "intended_use_tier": "IU_2_INDIVIDUAL_TRAINING",
        "requested_release_level": "PRIVATE_PRODUCTION",
        "supported_locales": ["zh-CN"],
        "gate_results": {code: "PASS" for code, _, _ in RELEASE_GATES},
        "obtained_signoffs": list(required_signoffs("PILOT")),
    }
    values.update(updates)
    return CertificationDossier(**values)


def test_pilot_certificate_is_capped_at_restricted_pilot():
    result = certify_release(pilot_dossier(), profile="PILOT")
    assert result["decision"] == "GO"
    assert result["certified_level"] == "RESTRICTED_PILOT"
    assert result["sharing_allowed"] is False
    assert "exploratory" in result["required_labels"]


def test_pilot_signoff_set_is_sufficient_for_pilot_but_not_for_production():
    assert certify_release(pilot_dossier(), profile="PILOT")["decision"] == "GO"
    production = certify_release(pilot_dossier(), profile="PRODUCTION")
    assert production["decision"] == "NO_GO"
    assert "psychometric" in production["missing_signoffs"]


def test_a_blocking_gate_failure_still_blocks_in_the_pilot_profile():
    result = certify_release(
        pilot_dossier(gate_results={
            **{code: "PASS" for code, _, _ in RELEASE_GATES}, "G5_PRIVACY": "BLOCKED",
        }),
        profile="PILOT",
    )
    assert result["decision"] == "NO_GO"
    assert "G5_PRIVACY" in result["failing_blocking_gates"]


def test_forbidden_use_is_still_never_certifiable_in_the_pilot_profile():
    result = certify_release(pilot_dossier(intended_use_tier="IU_X_FORBIDDEN"), profile="PILOT")
    assert result["decision"] == "NO_GO"


# ── 清单 ─────────────────────────────────────────────────────────────────────

def test_checklist_covers_three_priorities():
    checklist = generate_checklist(profile="PILOT")
    assert set(checklist["counts"]) == set(CHECKLIST_PRIORITIES)


def test_without_auto_verification_the_blocking_items_are_outstanding():
    """The checklist must not treat an item as done merely because it is listed."""
    checklist = generate_checklist(profile="PILOT", auto_verify=False)
    assert checklist["ready_for_pilot_use"] is False
    assert "SAFETY_E2E" in checklist["outstanding_blocking_items"]


def test_auto_verification_finds_the_wired_up_evidence():
    checklist = generate_checklist(profile="PILOT")
    assert set(checklist["auto_verified_items"]) == {
        "SAFETY_E2E", "DELETION_PROPAGATION", "MODEL_TRAINING_OPTOUT", "UI_LABELS", "SHARING_OFF",
        # 红队的确定性层已自动化；模型层仍在 still_needs_humans 里
        "RED_TEAM_LIGHT",
    }
    assert checklist["ready_for_pilot_use"] is True
    assert checklist["outstanding_blocking_items"] == []


def test_auto_verification_only_claims_structural_evidence():
    """It proves the wiring exists; deciding the suite passed is CI's job, not the checklist's."""
    checklist = generate_checklist(profile="PILOT")
    assert "CI" in checklist["auto_verification_note"]
    for item in checklist["items"]:
        if item["auto_verified"]:
            assert item["missing_evidence"] == []


def test_completing_the_must_do_items_marks_the_pilot_ready():
    must_do = [item["id"] for item in CHECKLIST_ITEMS if item["priority"] == "MUST_DO_NOW"]
    checklist = generate_checklist(profile="PILOT", completed_ids=must_do)
    assert checklist["ready_for_pilot_use"] is True
    assert checklist["outstanding_blocking_items"] == []


def test_public_launch_items_are_out_of_scope_for_a_pilot():
    checklist = generate_checklist(profile="PILOT")
    statuses = {item["id"]: item["status"] for item in checklist["items"]}
    assert statuses["PILOT_SAMPLE"] == "LATER"
    assert statuses["FULL_SIGNOFFS"] == "LATER"
    production = generate_checklist(profile="PRODUCTION")
    production_statuses = {item["id"]: item["status"] for item in production["items"]}
    assert production_statuses["PILOT_SAMPLE"] == "TODO"


def test_every_checklist_item_is_verifiable():
    for item in CHECKLIST_ITEMS:
        assert item["verification"]
        assert item["gate"]
        assert item["priority"] in CHECKLIST_PRIORITIES


def test_the_safety_end_to_end_item_points_at_a_real_test_file():
    item = next(entry for entry in CHECKLIST_ITEMS if entry["id"] == "SAFETY_E2E")
    assert item["automatable"] is True
    assert (ROOT / "backend/tests/test_emd_safety_end_to_end.py").exists()


def test_checklist_reminds_that_relaxed_thresholds_are_not_relaxed_conclusions():
    checklist = generate_checklist(profile="PILOT")
    assert "RESTRICTED_PILOT" in checklist["reminder"]
    assert "exploratory" in checklist["reminder"]


# ── 描述与路由 ───────────────────────────────────────────────────────────────

def test_describe_profiles_states_why_four_gates_never_relax():
    described = describe_profiles()
    assert set(described["profiles"]) == {"PILOT", "PRODUCTION"}
    assert "与规模无关" in described["unchanged_gate_reason"]


def test_router_exposes_the_profile_and_checklist_endpoints():
    from routers.production_governance import router

    paths = {route.path for route in router.routes}
    assert "/api/v1/assurance/emd/profiles" in paths
    assert "/api/v1/assurance/emd/checklist" in paths


def test_pilot_checklist_document_exists():
    assert (ROOT / "EMD_OS_PILOT_CHECKLIST.md").exists()


def test_items_that_need_people_are_never_auto_verified():
    """工具就绪不等于事情做完——有 evidence 模块也不能替人打勾。"""
    checklist = generate_checklist(profile="PILOT")
    by_id = {item["id"]: item for item in checklist["items"]}
    for item_id in ("COGNITIVE_INTERVIEWS", "INTER_RATER", "PRIVACY_ASSESSMENT", "INCIDENT_DRILL"):
        item = by_id[item_id]
        assert item["auto_verified"] is False, f"{item_id} 不该自动通过"
        assert item["still_needs_humans"], f"{item_id} 必须写明还需要人做什么"


def test_every_remaining_human_item_names_the_human_work():
    for item in CHECKLIST_ITEMS:
        if item.get("automatable"):
            continue
        assert item.get("still_needs_humans"), item["id"]
