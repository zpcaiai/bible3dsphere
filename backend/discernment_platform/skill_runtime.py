"""Runtime that binds every SKILL.md contract to an executable handler.

Three binding modes exist, and a skill always declares which one it used:

``native``
    The contract is fully implemented in Python by one of the platform
    engines.  ``status`` is ``ok`` and ``outputs`` are computed.
``model``
    The contract needs a language model.  If an adapter is configured the
    runtime calls it and validates the structured result; if not, the runtime
    returns ``requires_model`` together with the fully rendered prompt and the
    declared output envelope.  Nothing is fabricated.
``deterministic-envelope``
    The contract is a checklist/composition step that the runtime can execute
    directly from the Processing Contract.

Every invocation enforces the contract's Guardrails section and maps errors
onto the contract's Failure Handling section.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Callable, Protocol

from . import guardrails as guardrail_module
from .skills import SkillContract, SkillRegistry, get_skill_registry

Payload = dict[str, Any]
Handler = Callable[[SkillContract, Payload, Payload], Payload]

KNOWN_FAILURE_CODES = (
    "INSUFFICIENT_EVIDENCE",
    "HIGH_RISK_REVIEW",
    "UNSUPPORTED_THEOLOGICAL_CLAIM",
    "MODEL_OUTPUT_INVALID",
    "USER_CONSENT_REQUIRED",
    "MISSING_REQUIRED_INPUT",
    "GUARDRAIL_VIOLATION",
    "HANDLER_ERROR",
)


class SkillInvocationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class ModelAdapter(Protocol):
    """Provider-neutral LLM seam (BATCH_01_IMPLEMENTATION step 3)."""

    name: str

    def complete(self, prompt: str, *, schema: Payload) -> Payload: ...


class NullAdapter:
    """Default adapter: refuses to invent output."""

    name = "null"

    def complete(self, prompt: str, *, schema: Payload) -> Payload:  # pragma: no cover
        raise SkillInvocationError(
            "MODEL_OUTPUT_INVALID", "no model adapter configured"
        )


@dataclass
class SkillResult:
    skill_id: str
    skill_version: str
    batch: int
    status: str  # ok | requires_model | failed | blocked
    binding: str  # native | model | deterministic-envelope
    outputs: Payload = field(default_factory=dict)
    guardrail_findings: list[dict] = field(default_factory=list)
    guardrail_coverage: dict[str, int] = field(default_factory=dict)
    processing_steps: list[dict] = field(default_factory=list)
    failure_code: str | None = None
    message: str = ""
    prompt: str = ""
    limitations: list[str] = field(default_factory=list)
    trace: Payload = field(default_factory=dict)
    rollout: Payload = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    @property
    def authoritative(self) -> bool:
        """True only when the caller may act on ``outputs``."""

        return self.status == "ok"

    def as_dict(self) -> Payload:
        return {
            "skill_id": self.skill_id,
            "skill_version": self.skill_version,
            "batch": self.batch,
            "status": self.status,
            "binding": self.binding,
            "outputs": self.outputs,
            "guardrail_findings": self.guardrail_findings,
            "guardrail_coverage": self.guardrail_coverage,
            "processing_steps": self.processing_steps,
            "failure_code": self.failure_code,
            "message": self.message,
            "prompt": self.prompt,
            "limitations": self.limitations,
            "trace": self.trace,
            "rollout": self.rollout,
            "authoritative": self.authoritative,
        }


# --- handler registry ------------------------------------------------------

_HANDLERS: dict[str, Handler] = {}
_BINDING_KIND: dict[str, str] = {}


def handler(skill_id: str, *, binding: str = "native") -> Callable[[Handler], Handler]:
    """Register a native implementation for a skill_id."""

    def decorator(func: Handler) -> Handler:
        if skill_id in _HANDLERS:
            raise ValueError(f"Handler already registered for {skill_id}")
        _HANDLERS[skill_id] = func
        _BINDING_KIND[skill_id] = binding
        return func

    return decorator


def registered_handlers() -> dict[str, str]:
    return dict(_BINDING_KIND)


# --- contract-derived helpers ---------------------------------------------

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slug(text: str) -> str:
    ascii_only = re.sub(r"[^\x00-\x7F]+", " ", text).strip().lower()
    return _SLUG_RE.sub("_", ascii_only).strip("_")


def output_envelope(contract: SkillContract) -> Payload:
    """Empty structured envelope keyed by the contract's declared outputs."""

    envelope: Payload = {}
    for item in contract.outputs:
        cleaned = re.sub(r"^Structured output containing:?\s*", "", item).strip(" :;。，,")
        if not cleaned:
            continue
        key = slug(cleaned) or f"output_{len(envelope) + 1}"
        envelope[key] = {"declared_as": cleaned, "value": None}
    return envelope


