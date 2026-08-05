from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import speech

pytestmark = pytest.mark.no_db


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(speech.router)
    return TestClient(app)


def test_transcribe_requires_backend_deepgram_key(monkeypatch):
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    monkeypatch.delenv("VITE_DEEPGRAM_API_KEY", raising=False)

    response = _client().post(
        "/api/speech/transcribe",
        files={"file": ("voice.webm", b"audio", "audio/webm")},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Speech transcription is not configured"


def test_legacy_vite_deepgram_key_is_temporarily_supported(monkeypatch):
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    monkeypatch.setenv("VITE_DEEPGRAM_API_KEY", "legacy-server-key")

    assert speech._deepgram_key() == "legacy-server-key"


def test_standard_deepgram_key_takes_priority(monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "server-key")
    monkeypatch.setenv("VITE_DEEPGRAM_API_KEY", "legacy-server-key")

    assert speech._deepgram_key() == "server-key"


def test_transcribe_rejects_non_audio_upload(monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "server-key")

    response = _client().post(
        "/api/speech/transcribe",
        files={"file": ("note.txt", b"not audio", "text/plain")},
    )

    assert response.status_code == 415


def test_transcribe_proxies_audio_to_deepgram(monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "server-key")
    calls = []

    class FakeResponse:
        status_code = 200
        text = ""

        def json(self):
            return {
                "results": {
                    "channels": [
                        {
                            "detected_language": "zh",
                            "alternatives": [{"transcript": "我感到平安"}],
                        }
                    ]
                }
            }

    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, params, headers, content):
            calls.append({"url": url, "params": params, "headers": headers, "content": content})
            return FakeResponse()

    monkeypatch.setattr(speech.httpx, "AsyncClient", FakeAsyncClient)

    response = _client().post(
        "/api/speech/transcribe",
        files={"file": ("voice.webm", b"audio-bytes", "audio/webm")},
        data={"language": "zh-CN"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "transcript": "我感到平安",
        "detected_language": "zh",
        "provider": "deepgram",
    }
    assert calls[0]["headers"]["Authorization"] == "Token server-key"
    assert calls[0]["headers"]["Content-Type"] == "audio/webm"
    assert calls[0]["content"] == b"audio-bytes"
    assert calls[0]["params"]["model"] == "nova-3"
    assert calls[0]["params"]["language"] == "zh-CN"
    assert calls[0]["params"]["keyterm"] == speech._BIBLE_KEYTERMS["zh-CN"]
    assert "detect_language" not in calls[0]["params"]


def test_transcribe_without_supported_language_uses_detection(monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "server-key")
    calls = []

    class FakeResponse:
        status_code = 200
        text = ""

        def json(self):
            return {
                "results": {
                    "channels": [
                        {
                            "detected_language": "en",
                            "alternatives": [{"transcript": "grace"}],
                        }
                    ]
                }
            }

    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, params, headers, content):
            calls.append(params)
            return FakeResponse()

    monkeypatch.setattr(speech.httpx, "AsyncClient", FakeAsyncClient)

    response = _client().post(
        "/api/speech/transcribe",
        files={"file": ("voice.webm", b"audio-bytes", "audio/webm")},
        data={"language": "unsupported"},
    )

    assert response.status_code == 200
    assert response.json()["detected_language"] == "en"
    assert calls[0]["model"] == "nova-3"
    assert calls[0]["detect_language"] == "true"
    assert "language" not in calls[0]
    assert "keyterm" not in calls[0]
