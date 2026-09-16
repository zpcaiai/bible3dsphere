"""Generate golden fixtures for every model-bound skill.

A golden is an example of *correct* output for a SKILL.md contract: it locks
the output shape, and it must pass the contract's own guardrails. Anything the
generator emits is run through the real runtime before being written, so a
fixture that would be blocked never lands on disk.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.discernment_platform.model_adapter import ScriptedAdapter  # noqa: E402
from backend.discernment_platform.skill_runtime import (  # noqa: E402
    SkillRuntime,
    get_runtime,
    output_envelope,
)
from backend.discernment_platform.skills import get_skill_registry  # noqa: E402

GOLDEN_ROOT = Path(__file__).resolve().parents[1] / "backend/discernment_platform/data/golden"

HEDGE = "值得察验的是，这里可能"
LIMITATION_BASE = [
    "本结果基于所提供材料，系统不能读心，也不领受新启示。",
    "所有关于动机的表述均为假设，附证据等级与替代解释。",
]

LIST_TOKENS = (
    "observations", "findings", "claims", "signals", "hypotheses", "questions",
    "risks", "limitations", "uncertainties", "evidence", "references", "steps",
    "actions", "recommendations", "blockers", "decisions", "results", "options",
    "triggers", "segments", "nodes", "edges", "items", "notes", "flags",
    "updates", "comparisons", "experiments", "themes", "patterns", "sources",
)
TEXT_TOKENS = ("summary", "narrative", "answer", "recommendation", "status", "state", "level", "tier")
OBJECT_TOKENS = ("trace", "metadata", "profile", "graph", "snapshot", "map", "matrix", "plan")


def _slug_words(key: str) -> set[str]:
    return set(re.split(r"[_\s]+", key))


def _finding(index: int, subject: str) -> dict:
    return {
        "id": f"item-{index:02d}",
        "observation": f"材料中出现与「{subject}」相关的可核验表述。",
        "interpretation_hypothesis": f"{HEDGE}存在与「{subject}」相关的模式；这是假设，不是结论。",
        "evidence_level": "E2",
        "alternative_explanations": [
            "可能只是特定语境下的表达习惯",
            "可能是营销话术，不代表当事人真实自我认知",
        ],
        "disconfirming_evidence_needed": ["跨场景、跨时间是否出现同一模式"],
        "limitations": ["证据等级为 E2，不足以作为结论"],
    }


def _value_for(key: str, declared: str, contract) -> object:
    words = _slug_words(key)
    subject = declared[:24] or key

    if words & set(TEXT_TOKENS):
        return f"针对「{contract.name}」的中性摘要：以下区分观察、解释与假设，解释与假设均可被推翻。"
    if words & set(OBJECT_TOKENS):
        return {
            "declared_as": declared,
            "nodes": [_finding(1, subject)],
            "evidence_level": "E2",
            "unknowns": ["材料之外的行为模式是否一致"],
        }
    if words & set(LIST_TOKENS) or key.endswith("s"):
        return [_finding(1, subject), _finding(2, subject)]
    return {
        "declared_as": declared,
        "value": f"依据契约「{declared}」产出的结构化结果（示例值）。",
        "evidence_level": "E2",
        "limitations": list(LIMITATION_BASE),
    }


# --- guardrail-aware enrichment --------------------------------------------

CHRIST_LINE = (
    "基督替我们成全了标准，祂的死与复活重新定义了荣耀；回应是悔改与信靠，"
    "不是靠表现赢取接纳。"
)


def _enrich(payload: dict, contract) -> dict:
    """Make the golden satisfy the structural guardrails it will be judged by."""

    blob = json.dumps(payload, ensure_ascii=False)
    guardrails = " ".join(contract.guardrails)

    for key, value in list(payload.items()):
        words = _slug_words(key)

        # practice/action output must be Christ-centred, not a behaviour list
        if words & {"practice", "practices", "action", "response", "next"}:
            if isinstance(value, dict):
                value.setdefault("christ_center", CHRIST_LINE)
            elif isinstance(value, list):
                value.append({"id": "christ", "note": CHRIST_LINE})

        # gospel output must name sin and repentance
        if words & {"gospel", "bridge", "path"}:
            if isinstance(value, dict):
                value.setdefault("repentance_and_faith", "指明罪、呼召悔改，并指向基督的赦免。")
            elif isinstance(value, list):
                value.append({"id": "repentance", "note": "指明罪、呼召悔改，并指向基督的赦免。"})

        # disclosure-like output needs scope and expiry
        if words & {"disclosure", "access", "workbench"}:
            if isinstance(value, dict):
                value.setdefault("purpose", "pastoral_care")
                value.setdefault("expires_at", "2027-01-01T00:00:00Z")

        # doctrine tiers must carry a tradition label
        if words & {"doctrine", "claim", "claims"} and isinstance(value, dict):
            value.setdefault("tradition_label", "标注为特定传统立场，未作普遍陈述")

        # business-model analysis must cover all four risk dimensions
        if words & {"business", "monetization", "model"} and isinstance(value, dict):
            value.setdefault("disclosure", "收费与利益关系披露充分")
            value.setdefault("honesty", "宣称与可核验事实一致")
            value.setdefault("fit", "产品与目标人群需求适配")
            value.setdefault("vulnerability", "未见针对脆弱人群的定向利用")

        # certification decisions must not self-certify high-severity controls
        if words & {"certification", "certifier", "control", "decisions"}:
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        item.setdefault("severity", "C1")
                        item.setdefault("human_reviewer", "release_board")

    # Contract-level enrichment must live INSIDE a declared output key: the
    # runtime strips anything outside the envelope, so a top-level helper key
    # would be dropped and show up as a shape diff on replay.
    first_key = next(iter(payload), None)
    if first_key is None:
        return payload

    def _attach(field: str, value: object) -> None:
        slot = payload[first_key]
        if isinstance(slot, dict):
            slot.setdefault(field, value)
        elif isinstance(slot, list):
            slot.append({"id": field, "note": value})
        else:
            payload[first_key] = {"value": slot, field: value}

    # scripture-citing skills must show context, never bare proof-texts
    if "proof-text" in guardrails or "断章取义" in guardrails:
        _attach(
            "scripture_context",
            {
                "used_as_proof": True,
                "literary_context": "已提供上下文与体裁说明",
                "canonical_context": "已置于救赎历史脉络中",
            },
        )

    # high-risk domains and crisis language must route to real care
    if "professional care" in guardrails or "替代专业" in guardrails:
        _attach("care_note", "如涉及高风险情形，转介合格牧者与专业人员，不取代专业照护。")

    del blob
    return payload


def build_golden(contract) -> dict:
    envelope = output_envelope(contract)
    payload = {
        key: _value_for(key, slot["declared_as"], contract)
        for key, slot in envelope.items()
    }
    return _enrich(payload, contract)


def build_input(contract) -> dict:
    return {
        "case_id": f"golden-{contract.skill_id}",
        "declared_inputs": list(contract.inputs),
        "material": "某公开材料片段，用于锁定该技能的输出形状。",
        "consent_scope": {
            "allow_spiritual_analysis": True,
            "allow_gospel_bridge": True,
        },
        "sensitivity": "normal",
    }


def main() -> int:
    registry = get_skill_registry()
    native = set(get_runtime().binding_report()["native_skill_ids"])
    bound = [c for c in registry if c.skill_id not in native]

    written, blocked = 0, []
    for contract in bound:
        golden = build_golden(contract)
        payload = build_input(contract)
        runtime = SkillRuntime(adapter=ScriptedAdapter({contract.skill_id: golden}))
        result = runtime.invoke(contract.skill_id, payload)
        if result.status != "ok":
            blocked.append((contract.skill_id, result.status, result.message[:160]))
            continue

        target = GOLDEN_ROOT / contract.batch_key
        target.mkdir(parents=True, exist_ok=True)
        (target / f"{contract.skill_id}.json").write_text(
            json.dumps(
                {
                    "skill_id": contract.skill_id,
                    "skill_name": contract.name,
                    "skill_version": contract.version,
                    "batch": contract.batch,
                    "tier": "structural",
                    "notes": "结构性黄金样例：锁定输出形状并通过该契约的全部 guardrail。",
                    "input": payload,
                    "expected_output_keys": sorted(golden),
                    "golden_output": golden,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        written += 1

    print(f"written: {written} / {len(bound)}")
    if blocked:
        print(f"blocked: {len(blocked)}")
        for skill_id, status, message in blocked[:25]:
            print(f"  {skill_id}: {status} | {message}")
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
