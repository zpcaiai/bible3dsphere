"""Tests for the provider-neutral model adapter layer.

No network is used anywhere: SDK clients and the HTTP opener are injected.
"""

from __future__ import annotations

import json
import types
import urllib.error

import pytest

from backend.discernment_platform.model_adapter import (
    AnthropicAdapter,
    BaseModelAdapter,
    LocalOpenAIAdapter,
    OpenAIAdapter,
    RecordingAdapter,
    ScriptedAdapter,
    build_adapter,
    build_adapter_from_env,
    extract_json,
    missing_keys,
    repair_instruction,
)
from backend.discernment_platform.skill_runtime import (
    NullAdapter,
    SkillInvocationError,
    SkillRuntime,
    get_runtime,
)
from backend.discernment_platform.skills import get_skill_registry

pytestmark = pytest.mark.no_db

SCHEMA = {"findings": "list of findings", "limitations": "list of limitations"}


# --- JSON extraction --------------------------------------------------------

def test_extract_plain_json():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_fenced_json():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_unlabelled_fence():
    assert extract_json('```\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_after_prose():
    assert extract_json('Here is the result:\n{"a": 1}\nHope that helps.') == {"a": 1}


def test_extract_rejects_array():
    with pytest.raises(SkillInvocationError) as exc:
        extract_json("[1, 2, 3]")
    assert exc.value.code == "MODEL_OUTPUT_INVALID"


def test_extract_rejects_empty():
    with pytest.raises(SkillInvocationError):
        extract_json("   ")


def test_extract_rejects_garbage():
    with pytest.raises(SkillInvocationError):
        extract_json("I cannot help with that.")


def test_extract_handles_nested_objects():
    assert extract_json('{"a": {"b": [1, {"c": 2}]}}')["a"]["b"][1]["c"] == 2


def test_missing_keys_reports_absent():
    assert missing_keys({"findings": []}, SCHEMA) == ["limitations"]


def test_repair_instruction_names_missing_keys():
    text = repair_instruction({"findings": []}, SCHEMA)
    assert "limitations" in text
    assert "never invent" in text


# --- retry / repair ---------------------------------------------------------

class SequenceAdapter(BaseModelAdapter):
    name = "sequence"

    def __init__(self, replies, **kw):
        super().__init__(**kw)
        self.replies = list(replies)
        self.prompts = []

    def _generate(self, prompt):
        self.prompts.append(prompt)
        return self.replies.pop(0) if self.replies else "{}"


def test_first_attempt_success_does_not_retry():
    adapter = SequenceAdapter(['{"findings": [], "limitations": []}'])
    adapter.complete("p", schema=SCHEMA)
    assert len(adapter.prompts) == 1
    assert adapter.last_usage.attempts == 1


def test_missing_key_triggers_repair_retry():
    adapter = SequenceAdapter(
        ['{"findings": []}', '{"findings": [], "limitations": ["x"]}']
    )
    result = adapter.complete("p", schema=SCHEMA)
    assert result["limitations"] == ["x"]
    assert len(adapter.prompts) == 2
    assert "Repair required" in adapter.prompts[1]


def test_invalid_json_triggers_repair_retry():
    adapter = SequenceAdapter(["not json", '{"findings": [], "limitations": []}'])
    adapter.complete("p", schema=SCHEMA)
    assert "not valid JSON" in adapter.prompts[1]


def test_exhausted_attempts_raise_invalid_output():
    adapter = SequenceAdapter(['{"findings": []}', '{"findings": []}'])
    with pytest.raises(SkillInvocationError) as exc:
        adapter.complete("p", schema=SCHEMA)
    assert exc.value.code == "MODEL_OUTPUT_INVALID"
    assert "limitations" in exc.value.message


def test_extra_keys_are_dropped():
    adapter = SequenceAdapter(['{"findings": [], "limitations": [], "extra": 1}'])
    assert set(adapter.complete("p", schema=SCHEMA)) == set(SCHEMA)


def test_max_attempts_is_respected():
    adapter = SequenceAdapter(["bad", "bad", "bad"], max_attempts=3)
    with pytest.raises(SkillInvocationError):
        adapter.complete("p", schema=SCHEMA)
    assert len(adapter.prompts) == 3


# --- Anthropic --------------------------------------------------------------

def fake_anthropic_client(text, *, input_tokens=11, output_tokens=22, error=None):
    def create(**kwargs):
        if error:
            raise error
        return types.SimpleNamespace(
            content=[types.SimpleNamespace(text=text)],
            usage=types.SimpleNamespace(
                input_tokens=input_tokens, output_tokens=output_tokens
            ),
        )

    return types.SimpleNamespace(messages=types.SimpleNamespace(create=create))


def test_anthropic_adapter_returns_parsed_payload():
    adapter = AnthropicAdapter(
        client=fake_anthropic_client('{"findings": [1], "limitations": []}')
    )
    assert adapter.complete("p", schema=SCHEMA)["findings"] == [1]
    assert adapter.name == "anthropic"


def test_anthropic_adapter_records_usage():
    adapter = AnthropicAdapter(
        client=fake_anthropic_client('{"findings": [], "limitations": []}')
    )
    adapter.complete("p", schema=SCHEMA)
    assert adapter.last_usage.input_tokens == 11
    assert adapter.last_usage.output_tokens == 22


def test_anthropic_adapter_wraps_provider_errors():
    adapter = AnthropicAdapter(client=fake_anthropic_client("", error=RuntimeError("429")))
    with pytest.raises(SkillInvocationError) as exc:
        adapter.complete("p", schema=SCHEMA)
    assert exc.value.code == "HANDLER_ERROR"
    assert "anthropic call failed" in exc.value.message


def test_anthropic_adapter_without_key_or_client_fails_clearly(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(SkillInvocationError) as exc:
        AnthropicAdapter()
    assert "ANTHROPIC_API_KEY" in exc.value.message


def test_anthropic_adapter_handles_fenced_reply():
    adapter = AnthropicAdapter(
        client=fake_anthropic_client('```json\n{"findings": [], "limitations": []}\n```')
    )
    assert adapter.complete("p", schema=SCHEMA) == {"findings": [], "limitations": []}


# --- OpenAI -----------------------------------------------------------------

def fake_openai_client(content, *, choices=True, error=None):
    def create(**kwargs):
        if error:
            raise error
        if not choices:
            return types.SimpleNamespace(choices=[], usage=None)
        return types.SimpleNamespace(
            choices=[
                types.SimpleNamespace(message=types.SimpleNamespace(content=content))
            ],
            usage=types.SimpleNamespace(prompt_tokens=5, completion_tokens=7),
        )

    return types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create))
    )


