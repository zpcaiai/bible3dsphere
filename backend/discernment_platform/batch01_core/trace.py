"""Skill 10 - trace-review-packager (deterministic)."""

from __future__ import annotations

import hashlib
import json

from .models import TraceBundle, TraceRecord

SKILL_ID = "trace-review-packager"
SKILL_VERSION = "0.1.0"

POLICY_VERSION = "0.1.0"

REQUIRED_SKILLS = (
    "pastoral-safety-guardian",
    "case-intake-normalizer",
    "claim-evidence-extractor",
    "worldview-frame-mapper",
    "pride-signal-detector",
    "desire-idolatry-mapper",
    "socratic-question-planner",
    "discernment-report-composer",
)

INTERNAL_ONLY_FIELDS = (
    "pride_hypotheses",
    "desire_map",
    "safety_decisions",
)


def digest(payload: object) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def record(
    *,
    case_id: str,
    skill_id: str,
    skill_version: str,
    payload_in: object,
    payload_out: object,
    evidence_links: list[str] | None = None,
    safety_decisions: list[dict] | None = None,
    latency_ms: float = 0.0,
) -> TraceRecord:
    input_hash = digest(payload_in)
    output_hash = digest(payload_out)
    return TraceRecord(
        trace_id=f"{case_id}:{skill_id}:{output_hash[:12]}",
        case_id=case_id,
        skill_id=skill_id,
        skill_version=skill_version,
        prompt_hash=digest(f"{skill_id}@{skill_version}"),
        input_hash=input_hash,
        output_hash=output_hash,
        structured_output=payload_out if isinstance(payload_out, dict) else {"value": str(payload_out)},
        evidence_links=evidence_links or [],
        safety_decisions=safety_decisions or [],
        latency_ms=latency_ms,
        policy_version=POLICY_VERSION,
    )


def package(case_id: str, records: list[TraceRecord]) -> TraceBundle:
    """Bundle traces. A report without a complete trace is not production-ready."""

    present = {r.skill_id for r in records}
    missing = [s for s in REQUIRED_SKILLS if s not in present]
    return TraceBundle(
        case_id=case_id,
        records=records,
        production_ready=not missing,
        missing_skills=missing,
    )


def review_packet(bundle: TraceBundle, report: dict) -> dict:
    return {
        "case_id": bundle.case_id,
        "report": report,
        "trace_records": [r.model_dump(mode="json") for r in bundle.records],
        "production_ready": bundle.production_ready,
        "missing_skills": bundle.missing_skills,
        "policy_version": POLICY_VERSION,
    }


def redacted_user_view(report: dict) -> dict:
    """Hide internal inferences from the end-user surface."""

    view = {k: v for k, v in report.items() if k not in INTERNAL_ONLY_FIELDS}
    view["hidden_sections"] = list(INTERNAL_ONLY_FIELDS)
    return view


def apply_human_override(
    bundle: TraceBundle,
    trace_id: str,
    field: str,
    new_value: object,
    reason: str,
    reviewer: str,
) -> TraceBundle:
    """Human edits keep the original value and the stated reason."""

    for rec in bundle.records:
        if rec.trace_id == trace_id:
            original = rec.structured_output.get(field)
            rec.human_overrides.append(
                {
                    "field": field,
                    "original_value": original,
                    "new_value": new_value,
                    "reason": reason,
                    "reviewer": reviewer,
                }
            )
            rec.structured_output[field] = new_value
    return bundle
