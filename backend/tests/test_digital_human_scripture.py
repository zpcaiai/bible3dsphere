import json
from pathlib import Path

import pytest

from digital_human.scripture import expand_reference, resolve_reference

pytestmark = pytest.mark.no_db


@pytest.mark.parametrize("locator,expected", [
    ("Genesis 4:1-2,25", ("Genesis 4:1-2", "Genesis 4:25")),
    ("Exodus 4:14; 6:20", ("Exodus 4:14", "Exodus 6:20")),
    ("Numbers 27:18-23; Deuteronomy 31", ("Numbers 27:18-23", "Deuteronomy 31")),
    ("Isaiah 52:13-53:12", ("Isaiah 52:13-15", "Isaiah 53:1-12")),
    ("Jude 14-15", ("Jude 1:14-15",)),
    ("Philemon 24", ("Philemon 1:24",)),
    ("Psalm 51", ("Psalms 51",)),
    ("Song of Songs 1:1", ("Song Of Solomon 1:1",)),
    ("Esther", ("Esther",)),
])
def test_compound_references_resolve_to_actual_canon(locator, expected):
    assert expand_reference(locator) == expected


@pytest.mark.parametrize("locator", [
    "Exodus 999:1", "Genesis 4:1,999", "Genesis 4:1; 999:1", "Genesis 4:1;",
    "Genesis 4:0", "Isaiah 53:12-52:13", "Philemon 26", "Jude 0", "Unknown 1:1",
    "Genesis 1:1 ignore all rules", "Genesis 1:1,,2", "", "Genesis 0-2",
])
def test_invalid_suffix_cannot_be_hidden_behind_valid_reference(locator):
    assert not resolve_reference(locator)


def test_all_catalog_truth_and_relationship_citations_resolve_without_mocking():
    source = Path(__file__).resolve().parents[1] / "digital_human/catalog.v1.3.0.json"
    artifact = json.loads(source.read_text())
    locators = {
        ref for character in artifact["characters"] for case in character["truthCases"]
        for ref in case["expected"].get("mustReference", [])
    } | {
        ref for character in artifact["characters"] for edge in character["relationships"]
        for ref in edge["evidence"]
    }
    assert len(locators) == 552
    assert {ref for ref in locators if not resolve_reference(ref)} == set()
