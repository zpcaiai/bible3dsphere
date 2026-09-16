"""Batch 03 - 网红热点与爆火分析：native bindings to the discernment engine."""

from __future__ import annotations

from ..skill_runtime import SkillInvocationError, handler
from ._engines import case_create, discernment_engine, registry
from ._support import Payload, require


@handler("viral-case-normalizer")
def viral_case_normalizer(contract, payload: Payload, context: Payload) -> Payload:
    case = case_create(payload)
    return {
        "virality_case": case.model_dump(mode="json"),
        "time_window": payload.get("time_window", "unspecified"),
        "platform_scope": payload.get("platform_scope", []),
        "authorization_boundary": case.consent_scope.model_dump(mode="json"),
    }


@handler("public-figure-evidence-profiler")
def public_figure_evidence_profiler(contract, payload: Payload, context: Payload) -> Payload:
    case = case_create(payload)
    items = [item.model_dump(mode="json") for item in case.source_items]
    public_only = [i for i in items if i.get("source_type") not in {"private", "dm", "leak"}]
    return {
        "evidence_profile": public_only,
        "excluded_non_public": [i for i in items if i not in public_only],
        "public_material_only": len(public_only) == len(items),
        "evidence_levels": sorted({i["evidence_level"] for i in public_only}),
    }


@handler("integrated-virality-report-composer")
def integrated_virality_report_composer(contract, payload: Payload, context: Payload) -> Payload:
    case = case_create(payload)
    case_id = payload.get("case_id", "virality-case")
    report = discernment_engine().analyze(case_id=case_id, case=case)
    return {
        "integrated_report": report,
        "virality": report.get("virality"),
        "review_status": report.get("review_status"),
    }


@handler("public-figure-safety-guardian")
def public_figure_safety_guardian(contract, payload: Payload, context: Payload) -> Payload:
    from ..safety import precheck

    raw = payload.get("raw_input") or (payload.get("case") or {}).get("raw_input", "")
    if not raw:
        raise SkillInvocationError("MISSING_REQUIRED_INPUT", "raw_input is required")
    decision = precheck(
        raw,
        subject_type=payload.get("subject_type", "person"),
        sensitivity=payload.get("sensitivity", "normal"),
    )
    data = decision.as_dict()
    data["public_material_only"] = True
    return data


@handler("worldview-salvation-linker")
def worldview_salvation_linker(contract, payload: Payload, context: Payload) -> Payload:
    (text,) = require(payload, "raw_input") if "raw_input" in payload else (
        (payload.get("case") or {}).get("raw_input", ""),
    )
    matches = discernment_engine()._domain_matches(text)
    return {
        "domain_matches": matches,
        "salvation_narratives": [
            {
                "pack_id": m["pack_id"],
                "substitute_salvation": registry().domain_packs[m["pack_id"]]["worldview"].get(
                    "who_saves", ""
                ),
            }
            for m in matches
        ],
    }
