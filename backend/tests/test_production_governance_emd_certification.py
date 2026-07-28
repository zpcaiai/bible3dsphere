from __future__ import annotations

from pathlib import Path

import pytest

from production_governance.emd_certification import (
    BLOCKING_GATES,
    CERTIFICATE_STATUSES,
    DOMAIN_HARM_CATEGORIES,
    FORBIDDEN_USES,
    INTENDED_USE_TIERS,
    RELEASE_GATES,
    REQUIRED_REVIEW_ROLES,
    REQUIRED_SIGNOFFS,
    ZERO_TOLERANCE_HARMS,
    CertificationDossier,
    assess_privacy,
    audit_data_quality,
    audit_fairness,
    certify_release,
    classify_intended_use,
    control_change,
    describe_certification_engine,
    govern_psychometric_evidence,
    orchestrate_red_team,
    respond_to_incident,
)


pytestmark = pytest.mark.no_db
ROOT = Path(__file__).resolve().parents[2]
ALL_DELETION_TARGETS = [
    "RELATIONAL_DB", "SEARCH_INDEX", "VECTOR_DB", "CACHE", "REPORTS", "FORMATION_TWIN",
    "TRAINING_CANDIDATES", "EXPORT_BUNDLES", "SHARED_SUMMARIES", "ANALYTICS_METRICS", "BACKUPS",
]


# ── EM-78 intended use ───────────────────────────────────────────────────────

def test_pastoral_sharing_lands_in_iu3_with_a_capped_release_level():
    result = classify_intended_use(
        release_id="release_1.0.0",
        requested_features=["private_emotional_assessment", "formation_twin"],
        target_users=["adult_individual_users"],
        deployment_regions=["CN", "EU"],
        data_categories=["religious_belief", "emotional_events"],
        sharing_modes=["user_authorized_pastoral_summary"],
    )
    assert result["intended_use_tier"] == "IU_3_HUMAN_SUPPORTED"
    assert result["maximum_certifiable_level"] == "HUMAN_SUPPORTED_PRODUCTION"
    assert "不得用于教会资格或纪律决定" in result["hard_restrictions"]


def test_forbidden_uses_cannot_be_fixed_with_a_disclaimer():
    result = classify_intended_use(
        release_id="release_1.0.0", requested_features=["ranking"], target_users=["adults"],
        deployment_regions=["CN"], data_categories=["religious_belief"],
        stated_purposes=["用于小组长资格判断"],
    )
    assert result["status"] == "BLOCKED"
    assert result["intended_use_tier"] == "IU_X_FORBIDDEN"
    assert "免责声明" in result["disclaimer_cannot_fix"]


def test_minor_users_require_separate_certification():
    result = classify_intended_use(
        release_id="r", requested_features=["assessment"], target_users=["minor_users"],
        deployment_regions=["CN"], data_categories=["emotional_events"],
    )
    assert "MINOR_USERS_REQUIRE_SEPARATE_CERTIFICATION" in result["hard_blocks"]


def test_high_impact_actions_need_human_confirmation():
    result = classify_intended_use(
        release_id="r", requested_features=["assessment"], target_users=["adults"],
        deployment_regions=["CN"], data_categories=["emotional_events"],
        external_actions=["auto_send_message"],
    )
    assert "HIGH_IMPACT_ACTION_WITHOUT_CONFIRMATION" in result["hard_blocks"]


def test_all_documented_forbidden_uses_are_listed():
    result = classify_intended_use(
        release_id="r", requested_features=["assessment"], target_users=["adults"],
        deployment_regions=["CN"], data_categories=["emotional_events"],
    )
    assert set(FORBIDDEN_USES) <= set(result["prohibited_uses"])
    assert len(INTENDED_USE_TIERS) == 6


# ── EM-79 psychometrics ──────────────────────────────────────────────────────

def test_evidence_level_climbs_only_with_the_documented_evidence():
    weak = govern_psychometric_evidence(
        instrument_version="emd_v1", interpretation_claims=["私人画像"],
        content_expert_agreement=0.85,
    )
    assert weak["evidence_level"] in {"PM1_EXPLORATORY_CONTENT", "PM2_CONTENT_SUPPORTED"}
    strong = govern_psychometric_evidence(
        instrument_version="emd_v1", interpretation_claims=["纵向趋势"],
        content_expert_agreement=0.85, inter_rater_agreement=0.8,
        pilot_sample_per_locale={"zh-CN": 320}, cognitive_interviews_per_locale={"zh-CN": 16},
        retest_reliability=0.75, responsiveness_days=120,
    )
    assert strong["evidence_level"] == "PM5_LONGITUDINAL_RESPONSIVE"


