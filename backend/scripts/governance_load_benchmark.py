#!/usr/bin/env python3
"""Deterministic, synthetic-only Scenario policy micro-benchmark."""
from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import datetime, timezone

from production_governance.scenarios import ScenarioCreate, build_scenario


def case(index: int) -> ScenarioCreate:
    now = datetime.now(timezone.utc)
    return ScenarioCreate(
        title=f"synthetic-{index}", question="未来七天值得观察什么？",
        scenario_type="CONTINUE_CURRENT_PATTERN", baseline_snapshot_ids=["00000000-0000-0000-0000-000000000001"],
        baseline_generated_at=now,
        assumptions=[{
            "assumption_type": "USER_DEFINED_BASELINE", "description": "当前负担保持不变。",
            "source_kind": "USER_DEFINED", "source_reference_ids": [], "user_confirmed": True,
            "uncertainty": "外部环境目前无法确定。",
        }],
        fixed_constraints=[], excluded_factors=["他人的决定"], horizon="NEXT_7_DAYS",
        evidence=[{
            "evidence_level": "USER_CONFIRMED_EFFECT", "source_reference_id": f"synthetic:{index}",
            "summary": "过去记录中，休息与较低负担曾同时出现。", "supports_branch": True,
            "user_confirmed": True,
        }],
    )


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--iterations", type=int, default=1000)
    args = parser.parse_args()
    if not 1 <= args.iterations <= 100_000:
        raise SystemExit("iterations must be between 1 and 100000")
    durations: list[float] = []
    start = time.perf_counter()
    for index in range(args.iterations):
        item = case(index); tick = time.perf_counter(); result = build_scenario(item)
        assert len(result.branches) <= 3 and result.model_version is None
        durations.append((time.perf_counter() - tick) * 1000)
    elapsed = time.perf_counter() - start
    ordered = sorted(durations)
    p95 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))]
    print(json.dumps({
        "data_source": "SYNTHETIC", "iterations": args.iterations,
        "throughput_per_second": round(args.iterations / elapsed, 2),
        "mean_ms": round(statistics.fmean(durations), 4), "p95_ms": round(p95, 4),
        "side_effects": 0, "model_calls": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
