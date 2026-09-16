"""Contract-level tests for every shipped SKILL.md (Batches 01-10)."""

from __future__ import annotations

import pytest

from backend.discernment_platform.skills import (
    EXPECTED_SKILL_COUNTS,
    EXPECTED_TOTAL_SKILLS,
    REQUIRED_SECTIONS,
    SkillContractError,
    as_items,
    get_skill_registry,
    parse_skill_md,
)

pytestmark = pytest.mark.no_db


@pytest.fixture(scope="module")
def skills():
    return get_skill_registry()


def test_all_runtime_skills_load(skills):
    assert len(skills) == EXPECTED_TOTAL_SKILLS == 174


def test_per_batch_counts_match(skills):
    for batch_key, expected in EXPECTED_SKILL_COUNTS.items():
        assert len(skills.for_batch(batch_key)) == expected


def test_every_contract_has_all_required_sections(skills):
    for contract in skills:
        for section in REQUIRED_SECTIONS:
            assert section in contract.sections, f"{contract.skill_id} missing {section}"


def test_no_contract_has_empty_required_lists(skills):
    for contract in skills:
        assert contract.purpose
        assert contract.inputs
        assert contract.outputs
        assert contract.processing_contract
        assert contract.guardrails
        assert contract.failure_handling
        assert contract.acceptance_tests


def test_skill_ids_are_unique(skills):
    assert len({c.skill_id for c in skills}) == len(skills)


def test_front_matter_batch_matches_directory(skills):
    for contract in skills:
        assert contract.source_path.split("/")[2] == contract.batch_key


def test_versions_follow_batch_numbering(skills):
    for contract in skills:
        major_minor = contract.version.rsplit(".", 1)[0]
        assert major_minor in {"0.1", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8", "0.9", "1.0"}


def test_lookup_by_skill_id(skills):
    contract = skills.get("pastoral-safety-guardian")
    assert contract.batch == 1
    assert contract.always_on


def test_unknown_skill_id_raises(skills):
    with pytest.raises(KeyError):
        skills.get("no-such-skill")


def test_pipeline_puts_always_on_guardians_first(skills):
    pipeline = skills.pipeline(1)
    assert pipeline[0] == "pastoral-safety-guardian"
    assert len(pipeline) == 10


def test_search_finds_by_purpose(skills):
    assert any(c.skill_id == "scripture-misuse-detector" for c in skills.search("misuse"))


def test_catalog_reports_every_batch(skills):
    catalog = skills.catalog()
    assert catalog["total"] == 174
    assert sum(catalog["counts"].values()) == 174


def test_parse_rejects_missing_front_matter():
    with pytest.raises(SkillContractError):
        parse_skill_md("# Purpose\nx\n")


def test_parse_rejects_missing_sections():
    text = "---\nid: x\nname: x\nversion: 1\nbatch: 1\ntype: t\n---\n\n# Purpose\n\nok\n"
    with pytest.raises(SkillContractError):
        parse_skill_md(text)


def test_as_items_handles_bullets_numbers_and_prose():
    assert as_items("- a\n- b") == ("a", "b")
    assert as_items("1. a\n2. b") == ("a", "b")
    assert as_items("一句话；另一句话。") == ("一句话", "另一句话")


def test_always_on_guardians_are_identified(skills):
    always_on = {c.skill_id for c in skills if c.always_on}
    assert "pastoral-safety-guardian" in always_on
    assert "public-figure-safety-guardian" in always_on
