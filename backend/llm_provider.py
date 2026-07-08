"""
llm_provider.py — Advanced Batch · Module 1 (Real LLM Provider Layer)

A single, pluggable provider abstraction that replaces the per-router
``_chat_complete`` helpers duplicated across agent.py / guardian.py / crisis.py.

Providers (all behind one interface):
    MockLLMProvider            deterministic, offline — used for tests & when no key
    OpenAICompatibleProvider   OpenAI / Gemini-OpenAI / DeepSeek / SiliconFlow / vLLM …
    AnthropicCompatibleProvider Claude messages API
    GeminiCompatibleProvider   native generativelanguage endpoint
    LocalLLMProvider           OpenAI-compatible server at LLM_BASE_URL

Guarantees required by the spec:
    • Unified return structure for every provider.
    • Structured output validated with a Pydantic schema; ONE automatic retry
      on validation failure; a second failure marks agent_runs.status='FAILED'.
    • Provider observability (model/latency/tokens/error) is recorded on
      agent_runs (migration 0074 columns) — reconciled onto the concurrent design.
    • Secrets / private user text are REDACTED before logging (no plaintext).
    • Designed to be wrapped by TheologicalSafetyService before anything ships.

NB: this codebase is synchronous (psycopg2 + sync httpx), so the provider
methods are synchronous. The spec's async signatures are adapted to match the
host application rather than introduce an event loop into sync FastAPI routes.
"""
from __future__ import annotations

import json
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type

try:
    from pydantic import BaseModel, ValidationError
except Exception as exc:  # pragma: no cover
    raise RuntimeError("pydantic is required for llm_provider") from exc

try:  # settings is optional at import time (tests may run without it)
    from backend.core.config import settings as _settings  # type: ignore
except Exception:  # pragma: no cover
    try:
        from core.config import settings as _settings  # type: ignore
    except Exception:
        _settings = None

try:
    from backend import theological_safety as _safety  # type: ignore
except Exception:  # pragma: no cover
    import theological_safety as _safety


# ── Exceptions ──────────────────────────────────────────────────────────────
class LLMError(RuntimeError):
    pass


class LLMValidationError(LLMError):
    pass


# ── Unified response object ─────────────────────────────────────────────────
@dataclass
class ProviderResponse:
    text: str = ""
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    raw: Optional[dict] = None


# ── Shared config + HTTP client ──────────────────────────────────────────────
DEFAULT_MAX_TOKENS = 2048  # sane cap so callers that omit max_tokens stay bounded

_HTTP_CLIENT = None


def _http_client():
    """Lazily build one keep-alive httpx.Client shared across calls.
    httpx.Client is thread-safe for concurrent requests; per-request timeouts are
    passed at call sites, so a single shared pool serves every provider."""
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None:
        import httpx
        _HTTP_CLIENT = httpx.Client(timeout=60)
    return _HTTP_CLIENT


# ── Pluggable DB logging ─────────────────────────────────────────────────────
_get_db: Optional[Callable] = None
_release_db: Optional[Callable] = None


def set_db_accessors(get_db: Callable, release_db: Callable) -> None:
    """Wire provider observability + safety logging to the app DB pool (from main.py)."""
    global _get_db, _release_db
    _get_db, _release_db = get_db, release_db
    _safety.set_db_accessors(get_db, release_db)


# ── Redaction ────────────────────────────────────────────────────────────────
_SECRET_KEYS = re.compile(r"(authorization|api[_-]?key|secret|token|password|cookie)", re.I)
_BEARER = re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]+", re.I)


def _redact(obj: Any, _depth: int = 0) -> Any:
    """Deep-redact secrets and shrink free-text so no plaintext PII is logged."""
    if _depth > 6:
        return "…"
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if _SECRET_KEYS.search(str(k)):
                out[k] = "***REDACTED***"
            elif str(k) in ("content", "user_prompt", "raw_lament", "text") and isinstance(v, str):
                out[k] = _preview(v)
            else:
                out[k] = _redact(v, _depth + 1)
        return out
    if isinstance(obj, list):
        return [_redact(v, _depth + 1) for v in obj[:20]]
    if isinstance(obj, str):
        return _BEARER.sub(r"\1***", obj if len(obj) <= 400 else _preview(obj))
    return obj


