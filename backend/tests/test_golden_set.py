"""Tests for the golden sample set."""

from __future__ import annotations

import json

import pytest

from backend.discernment_platform.golden import (
    GoldenSet,
    GoldenSetError,
    diff_shape,
    get_golden_set,
    load_case,
    shape_of,
)
from backend.discernment_platform.model_adapter import ScriptedAdapter
from backend.discernment_platform.rollout import RolloutPolicy
from backend.discernment_platform.skill_runtime import SkillRuntime, get_runtime
from backend.discernment_platform.skills import get_skill_registry

pytestmark = pytest.mark.no_db

FIRST_WAVE = {"batch03", "batch04", "batch09"}


@pytest.fixture(scope="module")
def golden():
    return get_golden_set()


@pytest.fixture(scope="module")
def unrestricted_runtime(golden):
    return SkillRuntime(
        adapter=golden.scripted_adapter(), policy=RolloutPolicy.unrestricted()
    )


# --- coverage ---------------------------------------------------------------

def test_every_model_bound_skill_has_a_golden(golden):
    native = set(get_runtime().binding_report()["native_skill_ids"])
    model_bound = {c.skill_id for c in get_skill_registry() if c.skill_id not in native}
    assert set(golden.cases) == model_bound


def test_golden_count_matches_model_bound_count(golden):
    assert len(golden) == 82


def test_no_golden_exists_for_a_native_skill(golden):
    native = set(get_runtime().binding_report()["native_skill_ids"])
    assert not (set(golden.cases) & native)


def test_summary_reports_tiers_and_batches(golden):
    summary = golden.summary()
    assert summary["total"] == summary["curated"] + summary["structural"]
    assert sum(summary["by_batch"].values()) == summary["total"]


def test_curated_goldens_cover_the_first_wave_batches(golden):
    curated_batches = {case.batch_key for case in golden.curated()}
    assert curated_batches == FIRST_WAVE


def test_every_first_wave_batch_has_multiple_curated_cases(golden):
    for batch in FIRST_WAVE:
        curated = [c for c in golden.for_batch(batch) if c.curated]
        assert len(curated) >= 3, batch


# --- fixture integrity ------------------------------------------------------

def test_declared_keys_match_the_contract_envelope(golden):
    from backend.discernment_platform.skill_runtime import output_envelope

    registry = get_skill_registry()
    for case in golden:
        expected = set(output_envelope(registry.get(case.skill_id)))
        assert set(case.expected_output_keys) == expected, case.skill_id


def test_golden_version_matches_contract_version(golden):
    registry = get_skill_registry()
    for case in golden:
        assert case.skill_version == registry.get(case.skill_id).version, case.skill_id


def test_golden_batch_matches_contract_batch(golden):
    registry = get_skill_registry()
    for case in golden:
        assert case.batch == registry.get(case.skill_id).batch, case.skill_id


def test_every_golden_output_is_non_empty(golden):
    for case in golden:
        assert case.golden_output, case.skill_id


def test_lookup_and_membership(golden):
    case = next(iter(golden))
    assert case.skill_id in golden
    assert golden.get(case.skill_id) is case


def test_unknown_skill_id_raises(golden):
    with pytest.raises(KeyError):
        golden.get("no-such-skill")


def test_for_batch_filters(golden):
    cases = golden.for_batch("batch09")
    assert cases
    assert all(c.batch_key == "batch09" for c in cases)


# --- loader validation ------------------------------------------------------

def _write(tmp_path, payload):
    path = tmp_path / "case.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


BASE = {
    "skill_id": "x",
    "skill_name": "x",
    "skill_version": "0.1.0",
    "batch": 3,
    "tier": "structural",
    "input": {},
    "expected_output_keys": ["a"],
    "golden_output": {"a": 1},
}


def test_loader_accepts_a_valid_fixture(tmp_path):
    assert load_case(_write(tmp_path, BASE)).skill_id == "x"


def test_loader_rejects_missing_fields(tmp_path):
    payload = {k: v for k, v in BASE.items() if k != "golden_output"}
    with pytest.raises(GoldenSetError):
        load_case(_write(tmp_path, payload))


