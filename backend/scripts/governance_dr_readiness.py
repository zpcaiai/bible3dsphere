#!/usr/bin/env python3
"""Fail-closed evidence checker for database and deletion-tombstone DR drills."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED = {
    "postgres_restore_verified", "consent_restore_verified", "kill_switch_restore_verified",
    "deletion_tombstones_replayed", "event_replay_idempotent", "crisis_degradation_verified",
    "observed_rpo_minutes", "observed_rto_minutes", "evidence_reference",
}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("evidence", type=Path)
    args = parser.parse_args(); data = json.loads(args.evidence.read_text())
    missing = sorted(REQUIRED - set(data))
    false_checks = sorted(key for key in REQUIRED if key.endswith("_verified") or key.endswith("_replayed") or key.endswith("_idempotent") if not data.get(key))
    passed = not missing and not false_checks and bool(data.get("evidence_reference"))
    print(json.dumps({"passed": passed, "missing": missing, "failed_checks": false_checks}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
