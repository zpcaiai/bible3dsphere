#!/usr/bin/env python3
"""Offline Batch 10 release gate; exits non-zero on any safety blocker."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from platform_orchestration.data_quality import scan_platform_contracts
from production_governance.evaluation import run_builtin_red_team
from production_governance.release import ReleaseCandidateSpec, evaluate_release_candidate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path, nargs="?", help="JSON release-candidate evidence")
    parser.add_argument("--batch08-available", action="store_true")
    args = parser.parse_args()

    platform = scan_platform_contracts()
    red_team = run_builtin_red_team()
    result = {"platform_contracts": platform, "red_team": red_team, "release": None}
    passed = platform["ok"] and red_team["pass"]
    if args.evidence:
        candidate = ReleaseCandidateSpec.model_validate_json(args.evidence.read_text())
        decision = evaluate_release_candidate(candidate, batch08_available=args.batch08_available)
        result["release"] = decision
        passed = passed and decision["passed"]
    print(json.dumps({"passed": passed, **result}, ensure_ascii=False, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
