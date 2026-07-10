#!/usr/bin/env python3
"""Static security audit for Attention Stewardship backend files."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

from attention_integration import static_log_scan  # noqa: E402


FILES = [
    ROOT / "backend" / "routers" / "attention.py",
    ROOT / "backend" / "attention_accountability.py",
]


def main() -> None:
    failures = []
    source = (ROOT / "backend" / "routers" / "attention.py").read_text(encoding="utf-8")
    checks = [
        ("auth_helper_present", "_require_user(request)" in source),
        ("admin_helper_present", "_require_attention_admin(request)" in source),
        ("share_active_relationship_check", "_has_active_relationship" in source),
        ("group_membership_check", "_require_group_member" in source),
        ("revoked_share_filtered", "revoked_at IS NULL" in source),
        ("no_user_id_body_trust_for_personal_tables", not re.search(r"body\\.user_?id", source)),
        ("crisis_safety_flow_present", "safety_check" in source and "crisis" in source),
        ("ai_fallback_present", "generate_fallback_diagnosis" in source),
    ]
    for key, ok in checks:
        if not ok:
            failures.append({"key": key, "status": "fail"})
    log_scan = static_log_scan(FILES)
    report = {"ok": not failures and log_scan["ok"], "failures": failures, "logScan": log_scan}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
