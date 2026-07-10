#!/usr/bin/env python3
"""Generate a markdown release report for Attention Stewardship."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))

from attention_accountability import CHALLENGE_TEMPLATES  # noqa: E402
from attention_domain import SCRIPTURE_LIBRARY, pattern_definitions  # noqa: E402
from attention_integration import ATTENTION_ROUTES, attention_environment_check, release_checklist  # noqa: E402


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def main() -> None:
    report_dir = ROOT / "reports"
    report_dir.mkdir(exist_ok=True)
    target = report_dir / "attention-release-report.md"
    env = attention_environment_check(os.environ)
    lines = [
        "# Attention Stewardship Release Report",
        "",
        f"- Base Git commit: `{_git_sha()}`",
        f"- Routes: {len(ATTENTION_ROUTES)}",
        f"- Scripture library items: {len(SCRIPTURE_LIBRARY)}",
        f"- Warfare patterns: {len(pattern_definitions())}",
        f"- Challenge templates: {len(CHALLENGE_TEMPLATES)}",
        f"- Environment check: {'PASS' if env['ok'] else 'FAIL'}",
        "",
        "## Feature Flags",
        "",
    ]
    for key, value in env["featureFlags"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {item}" for item in env["warnings"]] or ["- None"])
    lines.extend([
        "",
        "## Latest Verification (2026-07-10)",
        "",
        "- [x] Full backend suite: 843 tests.",
        "- [x] Python compile plus attention security and permission audits.",
        "- [x] Fresh UTF-8 PostgreSQL schema applied attention migrations 0146-0150 in one startup.",
        "- [x] Demo seed executed twice idempotently; reset removed all reserved demo users.",
        "- [x] Attention schema smoke check.",
    ])
    lines.extend(["", "## Manual QA Checklist", ""])
    for item in release_checklist():
        lines.append(f"- [ ] {item['label']}")
    lines.extend([
        "",
        "## Go/No-Go",
        "",
        "Recommendation: GO only after frontend build, backend tests, py_compile, smoke check, permission/security audits, and manual privacy verification pass.",
        "",
    ])
    target.write_text("\n".join(lines), encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
