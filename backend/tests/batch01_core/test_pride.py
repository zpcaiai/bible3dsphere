"""Skill 04 - pride-signal-detector."""

from backend.discernment_platform.batch01_core.claims import extract
from backend.discernment_platform.batch01_core.models import EvidenceLevel, PrideSignal
from backend.discernment_platform.batch01_core.pride import (
    conclusive,
    detect,
    redirect_to_self_examination,
)
from backend.discernment_platform.batch01_core.worldview import map_worldview


def _detect(normalized, reaction=""):
    claims = extract(normalized)
    wv = map_worldview(normalized, claims)
    return detect(normalized, claims, wv, reaction)


def test_detects_contempt_for_weakness_in_influencer(influencer_normalized):
    patterns = {h.possible_pattern for h in _detect(influencer_normalized)}
    assert PrideSignal.CONTEMPT_FOR_WEAKNESS in patterns


def test_every_hypothesis_has_alternative_explanations(influencer_normalized):
    assert all(h.alternative_explanations for h in _detect(influencer_normalized))


def test_every_hypothesis_requests_disconfirming_evidence(influencer_normalized):
    assert all(h.disconfirming_evidence_needed for h in _detect(influencer_normalized))


def test_language_is_hedged_never_verdict(influencer_normalized):
    for hypothesis in _detect(influencer_normalized):
        assert "可能" in hypothesis.interpretation_hypothesis
        assert "就是骄傲" not in hypothesis.interpretation_hypothesis
        assert "神显明" not in hypothesis.interpretation_hypothesis


def test_e0_to_e2_are_not_conclusions(influencer_normalized):
    for hypothesis in conclusive(_detect(influencer_normalized)):
        assert hypothesis.evidence_level.rank >= 3


def test_evidence_ladder_ranks_correctly():
    assert EvidenceLevel.E4.rank > EvidenceLevel.E1.rank
    assert not EvidenceLevel.E2.is_conclusive
    assert EvidenceLevel.E3.is_conclusive


def test_public_person_marked_public_material_only(influencer_normalized):
    assert all(h.public_material_only for h in _detect(influencer_normalized))


def test_self_reflection_scope_is_self(scrupulosity_case):
    from backend.discernment_platform.batch01_core.intake import normalize

    hypotheses = _detect(normalize(scrupulosity_case))
    assert all(h.scope == "self" for h in hypotheses)


def test_other_directed_questions_turn_back_on_the_user(influencer_normalized):
    for hypothesis in _detect(influencer_normalized):
        assert "先用在自己身上" in hypothesis.pastoral_question


def test_condemnation_request_is_redirected(influencer_normalized):
    prompts = redirect_to_self_examination(_detect(influencer_normalized))
    assert any("你里面" in p or "你身上" in p for p in prompts)
