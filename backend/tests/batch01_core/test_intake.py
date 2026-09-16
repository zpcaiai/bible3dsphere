"""Skill 01 - case-intake-normalizer."""

import pytest

from backend.discernment_platform.batch01_core.intake import MIN_INPUT_LENGTH, normalize
from backend.discernment_platform.batch01_core.models import (
    ConsentScope,
    DiscernmentCase,
    FailureCode,
    SkillFailure,
    SourceKind,
    SubjectType,
)


def _case(raw, subject_type=SubjectType.PERSON, **kw):
    return DiscernmentCase(
        case_id="t-1",
        subject_type=subject_type,
        raw_input=raw,
        user_goal="辨识",
        consent_scope=ConsentScope(
            allow_spiritual_analysis=True, allow_gospel_bridge=True
        ),
        **kw,
    )


def test_short_input_returns_insufficient_evidence():
    with pytest.raises(SkillFailure) as exc:
        normalize(_case("太短"))
    assert exc.value.code is FailureCode.INSUFFICIENT_EVIDENCE


def test_min_length_boundary_is_enforced():
    assert len("太短") < MIN_INPUT_LENGTH


def test_separates_analysed_object_from_user_reaction(influencer_normalized):
    assert influencer_normalized.analyzed_object_segments


def test_self_reflection_routes_everything_to_user_reaction(scrupulosity_case):
    normalized = normalize(scrupulosity_case)
    assert normalized.user_reaction_segments
    assert not normalized.analyzed_object_segments
    assert all(
        seg.source_kind is SourceKind.USER_COMMENT
        for seg in normalized.user_reaction_segments
    )


def test_marks_quotes_distinctly(influencer_normalized):
    kinds = {seg.source_kind for seg in influencer_normalized.analyzed_object_segments}
    assert SourceKind.QUOTE in kinds


def test_invents_no_new_facts(influencer_case, influencer_normalized):
    for segment in influencer_normalized.analyzed_object_segments:
        assert segment.text in influencer_case.raw_input


def test_detects_missing_context(influencer_normalized):
    assert influencer_normalized.missing_context


def test_preserves_conflicts_without_adjudicating():
    normalized = normalize(_case("他说他从不撒谎，但也承认有时会说善意的谎言，这让人困惑。"))
    assert normalized.conflicts
    assert "未自行裁决" in normalized.conflicts[0]


def test_deduplicates_repeated_lines():
    normalized = normalize(_case("重复的一句话内容在这里\n重复的一句话内容在这里\n另一句"))
    assert normalized.subject_description.count("重复的一句话内容在这里") == 1


def test_unknowns_always_state_no_mind_reading(influencer_normalized):
    assert any("不可读心" in u for u in influencer_normalized.unknowns)
