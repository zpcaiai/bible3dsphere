"""Focused no-DB hardening regressions for shared backend helpers."""

import asyncio

import pytest

pytestmark = pytest.mark.no_db


class _FakeConnection:
    def __init__(self):
        self.rollbacks = 0

    def rollback(self):
        self.rollbacks += 1


class _FailingCursor:
    def __init__(self):
        self.connection = _FakeConnection()

    def execute(self, sql, params=()):
        raise RuntimeError("missing optional table")


def test_formation_agent_optional_query_helpers_rollback_failed_transaction():
    from routers import formation_agent

    cur = _FailingCursor()

    assert formation_agent._count(cur, "SELECT COUNT(*) FROM optional_table") == 0
    assert cur.connection.rollbacks == 1

    assert formation_agent._exists(cur, "SELECT 1 FROM optional_table") is False
    assert cur.connection.rollbacks == 2


class _FakeResponse:
    def __init__(self, status_code=200, data=None, text=""):
        self.status_code = status_code
        self._data = data or {}
        self.text = text

    def json(self):
        return self._data


class _FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.posts = []

    def post(self, url, **kwargs):
        self.posts.append({"url": url, **kwargs})
        if not self.responses:
            raise AssertionError("unexpected HTTP call")
        return self.responses.pop(0)


def test_openai_provider_applies_default_max_tokens_when_called_directly(monkeypatch):
    import llm_provider

    client = _FakeClient([
        _FakeResponse(data={
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        })
    ])
    monkeypatch.setattr(llm_provider, "_http_client", lambda: client)

    provider = llm_provider.OpenAICompatibleProvider(api_key="test")
    resp = provider.complete([{"role": "user", "content": "hello"}])

    assert resp.text == "ok"
    assert client.posts[0]["json"]["max_tokens"] == llm_provider.DEFAULT_MAX_TOKENS


def test_anthropic_provider_retries_retryable_errors_and_uses_default_max_tokens(monkeypatch):
    import llm_provider

    client = _FakeClient([
        _FakeResponse(status_code=503, text="temporarily unavailable"),
        _FakeResponse(data={
            "content": [{"type": "text", "text": "ok"}],
            "usage": {"input_tokens": 2, "output_tokens": 3},
        }),
    ])
    monkeypatch.setattr(llm_provider, "_http_client", lambda: client)
    monkeypatch.setattr(llm_provider.time, "sleep", lambda _seconds: None)

    provider = llm_provider.AnthropicCompatibleProvider(api_key="test", max_retries=1)
    resp = provider.complete([{"role": "user", "content": "hello"}])

    assert resp.text == "ok"
    assert len(client.posts) == 2
    assert client.posts[0]["json"]["max_tokens"] == llm_provider.DEFAULT_MAX_TOKENS


def test_anthropic_provider_fails_fast_on_non_retryable_4xx(monkeypatch):
    import llm_provider

    client = _FakeClient([
        _FakeResponse(status_code=401, text="bad key"),
    ])
    monkeypatch.setattr(llm_provider, "_http_client", lambda: client)

    provider = llm_provider.AnthropicCompatibleProvider(api_key="bad", max_retries=2)

    with pytest.raises(llm_provider.LLMError):
        provider.complete([{"role": "user", "content": "hello"}])
    assert len(client.posts) == 1


def test_deferred_startup_serves_liveness_and_guards_other_apis(monkeypatch):
    from fastapi.testclient import TestClient
    import main

    initialization_started = asyncio.Event()

    async def slow_initialization(_app):
        initialization_started.set()
        await asyncio.Event().wait()

    monkeypatch.setenv("DEFER_STARTUP_INITIALIZATION", "1")
    monkeypatch.setattr(main, "_initialize_runtime", slow_initialization)
    from routers import realtime

    monkeypatch.setitem(realtime._state, "get_session_user", lambda request: None)

    try:
        with TestClient(main.app) as client:
            assert initialization_started.is_set()

            live = client.get("/health/live")
            assert live.status_code == 200
            assert live.json()["status"] == "live"

            guarded = client.get("/api/ai-status")
            assert guarded.status_code == 503
            assert guarded.headers["Retry-After"] == "5"
            assert guarded.json()["status"] == "starting"

            realtime_ticket = client.post("/api/rtc/ws-ticket")
            assert realtime_ticket.status_code == 401
    finally:
        main._runtime_ready.set()
