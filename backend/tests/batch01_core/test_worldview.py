"""Skill 03 - worldview-frame-mapper."""

from backend.discernment_platform.batch01_core.claims import extract
from backend.discernment_platform.batch01_core.worldview import SEVEN_QUESTIONS, map_worldview


def _map(normalized):
    return map_worldview(normalized, extract(normalized))


def test_always_emits_creation_good_and_fall_distortion(influencer_normalized):
    wv = _map(influencer_normalized)
    assert wv.layers.creation_good
    assert wv.layers.fall_distortion


def test_never_only_negative_labels(influencer_normalized):
    wv = _map(influencer_normalized)
    assert wv.possible_correct_points


def test_steelman_precedes_evaluation(influencer_normalized):
    wv = _map(influencer_normalized)
    assert "最强版本" in wv.steelman


def test_answers_all_seven_questions(influencer_normalized):
    wv = _map(influencer_normalized)
    assert set(wv.seven_questions) == set(SEVEN_QUESTIONS)


def test_identifies_redemption_substitute(influencer_normalized):
    wv = _map(influencer_normalized)
    assert wv.layers.redemption_substitute


def test_thin_material_yields_questions_not_verdicts(influencer_case):
    from backend.discernment_platform.batch01_core.intake import normalize

    influencer_case.raw_input = "他说了一句很短的话而已。"
    wv = _map(normalize(influencer_case))
    if not wv.sufficient_material:
        assert wv.open_questions


def test_common_grace_is_recorded(influencer_normalized):
    assert _map(influencer_normalized).common_grace_insights


def test_supporting_claims_are_linked(influencer_normalized):
    wv = _map(influencer_normalized)
    assert wv.supporting_claim_ids


def test_telos_layer_is_present(influencer_normalized):
    assert _map(influencer_normalized).layers.consummation_telos
