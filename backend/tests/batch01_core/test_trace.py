"""Skill 10 - trace-review-packager."""

from backend.discernment_platform.batch01_core.trace import (
    REQUIRED_SKILLS,
    apply_human_override,
    digest,
    package,
    record,
    redacted_user_view,
    review_packet,
)


def _record(skill_id="case-intake-normalizer"):
    return record(
        case_id="c-1",
        skill_id=skill_id,
        skill_version="0.1.0",
        payload_in={"a": 1},
        payload_out={"b": 2},
        evidence_links=["claim-001"],
    )


def test_record_captures_hashes_and_versions():
    rec = _record()
    assert rec.input_hash and rec.output_hash and rec.prompt_hash
    assert rec.skill_version == "0.1.0"


def test_digest_is_stable_and_order_independent():
    assert digest({"a": 1, "b": 2}) == digest({"b": 2, "a": 1})


def test_incomplete_trace_is_not_production_ready():
    bundle = package("c-1", [_record()])
    assert not bundle.production_ready
    assert bundle.missing_skills


def test_complete_trace_is_production_ready():
    bundle = package("c-1", [_record(s) for s in REQUIRED_SKILLS])
    assert bundle.production_ready
    assert not bundle.missing_skills


def test_evidence_links_are_preserved():
    assert _record().evidence_links == ["claim-001"]


def test_redacted_view_hides_internal_inferences():
    view = redacted_user_view(
        {"summary": "s", "pride_hypotheses": [{"x": 1}], "desire_map": [], "safety_decisions": []}
    )
    assert "pride_hypotheses" not in view
    assert "desire_map" not in view
    assert view["hidden_sections"]


def test_human_override_preserves_original_and_reason():
    bundle = package("c-1", [_record()])
    trace_id = bundle.records[0].trace_id
    bundle = apply_human_override(bundle, trace_id, "b", 99, "牧者判断有误", "elder-1")
    override = bundle.records[0].human_overrides[0]
    assert override["original_value"] == 2
    assert override["new_value"] == 99
    assert override["reason"] == "牧者判断有误"
    assert override["reviewer"] == "elder-1"


def test_review_packet_carries_trace_and_policy_version():
    packet = review_packet(package("c-1", [_record()]), {"summary": "s"})
    assert packet["trace_records"]
    assert packet["policy_version"]


def test_trace_id_binds_case_and_skill():
    assert _record().trace_id.startswith("c-1:case-intake-normalizer:")