def _preview(s: str) -> str:
    s = s or ""
    return f"[redacted len={len(s)} sha={_safety.content_hash(s)}]"


# ── Provider interface ───────────────────────────────────────────────────────
class LLMProvider(ABC):
    name: str = "base"

    def __init__(self, *, model: str = "", api_key: str = "", base_url: str = "",
                 timeout: int = 60, max_retries: int = 2):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    @abstractmethod
    def complete(self, messages: List[Dict[str, str]], *, temperature: float = 0.3,
                 max_tokens: Optional[int] = None) -> ProviderResponse:
        ...

    def embed(self, text: str) -> List[float]:
        raise NotImplementedError


# ── Mock provider (deterministic, offline) ──────────────────────────────────
class MockLLMProvider(LLMProvider):
    name = "mock"

    def complete(self, messages, *, temperature: float = 0.3, max_tokens=None) -> ProviderResponse:
        user = _last_user(messages)
        crisis = _safety.detect_crisis(user)
        if crisis["risk_level"] in ("high", "critical"):
            body = ("我听见你了，你现在承受的远不只是情绪。你并不孤单，也不需要独自扛。"
                    "请尽快联系一位你信任的真实的人——牧者、家人或可信的属灵同伴；"
                    "若有立即危险，请联系当地紧急服务。我会一直陪着你，但我不能代替真实的陪伴与帮助。")
        else:
            body = ("谢谢你愿意说出来。让我们一起，把目光从处境慢慢转向那位看顾你的基督——"
                    "祂没有要你靠表现赢得接纳。这一周，试着用一句经文向自己传讲福音。")
        return ProviderResponse(text=body, input_tokens=0, output_tokens=0, total_tokens=0,
                                raw={"mock": True})

    def structured(self, schema: Type[BaseModel], payload: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic, schema-shaped output keyed by schema name."""
        name = schema.__name__
        text = _payload_text(payload)
        crisis = _safety.detect_crisis(text)
        risk = crisis["risk_level"]
        builder = _MOCK_BUILDERS.get(name)
        if builder is None:
            # Generic: satisfy required fields with neutral content.
            return _generic_mock(schema)
        return builder(payload, risk, crisis)

    def embed(self, text: str) -> List[float]:
        h = _safety.content_hash(text)
        # 16-dim deterministic pseudo-embedding from the hash (offline-safe).
        return [((int(h[i % len(h)], 16) / 15.0) * 2 - 1) for i in range(16)]


def _mock_diagnosis(payload, risk, crisis):
    pastor = risk in ("high", "critical")
    findings = [{
        "category": "identity", "finding_type": "lie", "title": "以表现定义价值",
        "description": "反复出现以成败衡量自我价值的语气。", "severity": 3 if not pastor else 4,
        "confidence": 0.7, "possible_root": "功能性偶像：他人的认可",
        "gospel_truth": "在基督里，你的身份先于表现被神接纳。",
        "scripture_anchors": ["罗马书8:15-16", "以弗所书1:4-5"],
        "recommended_practice_types": ["identity_prayer", "gratitude"],
        "recommended_community_action": "向一位属灵同伴坦诚分享" if not pastor else "尽快联系牧者或可信的人",
        "requires_pastor_attention": pastor,
        "risk_level": risk,
    }]
    return {
        "primary_theme": "身份与苦难中的信靠" if pastor else "身份认同与福音安息",
        "risk_level": risk,
        "summary": ("检测到需要真实关怀的高风险信号，已建议连接真实的人。" if pastor
                    else "温柔的初步辨识：核心议题是把价值建立在表现上。"),
        "findings": findings,
    }


def _mock_worldview(payload, risk, crisis):
    return {
        "summary": "底层世界观中，自我观与苦难观最需要被福音更新。",
        "dominant_distortions": ["表现主义", "控制主义"],
        "renewal_focus": ["身份认同", "神的护理"],
        "risk_level": risk,
        "findings": [{
            "dimension_code": "self_view", "expressed_belief": "我的价值取决于成功",
            "belief_type": "implicit", "distortion_type": "performance_identity",
            "biblical_counter_truth": "在基督里，人的身份先于表现被神接纳。",
            "scripture_anchors": ["罗马书8:15-16", "以弗所书1:4-5"],
            "evidence": "多次把失败描述为自己没有价值。", "confidence": 0.84,
            "recommended_practices": ["身份认同祷告", "感恩操练", "属灵同伴分享"],
        }],
    }


def _mock_gift(payload, risk, crisis):
    return {
        "summary": "初步辨识：教导与组织恩赐较为明显；这是可能方向，需群体确认与小步验证。",
        "dominant_gifts": [{"name": "教导", "evidence": "喜欢结构化解释圣经与复杂系统。", "confidence": 0.78}],
        "secondary_gifts": [{"name": "治理", "evidence": "倾向把事情系统化推进。", "confidence": 0.6}],
        "growth_edges": ["耐心倾听", "团队协作"],
        "misuse_risks": ["用知识建立优越感", "忽略关系中的温柔"],
        "calling_patterns": [{"burden_area": "门徒训练与AI工具",
                               "possible_calling": "用技术辅助属灵成长与教会门训", "confidence": 0.8}],
        "ministry_matches": [{"ministry_area": "成人主日学/门训内容设计",
                              "match_reason": "结合教导、系统设计与长期神学兴趣。",
                              "suggested_first_step": "设计一个4周小组材料，并邀请2位成熟信徒反馈。",
                              "risk_notes": "避免变成单向灌输；保留聆听与回应。"}],
        "calling_experiments": [{"title": "4周门徒训练材料试运行",
                                 "hypothesis": "可能适合做结构化门训内容设计。",
                                 "ministry_area": "教导/门训",
                                 "expected_fruit": ["参与者更清楚福音根基", "获得群体反馈"]}],
    }


def _mock_suffering(payload, risk, crisis):
    pastor = risk in ("high", "critical")
    real_actions = []
    if pastor:
        real_actions = [
            "现在就联系一位你信任的真实的人（牧者、家人或可信的属灵同伴）。",
            "若你有立即的危险或想伤害自己，请联系当地紧急服务或危机热线。",
            "邀请一位同伴今天陪你，不要独自一人。",
        ]
    return {
        "case_type": "绝望危机" if pastor else "属灵干旱",
        "risk_level": risk,
        "suffering_stage": "lament",
        "theological_theme": "黑暗中的同在（诗篇13；哥林多后书1:3-5）",
        "summary": ("检测到高危信号，已优先建议连接真实的人与专业帮助。" if pastor
                    else "这是可以哀哭的时刻；神并不嫌弃你的眼泪。"),
        "lament_needed": True,
        "community_support_needed": True,
        "professional_help_recommended": pastor,
        "scripture_anchors": ["诗篇13", "哥林多后书1:3-5"],
        "guided_prayer": "主啊，我在黑暗里向你呼求……求你的同在托住我，也差遣真实的人陪我。",
        "real_person_actions": real_actions,
        "care_plan": {
            "title": "14天哀歌与盼望之路" if not pastor else "危机后的陪伴与稳固之路",
            "scripture_path": ["诗篇13", "诗篇42", "哥林多后书1:3-5"],
            "prayer_path": ["写下你的哀歌", "把它带到神面前", "邀请一位同伴一起祷告"],
            "community_actions": ["本周与一位同伴见面", "向小组请求代祷"],
            "duration_days": 14,
        },
    }


_MOCK_BUILDERS = {
    "DiagnosisAgentOutput": _mock_diagnosis,
    "WorldviewAgentOutput": _mock_worldview,
    "GiftCallingAgentOutput": _mock_gift,
    "SufferingAgentOutput": _mock_suffering,
}


def _generic_mock(schema: Type[BaseModel]) -> Dict[str, Any]:
    fields = getattr(schema, "model_fields", {})
    out: Dict[str, Any] = {}
    for fname, finfo in fields.items():
        if finfo.is_required():
            ann = str(finfo.annotation)
            if "int" in ann:
                out[fname] = 1
            elif "float" in ann:
                out[fname] = 0.5
            elif "List" in ann or "list" in ann:
                out[fname] = []
            else:
                out[fname] = "n/a"
    return out


# ── OpenAI-compatible provider (the workhorse) ──────────────────────────────
class OpenAICompatibleProvider(LLMProvider):
    name = "openai"
    default_base = "https://api.openai.com/v1"

    def _url(self) -> str:
        base = self.base_url or self.default_base
        if base.endswith("/chat/completions"):
            return base
        return base + "/chat/completions"

    def complete(self, messages, *, temperature: float = 0.3, max_tokens=None) -> ProviderResponse:
        body = {"model": self.model or "gpt-4o-mini", "messages": messages,
                "temperature": temperature}
        if max_tokens:
            body["max_tokens"] = max_tokens
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        last = None
        for attempt in range(self.max_retries + 1):
            try:
                r = _http_client().post(self._url(), headers=headers, json=body,
                                        timeout=self.timeout)
                if r.status_code >= 400:
                    msg = f"{self.name} HTTP {r.status_code}: {r.text[:200]}"
                    if r.status_code in (429, 500, 502, 503, 504):
                        last = LLMError(msg)
                        time.sleep(0.6 * (attempt + 1)); continue
                    # Non-retryable 4xx (400/401/403/404 …): fail fast, no retry.
                    raise LLMError(msg)
                data = r.json()
                text = data["choices"][0]["message"]["content"].strip()
                usage = data.get("usage", {}) or {}
                return ProviderResponse(
                    text=text,
                    input_tokens=usage.get("prompt_tokens"),
                    output_tokens=usage.get("completion_tokens"),
                    total_tokens=usage.get("total_tokens"),
                    raw=data,
                )
            except LLMError:
                raise  # non-retryable provider error — do not retry
            except Exception as exc:  # transport / parse error — retry
                last = exc
                time.sleep(0.6 * (attempt + 1))
        raise LLMError(f"{self.name} failed after retries: {last}")

    def embed(self, text: str) -> List[float]:
        base = (getattr(_settings, "embedding_base_url", "") or self.base_url or self.default_base).rstrip("/")
        url = base if base.endswith("/embeddings") else base + "/embeddings"
        key = getattr(_settings, "embedding_api_key", "") or self.api_key
        model = getattr(_settings, "embedding_model", "") or "text-embedding-3-small"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        r = _http_client().post(url, headers=headers,
                                json={"model": model, "input": text}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()["data"][0]["embedding"]


class LocalLLMProvider(OpenAICompatibleProvider):
    """OpenAI-compatible local server (vLLM / Ollama / LM Studio) at LLM_BASE_URL."""
    name = "local"
    default_base = "http://localhost:8000/v1"


class GeminiCompatibleProvider(OpenAICompatibleProvider):
    """Google Gemini via its OpenAI-compatible endpoint."""
    name = "gemini"
    default_base = "https://generativelanguage.googleapis.com/v1beta/openai"


# ── Anthropic provider ──────────────────────────────────────────────────────
class AnthropicCompatibleProvider(LLMProvider):
    name = "anthropic"
    default_base = "https://api.anthropic.com"

    def complete(self, messages, *, temperature: float = 0.3, max_tokens=None) -> ProviderResponse:
        system = " ".join(m["content"] for m in messages if m.get("role") == "system")
        turns = [{"role": ("assistant" if m["role"] == "assistant" else "user"),
                  "content": m["content"]} for m in messages if m.get("role") != "system"]
        body = {"model": self.model or "claude-3-5-sonnet-latest",
                "system": system, "messages": turns,
                "max_tokens": max_tokens or 1024, "temperature": temperature}
        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01",
                   "Content-Type": "application/json"}
        base = self.base_url or self.default_base
        r = _http_client().post(base + "/v1/messages", headers=headers, json=body,
                                timeout=self.timeout)
        if r.status_code >= 400:
            raise LLMError(f"anthropic HTTP {r.status_code}: {r.text[:200]}")
        data = r.json()
        text = "".join(blk.get("text", "") for blk in data.get("content", []) if blk.get("type") == "text").strip()
        usage = data.get("usage", {}) or {}
        return ProviderResponse(text=text, input_tokens=usage.get("input_tokens"),
                                output_tokens=usage.get("output_tokens"),
                                total_tokens=(usage.get("input_tokens", 0) + usage.get("output_tokens", 0)) or None,
                                raw=data)


# ── Factory ──────────────────────────────────────────────────────────────────
_PROVIDERS = {
    "mock": MockLLMProvider,
    "openai": OpenAICompatibleProvider,
    "anthropic": AnthropicCompatibleProvider,
    "gemini": GeminiCompatibleProvider,
    "local": LocalLLMProvider,
}


def _real_configured() -> bool:
    if _settings is None:
        return False
    if (getattr(_settings, "agent_mode", "mock") or "mock").lower() != "real":
        return False
    return bool(getattr(_settings, "llm_api_key", "") or getattr(_settings, "llm_base_url", ""))


def get_provider(force: Optional[str] = None) -> LLMProvider:
    """Return the active provider. Falls back to Mock unless AGENT_MODE=real
    AND a key/base_url is configured — preserving graceful degradation."""
    if force:
        cls = _PROVIDERS.get(force, MockLLMProvider)
        if cls is MockLLMProvider:
            return MockLLMProvider()
        return cls(model=getattr(_settings, "llm_model", "") or "",
                   api_key=getattr(_settings, "llm_api_key", "") or "",
                   base_url=getattr(_settings, "llm_base_url", "") or "",
                   timeout=getattr(_settings, "llm_timeout_seconds", 60),
                   max_retries=getattr(_settings, "llm_max_retries", 2))
    if not _real_configured():
        return MockLLMProvider()
    cls = _PROVIDERS.get((getattr(_settings, "llm_provider", "openai") or "openai").lower(),
                         OpenAICompatibleProvider)
    return cls(model=getattr(_settings, "llm_model", "") or "",
               api_key=getattr(_settings, "llm_api_key", "") or "",
               base_url=getattr(_settings, "llm_base_url", "") or "",
               timeout=getattr(_settings, "llm_timeout_seconds", 60),
               max_retries=getattr(_settings, "llm_max_retries", 2))


# ── Helpers ──────────────────────────────────────────────────────────────────
def _last_user(messages: List[Dict[str, str]]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return m.get("content", "")
    return ""


def _payload_text(payload: Any) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False)
    except Exception:
        return str(payload)


_JSON_RE = re.compile(r"\{.*\}", re.S)


def _extract_json(text: str) -> dict:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*", "", text).strip().rstrip("`").strip()
    m = _JSON_RE.search(text)
    if not m:
        raise LLMValidationError("no JSON object found in model output")
    return json.loads(m.group(0))


# ── Orchestrators ────────────────────────────────────────────────────────────
def generate_text(system_prompt: str, user_prompt: str, *, temperature: float = 0.3,
                  max_tokens: Optional[int] = None, email: Optional[str] = None,
                  agent_run_id: Optional[int] = None, agent_name: str = "agent") -> str:
    provider = get_provider()
    max_tokens = max_tokens or DEFAULT_MAX_TOKENS
    messages = [{"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}]
    t0 = time.time()
    try:
        resp = provider.complete(messages, temperature=temperature, max_tokens=max_tokens)
        _record_run_metrics(agent_run_id, provider, resp, int((time.time() - t0) * 1000), status="ok")
        return resp.text
    except Exception as exc:
        _record_run_metrics(agent_run_id, provider, None, int((time.time() - t0) * 1000),
                            status="error", error=str(exc))
        raise


def generate_json(system_prompt: str, user_payload: Dict[str, Any], schema: Type[BaseModel], *,
                  temperature: float = 0.2, max_tokens: Optional[int] = None,
                  email: Optional[str] = None, agent_run_id: Optional[int] = None,
                  agent_name: str = "agent", skill_name: str = "") -> BaseModel:
    """Return a validated *schema* instance. One automatic retry on invalid JSON;
    a second failure raises LLMValidationError (callers fall back deterministically)."""
    provider = get_provider()
    max_tokens = max_tokens or DEFAULT_MAX_TOKENS

    # Mock path: deterministic structured output, still schema-validated.
    if isinstance(provider, MockLLMProvider):
        t0 = time.time()
        data = provider.structured(schema, user_payload)
        model = schema.model_validate(data)
        _record_run_metrics(agent_run_id, provider, None, int((time.time() - t0) * 1000),
                            status="ok", skill_name=skill_name)
        return model

    schema_hint = (
        "你必须只输出严格 JSON，且符合以下 JSON Schema，不要输出任何解释或代码块标记：\n"
        + json.dumps(schema.model_json_schema(), ensure_ascii=False)
    )
    messages = [
        {"role": "system", "content": system_prompt + "\n\n" + schema_hint},
        {"role": "user", "content": _payload_text(user_payload)},
    ]
    last_err: Optional[str] = None
    for attempt in range(2):  # initial try + exactly one retry
        t0 = time.time()
        try:
            resp = provider.complete(messages, temperature=temperature, max_tokens=max_tokens)
            data = _extract_json(resp.text)
            model = schema.model_validate(data)
            _record_run_metrics(agent_run_id, provider, resp, int((time.time() - t0) * 1000),
                                status="ok", skill_name=skill_name)
            return model
        except (ValidationError, LLMValidationError, json.JSONDecodeError) as exc:
            last_err = str(exc)[:300]
            _record_run_metrics(agent_run_id, provider, None, int((time.time() - t0) * 1000),
                                status="invalid_json", error=last_err, skill_name=skill_name)
            messages.append({"role": "user",
                             "content": "你上一次的输出不是有效 JSON 或不符合 schema，请只返回符合 schema 的纯 JSON。"})
        except Exception as exc:
            last_err = str(exc)[:300]
            _record_run_metrics(agent_run_id, provider, None, int((time.time() - t0) * 1000),
                                status="error", error=last_err, skill_name=skill_name)
            break
    _mark_agent_run_failed(agent_run_id, last_err)
    raise LLMValidationError(f"schema validation failed after retry: {last_err}")


def embed_text(text: str) -> Optional[List[float]]:
    """Return a retrieval embedding, or ``None`` when unavailable.

    On provider failure we deliberately return ``None`` rather than a
    different-dimensional mock vector: a 16-dim mock silently mismatches stored
    1536-dim (OpenAI) / 1024-dim (BGE-M3) vectors and empties similarity search.
    In Mock mode the Mock provider returns a consistent 16-dim vector for both
    index and query, so that path stays coherent.  Callers must treat ``None``
    as 'embedding unavailable' and degrade explicitly."""
    provider = get_provider()
    try:
        vec = provider.embed(text)
    except Exception:
        return None
    if isinstance(vec, list) and vec:
        return [float(x) for x in vec]
    return None


def complete_text(prompt: str, *, system_prompt: str = "", temperature: float = 0.3,
                  max_tokens: Optional[int] = None,
                  agent_run_id: Optional[int] = None,
                  agent_name: str = "engine") -> Optional[str]:
    """Single-shot text completion from a raw prompt string.

    Builds a proper messages list and routes through the unified provider (with
    its own timeout/retry), returning the model text or ``None`` on any failure.
    This is the shared entrypoint the per-engine ``_call_ai`` helpers use (via
    engine_ai.call_ai), replacing the historical broken reference to a
    non-existent ``call_llm``."""
    if not (prompt or "").strip():
        return None
    provider = get_provider()
    messages: List[Dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    t0 = time.time()
    try:
        resp = provider.complete(messages, temperature=temperature,
                                 max_tokens=max_tokens or DEFAULT_MAX_TOKENS)
        _record_run_metrics(agent_run_id, provider, resp, int((time.time() - t0) * 1000),
                            status="ok")
        return resp.text or None
    except Exception as exc:
        _record_run_metrics(agent_run_id, provider, None, int((time.time() - t0) * 1000),
                            status="error", error=str(exc))
        return None


# ── Logging ──────────────────────────────────────────────────────────────────
def _record_run_metrics(agent_run_id, provider, resp: Optional[ProviderResponse],
                        latency_ms: int, *, status: str = "ok", error: str = "",
                        skill_name: str = "", prompt_version: str = "") -> None:
    """Record provider observability onto agent_runs (migration 0074 columns:
    model_name / latency_ms / token_usage / error_message / skill_name /
    prompt_version). Per-call metrics accumulate across retries within one run.
    No request/response payloads are stored — only metrics — so no plaintext
    user text is ever persisted here. Best-effort; silently no-op if the
    observability columns are not present."""
    if _get_db is None or agent_run_id is None:
        return
    inp = int(getattr(resp, "input_tokens", None) or 0)
    outp = int(getattr(resp, "output_tokens", None) or 0)
    tot = int(getattr(resp, "total_tokens", None) or (inp + outp))
    model = getattr(provider, "model", "") or getattr(provider, "name", "")
    conn = None
    try:
        conn = _get_db()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE agent_runs SET
                    model_name = %s,
                    skill_name = COALESCE(NULLIF(skill_name, ''), %s),
                    prompt_version = COALESCE(NULLIF(prompt_version, ''), %s),
                    latency_ms = COALESCE(latency_ms, 0) + %s,
                    token_usage = jsonb_build_object(
                        'input',  COALESCE((token_usage->>'input')::int, 0) + %s,
                        'output', COALESCE((token_usage->>'output')::int, 0) + %s,
                        'total',  COALESCE((token_usage->>'total')::int, 0) + %s),
                    error_message = CASE WHEN %s <> '' THEN %s ELSE error_message END
                WHERE id = %s
                """,
                (model, skill_name, prompt_version, int(latency_ms or 0),
                 inp, outp, tot, (error or ""), (error or "")[:500], agent_run_id),
            )
        conn.commit()
    except Exception:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
    finally:
        if conn is not None and _release_db is not None:
            _release_db(conn)


def _mark_agent_run_failed(agent_run_id: Optional[int], err: Optional[str]) -> None:
    if _get_db is None or agent_run_id is None:
        return
    conn = None
    try:
        conn = _get_db()
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "UPDATE agent_runs SET status='FAILED', error_message=%s, "
                    "output_payload = output_payload || %s::jsonb WHERE id=%s",
                    ((err or "")[:500], json.dumps({"error_message": (err or "")[:500]}), agent_run_id),
                )
            except Exception:
                conn.rollback()
                cur.execute(
                    "UPDATE agent_runs SET status='FAILED', "
                    "output_payload = output_payload || %s::jsonb WHERE id=%s",
                    (json.dumps({"error_message": (err or "")[:500]}), agent_run_id),
                )
        conn.commit()
    except Exception:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
    finally:
        if conn is not None and _release_db is not None:
            _release_db(conn)
