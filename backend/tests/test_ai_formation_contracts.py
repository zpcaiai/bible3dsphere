from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_formation.catalog import BATCHES, MODULE_MANIFEST, RELEASE_GATES, TRACKS
from ai_formation.contracts import AiUseIntentV1, FormationPlanV1, LearnerContextV1, RecordType, ReleaseEvidenceV1, validate_record_payload
from ai_formation.content_audit import HUMAN_REVIEW_ROLES, build_review_bundle
from ai_formation.policy import assess_ai_authority, assess_pastoral_safety, evaluate_release_evidence
from ai_formation.spec_registry import SpecValidationError, asset_catalog, schema_catalog, validate_spec_payload

pytestmark = pytest.mark.no_db
ROOT = Path(__file__).parents[1]


def test_registry_is_one_module_with_four_tracks_and_twelve_batches():
    assert MODULE_MANIFEST["moduleId"] == "sunday_school.ai_formation"
    assert MODULE_MANIFEST["route"] == "/sunday-school/ai-formation"
    assert len(TRACKS) == 4
    assert [item["id"] for item in BATCHES] == [f"{number:02d}" for number in range(1, 13)]
    assert all(item["learnerContentAvailable"] is False for item in BATCHES)


def test_learner_context_rejects_unknown_fields_and_unconfirmed_minor():
    base = {
        "role": "learner", "age_band": "13_15", "locale": "zh-CN", "goals": ["ai_discernment"],
        "consent": {"data_minimization_accepted": True, "guardian_confirmed": True},
    }
    assert LearnerContextV1.model_validate(base).age_band == "13_15"
    with pytest.raises(ValidationError):
        LearnerContextV1.model_validate({**base, "secret_profile": "x"})
    with pytest.raises(ValidationError):
        LearnerContextV1.model_validate({**base, "consent": {"data_minimization_accepted": True, "guardian_confirmed": False}})


def test_formation_plan_is_non_scoring_and_caps_priorities_and_practices():
    valid = {
        "horizon_days": 14, "priority_domains": ["attention", "rest"],
        "practice_ids": ["attention.pause", "body.rest"], "starts_on": "2026-07-31",
    }
    plan = FormationPlanV1.model_validate(valid)
    assert plan.spiritual_score_generated is False
    with pytest.raises(ValidationError):
        FormationPlanV1.model_validate({**valid, "practice_ids": ["a", "b", "c", "d"]})
    with pytest.raises(ValidationError):
        FormationPlanV1.model_validate({**valid, "horizon_days": 21})


def test_record_dispatch_rejects_raw_prompt_and_unknown_payload_fields():
    payload = {
        "task_category": "research", "stakes": "medium", "requested_role": "verifier",
        "delegation_level": "verify", "privacy_class": "ordinary",
    }
    normalized = validate_record_payload(RecordType.AI_USE_INTENT, payload)
    assert normalized["raw_prompt_persisted"] is False
    with pytest.raises(ValidationError):
        validate_record_payload(RecordType.AI_USE_INTENT, {**payload, "raw_prompt": "private text"})


def test_s3_interrupts_without_returning_or_storing_the_narrative():
    text = "我不想活了"
    decision = assess_pastoral_safety(text, age_band="13_15")
    assert decision["level"] == "S3"
    assert decision["continueCourse"] is False
    assert decision["storeSensitiveDetails"] is False
    assert text not in str(decision)


def test_ai_cannot_be_divine_messenger_or_final_decision_owner():
    intent = AiUseIntentV1.model_validate({
        "task_category": "spiritual_content", "stakes": "high", "requested_role": "divine_messenger",
        "delegation_level": "assist", "privacy_class": "sensitive",
    })
    result = assess_ai_authority(intent.model_dump())
    assert result["decision"] == "prohibited_substitution"
    assert result["finalDecisionOwner"] == "human"


def test_release_evidence_fails_closed_and_never_auto_approves():
    empty = evaluate_release_evidence([])
    assert empty["status"] == "NOT_CERTIFIED"
    assert len(empty["blockers"]) == len(RELEASE_GATES)
    assert empty["automatedApproval"] is False

    with pytest.raises(ValidationError):
        ReleaseEvidenceV1.model_validate({
            "artifact_id": "artifact", "artifact_version": "1", "environment": "ci",
            "artifact_sha256": "a" * 64, "gate": "unrecognized_gate", "result": "passed",
            "command": "verify", "exit_code": 0, "executed_at": "2026-07-31T00:00:00Z",
        })


