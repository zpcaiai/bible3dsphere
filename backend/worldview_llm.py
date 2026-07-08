"""
worldview_llm.py — Worldview Formation OS 的可选 LLM 语义增强层

定位
====
本模块是 worldview 各引擎（diagnoser / truth_mapper / narrative / apologetics / cultural /
vocation / decision）做 **prose 润色** 的统一入口。它**委托项目既有的 `llm_provider`**
（OpenAI / Gemini / DeepSeek / Anthropic 兼容层 + MockLLMProvider + agent-run 日志），
因此与 suffering_engine 等使用同一套 OpenAI 配置（settings.llm_* / AGENT_MODE=real）。

安全原则（不变）
================
1. **可选 + 优雅降级**：未配置真实 provider（AGENT_MODE!=real 或无 key）→ enhance 返回 None，
   引擎回退到确定性输出。Mock provider 不用于 prose 润色（避免把占位文本当成果）。
2. **永不抛异常**。
3. **经文/评分/危机判定不交给 LLM**：仅润色白名单 prose 字段（见 merge_fields）。
4. **危机路径绝不入 LLM**：由各引擎在调用前保证（suffering 高危分支不调用本模块）。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

_HTTP_CLIENT = None


def _http_client():
    """Lazily build one keep-alive httpx.Client shared across calls (thread-safe;
    per-request timeouts passed at call sites)."""
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None:
        import httpx
        _HTTP_CLIENT = httpx.Client(timeout=60)
    return _HTTP_CLIENT


def _provider_mod():
    try:
        from backend import llm_provider as lp  # type: ignore
        return lp
    except Exception:
        try:
            import llm_provider as lp  # type: ignore
            return lp
        except Exception:
            return None


def _settings(settings: Any = None):
    if settings is not None:
        return settings
    try:
        from backend.core.config import settings as s  # type: ignore
        return s
    except Exception:
        try:
            from core.config import settings as s  # type: ignore
            return s
        except Exception:
            return None


def _provider_real() -> bool:
    """是否配置了真实（非 mock）provider —— 复用 llm_provider 的判定。"""
    lp = _provider_mod()
    if lp is not None:
        try:
            return bool(lp._real_configured())
        except Exception:
            pass
    return False


def _openai_config(settings: Any = None) -> Optional[Dict[str, Any]]:
    """直连 OpenAI 的兜底配置（当 llm_provider 不可用但仍有 key 时）。"""
    s = _settings(settings)
    key = (getattr(s, "llm_api_key", "") if s else "") or \
        os.environ.get("OPENAI_API_KEY", "") or os.environ.get("LLM_API_KEY", "")
    if not key or key.startswith("your_"):
        return None
    model = (getattr(s, "llm_model", "") if s else "") or os.environ.get("OPENAI_MODEL", "") or "gpt-4o-mini"
    base = (getattr(s, "llm_base_url", "") if s else "") or os.environ.get("OPENAI_BASE_URL", "") \
        or "https://api.openai.com/v1"
    timeout = float(getattr(s, "llm_timeout_seconds", 0) or 0) or 40.0
    return {"key": key, "model": model, "base": base.rstrip("/"), "timeout": timeout}


def available(settings: Any = None) -> bool:
    """有真实 provider（llm_provider real）或直连 OpenAI key 即视为可用。"""
    if _provider_real():
        return True
    return _openai_config(settings) is not None


def structured_available(settings: Any = None) -> bool:
    """结构化（schema 校验）AI 是否可用 —— 需要真实 llm_provider（非 Mock）。"""
    return _provider_real()


def _schema(schema_name: str):
    try:
        from llm_schemas import SCHEMA_REGISTRY  # type: ignore
    except Exception:
        try:
            from backend.llm_schemas import SCHEMA_REGISTRY  # type: ignore
        except Exception:
            return None
    return SCHEMA_REGISTRY.get(schema_name)


def generate_structured(system: str, payload: Dict[str, Any], schema_name: str, *,
                        email: Optional[str] = None, temperature: float = 0.3) -> Optional[Dict[str, Any]]:
    """
    结构化 AI：委托 llm_provider.generate_json（schema 校验 + 一次重试 + agent-run 日志）。
    仅在配置了**真实** provider 时运行；否则返回 None（离线/Mock → 调用方回退确定性）。
    任何失败（无 provider / 校验失败 / 网络）→ None，绝不抛异常。
    """
    if not _provider_real():
        return None
    lp = _provider_mod()
    schema = _schema(schema_name)
    if lp is None or schema is None:
        return None
    try:
        model = lp.generate_json(system, payload, schema, temperature=temperature,
                                 email=email, agent_name="worldview_" + schema_name)
        return model.model_dump()
    except Exception:
        return None


def _parse_json(text: str) -> Optional[Dict[str, Any]]:
    lp = _provider_mod()
    if lp is not None:
        try:
            return lp._extract_json(text)
        except Exception:
            return None
    import json
    import re
    if not text:
        return None
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


def enhance(system: str, user: str, *, temperature: float = 0.5,
            max_tokens: int = 700, settings: Any = None,
            email: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    一次 JSON 补全。优先走 llm_provider（真实 provider）；否则直连 OpenAI 兜底。
    任何失败 / 未配置 → None（调用方回退确定性）。Mock 不参与 prose 润色。
    """
    # 1) 项目既有 llm_provider（OpenAI 等真实 provider）
    if _provider_real():
        lp = _provider_mod()
        try:
            text = lp.generate_text(system, user, temperature=temperature,
                                    max_tokens=max_tokens, email=email,
                                    agent_name="worldview_enhance")
            parsed = _parse_json(text)
            if parsed:
                return parsed
        except Exception:
            pass  # 落到直连兜底

    # 2) 直连 OpenAI 兜底（当 llm_provider 不可用但配置了 key）
    cfg = _openai_config(settings)
    if cfg is not None:
        out = _call_openai(system, user, cfg, temperature, max_tokens)
        if out is not None:
            return out

    return None