def test_high_stakes_uses_stay_forbidden_at_every_level():
    result = govern_psychometric_evidence(
        instrument_version="emd_v1", interpretation_claims=["x"],
        content_expert_agreement=0.9, inter_rater_agreement=0.9,
        pilot_sample_per_locale={"zh-CN": 500}, cognitive_interviews_per_locale={"zh-CN": 30},
        retest_reliability=0.85, responsiveness_days=200,
    )
    assert "精神疾病诊断" in result["forbidden_interpretations"]
    assert "教会资格与纪律决定" in result["forbidden_interpretations"]
    assert "PMX" in result["permanent_restriction"] or "禁止" in result["permanent_restriction"]


def test_self_report_only_cannot_claim_real_behaviour_validation():
    result = govern_psychometric_evidence(
        instrument_version="emd_v1", interpretation_claims=["x"], self_report_only=True,
    )
    assert any("不得宣称现实行为能力已被验证" in item for item in result["restricted_interpretations"])


def test_thresholds_are_marked_as_pilot_defaults():
    result = govern_psychometric_evidence(instrument_version="emd_v1", interpretation_claims=[])
    assert result["thresholds_are_pilot_defaults"] is True


# ── EM-80 data quality ───────────────────────────────────────────────────────

def test_a_single_critical_error_blocks_release():
    result = audit_data_quality(
        release_id="r",
        findings=[{"type": "CROSS_TENANT_CONTAMINATION", "domain": "PROVENANCE", "count": 1}],
    )
    assert result["status"] == "BLOCKED"
    assert result["release_allowed"] is False
    assert result["no_single_average_score"] is True


def test_duplicate_rate_and_double_scoring_gates_are_enforced():
    result = audit_data_quality(
        release_id="r", findings=[], duplicate_real_event_rate=0.02, open_response_double_scored=0.05,
    )
    assert "DUPLICATE_REAL_EVENT_RATE_ABOVE_GATE" in result["gate_failures"]
    assert "DOUBLE_SCORING_BELOW_GATE" in result["gate_failures"]


def test_clean_audit_passes_with_the_full_matrix():
    result = audit_data_quality(
        release_id="r", findings=[], duplicate_real_event_rate=0.0,
        open_response_double_scored=0.25, critical_field_validity=1.0,
    )
    assert result["status"] == "PASS"
    assert len(result["quality_matrix"]) == 8


# ── EM-81 fairness ───────────────────────────────────────────────────────────

def test_crisis_miss_by_locale_hard_blocks_the_release():
    result = audit_fairness(
        release_id="r", group_samples={"zh-CN": 400}, hard_block_codes=["CRISIS_MISS_BY_LOCALE"],
    )
    assert result["status"] == "BLOCKED"
    assert result["release_allowed"] is False


def test_insufficient_samples_never_claim_fairness():
    result = audit_fairness(release_id="r", group_samples={"zh-TW": 5})
    assert "zh-TW" in result["insufficient_sample_groups"]
    assert "不能宣称公平" in result["insufficient_sample_note"]


def test_fairness_can_restrict_one_locale_instead_of_failing_globally():
    result = audit_fairness(
        release_id="r", group_samples={"zh-CN": 400, "zh-TW": 200},
        measurement_findings=[{"group": "zh-TW", "issue": "D5 题目语义偏差", "severity": "medium"}],
    )
    assert result["status"] == "PASS_WITH_RESTRICTIONS"
    assert result["partial_release_allowed"] is True
    assert result["blocked_scope"]


def test_accessibility_failure_blocks_the_flow():
    result = audit_fairness(release_id="r", group_samples={"zh-CN": 400}, accessibility_passed=False)
    assert result["status"] == "BLOCKED"


# ── EM-82 domain safety ──────────────────────────────────────────────────────

def full_case_suite(passed: bool = True) -> list[dict]:
    return [
        {"case_id": f"c_{category}", "harm_category": category, "passed": passed}
        for category in DOMAIN_HARM_CATEGORIES
    ]


