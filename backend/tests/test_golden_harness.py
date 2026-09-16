"""Tests for the golden-set replay harness (``tools/run_golden_set.py``).

The harness is the gate operators run before promoting a batch, so its exit
codes and regression detection are load-bearing and get tested like code.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from backend.discernment_platform.rollout import Stage

pytestmark = pytest.mark.no_db

HARNESS_PATH = Path(__file__).resolve().parents[2] / "tools" / "run_golden_set.py"


@pytest.fixture(scope="module")
def harness():
    spec = importlib.util.spec_from_file_location("run_golden_set", HARNESS_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_harness_file_ships_with_the_repo():
    assert HARNESS_PATH.exists()


# --- policy resolution ------------------------------------------------------

def test_policy_staged(harness):
    assert harness.build_policy("staged").name == "staged"


def test_policy_unrestricted(harness):
    policy = harness.build_policy("unrestricted")
    assert set(policy.plan.values()) == {Stage.PRODUCTION}


def test_policy_from_shipped_file(harness):
    assert harness.build_policy("file").name == "first-wave"


def test_policy_from_explicit_path(harness, tmp_path):
    path = tmp_path / "p.json"
    path.write_text(json.dumps({"name": "p", "batches": {"batch03": "shadow"}}), encoding="utf-8")
    assert harness.build_policy(str(path)).plan["batch03"] is Stage.SHADOW


# --- selection --------------------------------------------------------------

def _args(harness, **kw):
    args = harness.parse_args([])
    for key, value in kw.items():
        setattr(args, key, value)
    return args


def test_selection_defaults_to_everything(harness):
    from backend.discernment_platform.golden import get_golden_set

    golden = get_golden_set()
    assert len(harness.select(golden, _args(harness))) == len(golden)


def test_selection_by_batch(harness):
    from backend.discernment_platform.golden import get_golden_set

    cases = harness.select(get_golden_set(), _args(harness, batch="batch09"))
    assert cases and all(c.batch_key == "batch09" for c in cases)


def test_selection_by_skill(harness):
    from backend.discernment_platform.golden import get_golden_set

    cases = harness.select(get_golden_set(), _args(harness, skill="content-corpus-curator"))
    assert [c.skill_id for c in cases] == ["content-corpus-curator"]


def test_selection_by_tier(harness):
    from backend.discernment_platform.golden import get_golden_set

    cases = harness.select(get_golden_set(), _args(harness, tier="curated"))
    assert cases and all(c.curated for c in cases)


def test_selection_limit_caps_the_run(harness):
    from backend.discernment_platform.golden import get_golden_set

    assert len(harness.select(get_golden_set(), _args(harness, limit=5))) == 5


def test_selection_is_deterministically_ordered(harness):
    from backend.discernment_platform.golden import get_golden_set

    golden = get_golden_set()
    first = [(c.batch_key, c.skill_id) for c in harness.select(golden, _args(harness))]
    second = [(c.batch_key, c.skill_id) for c in harness.select(golden, _args(harness))]
    assert first == second == sorted(first)


# --- argument parsing -------------------------------------------------------

def test_default_provider_is_offline(harness):
    assert harness.parse_args([]).provider == "scripted"


def test_default_policy_is_the_shipped_file(harness):
    assert harness.parse_args([]).policy == "file"


def test_flags_are_parsed(harness):
    args = harness.parse_args(
        ["--provider", "local", "--batch", "batch03", "--limit", "3", "--show-prompts"]
    )
    assert args.provider == "local"
    assert args.batch == "batch03"
    assert args.limit == 3
    assert args.show_prompts is True


# --- end-to-end runs --------------------------------------------------------

def test_offline_replay_of_the_whole_set_passes(harness):
    assert harness.main(["--provider", "scripted", "--policy", "unrestricted"]) == 0


def test_offline_replay_under_the_staged_plan_passes(harness):
    """Shadow output is not a regression - it is the expected staged behaviour."""

    assert harness.main(["--provider", "scripted", "--policy", "file"]) == 0


def test_disabled_plan_is_reported_as_a_regression(harness, tmp_path):
    path = tmp_path / "off.json"
    path.write_text(
        json.dumps({"name": "off", "batches": {key: "disabled" for key in
                                               ["batch03", "batch04", "batch05",
                                                "batch07", "batch08", "batch09", "batch10"]}}),
        encoding="utf-8",
    )
    assert harness.main(["--provider", "scripted", "--policy", str(path)]) == 1


def test_unknown_provider_exits_two(harness):
    assert harness.main(["--provider", "gemini", "--limit", "1"]) == 2


def test_missing_credentials_exit_two(harness, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert harness.main(["--provider", "anthropic", "--limit", "1"]) == 2


def test_empty_selection_exits_two(harness):
    assert harness.main(["--skill", "no-such-skill"]) == 2


def test_report_is_written_and_well_formed(harness, tmp_path):
    out = tmp_path / "nested" / "report.json"
    assert harness.main(
        ["--provider", "scripted", "--policy", "unrestricted", "--batch", "batch09",
         "--out", str(out)]
    ) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["selected"] == report["passed"] == 10
    assert report["regressions"] == 0
    assert report["by_batch"]["batch09"]["total"] == 10
    assert report["provider"] == "scripted"


def test_report_records_both_live_and_golden_output(harness, tmp_path):
    out = tmp_path / "r.json"
    harness.main(
        ["--provider", "scripted", "--policy", "unrestricted", "--limit", "2", "--out", str(out)]
    )
    case = json.loads(out.read_text(encoding="utf-8"))["cases"][0]
    assert case["live_output"]
    assert case["golden_output"]
    assert case["shape_diffs"] == []


def test_report_includes_the_transcript_for_review(harness, tmp_path):
    out = tmp_path / "r.json"
    harness.main(
        ["--provider", "scripted", "--policy", "unrestricted", "--limit", "3", "--out", str(out)]
    )
    report = json.loads(out.read_text(encoding="utf-8"))
    assert len(report["transcript"]) == 3
    assert report["transcript"][0]["schema_keys"]


def test_show_prompts_includes_the_rendered_prompt(harness, tmp_path):
    out = tmp_path / "r.json"
    harness.main(
        ["--provider", "scripted", "--policy", "unrestricted", "--limit", "1",
         "--show-prompts", "--out", str(out)]
    )
    prompt = json.loads(out.read_text(encoding="utf-8"))["cases"][0]["prompt"]
    assert "Guardrails" in prompt
    assert "Processing Contract" in prompt


def test_staged_run_records_the_rollout_stage(harness, tmp_path):
    out = tmp_path / "r.json"
    harness.main(
        ["--provider", "scripted", "--policy", "file", "--batch", "batch05", "--out", str(out)]
    )
    cases = json.loads(out.read_text(encoding="utf-8"))["cases"]
    assert all(c["rollout_stage"] == "shadow" for c in cases)
    assert all(c["authoritative"] is False for c in cases)


def test_pilot_batch_is_reported_as_authoritative(harness, tmp_path):
    out = tmp_path / "r.json"
    harness.main(
        ["--provider", "scripted", "--policy", "file", "--batch", "batch09", "--out", str(out)]
    )
    cases = json.loads(out.read_text(encoding="utf-8"))["cases"]
    assert all(c["rollout_stage"] == "pilot" for c in cases)
    assert all(c["authoritative"] for c in cases)
