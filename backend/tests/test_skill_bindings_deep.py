"""Behaviour tests that drive the batch 06-10 bindings with real payloads."""

from __future__ import annotations

import pytest

from backend.discernment_platform.skill_runtime import get_runtime

pytestmark = pytest.mark.no_db


@pytest.fixture(scope="module")
def runtime():
    return get_runtime()


ACTOR = {
    "actor_id": "actor-1",
    "display_name": "张长老",
    "roles": ["pastor_elder"],
    "tenant_id": "tenant-a",
    "church_relationships": [{"case_id": "case-1", "relation": "pastor"}],
}

PASTORAL_CASE = {
    "case_id": "case-1",
    "subject_user_id": "user-9",
    "purpose": "pastoral_care",
    "sensitivity": "L2",
    "status": "open",
    "assigned_roles": ["pastor_elder"],
}

GRANT = {
    "grant_id": "grant-1",
    "subject_user_id": "user-9",
    "recipient_actor_id": "actor-1",
    "purpose": "pastoral_care",
    "allowed_categories": ["summary"],
    "expires_at": "2027-01-01T00:00:00Z",
}

EVENT = {
    "event_id": "ev-1",
    "user_id": "user-9",
    "occurred_at": "2026-07-01T10:00:00Z",
    "context": "团队会议",
    "trigger": "被同事当众否定",
    "automatic_interpretation": "我一定是不够好",
    "desire_or_fear": ["怕被看轻"],
    "emotion": ["羞愧"],
    "chosen_action": ["沉默离场"],
    "consent_to_tracking": True,
    "evidence_quality": "E2",
    "data_level": "L1",
}

SOURCE = {
    "source_id": "src-1",
    "title": "和合本圣经",
    "source_type": "scripture",
    "language": "zh",
    "rights_status": "public_domain",
    "version": "1919",
}


# --- batch 06 -------------------------------------------------------------

def test_gospel_path_report_builds_a_path(runtime):
    result = runtime.invoke(
        "gospel-path-report-and-eval-composer",
        {
            "case_id": "case-1",
            "case": {
                "title": "成功主义",
                "subject_type": "self_reflection",
                "raw_input": "我总觉得必须靠业绩证明自己才配被爱。",
                "user_goal": "想找到出路",
                "faith_context": "christian",
                "consent_scope": {"allow_spiritual_analysis": True, "allow_gospel_bridge": True},
            },
            "pride_hypotheses": [{"pattern_id": "achievement_justification"}],
            "desire_map": [{"functional_savior": "成就"}],
        },
    )
    assert result.ok, result.message
    assert result.outputs["gospel_path"]


def test_gospel_path_report_refuses_without_consent(runtime):
    result = runtime.invoke(
        "gospel-path-report-and-eval-composer",
        {
            "case": {
                "title": "x",
                "subject_type": "self_reflection",
                "raw_input": "我总觉得必须靠业绩证明自己。",
                "user_goal": "想找到出路",
                "consent_scope": {"allow_spiritual_analysis": True, "allow_gospel_bridge": False},
            }
        },
    )
    assert result.failure_code == "USER_CONSENT_REQUIRED"


def test_suffering_balancer_keeps_structural_factors(runtime):
    result = runtime.invoke(
        "suffering-structure-responsibility-balancer",
        {"raw_input": "我被裁员之后一直很难走出来，也遇到过霸凌。"},
    )
    assert set(result.outputs["structural_factors"]) >= {"裁员", "霸凌"}


def test_justification_boundary_flags_conflation(runtime):
    result = runtime.invoke(
        "justification-sanctification-boundary-guardian", {"text": "越圣洁越被神接纳"}
    )
    assert result.outputs["boundary_violation"] is True


# --- batch 05 -------------------------------------------------------------

def test_pause_manager_continues_on_neutral_answer(runtime):
    result = runtime.invoke("pause-repair-and-exit-manager", {"answer": "我再想想这个问题。"})
    assert result.outputs["action"] == "continue"
    assert result.outputs["exit_available"] is True


def test_dialogue_session_initializer(runtime):
    result = runtime.invoke(
        "dialogue-session-initializer",
        {"session_id": "s-1", "case_id": "c-1", "report": {}, "faith_context": "christian"},
    )
    assert result.ok, result.message
    assert result.outputs["session"]


# --- batch 07 -------------------------------------------------------------

def test_formation_event_ingestor(runtime):
    result = runtime.invoke("formation-event-ingestor", {"event": EVENT})
    assert result.ok, result.message
    assert result.outputs["ingested"]


def test_event_consent_router_blocks_unconsented_persistence(runtime):
    result = runtime.invoke(
        "event-consent-and-privacy-router", {"event": {**EVENT, "consent_to_tracking": False}}
    )
    assert result.outputs["may_persist"] is False


def test_formation_chain_builder(runtime):
    result = runtime.invoke("formation-chain-builder", {"event": EVENT})
    assert result.ok, result.message
    assert result.outputs["formation_chain"]