def test_openai_adapter_returns_parsed_payload():
    adapter = OpenAIAdapter(client=fake_openai_client('{"findings": [], "limitations": []}'))
    assert adapter.complete("p", schema=SCHEMA) == {"findings": [], "limitations": []}
    assert adapter.name == "openai"


def test_openai_adapter_records_usage():
    adapter = OpenAIAdapter(client=fake_openai_client('{"findings": [], "limitations": []}'))
    adapter.complete("p", schema=SCHEMA)
    assert adapter.last_usage.input_tokens == 5
    assert adapter.last_usage.output_tokens == 7


def test_openai_adapter_no_choices_is_invalid_output():
    adapter = OpenAIAdapter(client=fake_openai_client("", choices=False))
    with pytest.raises(SkillInvocationError) as exc:
        adapter.complete("p", schema=SCHEMA)
    assert exc.value.code == "MODEL_OUTPUT_INVALID"


def test_openai_adapter_wraps_provider_errors():
    adapter = OpenAIAdapter(client=fake_openai_client("", error=RuntimeError("boom")))
    with pytest.raises(SkillInvocationError) as exc:
        adapter.complete("p", schema=SCHEMA)
    assert exc.value.code == "HANDLER_ERROR"


def test_openai_adapter_without_key_or_client_fails_clearly(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(SkillInvocationError) as exc:
        OpenAIAdapter()
    assert "OPENAI_API_KEY" in exc.value.message


# --- local OpenAI-compatible server -----------------------------------------

class FakeResponse:
    def __init__(self, body: str):
        self._body = body.encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def local_opener(body=None, *, error=None):
    def opener(request, timeout):
        if error:
            raise error
        return FakeResponse(body)

    return opener


def envelope(content):
    return json.dumps(
        {
            "choices": [{"message": {"content": content}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 4},
        }
    )


def test_local_adapter_returns_parsed_payload():
    adapter = LocalOpenAIAdapter(
        opener=local_opener(envelope('{"findings": [], "limitations": []}'))
    )
    assert adapter.complete("p", schema=SCHEMA) == {"findings": [], "limitations": []}
    assert adapter.name == "local"


def test_local_adapter_records_usage():
    adapter = LocalOpenAIAdapter(
        opener=local_opener(envelope('{"findings": [], "limitations": []}'))
    )
    adapter.complete("p", schema=SCHEMA)
    assert adapter.last_usage.output_tokens == 4


def test_local_adapter_unreachable_server_is_handler_error():
    adapter = LocalOpenAIAdapter(opener=local_opener(error=urllib.error.URLError("refused")))
    with pytest.raises(SkillInvocationError) as exc:
        adapter.complete("p", schema=SCHEMA)
    assert exc.value.code == "HANDLER_ERROR"
    assert "unreachable" in exc.value.message


def test_local_adapter_non_json_envelope_is_invalid_output():
    adapter = LocalOpenAIAdapter(opener=local_opener("<html>502</html>"))
    with pytest.raises(SkillInvocationError) as exc:
        adapter.complete("p", schema=SCHEMA)
    assert exc.value.code == "MODEL_OUTPUT_INVALID"


def test_local_adapter_no_choices_is_invalid_output():
    adapter = LocalOpenAIAdapter(opener=local_opener(json.dumps({"choices": []})))
    with pytest.raises(SkillInvocationError):
        adapter.complete("p", schema=SCHEMA)


def test_local_adapter_default_base_url_is_ollama():
    assert "11434" in LocalOpenAIAdapter(opener=local_opener("{}")).base_url


def test_local_adapter_honours_custom_base_url():
    adapter = LocalOpenAIAdapter(base_url="http://localhost:1234/v1/", opener=local_opener("{}"))
    assert adapter.base_url == "http://localhost:1234/v1"


# --- scripted / recording ---------------------------------------------------

def test_scripted_adapter_matches_by_substring():
    adapter = ScriptedAdapter({"pride-signal-detector": {"findings": [], "limitations": []}})
    assert adapter.complete("... pride-signal-detector ...", schema=SCHEMA) == {
        "findings": [],
        "limitations": [],
    }


def test_scripted_adapter_accepts_raw_json_string():
    adapter = ScriptedAdapter({"x": '{"findings": [], "limitations": []}'})
    assert adapter.complete("x", schema=SCHEMA)["findings"] == []


def test_scripted_adapter_strict_miss_raises():
    adapter = ScriptedAdapter({"x": {}})
    with pytest.raises(SkillInvocationError):
        adapter.complete("no match here", schema=SCHEMA)


def test_recording_adapter_records_exchanges():
    inner = ScriptedAdapter({"x": {"findings": [], "limitations": []}})
    recorder = RecordingAdapter(inner)
    recorder.complete("x", schema=SCHEMA)
    assert len(recorder.exchanges) == 1
    assert recorder.transcript()[0]["schema_keys"] == sorted(SCHEMA)
    assert recorder.name == "recording:scripted"


# --- factories --------------------------------------------------------------

def test_build_adapter_null_returns_null_adapter():
    assert isinstance(build_adapter("null"), NullAdapter)
    assert isinstance(build_adapter(None), NullAdapter)


def test_build_adapter_unknown_provider_raises():
    with pytest.raises(SkillInvocationError) as exc:
        build_adapter("definitely-not-a-provider")
    assert "unknown model provider" in exc.value.message


def test_build_adapter_local_constructs():
    assert build_adapter("local", model="qwen").name == "local"


def test_build_adapter_from_env_defaults_to_null():
    assert isinstance(build_adapter_from_env({}), NullAdapter)


def test_build_adapter_from_env_respects_off_switch():
    assert isinstance(
        build_adapter_from_env({"DISCERNMENT_MODEL_PROVIDER": "off"}), NullAdapter
    )


def test_build_adapter_from_env_builds_local_with_options():
    adapter = build_adapter_from_env(
        {
            "DISCERNMENT_MODEL_PROVIDER": "local",
            "DISCERNMENT_MODEL_NAME": "qwen2.5:7b",
            "DISCERNMENT_MODEL_BASE_URL": "http://localhost:1234/v1",
            "DISCERNMENT_MODEL_MAX_ATTEMPTS": "3",
            "DISCERNMENT_MODEL_TEMPERATURE": "0.2",
            "DISCERNMENT_MODEL_MAX_TOKENS": "2048",
        }
    )
    assert adapter.model == "qwen2.5:7b"
    assert adapter.base_url == "http://localhost:1234/v1"
    assert adapter.max_attempts == 3
    assert adapter.temperature == 0.2
    assert adapter.max_tokens == 2048


# --- runtime integration ----------------------------------------------------

def unbound_skill_id() -> str:
    native = set(get_runtime().binding_report()["native_skill_ids"])
    return next(c.skill_id for c in get_skill_registry() if c.skill_id not in native)


def test_default_runtime_is_null_adapter(monkeypatch):
    monkeypatch.delenv("DISCERNMENT_MODEL_PROVIDER", raising=False)
    assert isinstance(get_runtime().adapter, NullAdapter)


def test_scripted_adapter_completes_a_contract_bound_skill():
    skill_id = unbound_skill_id()
    contract = get_skill_registry().get(skill_id)
    from backend.discernment_platform.skill_runtime import output_envelope

    envelope_keys = output_envelope(contract)
    reply = {key: [] for key in envelope_keys}
    runtime = SkillRuntime(adapter=ScriptedAdapter({skill_id: reply}))
    result = runtime.invoke(skill_id, {"case_id": "c1"})
    assert result.status == "ok"
    assert result.binding == "model"
    assert set(result.outputs) == set(envelope_keys)


def test_model_bound_skill_marks_steps_delegated():
    skill_id = unbound_skill_id()
    from backend.discernment_platform.skill_runtime import output_envelope

    contract = get_skill_registry().get(skill_id)
    reply = {key: [] for key in output_envelope(contract)}
    runtime = SkillRuntime(adapter=ScriptedAdapter({skill_id: reply}))
    result = runtime.invoke(skill_id, {})
    assert all(step["status"] == "delegated_to_model" for step in result.processing_steps)


def test_trace_reports_adapter_and_usage():
    skill_id = unbound_skill_id()
    from backend.discernment_platform.skill_runtime import output_envelope

    contract = get_skill_registry().get(skill_id)
    reply = {key: [] for key in output_envelope(contract)}
    runtime = SkillRuntime(adapter=ScriptedAdapter({skill_id: reply}))
    result = runtime.invoke(skill_id, {})
    assert result.trace["adapter"] == "scripted"
    assert result.trace["usage"]["attempts"] >= 1


def test_guardrails_still_gate_model_output():
    """A model reply that breaks a guardrail must be blocked, not returned."""

    skill_id = next(
        c.skill_id
        for c in get_skill_registry()
        if c.skill_id not in set(get_runtime().binding_report()["native_skill_ids"])
        and any("salvation" in line.lower() or "得救" in line for line in c.guardrails)
    )
    from backend.discernment_platform.skill_runtime import output_envelope

    contract = get_skill_registry().get(skill_id)
    reply = {key: "他一定下地狱" for key in output_envelope(contract)}
    runtime = SkillRuntime(adapter=ScriptedAdapter({skill_id: reply}))
    result = runtime.invoke(skill_id, {})
    assert result.status == "blocked"
    assert result.failure_code == "GUARDRAIL_VIOLATION"


def test_model_failure_maps_to_failure_code():
    skill_id = unbound_skill_id()
    runtime = SkillRuntime(adapter=ScriptedAdapter({skill_id: {"wrong": 1}}))
    result = runtime.invoke(skill_id, {})
    assert result.status == "failed"
    assert result.failure_code == "MODEL_OUTPUT_INVALID"


def test_recording_adapter_gives_an_audit_transcript():
    skill_id = unbound_skill_id()
    from backend.discernment_platform.skill_runtime import output_envelope

    contract = get_skill_registry().get(skill_id)
    reply = {key: [] for key in output_envelope(contract)}
    recorder = RecordingAdapter(ScriptedAdapter({skill_id: reply}))
    SkillRuntime(adapter=recorder).invoke(skill_id, {})
    assert recorder.transcript()
    assert "Guardrails" in recorder.exchanges[0].prompt


def test_native_skills_ignore_the_adapter():
    runtime = SkillRuntime(adapter=ScriptedAdapter({}, strict=True))
    result = runtime.invoke("bible-reference-parser", {"text": "罗马书 8:1"})
    assert result.status == "ok"
    assert result.binding == "native"


# --- Gemini -----------------------------------------------------------------

def gemini_envelope(text, *, prompt_tokens=13, candidate_tokens=17):
    return json.dumps(
        {
            "candidates": [{"content": {"parts": [{"text": text}]}}],
            "usageMetadata": {
                "promptTokenCount": prompt_tokens,
                "candidatesTokenCount": candidate_tokens,
            },
        }
    )


def gemini_adapter(body=None, *, error=None, **kw):
    from backend.discernment_platform.model_adapter import GeminiAdapter

    return GeminiAdapter(opener=local_opener(body, error=error), **kw)


def test_gemini_adapter_returns_parsed_payload():
    adapter = gemini_adapter(gemini_envelope('{"findings": [1], "limitations": []}'))
    assert adapter.complete("p", schema=SCHEMA)["findings"] == [1]
    assert adapter.name == "gemini"


def test_gemini_adapter_records_usage():
    adapter = gemini_adapter(gemini_envelope('{"findings": [], "limitations": []}'))
    adapter.complete("p", schema=SCHEMA)
    assert adapter.last_usage.input_tokens == 13
    assert adapter.last_usage.output_tokens == 17


def test_gemini_adapter_handles_fenced_reply():
    adapter = gemini_adapter(
        gemini_envelope('```json\n{"findings": [], "limitations": []}\n```')
    )
    assert adapter.complete("p", schema=SCHEMA) == {"findings": [], "limitations": []}


def test_gemini_adapter_surfaces_api_errors():
    adapter = gemini_adapter(json.dumps({"error": {"message": "quota exceeded"}}))
    with pytest.raises(SkillInvocationError) as exc:
        adapter.complete("p", schema=SCHEMA)
    assert exc.value.code == "HANDLER_ERROR"
    assert "quota exceeded" in exc.value.message


def test_gemini_adapter_reports_a_blocked_prompt():
    adapter = gemini_adapter(json.dumps({"promptFeedback": {"blockReason": "SAFETY"}}))
    with pytest.raises(SkillInvocationError) as exc:
        adapter.complete("p", schema=SCHEMA)
    assert "blocked the prompt: SAFETY" in exc.value.message


def test_gemini_adapter_no_candidates_is_invalid_output():
    adapter = gemini_adapter(json.dumps({"candidates": []}))
    with pytest.raises(SkillInvocationError) as exc:
        adapter.complete("p", schema=SCHEMA)
    assert exc.value.code == "MODEL_OUTPUT_INVALID"


def test_gemini_adapter_non_json_envelope_is_invalid_output():
    adapter = gemini_adapter("<html>502 Bad Gateway</html>")
    with pytest.raises(SkillInvocationError) as exc:
        adapter.complete("p", schema=SCHEMA)
    assert exc.value.code == "MODEL_OUTPUT_INVALID"


def test_gemini_adapter_unreachable_endpoint_is_handler_error():
    adapter = gemini_adapter(error=urllib.error.URLError("dns"))
    with pytest.raises(SkillInvocationError) as exc:
        adapter.complete("p", schema=SCHEMA)
    assert "unreachable" in exc.value.message


def test_gemini_adapter_repairs_a_missing_key():
    from backend.discernment_platform.model_adapter import GeminiAdapter

    replies = [
        gemini_envelope('{"findings": []}'),
        gemini_envelope('{"findings": [], "limitations": ["x"]}'),
    ]

    def opener(request, timeout):
        return FakeResponse(replies.pop(0))

    adapter = GeminiAdapter(opener=opener)
    assert adapter.complete("p", schema=SCHEMA)["limitations"] == ["x"]
    assert adapter.last_usage.attempts == 2


def test_gemini_adapter_accumulates_usage_across_repairs():
    from backend.discernment_platform.model_adapter import GeminiAdapter

    replies = [
        gemini_envelope('{"findings": []}'),
        gemini_envelope('{"findings": [], "limitations": []}'),
    ]

    def opener(request, timeout):
        return FakeResponse(replies.pop(0))

    adapter = GeminiAdapter(opener=opener)
    adapter.complete("p", schema=SCHEMA)
    assert adapter.last_usage.output_tokens == 34


def test_gemini_adapter_uses_header_auth_not_query_string():
    seen = {}

    def opener(request, timeout):
        seen["url"] = request.full_url
        seen["headers"] = dict(request.headers)
        return FakeResponse(gemini_envelope('{"findings": [], "limitations": []}'))

    from backend.discernment_platform.model_adapter import GeminiAdapter

    GeminiAdapter(api_key="secret-key", opener=opener).complete("p", schema=SCHEMA)
    assert "secret-key" not in seen["url"]
    assert seen["headers"]["X-goog-api-key"] == "secret-key"


def test_gemini_adapter_requests_json_mime_type():
    seen = {}

    def opener(request, timeout):
        seen["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(gemini_envelope('{"findings": [], "limitations": []}'))

    from backend.discernment_platform.model_adapter import GeminiAdapter

    GeminiAdapter(opener=opener).complete("p", schema=SCHEMA)
    assert seen["body"]["generationConfig"]["responseMimeType"] == "application/json"
    assert seen["body"]["systemInstruction"]["parts"][0]["text"]


def test_gemini_adapter_targets_the_configured_model():
    seen = {}

    def opener(request, timeout):
        seen["url"] = request.full_url
        return FakeResponse(gemini_envelope('{"findings": [], "limitations": []}'))

    from backend.discernment_platform.model_adapter import GeminiAdapter

    GeminiAdapter(model="gemini-2.5-flash", opener=opener).complete("p", schema=SCHEMA)
    assert "models/gemini-2.5-flash:generateContent" in seen["url"]


def test_gemini_adapter_without_key_fails_clearly(monkeypatch):
    from backend.discernment_platform.model_adapter import GeminiAdapter

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(SkillInvocationError) as exc:
        GeminiAdapter()
    assert "GEMINI_API_KEY" in exc.value.message


def test_gemini_adapter_accepts_google_api_key(monkeypatch):
    from backend.discernment_platform.model_adapter import GeminiAdapter

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "from-google-var")
    assert GeminiAdapter().api_key == "from-google-var"


def test_build_adapter_knows_gemini():
    assert build_adapter("gemini", api_key="k").name == "gemini"


def test_build_adapter_from_env_builds_gemini():
    adapter = build_adapter_from_env(
        {
            "DISCERNMENT_MODEL_PROVIDER": "gemini",
            "DISCERNMENT_MODEL_NAME": "gemini-2.5-flash",
            "GEMINI_API_KEY": "k",
        }
    )
    assert adapter.name == "gemini"
    assert adapter.model == "gemini-2.5-flash"


def test_gemini_honours_a_base_url_override():
    adapter = build_adapter_from_env(
        {
            "DISCERNMENT_MODEL_PROVIDER": "gemini",
            "DISCERNMENT_MODEL_BASE_URL": "https://proxy.internal/v1beta",
            "GEMINI_API_KEY": "k",
        }
    )
    assert adapter.base_url == "https://proxy.internal/v1beta"


def test_unknown_provider_message_lists_gemini():
    with pytest.raises(SkillInvocationError) as exc:
        build_adapter("bard")
    assert "gemini" in exc.value.message
