"""Provider-neutral model adapters for the 82 contract-bound skills.

The runtime never talks to a vendor SDK directly.  It talks to an object
satisfying :class:`~discernment_platform.skill_runtime.ModelAdapter`:

    complete(prompt: str, *, schema: dict[str, str]) -> dict

``schema`` maps each declared output key of the SKILL.md contract to its
human-readable description.  An adapter must return a dict containing every
key, or raise :class:`SkillInvocationError` with ``MODEL_OUTPUT_INVALID``.

Adapters here:

``AnthropicAdapter``   Claude via the ``anthropic`` SDK
``OpenAIAdapter``      GPT via the ``openai`` SDK
``GeminiAdapter``      Gemini via the Generative Language REST API (stdlib only)
``LocalOpenAIAdapter`` any OpenAI-compatible local server (Ollama, LM Studio,
                       vLLM, llama.cpp) over stdlib ``urllib`` - no extra deps
``ScriptedAdapter``    replays canned payloads; for golden-set tests and dev
``RecordingAdapter``   wraps another adapter and records every exchange

All of them inherit the same JSON extraction, schema validation and repair
retry from :class:`BaseModelAdapter`, so provider choice never changes the
guarantees the runtime relies on.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable

from .skill_runtime import NullAdapter, SkillInvocationError

Schema = dict[str, str]
Payload = dict[str, Any]

DEFAULT_MAX_ATTEMPTS = 2
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.0

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    attempts: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "attempts": self.attempts,
        }


@dataclass
class Exchange:
    skill_schema: Schema
    prompt: str
    raw_text: str
    parsed: Payload
    attempts: int


def extract_json(text: str) -> Payload:
    """Pull a JSON object out of a model reply.

    Tolerates fenced blocks and leading prose, which every provider emits
    sooner or later, but refuses anything that is not a JSON object.
    """

    if not text or not text.strip():
        raise SkillInvocationError("MODEL_OUTPUT_INVALID", "model returned empty text")

    candidates: list[str] = []
    fenced = _JSON_FENCE_RE.search(text)
    if fenced:
        candidates.append(fenced.group(1).strip())
    stripped = text.strip()
    candidates.append(stripped)
    start, end = stripped.find("{"), stripped.rfind("}")
    if start != -1 and end > start:
        candidates.append(stripped[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(parsed, dict):
            return parsed
        raise SkillInvocationError(
            "MODEL_OUTPUT_INVALID", f"model returned {type(parsed).__name__}, expected object"
        )

    raise SkillInvocationError(
        "MODEL_OUTPUT_INVALID", f"could not parse JSON from model reply: {text[:200]!r}"
    )


def missing_keys(parsed: Payload, schema: Schema) -> list[str]:
    return [key for key in schema if key not in parsed]


def repair_instruction(parsed: Payload, schema: Schema) -> str:
    absent = missing_keys(parsed, schema)
    return (
        "\n\n## Repair required\n"
        "Your previous reply was missing these required keys: "
        f"{json.dumps(absent, ensure_ascii=False)}.\n"
        "Reply again with a single JSON object containing every key listed under "
        "'Required output'. Do not add commentary outside the JSON. "
        "If a value is genuinely unknown from the input, use null - never invent one."
    )


class BaseModelAdapter:
    """Shared parse / validate / repair-retry behaviour."""

    name = "base"

    def __init__(self, *, max_attempts: int = DEFAULT_MAX_ATTEMPTS) -> None:
        self.max_attempts = max(1, int(max_attempts))
        self.last_usage = Usage()

    # -- provider hook ---------------------------------------------------

    def _generate(self, prompt: str) -> str:  # pragma: no cover - abstract
        raise NotImplementedError

    # -- public API ------------------------------------------------------

    def complete(self, prompt: str, *, schema: Schema) -> Payload:
        # Bind first: ``_generate`` accumulates provider token counts onto
        # ``self.last_usage`` while the attempt loop runs.
        usage = Usage()
        self.last_usage = usage
        current = prompt
        last_error: SkillInvocationError | None = None
        parsed: Payload = {}

        for attempt in range(1, self.max_attempts + 1):
            usage.attempts = attempt
            text = self._generate(current)
            try:
                parsed = extract_json(text)
            except SkillInvocationError as exc:
                last_error = exc
                current = prompt + (
                    "\n\n## Repair required\nYour previous reply was not valid JSON. "
                    "Reply with a single JSON object only."
                )
                continue

            absent = missing_keys(parsed, schema)
            if not absent:
                self.last_usage = usage
                return {key: parsed[key] for key in schema}

            last_error = SkillInvocationError(
                "MODEL_OUTPUT_INVALID", f"model omitted required keys: {absent}"
            )
            current = prompt + repair_instruction(parsed, schema)

        self.last_usage = usage
        raise last_error or SkillInvocationError(
            "MODEL_OUTPUT_INVALID", "model produced no usable output"
        )


class AnthropicAdapter(BaseModelAdapter):
    """Claude via the official ``anthropic`` SDK."""

    name = "anthropic"

    def __init__(
        self,
        model: str = "claude-opus-4-5",
        *,
        api_key: str | None = None,
        client: Any | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        system: str | None = None,
    ) -> None:
        super().__init__(max_attempts=max_attempts)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.system = system or (
            "You execute a single versioned SKILL.md contract. Follow the Processing "
            "Contract and Guardrails exactly. Reply with one JSON object and nothing else."
        )
        if client is not None:
            self.client = client
            return
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise SkillInvocationError(
                "HANDLER_ERROR", "ANTHROPIC_API_KEY is not set and no client was supplied"
            )
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - env dependent
            raise SkillInvocationError(
                "HANDLER_ERROR", "anthropic SDK is not installed (pip install anthropic)"
            ) from exc
        self.client = anthropic.Anthropic(api_key=key)

    def _generate(self, prompt: str) -> str:
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=self.system,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:  # noqa: BLE001 - provider errors are opaque
            raise SkillInvocationError("HANDLER_ERROR", f"anthropic call failed: {exc}") from exc

        usage = getattr(message, "usage", None)
        if usage is not None:
            self.last_usage.input_tokens += getattr(usage, "input_tokens", 0) or 0
            self.last_usage.output_tokens += getattr(usage, "output_tokens", 0) or 0
        blocks = getattr(message, "content", []) or []
        return "".join(getattr(block, "text", "") for block in blocks)


class OpenAIAdapter(BaseModelAdapter):
    """GPT via the official ``openai`` SDK."""

    name = "openai"

    def __init__(
        self,
        model: str = "gpt-4o",
        *,
        api_key: str | None = None,
        client: Any | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        system: str | None = None,
    ) -> None:
        super().__init__(max_attempts=max_attempts)
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.system = system or (
            "You execute a single versioned SKILL.md contract. Follow the Processing "
            "Contract and Guardrails exactly. Reply with one JSON object and nothing else."
        )
        if client is not None:
            self.client = client
            return
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise SkillInvocationError(
                "HANDLER_ERROR", "OPENAI_API_KEY is not set and no client was supplied"
            )
        try:
            import openai
        except ImportError as exc:  # pragma: no cover - env dependent
            raise SkillInvocationError(
                "HANDLER_ERROR", "openai SDK is not installed (pip install openai)"
            ) from exc
        self.client = openai.OpenAI(api_key=key)

    def _generate(self, prompt: str) -> str:
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": self.system},
                    {"role": "user", "content": prompt},
                ],
            )
        except Exception as exc:  # noqa: BLE001
            raise SkillInvocationError("HANDLER_ERROR", f"openai call failed: {exc}") from exc

        usage = getattr(completion, "usage", None)
        if usage is not None:
            self.last_usage.input_tokens += getattr(usage, "prompt_tokens", 0) or 0
            self.last_usage.output_tokens += getattr(usage, "completion_tokens", 0) or 0
        choices = getattr(completion, "choices", []) or []
        if not choices:
            raise SkillInvocationError("MODEL_OUTPUT_INVALID", "openai returned no choices")
        return getattr(choices[0].message, "content", "") or ""


class LocalOpenAIAdapter(BaseModelAdapter):
    """Any OpenAI-compatible local server, over stdlib urllib only.

    Works with Ollama (``http://localhost:11434/v1``), LM Studio
    (``http://localhost:1234/v1``), vLLM and llama.cpp server. No third-party
    dependency, so this path stays available in a locked-down deployment.
    """

    name = "local"

    def __init__(
        self,
        model: str = "qwen2.5:14b",
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        opener: Callable[[urllib.request.Request, int], Any] | None = None,
    ) -> None:
        super().__init__(max_attempts=max_attempts)
        self.model = model
        self.base_url = (
            base_url or os.environ.get("DISCERNMENT_MODEL_BASE_URL") or "http://localhost:11434/v1"
        ).rstrip("/")
        self.api_key = api_key or os.environ.get("DISCERNMENT_MODEL_API_KEY", "not-needed")
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._opener = opener or (lambda req, t: urllib.request.urlopen(req, timeout=t))

    def _generate(self, prompt: str) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You execute a single versioned SKILL.md contract. Reply with "
                            "one JSON object and nothing else."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with self._opener(request, self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise SkillInvocationError(
                "HANDLER_ERROR", f"local model server unreachable at {self.base_url}: {exc}"
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise SkillInvocationError("HANDLER_ERROR", f"local model call failed: {exc}") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SkillInvocationError(
                "MODEL_OUTPUT_INVALID", f"local server returned non-JSON envelope: {raw[:200]!r}"
            ) from exc

        usage = data.get("usage") or {}
        self.last_usage.input_tokens += int(usage.get("prompt_tokens", 0) or 0)
        self.last_usage.output_tokens += int(usage.get("completion_tokens", 0) or 0)
        choices = data.get("choices") or []
        if not choices:
            raise SkillInvocationError("MODEL_OUTPUT_INVALID", "local server returned no choices")
        return choices[0].get("message", {}).get("content", "") or ""


class GeminiAdapter(BaseModelAdapter):
    """Gemini via the Generative Language REST API, over stdlib ``urllib``.

    Deliberately not built on ``google-generativeai``: the REST surface is
    stable, needs no extra dependency, and keeps this path available in a
    locked-down deployment - same reasoning as :class:`LocalOpenAIAdapter`.

    ``responseMimeType: application/json`` is set so the model is constrained
    to JSON, mirroring the OpenAI ``json_object`` response format.

    Model names move quickly; set ``--model`` or ``DISCERNMENT_MODEL_NAME``
    explicitly rather than relying on the default.
    """

    name = "gemini"
    DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        model: str = "gemini-2.5-pro",
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        system: str | None = None,
        opener: Callable[[urllib.request.Request, int], Any] | None = None,
    ) -> None:
        super().__init__(max_attempts=max_attempts)
        self.model = model
        self.base_url = (
            base_url or os.environ.get("DISCERNMENT_MODEL_BASE_URL") or self.DEFAULT_BASE_URL
        ).rstrip("/")
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.system = system or (
            "You execute a single versioned SKILL.md contract. Follow the Processing "
            "Contract and Guardrails exactly. Reply with one JSON object and nothing else."
        )
        self._opener = opener or (lambda req, t: urllib.request.urlopen(req, timeout=t))
        if opener is not None:
            self.api_key = api_key or "test-key"
            return
        key = (
            api_key
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        if not key:
            raise SkillInvocationError(
                "HANDLER_ERROR", "GEMINI_API_KEY (or GOOGLE_API_KEY) is not set"
            )
        self.api_key = key

    def _generate(self, prompt: str) -> str:
        body = json.dumps(
            {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "systemInstruction": {"parts": [{"text": self.system}]},
                "generationConfig": {
                    "temperature": self.temperature,
                    "maxOutputTokens": self.max_tokens,
                    "responseMimeType": "application/json",
                },
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/models/{self.model}:generateContent",
            data=body,
            headers={
                "Content-Type": "application/json",
                # header auth, so the key never lands in a URL or an access log
                "x-goog-api-key": self.api_key,
            },
            method="POST",
        )
        try:
            with self._opener(request, self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:  # pragma: no cover - network dependent
            detail = ""
            try:
                detail = exc.read().decode("utf-8")[:300]
            except Exception:  # noqa: BLE001
                pass
            raise SkillInvocationError(
                "HANDLER_ERROR", f"gemini call failed ({exc.code}): {detail or exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise SkillInvocationError(
                "HANDLER_ERROR", f"gemini endpoint unreachable at {self.base_url}: {exc}"
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise SkillInvocationError("HANDLER_ERROR", f"gemini call failed: {exc}") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SkillInvocationError(
                "MODEL_OUTPUT_INVALID", f"gemini returned non-JSON envelope: {raw[:200]!r}"
            ) from exc

        if "error" in data:
            message = (data["error"] or {}).get("message", "unknown error")
            raise SkillInvocationError("HANDLER_ERROR", f"gemini API error: {message}")

        usage = data.get("usageMetadata") or {}
        self.last_usage.input_tokens += int(usage.get("promptTokenCount", 0) or 0)
        self.last_usage.output_tokens += int(usage.get("candidatesTokenCount", 0) or 0)

        candidates = data.get("candidates") or []
        if not candidates:
            feedback = data.get("promptFeedback") or {}
            blocked = feedback.get("blockReason")
            if blocked:
                raise SkillInvocationError(
                    "HANDLER_ERROR", f"gemini blocked the prompt: {blocked}"
                )
            raise SkillInvocationError("MODEL_OUTPUT_INVALID", "gemini returned no candidates")

        parts = ((candidates[0].get("content") or {}).get("parts")) or []
        return "".join(part.get("text", "") for part in parts)


class ScriptedAdapter(BaseModelAdapter):
    """Replays canned replies. For golden-set regression tests and offline dev.

    ``replies`` may map a skill id (or any substring found in the prompt) to
    either a JSON string or a dict. Unknown prompts raise rather than guess.
    """

    name = "scripted"

    def __init__(
        self,
        replies: dict[str, Payload | str],
        *,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        strict: bool = True,
    ) -> None:
        super().__init__(max_attempts=max_attempts)
        self.replies = replies
        self.strict = strict
        self.prompts: list[str] = []

    def _generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        for key, reply in self.replies.items():
            if key in prompt:
                return reply if isinstance(reply, str) else json.dumps(reply, ensure_ascii=False)
        if self.strict:
            raise SkillInvocationError(
                "MODEL_OUTPUT_INVALID", "no scripted reply matches this prompt"
            )
        return "{}"


@dataclass
class RecordingAdapter:
    """Wraps another adapter and records every exchange for audit or replay."""

    inner: Any
    exchanges: list[Exchange] = field(default_factory=list)

    @property
    def name(self) -> str:
        return f"recording:{getattr(self.inner, 'name', 'unknown')}"

    @property
    def last_usage(self) -> Usage:
        return getattr(self.inner, "last_usage", Usage())

    def complete(self, prompt: str, *, schema: Schema) -> Payload:
        parsed = self.inner.complete(prompt, schema=schema)
        self.exchanges.append(
            Exchange(
                skill_schema=dict(schema),
                prompt=prompt,
                raw_text=json.dumps(parsed, ensure_ascii=False),
                parsed=parsed,
                attempts=getattr(self.last_usage, "attempts", 1),
            )
        )
        return parsed

    def transcript(self) -> list[dict[str, Any]]:
        return [
            {
                "schema_keys": sorted(exchange.skill_schema),
                "attempts": exchange.attempts,
                "output_keys": sorted(exchange.parsed),
            }
            for exchange in self.exchanges
        ]


PROVIDERS: dict[str, Callable[..., Any]] = {
    "anthropic": AnthropicAdapter,
    "openai": OpenAIAdapter,
    "gemini": GeminiAdapter,
    "local": LocalOpenAIAdapter,
}

#: Providers that accept a ``base_url`` override.
BASE_URL_PROVIDERS = frozenset({"local", "gemini"})

#: Where each provider looks for its credential, in priority order. Used so
#: ``build_adapter_from_env`` actually honours the mapping it is handed instead
#: of silently falling through to ``os.environ``.
PROVIDER_KEY_ENV: dict[str, tuple[str, ...]] = {
    "anthropic": ("ANTHROPIC_API_KEY",),
    "openai": ("OPENAI_API_KEY",),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "local": ("DISCERNMENT_MODEL_API_KEY",),
}


def build_adapter(provider: str | None, **kwargs: Any) -> Any:
    """Construct an adapter by provider name. ``None``/``null`` -> NullAdapter."""

    key = (provider or "null").strip().lower()
    if key in {"null", "none", "off", ""}:
        return NullAdapter()
    if key not in PROVIDERS:
        raise SkillInvocationError(
            "HANDLER_ERROR",
            f"unknown model provider {provider!r}; expected one of "
            f"{sorted(PROVIDERS) + ['null']}",
        )
    return PROVIDERS[key](**kwargs)


def build_adapter_from_env(env: dict[str, str] | None = None) -> Any:
    """Read ``DISCERNMENT_MODEL_*`` and build the configured adapter.

    Unset provider means NullAdapter, so the default deployment keeps the
    "never fabricate" behaviour until someone opts in explicitly.
    """

    env = dict(os.environ if env is None else env)
    provider = env.get("DISCERNMENT_MODEL_PROVIDER")
    if not provider or provider.lower() in {"null", "none", "off"}:
        return NullAdapter()

    kwargs: dict[str, Any] = {}
    if model := env.get("DISCERNMENT_MODEL_NAME"):
        kwargs["model"] = model
    if attempts := env.get("DISCERNMENT_MODEL_MAX_ATTEMPTS"):
        kwargs["max_attempts"] = int(attempts)
    if temperature := env.get("DISCERNMENT_MODEL_TEMPERATURE"):
        kwargs["temperature"] = float(temperature)
    if max_tokens := env.get("DISCERNMENT_MODEL_MAX_TOKENS"):
        kwargs["max_tokens"] = int(max_tokens)
    if provider.lower() in BASE_URL_PROVIDERS:
        if base_url := env.get("DISCERNMENT_MODEL_BASE_URL"):
            kwargs["base_url"] = base_url
    for key_name in PROVIDER_KEY_ENV.get(provider.lower(), ()):
        if value := env.get(key_name):
            kwargs["api_key"] = value
            break
    return build_adapter(provider, **kwargs)


__all__ = [
    "AnthropicAdapter",
    "BaseModelAdapter",
    "BASE_URL_PROVIDERS",
    "PROVIDER_KEY_ENV",
    "Exchange",
    "GeminiAdapter",
    "LocalOpenAIAdapter",
    "OpenAIAdapter",
    "PROVIDERS",
    "RecordingAdapter",
    "ScriptedAdapter",
    "Usage",
    "build_adapter",
    "build_adapter_from_env",
    "extract_json",
    "missing_keys",
    "repair_instruction",
]
