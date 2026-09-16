"""Tests for staged rollout gating of model-bound skills."""

from __future__ import annotations

import json

import pytest

from backend.discernment_platform.golden import get_golden_set
from backend.discernment_platform.rollout import (
    DEFAULT_PLAN,
    HUMAN_SIGNOFF_BATCHES,
    RolloutError,
    RolloutPolicy,
    Stage,
)
from backend.discernment_platform.skill_runtime import SkillRuntime
from backend.discernment_platform.skills import get_skill_registry

pytestmark = pytest.mark.no_db

FIRST_WAVE = {"batch03", "batch04", "batch09"}


@pytest.fixture(scope="module")
def golden():
    return get_golden_set()


def runtime_with(policy, golden):
    return SkillRuntime(adapter=golden.scripted_adapter(), policy=policy)


# --- stage semantics --------------------------------------------------------

def test_stage_order_is_increasing_trust():
    ranks = [stage.rank for stage in (Stage.DISABLED, Stage.SHADOW, Stage.PILOT, Stage.PRODUCTION)]
    assert ranks == sorted(ranks)


def test_disabled_does_not_run_the_model():
    assert not Stage.DISABLED.runs_model


def test_shadow_runs_but_is_not_authoritative():
    assert Stage.SHADOW.runs_model
    assert not Stage.SHADOW.authoritative


def test_pilot_is_authoritative_but_needs_review():
    assert Stage.PILOT.authoritative
    assert Stage.PILOT.requires_human_review


def test_production_needs_no_blanket_review():
    assert Stage.PRODUCTION.authoritative
    assert not Stage.PRODUCTION.requires_human_review


# --- the shipped plan -------------------------------------------------------

def test_default_plan_puts_first_wave_batches_in_pilot():
    for batch in FIRST_WAVE:
        assert DEFAULT_PLAN[batch] is Stage.PILOT


def test_default_plan_holds_pastoral_batches_in_shadow():
    for batch in ("batch05", "batch06", "batch07", "batch08"):
        assert DEFAULT_PLAN[batch] is Stage.SHADOW


def test_release_gate_is_never_model_authoritative_by_default():
    assert DEFAULT_PLAN["batch10"] is Stage.SHADOW


def test_signoff_batches_are_the_safety_critical_ones():
    assert HUMAN_SIGNOFF_BATCHES == {"batch08", "batch10"}


def test_shipped_config_file_loads():
    policy = RolloutPolicy.from_file()
    assert policy.name == "first-wave"
    assert policy.plan["batch03"] is Stage.PILOT


def test_shipped_config_pins_the_two_risky_guardian_skills():
    policy = RolloutPolicy.from_file()
    assert policy.overrides["scrupulosity-and-trauma-guardian"] is Stage.SHADOW
    assert policy.overrides["public-person-reputation-guardian"] is Stage.SHADOW


# --- constructors -----------------------------------------------------------

def test_unrestricted_puts_everything_in_production():
    policy = RolloutPolicy.unrestricted()
    assert set(policy.plan.values()) == {Stage.PRODUCTION}


def test_all_disabled_blocks_everything():
    policy = RolloutPolicy.all_disabled()
    assert set(policy.plan.values()) == {Stage.DISABLED}


def test_from_dict_merges_over_the_default_plan():
    policy = RolloutPolicy.from_dict({"batches": {"batch05": "production"}})
    assert policy.plan["batch05"] is Stage.PRODUCTION
    assert policy.plan["batch10"] is Stage.SHADOW


def test_from_dict_rejects_unknown_stage():
    with pytest.raises(RolloutError):
        RolloutPolicy.from_dict({"batches": {"batch03": "yolo"}})


def test_from_file_rejects_missing_path(tmp_path):
    with pytest.raises(RolloutError):
        RolloutPolicy.from_file(tmp_path / "nope.json")


