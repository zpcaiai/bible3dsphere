import json

import pytest

from digital_human.readiness import runtime_readiness
from digital_human.registry import _asset_manifest

pytestmark = pytest.mark.no_db


def test_unconfigured_readiness_is_honest_and_contains_no_secret(monkeypatch):
    for key in ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "DIGITAL_HUMAN_LIVEKIT_AGENT_READY", "DIGITAL_HUMAN_RELEASE_CERTIFICATE_PATH", "DIGITAL_HUMAN_ASSET_MANIFEST_JSON"):
        monkeypatch.delenv(key, raising=False)
    _asset_manifest.cache_clear()
    result = runtime_readiness(livespeak_configured=False)
    assert result["characterCount"] == 100
    assert result["truthCaseCount"] == 532
    assert result["preparedAnswerCount"] == 5
    assert result["preparedAnswerCharacterCount"] == 4
    assert result["validatedAssetCharacterCount"] == 0
    assert result["runtimeReadyCharacterCount"] == 0
    assert result["productAssurance"] == "NOT_CERTIFIED"
    states = {item["code"]: item["state"] for item in result["requirements"]}
    assert states["CONTENT_REVIEW"] == "PENDING_REVIEW"
    assert states["LIVEKIT_PROJECT"] == "MISSING"
    assert states["REAL_VOICE_JOURNEY"] == "NOT_VERIFIED"


def test_configuration_presence_never_claims_real_vendor_execution(monkeypatch):
    sentinel = "sensitive-sentinel-must-not-appear"
    for key in ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"):
        monkeypatch.setenv(key, sentinel)
    monkeypatch.setenv("DIGITAL_HUMAN_LIVEKIT_AGENT_READY", "true")
    result = runtime_readiness(livespeak_configured=True)
    assert sentinel not in json.dumps(result)
    states = {item["code"]: item["state"] for item in result["requirements"]}
    assert states["LIVEKIT_PROJECT"] == "CONFIGURED"
    assert states["STT_WORKER"] == "DECLARED"
    assert states["REAL_VOICE_JOURNEY"] == "NOT_VERIFIED"
    assert result["productAssurance"] == "NOT_CERTIFIED"
