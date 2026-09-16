"""Replay the golden set against a live provider and diff the result.

This is the pre-rollout gate: before promoting a batch from ``shadow`` to
``pilot`` (or ``pilot`` to ``production``), run it here, read the transcript,
and only promote if the diffs are ones you accept.

Every call goes through ``RecordingAdapter``, so the full prompt/response
exchange is written to the report for human review - the point is to look at
what the model actually said, not just whether it parsed.

Examples
--------

    # offline sanity check - replays the goldens through ScriptedAdapter
    python tools/run_golden_set.py --provider scripted

    # one batch against Claude, staged policy, write a transcript
    ANTHROPIC_API_KEY=... python tools/run_golden_set.py \
        --provider anthropic --batch batch03 --out reports/batch03.json

    # a local model, everything, ignore the rollout gate
    python tools/run_golden_set.py --provider local --policy unrestricted

Exit code is non-zero when any selected case regresses, so this can gate CI.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.discernment_platform.golden import GoldenSet, diff_shape  # noqa: E402
from backend.discernment_platform.model_adapter import (  # noqa: E402
    RecordingAdapter,
    build_adapter,
)
from backend.discernment_platform.rollout import RolloutPolicy  # noqa: E402
from backend.discernment_platform.skill_runtime import (  # noqa: E402
    SkillInvocationError,
    SkillRuntime,
)

ACCEPTED_STATUSES = {"ok", "shadow"}


def build_policy(name: str) -> RolloutPolicy:
    lowered = name.strip().lower()
    if lowered in {"staged", "default"}:
        return RolloutPolicy.staged()
    if lowered in {"unrestricted", "all"}:
        return RolloutPolicy.unrestricted()
    if lowered in {"file", "config"}:
        return RolloutPolicy.from_file()
    return RolloutPolicy.from_file(Path(name))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--provider",
        default="scripted",
        help="scripted (offline replay) | anthropic | openai | gemini | local | null",
    )
    parser.add_argument("--model", default=None, help="model name override")
    parser.add_argument("--batch", default=None, help="restrict to one batch, e.g. batch03")
    parser.add_argument("--skill", default=None, help="restrict to one skill_id")
    parser.add_argument("--tier", choices=["curated", "structural"], default=None)
    parser.add_argument("--limit", type=int, default=0, help="cap the number of cases")
    parser.add_argument("--policy", default="file", help="staged | unrestricted | file | <path>")
    parser.add_argument("--out", default=None, help="write the JSON report here")
    parser.add_argument(
        "--show-prompts",
        action="store_true",
        help="include full prompts in the report (verbose, but this is the point of a review run)",
    )
    return parser.parse_args(argv)


def select(golden: GoldenSet, args: argparse.Namespace) -> list:
    cases = list(golden)
    if args.batch:
        cases = [c for c in cases if c.batch_key == args.batch]
    if args.skill:
        cases = [c for c in cases if c.skill_id == args.skill]
    if args.tier:
        cases = [c for c in cases if c.tier == args.tier]
    cases.sort(key=lambda c: (c.batch_key, c.skill_id))
    if args.limit:
        cases = cases[: args.limit]
    return cases


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    golden = GoldenSet().load()
    cases = select(golden, args)
    if not cases:
        print("no cases selected", file=sys.stderr)
        return 2

    try:
        if args.provider == "scripted":
            inner = golden.scripted_adapter()
        else:
            kwargs = {"model": args.model} if args.model else {}
            inner = build_adapter(args.provider, **kwargs)
    except SkillInvocationError as exc:
        print(f"cannot start: {exc.message}", file=sys.stderr)
        return 2
    recorder = RecordingAdapter(inner)
    policy = build_policy(args.policy)
    runtime = SkillRuntime(adapter=recorder, policy=policy)

    records = []
    regressions = 0
    for case in cases:
        result = runtime.invoke(case.skill_id, case.input)
        diffs = (
            diff_shape(case.golden_output, result.outputs)
            if result.status in ACCEPTED_STATUSES
            else []
        )
        violations = [
            finding["guardrail"]
            for finding in result.guardrail_findings
            if finding["status"] == "violation"
        ]
        regressed = result.status not in ACCEPTED_STATUSES or bool(diffs) or bool(violations)
        regressions += int(regressed)
        record = {
            "skill_id": case.skill_id,
            "skill_name": case.skill_name,
            "batch": case.batch_key,
            "tier": case.tier,
            "status": result.status,
            "authoritative": result.authoritative,
            "rollout_stage": (result.rollout or {}).get("stage"),
            "shape_diffs": diffs,
            "guardrail_violations": violations,
            "regressed": regressed,
            "message": result.message,
            "limitations": result.limitations,
            "usage": (result.trace or {}).get("usage"),
            "live_output": result.outputs,
            "golden_output": case.golden_output,
        }
        if args.show_prompts:
            record["prompt"] = result.prompt
        records.append(record)

    report = {
        "provider": getattr(inner, "name", args.provider),
        "policy": policy.as_dict(),
        "selected": len(cases),
        "regressions": regressions,
        "passed": len(cases) - regressions,
        "by_batch": _by_batch(records),
        "transcript": recorder.transcript(),
        "cases": records,
    }

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    _print_summary(report, records)
    return 1 if regressions else 0


def _by_batch(records: list[dict]) -> dict:
    summary: dict[str, dict] = {}
    for record in records:
        entry = summary.setdefault(
            record["batch"], {"total": 0, "regressed": 0, "stages": {}}
        )
        entry["total"] += 1
        entry["regressed"] += int(record["regressed"])
        stage = record["rollout_stage"] or "n/a"
        entry["stages"][stage] = entry["stages"].get(stage, 0) + 1
    return dict(sorted(summary.items()))


def _print_summary(report: dict, records: list[dict]) -> None:
    print(f"provider: {report['provider']}   policy: {report['policy']['name']}")
    print(f"cases: {report['selected']}   passed: {report['passed']}   regressions: {report['regressions']}")
    print()
    print(f"{'batch':<10} {'total':>6} {'regressed':>10}  stages")
    for batch, entry in report["by_batch"].items():
        stages = ", ".join(f"{k}:{v}" for k, v in sorted(entry["stages"].items()))
        print(f"{batch:<10} {entry['total']:>6} {entry['regressed']:>10}  {stages}")
    failing = [r for r in records if r["regressed"]]
    if failing:
        print("\nregressions:")
        for record in failing:
            detail = record["shape_diffs"][:3] or record["guardrail_violations"][:3] or record["message"][:120]
            print(f"  {record['skill_id']:<45} {record['status']:<18} {detail}")


if __name__ == "__main__":
    raise SystemExit(main())