def test_one_zero_tolerance_failure_blocks_regardless_of_overall_accuracy():
    cases = full_case_suite()
    cases.append({"case_id": "unsafe_018", "harm_category": "UNSAFE_VULNERABILITY", "passed": False})
    result = certify_domain_safety_helper(cases)
    assert result["status"] == "BLOCKED"
    assert result["average_cannot_cover_critical"] is True
    assert result["case_summary"]["critical_failures"] == 1


def certify_domain_safety_helper(cases, roles=None, conflicts=None):
    from production_governance.emd_certification import certify_domain_safety

    return certify_domain_safety(
        release_id="r", case_results=cases,
        human_review_roles=list(roles or REQUIRED_REVIEW_ROLES),
        conflicted_reviewers=conflicts,
    )


def test_every_harm_category_must_be_covered():
    partial = [{"case_id": "c1", "harm_category": "CRISIS_UNDERRESPONSE", "passed": True}]
    result = certify_domain_safety_helper(partial)
    assert result["status"] == "BLOCKED"
    assert result["uncovered_harm_categories"]


def test_human_review_panel_roles_are_required():
    result = certify_domain_safety_helper(full_case_suite(), roles=["product_owner"])
    assert "licensed_mental_health_professional" in result["missing_review_roles"]
    assert result["status"] == "BLOCKED"


def test_conflicted_reviewers_block_certification():
    result = certify_domain_safety_helper(full_case_suite(), conflicts=["accused_church_leader"])
    assert result["status"] == "BLOCKED"
    assert result["conflicted_reviewers"] == ["accused_church_leader"]


def test_clean_suite_with_full_panel_passes():
    result = certify_domain_safety_helper(full_case_suite())
    assert result["status"] == "PASS"
    assert set(ZERO_TOLERANCE_HARMS) <= set(DOMAIN_HARM_CATEGORIES)


# ── EM-83 privacy ────────────────────────────────────────────────────────────

def privacy(**updates):
    values = {
        "release_id": "r",
        "data_inventory_complete": True,
        "consent_matrix": {"twin": ["CONSENT_LONGITUDINAL_TWIN"]},
        "retention_policies": {"raw_narrative": "processed_then_deleted"},
        "deletion_targets_covered": ALL_DELETION_TARGETS,
        "rights_supported": ["access", "correction", "deletion", "consent_withdrawal", "share_revocation"],
    }
    values.update(updates)
    return assess_privacy(**values)


def test_bundled_model_improvement_consent_is_blocked():
    result = privacy(consent_matrix={"twin": ["CONSENT_LONGITUDINAL_TWIN", "CONSENT_MODEL_IMPROVEMENT"]})
    assert "CONSENT_BUNDLED_WITH_MODEL_IMPROVEMENT" in result["blocks"]


def test_deletion_must_propagate_to_every_target():
    result = privacy(deletion_targets_covered=["RELATIONAL_DB"])
    assert "DELETION_DOES_NOT_PROPAGATE" in result["blocks"]
    assert "VECTOR_DB" in result["missing_deletion_targets"]


def test_default_on_training_and_role_based_pastor_access_are_blocked():
    assert "MODEL_TRAINING_DEFAULT_ON" in privacy(model_training_default_on=True)["blocks"]
    assert "ROLE_BASED_PASTOR_ACCESS" in privacy(role_based_pastor_access=True)["blocks"]


def test_missing_user_rights_block_the_gate():
    result = privacy(rights_supported=["access"])
    assert "USER_RIGHTS_INCOMPLETE" in result["blocks"]
    assert "deletion" in result["missing_rights"]


def test_cross_border_flows_restrict_rather_than_silently_pass():
    result = privacy(cross_border_flows=["CN_user_to_global_model_endpoint"])
    assert result["status"] == "PASS_WITH_RESTRICTIONS"
    assert result["cross_border_restriction"]


def test_unknown_consent_kind_is_rejected():
    with pytest.raises(ValueError):
        privacy(consent_matrix={"twin": ["CONSENT_EVERYTHING"]})


# ── EM-84 security red team ──────────────────────────────────────────────────

def full_attack_suite(succeeded: bool = False) -> list[dict]:
    from production_governance.emd_certification import ATTACK_SURFACES

    return [
        {"surface": surface, "succeeded": succeeded, "severity": "HIGH"}
        for surface in ATTACK_SURFACES
    ]


