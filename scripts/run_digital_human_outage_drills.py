#!/usr/bin/env python3
"""Deterministic vendor-outage drills; no provider credentials are consumed."""
from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.digital_human.livekit import mint_token, runtime_configured
from backend.digital_human.metrics import DigitalHumanMetrics
from backend.digital_human.registry import _asset_manifest, character_profile, content_review_state
from backend.digital_human.service import DigitalHumanService


@contextmanager
def environment(**values):
    before = {key: os.environ.get(key) for key in values}
    try:
        for key, value in values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        _asset_manifest.cache_clear()
        yield
    finally:
        for key, value in before.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        _asset_manifest.cache_clear()


def main() -> int:
    checks: list[dict[str, object]] = []
    with environment(LIVEKIT_URL=None, LIVEKIT_API_KEY=None, LIVEKIT_API_SECRET=None, DIGITAL_HUMAN_LIVEKIT_AGENT_READY=None):
        blocked = False
        try:
            mint_token(email="drill@example.test", session_id="session_drill", character_id="david")
        except RuntimeError:
            blocked = True
        checks.append({"id": "livekit-unavailable", "passed": not runtime_configured() and blocked, "fallback": "TEXT_INPUT"})

    with environment(DIGITAL_HUMAN_ASSET_MANIFEST_JSON='{"schemaVersion":"digital-human-assets/v1","characters":{"david":{"reviewState":"APPROVED","modelUrl":"https://cdn.invalid/david.glb"}}}'):
        profile = character_profile("david")
        checks.append({"id": "malformed-assets", "passed": bool(profile and not profile.runtimeReady and not profile.avatar.modelUrl), "fallback": "PORTRAIT_TEXT"})

    with environment(DIGITAL_HUMAN_RELEASE_CERTIFICATE_PATH=None, DIGITAL_HUMAN_TRUSTED_RELEASE_KEYS_PATH=None):
        turn = DigitalHumanService().answer(character_id="david", question="你为什么没有杀扫罗？")
        checks.append({"id": "release-evidence-missing", "passed": content_review_state() == "THEOLOGY_REVIEW" and turn.state == "TEXT_ONLY" and not turn.response.speechApproved, "fallback": "TEXT_ONLY"})

    drill_metrics = DigitalHumanMetrics()
    drill_metrics.record_provider(provider="livekit", state="FALLBACK")
    drill_metrics.record_provider(provider="livespeak", state="ERROR")
    snapshot = drill_metrics.snapshot()
    checks.append({"id": "provider-alert-visibility", "passed": snapshot["providers"]["livekit"]["lastState"] == "FALLBACK" and snapshot["providers"]["livespeak"]["lastState"] == "ERROR", "fallback": "OBSERVABLE"})

    passed = all(bool(item["passed"]) for item in checks)
    print(json.dumps({"schemaVersion": "digital-human-outage-drill/v1", "result": "PASS" if passed else "FAIL", "checks": checks, "containsRawContent": False}, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
