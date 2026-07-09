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

    response = _client().post(
        "/api/speech/transcribe",
        files={"file": ("voice.webm", b"audio", "audio/webm")},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Speech transcription is not configured"


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