def test_from_file_rejects_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{oops", encoding="utf-8")
    with pytest.raises(RolloutError):
        RolloutPolicy.from_file(path)


def test_from_file_reads_a_custom_plan(tmp_path):
    path = tmp_path / "plan.json"
    path.write_text(
        json.dumps({"name": "custom", "batches": {"batch10": "production"}}), encoding="utf-8"
    )
    policy = RolloutPolicy.from_file(path)
    assert policy.plan["batch10"] is Stage.PRODUCTION


def test_promote_returns_a_copy_without_mutating():
    base = RolloutPolicy.staged()
    promoted = base.promote("batch05", Stage.PILOT)
    assert promoted.plan["batch05"] is Stage.PILOT
    assert base.plan["batch05"] is Stage.SHADOW


def test_promote_accepts_a_string_stage():
    assert RolloutPolicy.staged().promote("batch05", "pilot").plan["batch05"] is Stage.PILOT


def test_promote_rejects_an_unknown_stage():
    with pytest.raises(RolloutError):
        RolloutPolicy.staged().promote("batch05", "supercharged")


# --- env configuration ------------------------------------------------------

def test_env_defaults_to_the_staged_plan():
    assert RolloutPolicy.from_env({}).name == "staged"


def test_env_can_select_unrestricted():
    policy = RolloutPolicy.from_env({"DISCERNMENT_ROLLOUT_PLAN": "unrestricted"})
    assert set(policy.plan.values()) == {Stage.PRODUCTION}


def test_env_can_disable_everything():
    policy = RolloutPolicy.from_env({"DISCERNMENT_ROLLOUT_PLAN": "off"})
    assert set(policy.plan.values()) == {Stage.DISABLED}


def test_env_per_batch_override_applies():
    policy = RolloutPolicy.from_env({"DISCERNMENT_ROLLOUT_BATCH05": "pilot"})
    assert policy.plan["batch05"] is Stage.PILOT


def test_env_override_rejects_bad_stage():
    with pytest.raises(RolloutError):
        RolloutPolicy.from_env({"DISCERNMENT_ROLLOUT_BATCH05": "nope"})


def test_env_ignores_unrelated_variables():
    policy = RolloutPolicy.from_env({"DISCERNMENT_ROLLOUT_SOMETHING": "pilot"})
    assert policy.plan["batch05"] is Stage.SHADOW


def test_env_can_point_at_a_file(tmp_path):
    path = tmp_path / "plan.json"
    path.write_text(json.dumps({"name": "f", "batches": {"batch07": "pilot"}}), encoding="utf-8")
    policy = RolloutPolicy.from_env({"DISCERNMENT_ROLLOUT_PLAN": str(path)})
    assert policy.plan["batch07"] is Stage.PILOT


# --- decisions --------------------------------------------------------------

def test_skill_override_beats_the_batch_plan():
    registry = get_skill_registry()
    policy = RolloutPolicy.from_file()
    contract = registry.get("scrupulosity-and-trauma-guardian")
    assert contract.batch_key == "batch04"
    assert policy.plan["batch04"] is Stage.PILOT
    assert policy.decide(contract).stage is Stage.SHADOW


def test_unknown_batch_defaults_to_shadow():
    registry = get_skill_registry()
    policy = RolloutPolicy({}, name="empty")
    assert policy.decide(registry.get("content-corpus-curator")).stage is Stage.SHADOW


def test_decision_explains_itself():
    registry = get_skill_registry()
    decision = RolloutPolicy.staged().decide(registry.get("content-corpus-curator"))
    assert decision.reason
    assert decision.batch_key == "batch03"


def test_signoff_batch_decision_mentions_human_signature():
    registry = get_skill_registry()
    policy = RolloutPolicy.staged().promote("batch10", Stage.PRODUCTION)
    decision = policy.decide(registry.get("full-safety-red-team-runner"))
    assert decision.human_signoff_required
    assert "人工签署" in decision.reason


def test_signoff_forces_review_even_in_production():
    registry = get_skill_registry()
    policy = RolloutPolicy.staged().promote("batch10", Stage.PRODUCTION)
    decision = policy.decide(registry.get("full-safety-red-team-runner"))
    assert decision.human_review_required


# --- runtime integration ----------------------------------------------------

def test_disabled_stage_blocks_the_call(golden):
    runtime = runtime_with(RolloutPolicy.all_disabled(), golden)
    case = golden.get("content-corpus-curator")
    result = runtime.invoke(case.skill_id, case.input)
    assert result.status == "blocked_by_rollout"
    assert not result.authoritative
    assert result.limitations


def test_shadow_stage_runs_but_is_not_authoritative(golden):
    runtime = runtime_with(RolloutPolicy.staged(), golden)
    case = golden.get("law-mirror-controller")  # batch05, shadow
    result = runtime.invoke(case.skill_id, case.input)
    assert result.status == "shadow"
    assert not result.authoritative
    assert result.outputs


def test_pilot_stage_is_authoritative_and_flagged(golden):
    runtime = runtime_with(RolloutPolicy.staged(), golden)
    case = golden.get("content-corpus-curator")  # batch03, pilot
    result = runtime.invoke(case.skill_id, case.input)
    assert result.status == "ok"
    assert result.authoritative
    assert any("需人工复核" in item for item in result.limitations)


def test_production_stage_has_no_review_flag(golden):
    runtime = runtime_with(RolloutPolicy.unrestricted(), golden)
    case = golden.get("content-corpus-curator")
    result = runtime.invoke(case.skill_id, case.input)
    assert result.status == "ok"
    assert not any("需人工复核" in item for item in result.limitations)


def test_rollout_decision_is_attached_to_the_result(golden):
    runtime = runtime_with(RolloutPolicy.staged(), golden)
    case = golden.get("content-corpus-curator")
    result = runtime.invoke(case.skill_id, case.input)
    assert result.rollout["stage"] == "pilot"
    assert result.rollout["batch_key"] == "batch03"


def test_native_skills_are_not_gated_by_rollout():
    runtime = SkillRuntime(policy=RolloutPolicy.all_disabled())
    result = runtime.invoke("bible-reference-parser", {"text": "罗马书 8:1"})
    assert result.status == "ok"
    assert result.binding == "native"


def test_rollout_report_counts_model_bound_skills_only(golden):
    report = runtime_with(RolloutPolicy.staged(), golden).rollout_report()
    assert report["model_bound_skills"] == 82
    assert sum(report["by_stage"].values()) == 82


def test_rollout_report_lists_blocked_skills(golden):
    report = runtime_with(RolloutPolicy.all_disabled(), golden).rollout_report()
    assert len(report["blocked"]) == 82


def test_staged_plan_makes_a_minority_authoritative(golden):
    report = runtime_with(RolloutPolicy.staged(), golden).rollout_report()
    assert 0 < report["authoritative"] < report["model_bound_skills"]


def test_guardrails_still_apply_in_shadow(golden):
    """Shadow output is non-authoritative but must still be screened."""

    from backend.discernment_platform.model_adapter import ScriptedAdapter

    case = golden.get("law-mirror-controller")
    bad = {key: {"text": "他一定下地狱"} for key in case.golden_output}
    runtime = SkillRuntime(
        adapter=ScriptedAdapter({case.skill_id: bad}), policy=RolloutPolicy.staged()
    )
    result = runtime.invoke(case.skill_id, case.input)
    assert result.status == "blocked"
    assert result.failure_code == "GUARDRAIL_VIOLATION"


def test_null_adapter_still_reports_requires_model_regardless_of_stage():
    runtime = SkillRuntime(policy=RolloutPolicy.unrestricted())
    result = runtime.invoke("content-corpus-curator", {})
    assert result.status == "requires_model"
