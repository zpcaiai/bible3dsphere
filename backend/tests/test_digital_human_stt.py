"""Actual SDK configuration regression for short Chinese clause preservation."""
import json
import os
import subprocess
import sys

import pytest

from digital_human.agent_worker import create_transcription_session, transcription_config_snapshot


@pytest.fixture
def local_constructor_credentials(monkeypatch):
    for prefix in ["LIVEKIT", "LIVEKIT_INFERENCE"]:
        monkeypatch.setenv(prefix + "_API_KEY", "isolated-constructor-check")
        monkeypatch.setenv(prefix + "_API_SECRET", "isolated-constructor-check-32-bytes")
    monkeypatch.delenv("DIGITAL_HUMAN_STT_MODEL", raising=False)


@pytest.mark.asyncio
@pytest.mark.parametrize("descriptor,language", [
    ("deepgram/nova-3:multi", "multi"),
    ("deepgram/nova-3:en", "en"),
    ("deepgram/nova-2:zh-CN", "zh-CN"),
])
async def test_actual_nova_session_preserves_clauses_inside_original_deadlines(local_constructor_credentials, monkeypatch, descriptor, language):
    monkeypatch.setenv("DIGITAL_HUMAN_STT_MODEL", descriptor)
    session = create_transcription_session()
    assert session.stt._opts.language == language
    assert session.stt._opts.model == descriptor.split(":")[0]
    assert session.stt._opts.extra_kwargs.get("endpointing") == 300
    assert session.stt._opts.extra_kwargs["endpointing"] <= session.options.endpointing["min_delay"] * 1000
    assert session.options.endpointing == {"mode": "fixed", "alpha": 0.9, "min_delay": 0.45, "max_delay": 2.5}
    assert session.options.transcription_timeout == 8.0
    assert session.llm is None and session.tts is None
    assert not {"replace", "keyterm", "keywords", "language_hint"} & session.stt._opts.extra_kwargs.keys()
    await session.stt.aclose()


@pytest.mark.asyncio
async def test_non_nova_override_keeps_original_provider_options(local_constructor_credentials, monkeypatch):
    monkeypatch.setenv("DIGITAL_HUMAN_STT_MODEL", "cartesia/ink-whisper:zh")
    session = create_transcription_session()
    assert session.stt._opts.model == "cartesia/ink-whisper"
    assert session.stt._opts.language == "zh"
    assert session.stt._opts.extra_kwargs == {}
    await session.stt.aclose()


@pytest.mark.asyncio
async def test_blank_override_retains_multilingual_default(local_constructor_credentials, monkeypatch):
    monkeypatch.setenv("DIGITAL_HUMAN_STT_MODEL", " ")
    session = create_transcription_session()
    assert session.stt._opts.model == "deepgram/nova-3"
    assert session.stt._opts.language == "multi"
    assert session.options.transcription_timeout == 8.0
    await session.stt.aclose()


@pytest.mark.asyncio
async def test_runtime_snapshot_projects_only_public_settings(local_constructor_credentials):
    session = create_transcription_session()
    snapshot = transcription_config_snapshot(session)
    assert set(snapshot) == {"model", "language", "provider_endpointing_ms", "transcription_deadline_seconds", "inference_host", "worker_source_sha256", "sdk_version"}
    assert snapshot["provider_endpointing_ms"] == 300
    assert snapshot["transcription_deadline_seconds"] == 8.0
    assert len(snapshot["worker_source_sha256"]) == 64
    assert "isolated-constructor-check" not in json.dumps(snapshot)
    await session.stt.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("descriptor", [
    "google/gemini-3.5-transcribe-live",
    "cartesia/ink-whisper",
    "deepgram/nova-3",
])
async def test_auto_language_snapshot_is_json_serializable(local_constructor_credentials, monkeypatch, descriptor):
    monkeypatch.setenv("DIGITAL_HUMAN_STT_MODEL", descriptor)
    session = create_transcription_session()
    snapshot = transcription_config_snapshot(session)
    encoded = json.dumps(snapshot)
    assert json.loads(encoded)["language"] is None
    assert snapshot["model"] == descriptor
    assert snapshot["transcription_deadline_seconds"] == 8.0
    assert "isolated-constructor-check" not in encoded
    assert session.llm is None and session.tts is None
    await session.stt.aclose()


def test_worker_module_import_is_domain_independent():
    script = """
import sys
from digital_human.agent_worker import create_server
assert 'digital_human.service' not in sys.modules
assert type(create_server()).__name__ == 'AgentServer'
from digital_human import DigitalHumanService
from digital_human.service import DigitalHumanService as DirectService
assert DigitalHumanService is DirectService
import digital_human
try:
    digital_human.nonexistent_export
except AttributeError:
    print('actual isolated worker import and public service export passed')
else:
    raise AssertionError('Unknown package export must raise AttributeError')
"""
    result = subprocess.run([sys.executable, "-c", script], env=os.environ.copy(),
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "actual isolated worker import and public service export passed" in result.stdout