@pytest.mark.parametrize(
    "skill_id,days",
    [
        ("fourteen-day-activation-reviewer", 14),
        ("thirty-day-transfer-reviewer", 30),
        ("ninety-day-stability-reviewer", 90),
    ],
)
def test_window_reviewers(runtime, skill_id, days):
    result = runtime.invoke(skill_id, {"user_id": "user-9", "events": [EVENT]})
    assert result.ok, result.message
    assert result.outputs["window_days"] == days


def test_relapse_transition_is_governed(runtime):
    result = runtime.invoke(
        "relapse-cycle-detector", {"current": "STABLE", "target": "VULNERABLE"}
    )
    assert result.ok, result.message
    assert result.outputs["relapse_is_event_not_identity_loss"] is True


def test_relationship_repair_verifier(runtime):
    result = runtime.invoke(
        "relationship-repair-verifier",
        {
            "repair": {
                "repair_id": "rep-1",
                "relationship_id": "rel-1",
                "harm_named": True,
                "responsibility_taken": True,
                "excuse_free": True,
                "behavior_change": True,
                "boundary_respected": True,
                "status": "in_progress",
            }
        },
    )
    assert result.ok, result.message
    assert result.outputs["repair_verification"]


def test_identity_migration_evaluator(runtime):
    result = runtime.invoke(
        "gospel-identity-migration-evaluator",
        {
            "migration": {
                "migration_id": "mig-1",
                "old_identity_basis": ["业绩"],
                "gospel_identity_truth": ["在基督里被接纳"],
            }
        },
    )
    assert result.ok, result.message
    assert result.outputs["identity_migration"]


def test_formation_safety_report(runtime):
    result = runtime.invoke("formation-safety-governance-and-report", {"text": "最近压力很大"})
    assert result.ok, result.message
    assert result.outputs["safety"]


# --- batch 08 -------------------------------------------------------------

def test_actor_role_resolver_returns_permissions(runtime):
    result = runtime.invoke("actor-role-credential-resolver", {"actor": ACTOR})
    assert result.ok, result.message
    assert result.outputs["permissions"]
    assert result.outputs["prohibitions"]


def test_actor_role_resolver_rejects_unknown_role(runtime):
    result = runtime.invoke(
        "actor-role-credential-resolver", {"actor": {**ACTOR, "roles": ["archbishop_of_mars"]}}
    )
    assert result.failure_code == "INSUFFICIENT_EVIDENCE"


def test_rbac_policy_evaluator_returns_a_decision(runtime):
    result = runtime.invoke(
        "rbac-abac-policy-evaluator",
        {
            "actor": ACTOR,
            "pastoral_case": PASTORAL_CASE,
            "consent_grants": [GRANT],
            "purpose": "pastoral_care",
            "requested_level": "L1",
        },
    )
    assert result.ok, result.message
    assert result.outputs["access_decision"]


def test_rbac_policy_evaluator_requires_purpose(runtime):
    result = runtime.invoke(
        "rbac-abac-policy-evaluator", {"actor": ACTOR, "pastoral_case": PASTORAL_CASE}
    )
    assert result.failure_code == "MISSING_REQUIRED_INPUT"


def test_disclosure_builder_is_minimum_necessary(runtime):
    result = runtime.invoke(
        "minimum-necessary-disclosure-builder",
        {
            "pastoral_case": PASTORAL_CASE,
            "recipient_actor_id": "actor-1",
            "purpose": "pastoral_care",
            "expires_at": "2027-01-01T00:00:00Z",
            "requested_fields": ["summary", "raw_input"],
            "allowed_fields": ["summary"],
            "prohibited_fields": ["raw_input"],
        },
    )
    assert result.ok, result.message
    assert result.outputs["minimum_necessary"] is True


def test_meeting_prep_generator(runtime):
    result = runtime.invoke(
        "meeting-preparation-generator",
        {
            "pastoral_case": PASTORAL_CASE,
            "meeting_purpose": "月度门训会面",
            "priority_question": "这个月哪一次你最想重来？",
            "gospel_truth": "在基督里已被接纳",
            "action_option": "本周约一位弟兄同行",
        },
    )
    assert result.ok, result.message
    assert result.outputs["meeting_preparation"]


def test_escalation_transition_is_governed(runtime):
    result = runtime.invoke(
        "escalation-state-machine", {"current": "ROUTINE", "target": "REVIEW_NEEDED"}
    )
    assert result.ok, result.message
    assert isinstance(result.outputs["transition_allowed"], bool)


def test_conflict_detector_flags_relationship(runtime):
    result = runtime.invoke(
        "conflict-of-interest-detector", {"actor": ACTOR, "case_relationships": ["case-1"]}
    )
    assert result.ok, result.message
    assert result.outputs["conflict"]


def test_sensitive_case_triage(runtime):
    result = runtime.invoke("sensitive-case-triage", {"text": "我丈夫经常打我"})
    assert result.ok, result.message
    assert result.outputs["triage"]


def test_safeguarding_guardian_marks_external_duty(runtime):
    result = runtime.invoke("safeguarding-and-external-duty-guardian", {"text": "我丈夫经常打我"})
    assert result.ok, result.message
    assert "external_duty_may_apply" in result.outputs["safeguarding"]


# --- batch 09 -------------------------------------------------------------

