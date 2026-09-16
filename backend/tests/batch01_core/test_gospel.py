"""Skill 07 - gospel-bridge-builder."""

import pytest

from backend.discernment_platform.batch01_core.claims import extract
from backend.discernment_platform.batch01_core.desire import map_desires
from backend.discernment_platform.batch01_core.gospel import build, requires_consent_first
from backend.discernment_platform.batch01_core.intake import normalize
from backend.discernment_platform.batch01_core.models import FailureCode, FaithContext, SkillFailure
from backend.discernment_platform.batch01_core.pride import detect
from backend.discernment_platform.batch01_core.worldview import map_worldview


def _build(normalized):
    claims = extract(normalized)
    wv = map_worldview(normalized, claims)
    hypotheses = detect(normalized, claims, wv)
    desires = map_desires(normalized, wv, hypotheses)
    return build(normalized, wv, hypotheses, desires)


def test_bridge_contains_christ_person_and_work(influencer_normalized):
    bridge = _build(influencer_normalized)
    assert "基督" in bridge.christ_person_and_work
    assert "复活" in bridge.christ_person_and_work


def test_bridge_is_not_a_behaviour_checklist(influencer_normalized):
    bridge = _build(influencer_normalized)
    assert bridge.union_identity
    assert "被赐予的，不是被赢得的" in bridge.union_identity


def test_justification_and_sanctification_are_distinguished(influencer_normalized):
    note = _build(influencer_normalized).justification_sanctification_note
    assert "称义" in note and "成圣" in note


def test_all_seven_sections_present(influencer_normalized):
    bridge = _build(influencer_normalized)
    for field in (
        "affirmed_good",
        "exposure",
        "law_mirror",
        "christ_person_and_work",
        "union_identity",
        "practice",
        "hope",
    ):
        assert getattr(bridge, field)


def test_hope_does_not_promise_immediate_relief(influencer_normalized):
    assert "不保证立刻消失" in _build(influencer_normalized).hope


def test_missing_consent_raises_consent_required(influencer_case):
    influencer_case.consent_scope.allow_gospel_bridge = False
    with pytest.raises(SkillFailure) as exc:
        _build(normalize(influencer_case))
    assert exc.value.code is FailureCode.USER_CONSENT_REQUIRED


def test_scripture_anchors_are_attached(influencer_normalized):
    assert _build(influencer_normalized).scripture_anchors


def test_non_christian_requires_consent_first(influencer_case):
    influencer_case.faith_context = FaithContext.SEEKER
    assert requires_consent_first(normalize(influencer_case))


def test_mental_health_softens_law_mirror(scrupulosity_case):
    bridge = _build(normalize(scrupulosity_case))
    assert "压得更低" in bridge.law_mirror
    assert "罗马书 8:1" in bridge.scripture_anchors


def test_no_direct_revelation_language(influencer_normalized):
    bridge = _build(influencer_normalized)
    assert "神对你说" not in bridge.model_dump_json()
