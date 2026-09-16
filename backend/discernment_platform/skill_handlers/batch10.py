"""Batch 10 - 统一 Production Release Gate：bindings to production_gate."""

from __future__ import annotations

from ..skill_runtime import SkillInvocationError, handler
from ._engines import registry
from ._support import Payload, dumped, require


def _candidate(payload: Payload):
    from ..production_gate.models import ReleaseCandidate

    raw = payload.get("release_candidate") or payload.get("candidate")
    if raw is None:
        raise SkillInvocationError("MISSING_REQUIRED_INPUT", "release_candidate is required")
    return raw if isinstance(raw, ReleaseCandidate) else ReleaseCandidate(**raw)


def _findings(payload: Payload) -> list:
    from ..production_gate.models import Finding

    return [f if isinstance(f, Finding) else Finding(**f) for f in payload.get("findings", []) or []]


def _domain_results(payload: Payload) -> list:
    from ..production_gate.models import DomainResult

    return [
        d if isinstance(d, DomainResult) else DomainResult(**d)
        for d in payload.get("domain_results", []) or []
    ]


def _evidence(payload: Payload) -> list:
    from ..production_gate.models import EvidenceItem

    return [
        e if isinstance(e, EvidenceItem) else EvidenceItem(**e)
        for e in payload.get("evidence", []) or []
    ]


@handler("release-candidate-intake")
def release_candidate_intake(contract, payload: Payload, context: Payload) -> Payload:
    candidate = _candidate(payload)
    return {
        "release_candidate": dumped(candidate),
        "build_bound": bool(candidate.build_hash),
        "target_scope": candidate.target_scope,
    }


@handler("batch-manifest-dependency-validator")
def batch_manifest_validator(contract, payload: Payload, context: Payload) -> Payload:
    manifests = registry().manifests
    missing = [f"batch{n:02d}" for n in range(1, 11) if f"batch{n:02d}" not in manifests]
    if missing:
        raise SkillInvocationError("INSUFFICIENT_EVIDENCE", f"missing manifests: {missing}")
    required = manifests["batch10"].get("requires", {})
    unsatisfied = [
        key for key in required if key not in manifests
    ]
    return {
        "manifest_count": len(manifests),
        "versions": {k: v["version"] for k, v in sorted(manifests.items())},
        "declared_requirements": required,
        "unsatisfied_requirements": unsatisfied,
        "valid": not unsatisfied,
    }


@handler("certification-pack-registry-loader")
def certification_registry_loader(contract, payload: Payload, context: Payload) -> Payload:
    reg = registry()
    controls = [
        control
        for packet in reg.certification_packs.values()
        for control in packet["controls"]
    ]
    return {
        "certification_pack_count": len(reg.certification_packs),
        "control_count": len(controls),
        "control_ids": sorted(c["control_id"] for c in controls),
        "by_severity": {
            severity: sum(1 for c in controls if c.get("severity") == severity)
            for severity in ("C0", "C1", "C2", "C3", "C4")
        },
    }


@handler("evidence-completeness-validator")
def evidence_completeness_validator(contract, payload: Payload, context: Payload) -> Payload:
    from datetime import datetime, timezone

    from ..production_gate import validate_evidence
    from ..production_gate.models import CertificationControl

    controls_raw = payload.get("controls") or []
    if not controls_raw:
        raise SkillInvocationError("MISSING_REQUIRED_INPUT", "controls are required")
    controls = [
        c if isinstance(c, CertificationControl) else CertificationControl(**c)
        for c in controls_raw
    ]
    evidence = _evidence(payload)
    now = datetime.now(timezone.utc)
    results = [validate_evidence(control, evidence, now) for control in controls]
    return {"control_results": dumped(results), "evaluated": len(results)}


@handler("critical-blocker-engine")
def critical_blocker_engine(contract, payload: Payload, context: Payload) -> Payload:
    from ..production_gate import CriticalBlockerEngine

    return {"blockers": dumped(CriticalBlockerEngine().evaluate(_findings(payload)))}


@handler("release-board-workflow-manager")
def release_board_workflow(contract, payload: Payload, context: Payload) -> Payload:
    signatories = payload.get("signatories", []) or []
    dissent = [s for s in signatories if isinstance(s, dict) and s.get("dissent")]
    return {
        "signatories": signatories,
        "signed": bool(signatories) and not dissent,
        "dissent_preserved": dissent,
        "human_review": True,
    }


@handler("release-certificate-issuer")
def release_certificate_issuer(contract, payload: Payload, context: Payload) -> Payload:
    from ..production_gate import issue_certificate
    from ..production_gate.models import ReleaseStatus

    certificate_id, release_id, expires_at, rollback_target = require(
        payload, "certificate_id", "release_id", "expires_at", "rollback_target"
    )
    status_raw = payload.get("status", "APPROVED_FOR_PILOT")
    try:
        status = ReleaseStatus(status_raw)
    except ValueError as exc:
        raise SkillInvocationError("MODEL_OUTPUT_INVALID", str(exc)) from exc
    certificate = issue_certificate(
        certificate_id=certificate_id,
        release_id=release_id,
        status=status,
        expires_at=expires_at,
        scope=payload.get("scope", {}),
        domain_results=payload.get("domain_results", []),
        open_findings=payload.get("open_findings", []),
        accepted_risks=payload.get("accepted_risks", []),
        feature_restrictions=payload.get("feature_restrictions", []),
        rollback_target=rollback_target,
        recertification_triggers=payload.get("recertification_triggers", []),
        signatories=payload.get("signatories", []),
    )
    return {"certificate": dumped(certificate)}


@handler("certificate-revocation-manager")
def certificate_revocation_manager(contract, payload: Payload, context: Payload) -> Payload:
    from ..production_gate import revoke_certificate

    (certificate_id,) = require(payload, "certificate_id")
    return {
        "revocation": dumped(
            revoke_certificate(
                certificate_id,
                payload.get("reason_codes", []),
                payload.get("actions", []),
            )
        )
    }


@handler("continuous-recertification-scheduler")
def recertification_scheduler(contract, payload: Payload, context: Payload) -> Payload:
    from ..production_gate import required_domains_for_trigger

    (trigger_type,) = require(payload, "trigger_type")
    domains = required_domains_for_trigger(str(trigger_type))
    return {
        "trigger_type": trigger_type,
        "required_domains": domains,
        "recertification_enabled": True,
    }


@handler("production-gate-report-and-red-team")
def production_gate_report(contract, payload: Payload, context: Payload) -> Payload:
    from ..production_gate import ProductionReleaseGate

    candidate = _candidate(payload)
    result = ProductionReleaseGate().evaluate(
        candidate,
        _domain_results(payload),
        _findings(payload),
        bool(payload.get("release_board_signed", False)),
        bool(payload.get("rollback_ready", False)),
        bool(payload.get("recertification_enabled", False)),
    )
    result = dumped(result)
    result.setdefault("rollback_target", payload.get("rollback_target", ""))
    result["rollback_ready"] = bool(payload.get("rollback_ready", False))
    return result


@handler("release-evidence-archive-and-audit")
def evidence_archive(contract, payload: Payload, context: Payload) -> Payload:
    from ..skill_runtime import digest

    evidence = _evidence(payload)
    return {
        "archived_evidence": dumped(evidence),
        "archive_hash": digest(dumped(evidence)),
        "immutable": True,
        "evidence_count": len(evidence),
    }
