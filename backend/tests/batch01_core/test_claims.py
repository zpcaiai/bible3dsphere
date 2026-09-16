"""Skill 02 - claim-evidence-extractor."""

from backend.discernment_platform.batch01_core.claims import HIGH_CONFIDENCE_FLOOR, extract, high_confidence
from backend.discernment_platform.batch01_core.models import ClaimType


def test_extracts_claims_from_fixture(influencer_normalized):
    assert extract(influencer_normalized)


def test_every_high_confidence_claim_has_evidence_span(influencer_normalized):
    for claim in high_confidence(extract(influencer_normalized)):
        assert claim.evidence_span


def test_recognises_wealth_freedom_as_salvation_claim(influencer_normalized):
    types = {c.claim_type for c in extract(influencer_normalized)}
    assert ClaimType.SALVATION in types


def test_distinguishes_fact_from_value(influencer_normalized):
    types = {c.claim_type for c in extract(influencer_normalized)}
    assert types & {ClaimType.MORAL, ClaimType.CAUSAL}


def test_rhetoric_lowers_confidence(influencer_normalized):
    claims = extract(influencer_normalized)
    rhetorical = [c for c in claims if c.rhetoric_discount > 0]
    for claim in rhetorical:
        assert claim.confidence < 0.8


def test_implicit_claims_never_reach_high_confidence(influencer_normalized):
    for claim in extract(influencer_normalized):
        if claim.implicit:
            assert claim.confidence < HIGH_CONFIDENCE_FLOOR
            assert claim not in high_confidence(extract(influencer_normalized))


def test_nothing_is_marked_externally_verified_offline(influencer_normalized):
    assert not any(c.externally_verified for c in extract(influencer_normalized))


def test_every_claim_requests_counter_evidence(influencer_normalized):
    assert all(c.counter_evidence_needed for c in extract(influencer_normalized))


def test_self_reflection_yields_emotional_signals(scrupulosity_case):
    from backend.discernment_platform.batch01_core.intake import normalize

    types = {c.claim_type for c in extract(normalize(scrupulosity_case))}
    assert ClaimType.EMOTIONAL in types