def test_migration_has_review_gates_owner_rls_and_review_only_seed():
    sql = (ROOT / "migrations" / "0238_sunday_school_ai_formation_batches_01_12.sql").read_text()
    workflow_sql = (ROOT / "migrations" / "0239_ai_formation_production_workflows.sql").read_text()
    seed_sql = (ROOT / "migrations" / "0240_ai_formation_reviewed_asset_catalog.sql").read_text()
    for table in (
        "sunday_school_ai_formation_records", "sunday_school_ai_formation_content",
        "sunday_school_ai_formation_content_reviews", "sunday_school_ai_formation_audit",
        "sunday_school_ai_formation_release_evidence", "sunday_school_ai_formation_release_decisions",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "PRIMARY KEY(id,version)" in sql
    assert "FOREIGN KEY(content_id,content_version)" in sql
    assert "app.current_user_email" in sql
    assert "'theology_review'" in sql
    assert "content_sha256" in workflow_sql
    assert "required_reviews_json" in workflow_sql
    assert seed_sql.count("INSERT INTO sunday_school_ai_formation_content") == 67
    assert "this migration publishes nothing" in seed_sql
    assert "'theology_review'" in seed_sql


def test_exact_skill_specs_are_complete_and_validated_fail_closed():
    assert len(schema_catalog(include_schema=True)) == 132
    assert len(asset_catalog()) == 67
    payload = {
        "intentId": "intent-001",
        "disposition": "allow",
        "reasonCodes": ["low_stakes_tool_use"],
        "humanFinalDecisionRequired": True,
        "aiIsUltimateAuthority": True,
    }
    with pytest.raises(SpecValidationError, match="prohibited safety/privacy flag"):
        validate_spec_payload(
            "ai-authority-boundary-decision", payload,
            tenant_id="personal:test@example.com", learner_id="test@example.com",
        )
    valid = {**payload, "aiIsUltimateAuthority": False, "claimsDivineRevelationAllowed": False}
    batch_id, _version, normalized = validate_spec_payload(
        "ai-authority-boundary-decision", valid,
        tenant_id="personal:test@example.com", learner_id="test@example.com",
    )
    assert batch_id == "03"
    assert normalized["decisionId"]
    with pytest.raises(SpecValidationError, match="required property"):
        validate_spec_payload(
            "ai-authority-boundary-decision", {key: value for key, value in valid.items() if key != "intentId"},
            tenant_id="personal:test@example.com", learner_id="test@example.com",
        )


def test_all_67_content_versions_have_hash_bound_human_review_packets():
    bundle = build_review_bundle(generated_at="2026-08-01T00:00:00+00:00")
    assert bundle["contentVersionCount"] == 67
    assert bundle["status"] == "BLOCKED"
    assert bundle["automatedApprovalAllowed"] is False
    assert set(bundle["blockers"]) == {
        "SOURCE_RIGHTS_OWNER_ATTESTATION_REQUIRED",
        "STATEMENT_OF_FAITH_VERSION_REQUIRED",
    }
    assert len({packet["contentSha256"] for packet in bundle["packets"]}) == 67
    for packet in bundle["packets"]:
        assert packet["humanReview"]
        assert set(packet["humanReview"]).issubset(HUMAN_REVIEW_ROLES)
        assert all(item["status"] == "not_signed" for item in packet["humanReview"].values())
        assert packet["automatedApprovalAllowed"] is False
        assert packet["autoPublishAllowed"] is False


def test_full_postgis_verifier_refuses_unmarked_or_unconfirmed_databases():
    from scripts.verify_full_postgis_migration_chain import _require_disposable

    with pytest.raises(SystemExit, match="refusing migration rehearsal"):
        _require_disposable("postgresql://postgres:x@localhost/production", True)
    with pytest.raises(SystemExit, match="refusing migration rehearsal"):
        _require_disposable("postgresql://postgres:x@localhost/ai_gate", False)
    _require_disposable("postgresql://postgres:x@localhost/ai_gate", True)


def test_router_exposes_manifest_safety_data_rights_and_certification_contracts():
    from fastapi import HTTPException

    from routers.ai_formation import _idempotent_replay, router

    routes = {(method, route.path) for route in router.routes for method in route.methods}
    assert ("GET", "/api/v1/sunday-school/ai-formation/manifest") in routes
    assert ("POST", "/api/v1/sunday-school/ai-formation/safety/check") in routes
    assert ("POST", "/api/v1/sunday-school/ai-formation/records") in routes
    assert ("PATCH", "/api/v1/sunday-school/ai-formation/records/{record_id}") in routes
    assert ("POST", "/api/v1/sunday-school/ai-formation/records/{record_id}/transition") in routes
    assert ("DELETE", "/api/v1/sunday-school/ai-formation/records/{record_id}") in routes
    assert ("GET", "/api/v1/sunday-school/ai-formation/schemas") in routes
    assert ("GET", "/api/v1/sunday-school/ai-formation/content") in routes
    assert ("GET", "/api/v1/sunday-school/ai-formation/scenarios") in routes
    assert ("POST", "/api/v1/sunday-school/ai-formation/scenarios/sessions") in routes
    assert ("POST", "/api/v1/sunday-school/ai-formation/scenarios/sessions/{session_id}/choices") in routes
    assert ("POST", "/api/v1/sunday-school/ai-formation/content/{content_id}/versions/{version}/reviews") in routes
    assert ("POST", "/api/v1/sunday-school/ai-formation/content/{content_id}/versions/{version}/publish") in routes
    assert ("GET", "/api/v1/sunday-school/ai-formation/certification/status") in routes
    assert ("POST", "/api/v1/sunday-school/ai-formation/certification/release-decisions") in routes

    existing = {"id": "record", "record_type": "learner_context", "payload_hash": "same"}
    assert "payload_hash" not in _idempotent_replay(existing, payload_hash="same", record_type="learner_context")
    with pytest.raises(HTTPException) as conflict:
        _idempotent_replay(existing, payload_hash="different", record_type="learner_context")
    assert conflict.value.status_code == 409
