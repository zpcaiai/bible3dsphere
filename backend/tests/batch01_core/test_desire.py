"""Skill 05 - desire-idolatry-mapper."""

from backend.discernment_platform.batch01_core.claims import extract
from backend.discernment_platform.batch01_core.desire import map_desires, more_self_report_needed
from backend.discernment_platform.batch01_core.intake import normalize
from backend.discernment_platform.batch01_core.pride import detect
from backend.discernment_platform.batch01_core.worldview import map_worldview


def _chains(normalized, reaction=""):
    claims = extract(normalized)
    wv = map_worldview(normalized, claims)
    hypotheses = detect(normalized, claims, wv, reaction)
    return map_desires(normalized, wv, hypotheses, reaction)


def test_builds_full_five_link_chain(influencer_normalized):
    for chain in _chains(influencer_normalized):
        assert chain.good_desire
        assert chain.absolutized_desire
        assert chain.functional_savior
        assert chain.demanded_sacrifice
        assert chain.enslaving_fruit


def test_good_desire_is_never_stigmatised(influencer_normalized):
    for chain in _chains(influencer_normalized):
        assert "渴望" in chain.good_desire or "希望" in chain.good_desire


def test_every_chain_reanchors_in_christ(influencer_normalized):
    assert all(chain.reanchoring_in_christ for chain in _chains(influencer_normalized))


def test_structural_factors_are_preserved(influencer_case):
    influencer_case.raw_input += "他也提到自己经历过裁员和长期债务的压力。"
    chains = _chains(normalize(influencer_case))
    assert any(chain.structural_factors for chain in chains)


def test_structural_note_warns_against_individualising(influencer_case):
    influencer_case.raw_input += "他也提到自己经历过裁员和长期债务的压力。"
    for chain in _chains(normalize(influencer_case)):
        for factor in chain.structural_factors:
            assert "不应仅归因于个人偶像" in factor


def test_low_evidence_chains_are_marked_candidate(influencer_normalized):
    for chain in _chains(influencer_normalized):
        if not chain.confidence.is_conclusive:
            assert chain.candidate


def test_no_signal_yields_candidate_models(influencer_case):
    influencer_case.raw_input = "今天天气很好，我去公园散步了一会儿，看到很多人。"
    chains = _chains(normalize(influencer_case))
    assert chains
    assert more_self_report_needed(chains)


def test_chains_are_deduplicated_by_functional_savior(influencer_normalized):
    saviors = [c.functional_savior for c in _chains(influencer_normalized)]
    assert len(saviors) == len(set(saviors))


def test_loss_reaction_is_recorded(influencer_normalized):
    assert all(chain.loss_reaction for chain in _chains(influencer_normalized))
