"""Runtime behaviour: bindings, prompts, guardrails, failure mapping."""

from __future__ import annotations

import pytest

from backend.discernment_platform.skill_runtime import (
    NullAdapter,
    SkillInvocationError,
    SkillRuntime,
    get_runtime,
    output_envelope,
    processing_checklist,
    render_prompt,
    slug,
)
from backend.discernment_platform.skills import get_skill_registry

pytestmark = pytest.mark.no_db


@pytest.fixture(scope="module")
def runtime():
    return get_runtime()


class EchoAdapter:
    name = "echo"

    def __init__(self, payload=None):
        self.payload = payload
        self.calls = []

    def complete(self, prompt, *, schema):
        self.calls.append(prompt)
        if self.payload is not None:
            return self.payload
        return {key: f"model:{key}" for key in schema}


class BrokenAdapter:
    name = "broken"

    def complete(self, prompt, *, schema):
        return {}


def test_every_skill_is_invocable(runtime):
    for contract in get_skill_registry():
        result = runtime.invoke(contract.skill_id, {}, {})
        assert result.status in {"ok", "requires_model", "failed", "blocked"}
        assert result.skill_id == contract.skill_id


def test_no_skill_returns_unknown_binding(runtime):
    for contract in get_skill_registry():
        result = runtime.invoke(contract.skill_id, {}, {})
        assert result.binding in {"native", "model", "deterministic-envelope"}


def test_binding_report_covers_all_skills(runtime):
    report = runtime.binding_report()
    assert report["total_skills"] == 174
    assert report["native_bindings"] + report["contract_bindings"] == 174
    assert report["native_bindings"] >= 90


def test_unbound_skill_returns_requires_model_not_fabrication(runtime):
    unbound = [
        c.skill_id
        for c in get_skill_registry()
        if c.skill_id not in runtime.binding_report()["native_skill_ids"]
    ]
    assert unbound
    result = runtime.invoke(unbound[0], {"x": 1})
    assert result.status == "requires_model"
    assert result.prompt
    assert all(slot["value"] is None for slot in result.outputs.values())


def test_requires_model_declares_the_limitation(runtime):
    unbound = [
        c.skill_id
        for c in get_skill_registry()
        if c.skill_id not in runtime.binding_report()["native_skill_ids"]
    ]
    result = runtime.invoke(unbound[0], {})
    assert any("未配置模型适配器" in item for item in result.limitations)


def test_model_adapter_result_is_accepted():
    runtime = SkillRuntime(adapter=EchoAdapter())
    result = runtime.invoke("content-corpus-curator", {"x": 1})
    assert result.status in {"ok", "blocked"}
    assert result.binding == "model"
    assert all(v is not None for v in result.outputs.values())


def test_model_adapter_missing_keys_is_invalid_output():
    runtime = SkillRuntime(adapter=BrokenAdapter())
    result = runtime.invoke("content-corpus-curator", {"x": 1})
    assert result.status == "failed"
    assert result.failure_code == "MODEL_OUTPUT_INVALID"


def test_prompt_contains_contract_sections():
    contract = get_skill_registry().get("pride-signal-detector")
    prompt = render_prompt(contract, {"case_id": "c1"})
    assert contract.purpose in prompt
    assert "Guardrails" in prompt
    assert "Failure Handling" in prompt
    assert contract.processing_contract[0] in prompt


def test_output_envelope_is_keyed_by_declared_outputs():
    contract = get_skill_registry().get("critical-blocker-engine")
    envelope = output_envelope(contract)
    assert envelope
    assert all("declared_as" in slot for slot in envelope.values())


def test_processing_checklist_mirrors_contract():
    contract = get_skill_registry().get("critical-blocker-engine")
    checklist = processing_checklist(contract)
    assert len(checklist) == len(contract.processing_contract)
    assert checklist[0]["status"] == "pending"


def test_native_handler_marks_steps_executed(runtime):
    result = runtime.invoke(
        "pastoral-safety-guardian",
        {
            "case": {
                "case_id": "c1",
                "subject_type": "self_reflection",
                "raw_input": "我最近在读罗马书，对恩典有新的理解，很感恩。",
                "user_goal": "自省",
                "consent_scope": {"allow_spiritual_analysis": True, "allow_gospel_bridge": True},
            }
        },
    )
    assert result.status == "ok"
    assert all(step["status"] == "executed" for step in result.processing_steps)


def test_missing_required_input_is_mapped(runtime):
    result = runtime.invoke("relapse-cycle-detector", {})
    assert result.status == "failed"
    assert result.failure_code == "MISSING_REQUIRED_INPUT"


def test_trace_is_always_emitted(runtime):
    result = runtime.invoke("bible-reference-parser", {"text": "罗马书 8:1"})
    assert result.trace["input_hash"]
    assert result.trace["output_hash"]
    assert result.trace["skill_version"]


def test_guardrail_findings_are_attached(runtime):
    result = runtime.invoke("bible-reference-parser", {"text": "罗马书 8:1"})
    assert result.guardrail_findings
    assert sum(result.guardrail_coverage.values()) == len(result.guardrail_findings)


def test_guardrail_violation_blocks_the_result():
    class BadAdapter:
        name = "bad"

        def complete(self, prompt, *, schema):
            return {key: "他一定下地狱" for key in schema}

    runtime = SkillRuntime(adapter=BadAdapter())
    native = set(get_runtime().binding_report()["native_skill_ids"])
    contract = next(
        c
        for c in get_skill_registry()
        if c.skill_id not in native
        and any("salvation" in g.lower() or "得救" in g for g in c.guardrails)
    )
    result = runtime.invoke(contract.skill_id, {})
    assert result.status == "blocked"
    assert result.failure_code == "GUARDRAIL_VIOLATION"


def test_null_adapter_never_invents_output():
    runtime = SkillRuntime(adapter=NullAdapter())
    result = runtime.invoke("content-corpus-curator", {})
    assert result.status == "requires_model"


def test_prompt_for_helper(runtime):
    assert "Skill:" in runtime.prompt_for("pride-signal-detector", {})


def test_slug_is_ascii_safe():
    assert slug("Control decisions") == "control_decisions"
    assert slug("中文 output") == "output"


def test_invocation_error_carries_code():
    error = SkillInvocationError("HIGH_RISK_REVIEW", "halt")
    assert error.code == "HIGH_RISK_REVIEW"