def processing_checklist(contract: SkillContract) -> list[dict]:
    return [
        {"step": index + 1, "requirement": item, "status": "pending"}
        for index, item in enumerate(contract.processing_contract)
    ]


def render_prompt(contract: SkillContract, payload: Payload) -> str:
    """Render the provider-neutral prompt from the contract itself."""

    lines = [
        f"# Skill: {contract.name} ({contract.skill_id} v{contract.version})",
        "",
        "## Purpose",
        contract.purpose,
        "",
        "## Processing Contract (follow every step in order)",
    ]
    lines += [f"{i + 1}. {step}" for i, step in enumerate(contract.processing_contract)]
    if contract.prompt_contract:
        lines += ["", "## Prompt Contract", contract.prompt_contract]
    lines += ["", "## Guardrails (hard constraints)"]
    lines += [f"- {g}" for g in contract.guardrails]
    lines += ["", "## Failure Handling"]
    lines += [f"- {f}" for f in contract.failure_handling]
    lines += [
        "",
        "## Required output",
        "Return JSON matching exactly these keys:",
        json.dumps(
            {k: v["declared_as"] for k, v in output_envelope(contract).items()},
            ensure_ascii=False,
            indent=2,
        ),
        "",
        "## Input payload",
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
    ]
    return "\n".join(lines)


def digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()
    ).hexdigest()


def _failure_code_for(contract: SkillContract, exc: Exception) -> str:
    if isinstance(exc, SkillInvocationError):
        return exc.code
    blob = " ".join(contract.failure_handling)
    for code in KNOWN_FAILURE_CODES:
        if code in blob:
            return code
    return "HANDLER_ERROR"


# --- the runtime -----------------------------------------------------------