def test_zero_tolerance_failures_block_the_release():
    attacks = full_attack_suite()
    attacks.append({
        "surface": "INDIRECT_PROMPT_INJECTION", "succeeded": True, "severity": "CRITICAL",
        "zero_tolerance_check": "unauthorized_send",
    })
    result = orchestrate_red_team(release_id="r", attack_results=attacks)
    assert result["status"] == "BLOCKED"
    assert result["zero_tolerance_results"]["unauthorized_send"] == "FAIL"


def test_every_attack_surface_must_be_exercised():
    result = orchestrate_red_team(release_id="r", attack_results=[{"surface": "TOOL_MISUSE", "succeeded": False}])
    assert result["status"] == "BLOCKED"
    assert result["uncovered_attack_surfaces"]


def test_autonomous_high_impact_tools_are_never_allowed():
    result = orchestrate_red_team(
        release_id="r", attack_results=full_attack_suite(),
        tool_permission_manifest={"delete_profile": "T4_DESTRUCTIVE_OR_HIGH_IMPACT"},
    )
    assert result["zero_tolerance_results"]["high_impact_tool_without_confirmation"] == "FAIL"
    assert result["status"] == "BLOCKED"


def test_clean_red_team_passes_and_treats_content_as_data():
    result = orchestrate_red_team(release_id="r", attack_results=full_attack_suite())
    assert result["status"] == "PASS"
    assert result["user_content_is_data_not_instructions"] is True


# ── EM-85 change control ─────────────────────────────────────────────────────

def test_model_family_change_is_escalated_to_major():
    result = control_change(
        change_request_id="change_001", current_release="1.0.0", proposed_release="1.1.0",
        changes=[{"component": "base_model", "from": "model_a", "to": "model_b"}],
        requested_change_level="MINOR",
    )
    assert result["actual_change_level"] == "MAJOR"
    assert result["level_escalated"] is True
    assert result["invalidated_certificates"] == ["cert_1.0.0"]


def test_a_one_line_prompt_change_affecting_safety_routing_is_major():
    result = control_change(
        change_request_id="c", current_release="1.0.0", proposed_release="1.0.1",
        changes=[{"component": "prompt", "affects_safety_routing": True}],
        requested_change_level="PATCH",
    )
    assert result["actual_change_level"] == "MAJOR"
    assert "full_domain_safety" in result["required_retests"]


def test_canary_policy_disables_external_sharing():
    result = control_change(
        change_request_id="c", current_release="1.0.0", proposed_release="1.0.1",
        changes=[{"component": "copy"}],
    )
    assert result["canary_policy"]["external_sharing_disabled"] is True
    assert result["canary_policy"]["private_use_only"] is True


# ── EM-86 release certification ──────────────────────────────────────────────

def dossier(**updates) -> CertificationDossier:
    values = {
        "release_id": "release_1.0.0",
        "intended_use_tier": "IU_3_HUMAN_SUPPORTED",
        "requested_release_level": "HUMAN_SUPPORTED_PRODUCTION",
        "supported_locales": ["zh-CN"],
        "gate_results": {code: "PASS" for code, _, _ in RELEASE_GATES},
        "obtained_signoffs": list(REQUIRED_SIGNOFFS),
    }
    values.update(updates)
    return CertificationDossier(**values)


def test_a_failing_blocking_gate_is_never_averaged_into_a_pass():
    result = certify_release(dossier(gate_results={
        **{code: "PASS" for code, _, _ in RELEASE_GATES}, "G4_DOMAIN_SAFETY": "BLOCKED",
    }))
    assert result["decision"] == "NO_GO"
    assert "G4_DOMAIN_SAFETY" in result["failing_blocking_gates"]
    assert result["average_cannot_cover_red_gate"] is True


def test_missing_independent_signoff_blocks_release():
    result = certify_release(dossier(obtained_signoffs=["product", "engineering"]))
    assert result["decision"] == "NO_GO"
    assert "independent_reviewer" in result["missing_signoffs"]


def test_release_level_is_capped_by_the_intended_use_tier():
    result = certify_release(dossier(
        intended_use_tier="IU_1_PRIVATE_REFLECTION", requested_release_level="COMMUNITY_RESTRICTED",
    ))
    assert result["certified_level"] == "PRIVATE_PRODUCTION"