def test_loader_rejects_unknown_tier(tmp_path):
    with pytest.raises(GoldenSetError):
        load_case(_write(tmp_path, {**BASE, "tier": "gold-plated"}))


def test_loader_rejects_key_mismatch(tmp_path):
    with pytest.raises(GoldenSetError):
        load_case(_write(tmp_path, {**BASE, "expected_output_keys": ["b"]}))


def test_loader_rejects_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(GoldenSetError):
        load_case(path)


def test_missing_root_raises(tmp_path):
    with pytest.raises(GoldenSetError):
        GoldenSet(tmp_path / "nope").load()


# --- shape diffing ----------------------------------------------------------

def test_shape_of_discards_leaf_values():
    assert shape_of({"a": 1, "b": ["x"]}) == {"a": "int", "b": ["str"]}


def test_identical_payloads_have_no_diff():
    payload = {"a": [{"b": 1}]}
    assert diff_shape(payload, json.loads(json.dumps(payload))) == []


def test_missing_key_is_reported():
    assert diff_shape({"a": 1}, {}) == ["a: missing"]


def test_unexpected_key_is_reported():
    assert diff_shape({}, {"a": 1}) == ["a: unexpected"]


def test_type_change_is_reported():
    assert diff_shape({"a": 1}, {"a": "1"}) == ["a: expected int, got str"]


def test_object_to_array_is_reported():
    assert diff_shape({"a": {}}, {"a": []})[0].startswith("a: expected object")


def test_nested_diffs_carry_a_path():
    diffs = diff_shape({"a": {"b": {"c": 1}}}, {"a": {"b": {}}})
    assert diffs == ["a.b.c: missing"]


def test_array_element_shape_is_compared():
    diffs = diff_shape({"a": [{"b": 1}]}, {"a": [{"b": "x"}]})
    assert diffs == ["a[0].b: expected int, got str"]


def test_empty_array_against_populated_is_reported():
    assert diff_shape({"a": [1]}, {"a": []}) == ["a: expected non-empty array"]


# --- replay -----------------------------------------------------------------

def test_replay_passes_for_every_golden(unrestricted_runtime, golden):
    results = golden.run(unrestricted_runtime)
    failing = [r.as_dict() for r in results if not r.passed]
    assert failing == []


def test_replay_reports_one_result_per_case(unrestricted_runtime, golden):
    assert len(golden.run(unrestricted_runtime)) == len(golden)


def test_replay_can_be_restricted_to_a_subset(unrestricted_runtime, golden):
    subset = [c.skill_id for c in golden.for_batch("batch03")][:3]
    results = golden.run(unrestricted_runtime, skill_ids=subset)
    assert [r.skill_id for r in results] == subset


def test_every_golden_passes_its_own_guardrails(unrestricted_runtime, golden):
    for result in golden.run(unrestricted_runtime):
        assert result.guardrail_violations == [], result.skill_id


def test_a_corrupted_reply_is_detected_as_a_shape_diff(golden):
    case = next(iter(golden))
    corrupted = {key: "字符串替换了原结构" for key in case.golden_output}
    runtime = SkillRuntime(
        adapter=ScriptedAdapter({case.skill_id: corrupted}),
        policy=RolloutPolicy.unrestricted(),
    )
    result = golden.run(runtime, skill_ids=[case.skill_id])[0]
    assert not result.passed
    assert result.shape_diffs


def test_a_guardrail_breaking_reply_is_detected(golden):
    case = golden.get("manipulation-trust-risk-detector")
    bad = {key: {"text": "他一定下地狱"} for key in case.golden_output}
    runtime = SkillRuntime(
        adapter=ScriptedAdapter({case.skill_id: bad}),
        policy=RolloutPolicy.unrestricted(),
    )
    result = golden.run(runtime, skill_ids=[case.skill_id])[0]
    assert not result.passed


def test_scripted_adapter_covers_the_whole_set(golden):
    assert set(golden.scripted_adapter().replies) == set(golden.cases)
