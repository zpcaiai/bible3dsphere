from __future__ import annotations

from pathlib import Path

import pytest

from discernment_platform import DialogueEngine, DiscernmentEngine, GospelPathEngine, get_registry
from discernment_platform.extended import CertificationService, FormationTwinService, TheologyEvidenceService
from discernment_platform.models import DiscernmentCaseCreate


pytestmark = pytest.mark.no_db
ROOT = Path(__file__).parents[1]


def make_case(**changes) -> DiscernmentCaseCreate:
    data = {
        "title": "成功与自我价值",
        "subject_type": "self_reflection",
        "raw_input": "只有不断成功和被看见，我才觉得自己有价值。我不能失败。",
        "user_goal": "分辨这个信念如何塑造我",
        "faith_context": "christian",
        "consent_scope": {
            "allow_spiritual_analysis": True,
            "allow_gospel_bridge": True,
            "allow_public_content_analysis": False,
            "allow_longitudinal_memory": False,
        },
    }
    data.update(changes)
    return DiscernmentCaseCreate(**data)


def test_all_batch_registries_load_exact_versioned_counts():
    catalog = get_registry().catalog()
    assert catalog["counts"] == {
        "domain_packs": 32,
        "hypothesis_packs": 9,
        "question_packs": 8,
        "doctrine_packs": 10,
        "formation_packs": 8,
        "role_packs": 8,
        "knowledge_packs": 12,
        "certification_packs": 12,
        "certification_controls": 58,
    }
    assert catalog["versions"] == {
        "batch01": "0.1.0", "batch02": "0.2.0", "batch03": "0.3.0",
        "batch04": "0.4.0", "batch05": "0.5.0", "batch06": "0.6.0",
        "batch07": "0.7.0", "batch08": "0.8.0", "batch09": "0.9.0",
        "batch10": "1.0.0",
    }


def test_batch_01_02_report_separates_claims_and_worldview_candidates():
    report = DiscernmentEngine().analyze(case_id="case-1", case=make_case())
    assert report["observed_claims"]
    assert report["domain_pack_matches"][0]["pack_id"] == "meritocracy_successism"
    assert report["worldview_map"]["status"] == "candidate_map"
    assert report["quality_gates"]["evidence_labeled"] is True
    assert report["quality_gates"]["no_mind_reading"] is True


def test_batch_04_hypotheses_remain_low_evidence_and_falsifiable():
    report = DiscernmentEngine().analyze(case_id="case-2", case=make_case())
    assert report["pride_hypotheses"]
    assert all(item["evidence_level"] == "H1" for item in report["pride_hypotheses"])
    assert all(item["stable_character_language_allowed"] is False for item in report["pride_hypotheses"])
    assert all(item["alternative_explanations"] for item in report["pride_hypotheses"])
    assert all(item["counter_evidence_needed"] for item in report["pride_hypotheses"])


def test_no_spiritual_consent_omits_pride_desire_law_and_gospel_analysis():
    case = make_case(consent_scope={
        "allow_spiritual_analysis": False,
        "allow_gospel_bridge": False,
        "allow_public_content_analysis": False,
        "allow_longitudinal_memory": False,
    })
    report = DiscernmentEngine().analyze(case_id="case-3", case=case)
    assert report["pride_hypotheses"] == []
    assert report["desire_map"] == []
    assert report["gospel_bridge"]["status"] == "consent_required"
    assert all(item["stage"] not in {"HEART", "WORSHIP", "LAW", "GOSPEL", "SELF_MIRROR"} for item in report["socratic_questions"])


@pytest.mark.parametrize("text", [
    "他一定没得救，神已经弃绝他",
    "这个网红就是被鬼附",
    "必须现在决志否则就证明你拒绝福音",
])
def test_unsafe_verdicts_stop_the_normal_pipeline(text):
    report = DiscernmentEngine().analyze(case_id="unsafe", case=make_case(raw_input=text))
    assert report["review_status"] == "blocked"
    assert report["safety"]["human_review_required"] is True
    assert report["socratic_questions"] == []


def test_crisis_and_abuse_route_to_safety_without_deeper_questioning():
    report = DiscernmentEngine().analyze(case_id="crisis", case=make_case(raw_input="我不想活了", sensitivity="crisis"))
    assert report["review_status"] == "blocked"
    assert report["safety"]["status"] == "safety_hold"
    assert "停止普通辨识流程" in report["safety"]["actions"]