def test_certificate_states_what_it_does_and_does_not_prove():
    result = certify_release(dossier())
    assert result["decision"] == "GO"
    assert result["external_certification_claims_allowed"] is False
    assert "ISO/IEC 42001 或 27001 外部认证" in result["certificate_does_not_prove"]
    assert result["expires_at"] > result["valid_from"]


def test_restricted_gates_downgrade_to_pass_with_restrictions():
    result = certify_release(dossier(gate_results={
        **{code: "PASS" for code, _, _ in RELEASE_GATES}, "G3_FAIRNESS": "PASS_WITH_RESTRICTIONS",
    }))
    assert result["decision"] == "PASS_WITH_RESTRICTIONS"
    assert "G3_FAIRNESS" in result["restricted_gates"]


def test_forbidden_use_tier_can_never_be_certified():
    result = certify_release(dossier(intended_use_tier="IU_X_FORBIDDEN"))
    assert result["decision"] == "NO_GO"
    assert result["certified_level"] is None


# ── EM-87 incidents ──────────────────────────────────────────────────────────

def test_consent_bypass_suspends_the_certificate_and_forces_recall():
    result = respond_to_incident(
        incident_id="incident_001", incident_type="CONSENT_BYPASS",
        affected_release="1.0.0", affected_users=12, affected_records=12,
    )
    assert result["severity"] == "SEV1_CRITICAL"
    assert result["certificate_action"] == "SUSPENDED"
    assert result["recall_plan"]["shared_links_to_disable"] == 12
    assert result["recertification_required"] is True


def test_cross_tenant_leak_triggers_the_global_kill_switch():
    result = respond_to_incident(
        incident_id="i", incident_type="CROSS_TENANT_LEAK", affected_release="1.0.0",
    )
    assert result["severity"] == "SEV0_CATASTROPHIC"
    assert "GLOBAL_KILL_SWITCH" in result["kill_switches"]
    assert result["certificate_action"] == "REVOKED"


def test_fixing_code_alone_cannot_close_an_incident():
    result = respond_to_incident(incident_id="i", incident_type="REPORT_DEFECT", affected_release="1.0.0")
    assert "必须召回派生证据与报告并重算" in result["code_fix_alone_insufficient"]
    assert result["new_regression_test_required"] is True


def test_unknown_incident_type_is_rejected():
    with pytest.raises(ValueError):
        respond_to_incident(incident_id="i", incident_type="SOMETHING", affected_release="1.0.0")


# ── module description and wiring ────────────────────────────────────────────

def test_module_is_merged_into_production_governance():
    described = describe_certification_engine()
    assert described["merged_into"].startswith("backend/production_governance")
    assert len(described["skills"]) == 10
    assert set(described["certificate_statuses"]) == set(CERTIFICATE_STATUSES)
    assert described["external_certification_claims_allowed"] is False
    assert described["initial_status"]["production_certificate"] == "NOT_ISSUED"


def test_blocking_gates_match_the_documented_matrix():
    assert len(RELEASE_GATES) == 10
    assert "G4_DOMAIN_SAFETY" in BLOCKING_GATES
    assert "G6_LLM_SECURITY" in BLOCKING_GATES
    assert "G1_PSYCHOMETRIC" not in BLOCKING_GATES


def test_router_exposes_the_assurance_surface():
    from routers.production_governance import router

    paths = {route.path for route in router.routes}
    for suffix in (
        "classify-use", "psychometric-review", "data-quality-audit", "fairness-audit",
        "domain-safety", "privacy-assessment", "security-redteam", "certify",
    ):
        assert f"/api/v1/assurance/emd/{suffix}" in paths
    assert "/api/v1/assurance/emd/changes" in paths
    assert "/api/v1/assurance/emd/incidents" in paths
    assert "/api/v1/assurance/emd/overview" in paths


def test_migration_file_exists_for_batch_ten():
    migration = ROOT / "backend/migrations/0232_production_governance_emd_certification.sql"
    rollback = ROOT / "backend/migrations/rollback/0232_production_governance_emd_certification_down.sql"
    assert migration.exists() and rollback.exists()
    sql = migration.read_text(encoding="utf-8")
    assert "production_emd_release_certificates" in sql
    assert "production_emd_incidents" in sql
