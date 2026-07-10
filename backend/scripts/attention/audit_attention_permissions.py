#!/usr/bin/env python3
"""Fail-closed static permission matrix for Attention Stewardship routes."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE = (ROOT / "backend" / "routers" / "attention.py").read_text(encoding="utf-8")


CHECKS = [
    ("owner", "personal covenant/entry/review", "can", "user_id=%s" in SOURCE),
    ("ordinary-user", "other-user personal records", "cannot", "AND user_id=%s" in SOURCE),
    ("active-partner", "partner share", "can", "_has_active_relationship" in SOURCE),
    ("ended-partner", "old partner share", "cannot", "row[2] == \"partner\" and not _has_active_relationship" in SOURCE),
    ("share-recipient", "revoked share", "cannot", "if row[12]:" in SOURCE and "revoked_at IS NULL" in SOURCE),
    ("group-member", "group challenge", "can", "_require_group_member" in SOURCE),
    ("non-member", "group challenge", "cannot", "_challenge_access_row" in SOURCE),
    ("group-leader", "member private ledger", "cannot", "attention_entries" not in SOURCE[SOURCE.find("def list_attention_group_members"):SOURCE.find("def update_attention_group_member")]),
    ("prayer-recipient", "sensitive prayer body", "cannot", "may_see_body" in SOURCE and "not is_sensitive" in SOURCE),
    ("ordinary-user", "admin overview", "cannot", "_require_attention_admin(request)" in SOURCE),
]


def main() -> None:
    matrix = [
        {"role": role, "resource": resource, "expected": expected, "status": "pass" if ok else "fail"}
        for role, resource, expected, ok in CHECKS
    ]
    failures = [item for item in matrix if item["status"] == "fail"]
    print(json.dumps({"ok": not failures, "matrix": matrix, "failures": failures}, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