def test_batch_03_public_figure_requires_consent_and_human_review():
    denied = DiscernmentEngine().analyze(case_id="person-1", case=make_case(subject_type="person"))
    assert denied["review_status"] == "blocked"
    allowed = DiscernmentEngine().analyze(
        case_id="person-2",
        case=make_case(
            subject_type="person", sensitivity="reputation_sensitive",
            consent_scope={"allow_spiritual_analysis": True, "allow_gospel_bridge": False, "allow_public_content_analysis": True},
            source_items=[{"source_type": "public_video", "locator": "https://example.test/video", "evidence_level": "P2"}],
        ),
    )
    assert allowed["review_status"] == "human_review_required"
    assert allowed["virality_analysis"]["propagation_graph"]["criticism_is_not_support"] is True
    assert allowed["virality_analysis"]["business_model"]["undisclosed_income_is_unknown"] is True
    assert allowed["virality_analysis"]["virality_decomposition"]["unknown_residual"] is True


def test_batch_05_dialogue_asks_one_question_and_respects_pause():
    report = DiscernmentEngine().analyze(case_id="dialogue-case", case=make_case())
    engine = DialogueEngine()
    session = engine.initialize(session_id="session-1", case_id="dialogue-case", report=report, faith_context="christian")
    assert session["current_question"]["text"].count("？") <= 1
    advanced = engine.receive(session, answer="我觉得失败就说明我整个人没有价值。", gospel_consent=None)
    assert advanced["status"] == "QUESTION_ASKED"
    assert advanced["current_question"]["text"].count("？") <= 1
    paused = engine.receive(advanced, answer="我想停止，到这里。", gospel_consent=None)
    assert paused["status"] == "PAUSED_BY_USER"
    assert paused["current_question"] is None


def test_batch_05_disagreement_is_not_pathologized():
    report = DiscernmentEngine().analyze(case_id="dialogue-case", case=make_case())
    session = DialogueEngine().initialize(session_id="session-2", case_id="dialogue-case", report=report, faith_context="christian")
    advanced = DialogueEngine().receive(session, answer="我不同意，这个前提不成立。", gospel_consent=None)
    assert advanced["last_answer_evaluation"]["resistance_type"] == "disagreement"
    assert advanced["last_answer_evaluation"]["disagreement_is_not_pathology"] is True


def test_batch_06_standard_path_contains_all_ten_doctrine_segments_and_balance_gates():
    report = DiscernmentEngine().analyze(case_id="gospel-case", case=make_case())
    plan = GospelPathEngine().build(
        case_id="gospel-case", presenting_issue=make_case().raw_input,
        faith_context="christian", consent_scope={"allow_gospel_bridge": True},
        pride_hypotheses=report["pride_hypotheses"], desire_map=report["desire_map"],
        preferred_depth="standard",
    )
    assert len(plan["segments"]) == 10
    assert {item["doctrine_pack_id"] for item in plan["segments"]} == {
        "creation_order", "sin_and_idolatry", "uses_of_law", "christ_and_atonement",
        "justification_by_faith", "adoption", "union_with_christ", "sanctification_by_spirit",
        "church_community", "eschatological_hope",
    }
    assert plan["law_gospel_balance"]["justification_sanctification_separated"] is True
    assert plan["law_gospel_balance"]["resurrection_and_new_creation_present"] is True
    assert all("不是赚取接纳" in item["acceptance_basis"] for item in plan["practice_plan"])


def test_batch_06_requires_explicit_gospel_consent():
    plan = GospelPathEngine().build(
        case_id="no-consent", presenting_issue="我想理解成功", faith_context="unknown",
        consent_scope={"allow_gospel_bridge": False}, pride_hypotheses=[], desire_map=[],
    )
    assert plan["review_status"] == "blocked"
    assert plan["reason"] == "gospel_consent_required"


def test_batch_07_snapshot_is_multidimensional_and_never_a_maturity_score():
    service = FormationTwinService()
    snapshot = service.snapshot(email="member@example.test", events=[])
    assert len(snapshot["dimensions"]) == 8
    assert snapshot["uncertainty"] == "high"
    assert "overall_maturity_score" in snapshot["prohibited_interpretations"]
    assert snapshot["quality_gates"]["no_single_maturity_score"] is True


def test_batch_09_requires_real_rights_allowed_citations_and_context():
    result = TheologyEvidenceService().query(
        query_id="query-1",
        payload={
            "question": "这段经文在上下文中如何理解？",
            "intent": "scripture_exegesis",
            "allowed_rights": ["public_domain"],
            "required_source_types": ["scripture"],
            "scripture_refs": ["Romans 8:1"],
            "scripture_context": {},
            "tradition_scope": [],
            "doctrine_tier": "D3",
            "citations": [],
        },
        sources=[],
    )
    assert result["answer_status"] == "insufficient_evidence"
    assert result["evidence_graph"]["generated_statements"] == []
    assert result["scripture_context_gates"]["paragraph_context_present"] is False


def test_batch_10_fails_closed_without_complete_evidence_and_release_board():
    result = CertificationService().evaluate(
        release_id="release-1",
        body={
            "build_hash": "a" * 64,
            "target_scope": "production",
            "expires_at": "2030-01-01T00:00:00+00:00",
            "evidence": [],
            "findings": [],
            "signatories": [],
            "rollback_ready": False,
            "recertification_enabled": False,
        },
    )
    assert result["status"] == "BLOCKED"
    assert result["certification_counts"] == {"domains": 12, "controls": 58, "valid_controls": 0}
    assert result["release_board_signed"] is False
    assert "certificate" not in result