def _call_openai(system: str, user: str, cfg: Dict[str, Any],
                 temperature: float, max_tokens: int) -> Optional[Dict[str, Any]]:
    try:
        import httpx
    except Exception:
        return None
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    try:
        from lang_context import apply_lang_messages as _apply_lang
        messages = _apply_lang(messages)
    except Exception:
        pass
    url = cfg["base"] + "/chat/completions"
    headers = {"Authorization": f"Bearer {cfg['key']}", "Content-Type": "application/json"}
    body = {"model": cfg["model"], "messages": messages, "temperature": temperature,
            "max_tokens": max_tokens, "response_format": {"type": "json_object"}}
    try:
        resp = _http_client().post(url, headers=headers, json=body, timeout=cfg["timeout"])
        if resp.status_code >= 400:
            body.pop("response_format", None)
            resp = _http_client().post(url, headers=headers, json=body, timeout=cfg["timeout"])
            if resp.status_code >= 400:
                return None
        return _parse_json(resp.json()["choices"][0]["message"]["content"])
    except Exception:
        return None


def merge_fields(base: Dict[str, Any], ai: Optional[Dict[str, Any]],
                 fields: List[str]) -> Dict[str, Any]:
    """把 AI 输出中**白名单字段**安全合并进确定性结果（仅非空 str / str 列表）。
    任何合并发生时标记 source='ai'。绝不允许覆盖未列出的字段（经文/评分/危机判定）。"""
    if not ai or not isinstance(ai, dict):
        return base
    out = dict(base)
    changed = False
    for f in fields:
        v = ai.get(f)
        if isinstance(v, str) and v.strip():
            out[f] = v.strip()
            changed = True
        elif isinstance(v, list) and v and all(isinstance(x, str) for x in v):
            out[f] = [x.strip() for x in v if x.strip()]
            changed = True
    if changed:
        out["source"] = "ai"
    return out


def meta(settings: Any = None) -> Dict[str, Any]:
    s = _settings(settings)
    provider = "none"
    model = None
    if _provider_real():
        provider = (getattr(s, "llm_provider", "openai") or "openai") if s else "openai"
        model = (getattr(s, "llm_model", "") if s else "") or "gpt-4o-mini"
    elif _openai_config(settings):
        provider = "openai"
        model = _openai_config(settings)["model"]
    return {
        "available": available(settings),
        "provider": provider,
        "model": model,
        "delegatesTo": "llm_provider",
        "note": "LLM 仅润色叙事/牧养文字；经文引用、评分、危机判定恒为确定性。",
    }