class SkillRuntime:
    def __init__(
        self,
        skills: SkillRegistry | None = None,
        adapter: ModelAdapter | None = None,
        policy: Any | None = None,
    ) -> None:
        # Importing here (not at module scope) both avoids the import cycle and
        # guarantees native handlers are registered no matter how the runtime is
        # constructed - otherwise a directly-built runtime would see an empty
        # handler table and treat every skill as model-bound.
        from . import skill_handlers  # noqa: F401

        self.skills = skills or get_skill_registry()
        self.adapter = adapter or NullAdapter()
        if policy is None:
            from .rollout import RolloutPolicy

            policy = RolloutPolicy.unrestricted()
        self.policy = policy

    # -- introspection ---------------------------------------------------

    def binding_report(self) -> Payload:
        native = [s for s in self.skills.skills if s in _HANDLERS]
        unbound = [s for s in self.skills.skills if s not in _HANDLERS]
        return {
            "total_skills": len(self.skills),
            "native_bindings": len(native),
            "contract_bindings": len(unbound),
            "by_kind": {
                kind: sum(1 for k in _BINDING_KIND.values() if k == kind)
                for kind in sorted(set(_BINDING_KIND.values()))
            },
            "native_skill_ids": sorted(native),
        }

    def rollout_report(self) -> Payload:
        """Which model-bound skills may run, and at what stage."""

        unbound = [c for c in self.skills if c.skill_id not in _HANDLERS]
        decisions = [self.policy.decide(c) for c in unbound]
        by_stage: dict[str, int] = {}
        for decision in decisions:
            by_stage[decision.stage.value] = by_stage.get(decision.stage.value, 0) + 1
        return {
            "policy": self.policy.as_dict(),
            "model_bound_skills": len(unbound),
            "by_stage": dict(sorted(by_stage.items())),
            "authoritative": sum(1 for d in decisions if d.authoritative),
            "blocked": sorted(d.skill_id for d in decisions if not d.allowed),
        }

    def prompt_for(self, skill_id: str, payload: Payload | None = None) -> str:
        return render_prompt(self.skills.get(skill_id), payload or {})

    # -- invocation ------------------------------------------------------

    def invoke(
        self,
        skill_id: str,
        payload: Payload | None = None,
        context: Payload | None = None,
    ) -> SkillResult:
        contract = self.skills.get(skill_id)
        payload = payload or {}
        context = context or {}
        started = time.perf_counter()

        result = SkillResult(
            skill_id=contract.skill_id,
            skill_version=contract.version,
            batch=contract.batch,
            status="ok",
            binding=_BINDING_KIND.get(skill_id, "model"),
        )
        result.processing_steps = processing_checklist(contract)

        try:
            if skill_id in _HANDLERS:
                outputs = _HANDLERS[skill_id](contract, payload, context)
                for step in result.processing_steps:
                    step["status"] = "executed"
            else:
                outputs = self._contract_binding(contract, payload, result)
        except SkillInvocationError as exc:
            result.status = "failed"
            result.failure_code = exc.code
            result.message = exc.message
            result.trace = self._trace(contract, payload, {}, started)
            return result
        except Exception as exc:  # noqa: BLE001 - mapped onto Failure Handling
            result.status = "failed"
            result.failure_code = _failure_code_for(contract, exc)
            result.message = str(exc)
            result.trace = self._trace(contract, payload, {}, started)
            return result

        result.outputs = outputs
        findings = guardrail_module.enforce(contract.guardrails, outputs, {**payload, **context})
        result.guardrail_findings = [f.as_dict() for f in findings]
        result.guardrail_coverage = guardrail_module.coverage(findings)

        breaches = guardrail_module.violations(findings)
        if breaches:
            result.status = "blocked"
            result.failure_code = "GUARDRAIL_VIOLATION"
            result.message = "; ".join(d for f in breaches for d in f.details)

        manual = [f for f in findings if f.status == "manual_review"]
        if manual:
            result.limitations.append(
                f"{len(manual)} 条 guardrail 无自动规则覆盖，需人工复核"
            )
        result.trace = self._trace(contract, payload, outputs, started)
        return result

    def _contract_binding(
        self, contract: SkillContract, payload: Payload, result: SkillResult
    ) -> Payload:
        """Model-backed contract binding, or an explicit requires_model result."""

        envelope = output_envelope(contract)
        prompt = render_prompt(contract, payload)
        result.prompt = prompt
        schema = {k: v["declared_as"] for k, v in envelope.items()}
        if isinstance(self.adapter, NullAdapter):
            result.status = "requires_model"
            result.binding = "model"
            result.limitations.append(
                "未配置模型适配器：已返回契约提示词与输出信封，未生成任何推断内容"
            )
            return envelope

        decision = self.policy.decide(contract)
        result.rollout = decision.as_dict()
        if not decision.allowed:
            result.status = "blocked_by_rollout"
            result.binding = "model"
            result.limitations.append(decision.reason)
            return envelope

        raw = self.adapter.complete(prompt, schema=schema)
        missing = [key for key in envelope if key not in raw]
        if missing:
            raise SkillInvocationError(
                "MODEL_OUTPUT_INVALID", f"model omitted required keys: {missing}"
            )
        result.binding = "model"
        for step in result.processing_steps:
            step["status"] = "delegated_to_model"
        if not decision.authoritative:
            result.status = "shadow"
            result.limitations.append(decision.reason)
        if decision.human_review_required:
            result.limitations.append(
                f"{decision.batch_key} 处于 {decision.stage.value} 阶段：本结果需人工复核"
            )
        return {key: raw[key] for key in envelope}

    def _trace(
        self, contract: SkillContract, payload: Payload, outputs: Payload, started: float
    ) -> Payload:
        trace = {
            "skill_id": contract.skill_id,
            "skill_version": contract.version,
            "batch": contract.batch,
            "input_hash": digest(payload),
            "output_hash": digest(outputs),
            "prompt_hash": digest(f"{contract.skill_id}@{contract.version}"),
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "adapter": self.adapter.name,
        }
        usage = getattr(self.adapter, "last_usage", None)
        if usage is not None and hasattr(usage, "as_dict"):
            trace["usage"] = usage.as_dict()
        return trace

    # -- pipelines --------------------------------------------------------

    def run_pipeline(
        self, batch: int | str, payload: Payload, context: Payload | None = None
    ) -> list[SkillResult]:
        """Run a batch's skills in declared order, stopping on a blocking failure."""

        results: list[SkillResult] = []
        state = dict(payload)
        for skill_id in self.skills.pipeline(batch):
            result = self.invoke(skill_id, state, context)
            results.append(result)
            if result.status == "ok":
                state = {**state, **{k: v for k, v in result.outputs.items()}}
            if result.status in {"failed", "blocked"} and _is_halting(result):
                break
        return results


def _is_halting(result: SkillResult) -> bool:
    return result.failure_code in {
        "HIGH_RISK_REVIEW",
        "USER_CONSENT_REQUIRED",
        "GUARDRAIL_VIOLATION",
    }


@lru_cache(maxsize=1)
def get_runtime() -> SkillRuntime:
    """Process-wide runtime.

    The adapter comes from ``DISCERNMENT_MODEL_PROVIDER``; unset means
    :class:`NullAdapter`, so the default deployment still refuses to fabricate.
    """

    from . import skill_handlers  # noqa: F401  - registers native handlers
    from .model_adapter import build_adapter_from_env
    from .rollout import get_policy

    return SkillRuntime(adapter=build_adapter_from_env(), policy=get_policy())