def test_citation_verifier(runtime):
    result = runtime.invoke(
        "citation-provenance-verifier",
        {
            "citation": {
                "citation_id": "cite-1",
                "source_id": "src-1",
                "locator": "罗马书 8:1",
                "quote_text": "如今那些在基督耶稣里的就不定罪了",
            },
            "source": SOURCE,
        },
    )
    assert result.ok, result.message
    assert result.outputs["citation_verification"]


def test_rights_policy_public_domain_allows_quoting(runtime):
    result = runtime.invoke(
        "rights-and-license-policy-enforcer", {"rights_status": "public_domain"}
    )
    assert result.outputs["can_quote"] is True


def test_rights_policy_blocks_prohibited_embedding(runtime):
    result = runtime.invoke(
        "rights-and-license-policy-enforcer", {"rights_status": "prohibited_for_embedding"}
    )
    assert result.outputs["can_embed"] is False


def test_scripture_misuse_detector(runtime):
    result = runtime.invoke(
        "scripture-misuse-detector", {"text": "神告诉我你必须顺服我，否则你会被咒诅。"}
    )
    assert result.ok, result.message
    assert result.outputs["misuse"]


def test_evidence_graph_builder(runtime):
    result = runtime.invoke(
        "theology-evidence-graph-builder",
        {"query_id": "q-1", "sources": [SOURCE], "passages": [], "claims": [], "generated_statements": []},
    )
    assert result.ok, result.message
    assert result.outputs["evidence_graph"]


def test_doctrine_governor_requires_tier(runtime):
    assert runtime.invoke("doctrine-tier-consensus-governor", {}).failure_code == "MISSING_REQUIRED_INPUT"


def test_doctrine_governor_evaluates_tier(runtime):
    result = runtime.invoke(
        "doctrine-tier-consensus-governor",
        {"tier": "D1", "tradition_scope": ["reformed"], "consensus_level": "ecumenical"},
    )
    assert result.ok, result.message
    assert result.outputs["tier"] == "D1"


def test_rag_retriever_requires_query(runtime):
    result = runtime.invoke("auditable-rag-retriever-reranker", {"sources": [SOURCE]})
    assert result.failure_code == "MISSING_REQUIRED_INPUT"


def test_rag_retriever_filters_sources(runtime):
    result = runtime.invoke(
        "auditable-rag-retriever-reranker",
        {
            "sources": [SOURCE],
            "query": {
                "query_id": "q-1",
                "question": "罗马书 8:1 的意思",
                "intent": "exegesis",
                "allowed_rights": ["public_domain"],
                "required_source_types": ["scripture"],
            },
        },
    )
    assert result.ok, result.message
    assert result.outputs["auditable"] is True


def test_historical_theology_retriever(runtime):
    result = runtime.invoke("historical-theology-retriever", {})
    assert result.outputs["scope"]


def test_denominational_matrix_does_not_adjudicate(runtime):
    result = runtime.invoke("denominational-position-matrix-builder", {})
    assert "do not adjudicate" in result.outputs["adjudication_policy"]


# --- batch 10 -------------------------------------------------------------

def test_release_candidate_intake_binds_build(runtime):
    result = runtime.invoke(
        "release-candidate-intake",
        {
            "release_candidate": {
                "release_id": "r-1",
                "build_hash": "abc123",
                "batch_manifests": [],
                "model_versions": [],
                "policy_versions": [],
                "target_scope": "pilot",
            }
        },
    )
    assert result.ok, result.message
    assert result.outputs["build_bound"] is True


def test_production_gate_blocks_on_critical_finding(runtime):
    result = runtime.invoke(
        "production-gate-report-and-red-team",
        {
            "release_candidate": {
                "release_id": "r-1",
                "build_hash": "abc",
                "batch_manifests": [],
                "model_versions": [],
                "policy_versions": [],
                "target_scope": "production",
            },
            "domain_results": [],
            "findings": [
                {"finding_id": "f1", "control_id": "c1", "severity": "C4", "title": "x", "status": "open"}
            ],
            "release_board_signed": True,
            "rollback_ready": True,
            "recertification_enabled": True,
        },
    )
    assert result.outputs["status"] == "BLOCKED"


def test_evidence_completeness_validator_requires_controls(runtime):
    assert (
        runtime.invoke("evidence-completeness-validator", {}).failure_code
        == "MISSING_REQUIRED_INPUT"
    )


def test_evidence_completeness_validator_runs(runtime):
    result = runtime.invoke(
        "evidence-completeness-validator",
        {
            "controls": [
                {
                    "control_id": "c1",
                    "domain_id": "d1",
                    "requirement": "x",
                    "severity": "C2",
                    "automated": True,
                    "decision_rule": "must pass",
                }
            ],
            "evidence": [],
        },
    )
    assert result.ok, result.message
    assert result.outputs["evaluated"] == 1


def test_release_board_preserves_dissent(runtime):
    result = runtime.invoke(
        "release-board-workflow-manager",
        {"signatories": [{"role": "elder", "dissent": True, "note": "证据不足"}]},
    )
    assert result.outputs["signed"] is False
    assert result.outputs["dissent_preserved"]