def test_migration_has_owner_isolation_and_all_persistence_surfaces():
    sql = (ROOT / "migrations" / "0236_spiritual_planet_discernment_batches_01_06.sql").read_text()
    for table in (
        "spiritual_planet_discernment_cases", "spiritual_planet_discernment_evidence",
        "spiritual_planet_discernment_dialogue_sessions", "spiritual_planet_discernment_dialogue_turns",
        "spiritual_planet_discernment_reviews",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "app.current_user_email" in sql
    assert "tenant_id TEXT NOT NULL" in sql


def test_batch_07_10_migration_encrypts_sensitive_payloads_and_isolates_participants():
    sql = (ROOT / "migrations" / "0237_spiritual_planet_discernment_batches_07_10.sql").read_text()
    for table in (
        "spiritual_planet_formation_events", "spiritual_planet_formation_artifacts",
        "spiritual_planet_collaboration_consents", "spiritual_planet_collaboration_disclosures",
        "spiritual_planet_collaboration_meeting_preps", "spiritual_planet_collaboration_audit",
        "spiritual_planet_theology_sources", "spiritual_planet_theology_queries",
        "spiritual_planet_certification_evaluations", "spiritual_planet_release_certificates",
        "spiritual_planet_recertification_events",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql
    assert sql.count("encrypted_payload BYTEA NOT NULL") >= 3
    assert "encrypted_query BYTEA NOT NULL" in sql
    assert "spiritual_planet_disclosure_participant_policy" in sql
    assert "spiritual_planet_meeting_prep_participant_policy" in sql


def test_router_exposes_complete_case_dialogue_gospel_review_and_erasure_contracts():
    from routers.spiritual_planet_discernment import router
    routes = {(method, route.path) for route in router.routes for method in route.methods}
    required = {
        ("GET", "/api/v1/platform/discernment/catalog"),
        ("POST", "/api/v1/platform/discernment/cases"),
        ("GET", "/api/v1/platform/discernment/cases"),
        ("GET", "/api/v1/platform/discernment/cases/{case_id}"),
        ("POST", "/api/v1/platform/discernment/cases/{case_id}/reanalyze"),
        ("DELETE", "/api/v1/platform/discernment/cases/{case_id}"),
        ("POST", "/api/v1/platform/discernment/cases/{case_id}/dialogue"),
        ("POST", "/api/v1/platform/discernment/dialogues/{session_id}/turns"),
        ("POST", "/api/v1/platform/discernment/dialogues/{session_id}/pause"),
        ("POST", "/api/v1/platform/discernment/cases/{case_id}/gospel-path"),
        ("POST", "/api/v1/platform/discernment/cases/{case_id}/reviews"),
        ("POST", "/api/v1/platform/discernment/admin/cases/{case_id}/review"),
    }
    assert required <= routes


def test_extended_router_exposes_formation_collaboration_theology_and_certification_contracts():
    from routers.spiritual_planet_discernment_extended import router
    routes = {(method, route.path) for route in router.routes for method in route.methods}
    required = {
        ("POST", "/api/v1/platform/discernment/formation/events"),
        ("GET", "/api/v1/platform/discernment/formation/events"),
        ("POST", "/api/v1/platform/discernment/formation/snapshot"),
        ("POST", "/api/v1/platform/discernment/formation/reviews"),
        ("POST", "/api/v1/platform/discernment/collaboration/consents"),
        ("DELETE", "/api/v1/platform/discernment/collaboration/consents/{consent_id}"),
        ("POST", "/api/v1/platform/discernment/collaboration/disclosures"),
        ("POST", "/api/v1/platform/discernment/collaboration/meeting-preps"),
        ("GET", "/api/v1/platform/discernment/collaboration/audit"),
        ("POST", "/api/v1/platform/discernment/theology/sources"),
        ("POST", "/api/v1/platform/discernment/theology/queries"),
        ("GET", "/api/v1/platform/discernment/certification/status"),
        ("POST", "/api/v1/platform/discernment/admin/certification/evaluations"),
        ("GET", "/api/v1/platform/discernment/data-export"),
        ("DELETE", "/api/v1/platform/discernment/extended-data"),
    }
    assert required <= routes


def test_main_wires_discernment_router_once():
    text = (ROOT / "main.py").read_text()
    assert text.count("app.include_router(spiritual_planet_discernment_router)") == 1
    assert "init_spiritual_planet_discernment_router(" in text
    assert text.count("app.include_router(spiritual_planet_discernment_extended_router)") == 1
    assert "init_spiritual_planet_discernment_extended_router(" in text
