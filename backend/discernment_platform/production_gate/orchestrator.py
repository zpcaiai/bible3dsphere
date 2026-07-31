from __future__ import annotations

from datetime import datetime, timezone

from .blockers import CriticalBlockerEngine
from .evidence import validate_evidence
from .gate import evaluate_release
from .models import (
    CertificationControl,
    DomainResult,
    EvidenceItem,
    Finding,
    ReleaseCandidate,
)


class ProductionReleaseGate:
    def __init__(self) -> None:
        self.blockers = CriticalBlockerEngine()

    def evaluate_controls(
        self,
        controls: list[CertificationControl],
        evidence: list[EvidenceItem],
    ) -> list[dict]:
        now = datetime.now(timezone.utc)
        return [validate_evidence(control, evidence, now) for control in controls]

    def evaluate(
        self,
        candidate: ReleaseCandidate,
        domain_results: list[DomainResult],
        findings: list[Finding],
        release_board_signed: bool,
        rollback_ready: bool,
        recertification_enabled: bool,
    ) -> dict:
        blocker_result = self.blockers.evaluate(findings)
        if blocker_result["blocked"]:
            return {
                "status": "BLOCKED",
                "critical_blockers": blocker_result["blocker_ids"],
            }

        gate_result = evaluate_release(
            domain_results=domain_results,
            findings=findings,
            target_scope=candidate.target_scope,
            release_board_signed=release_board_signed,
            rollback_ready=rollback_ready,
            recertification_enabled=recertification_enabled,
        )
        return {
            "status": gate_result["status"].value,
            "reasons": gate_result["reasons"],
            "release_id": candidate.release_id,
            "build_hash": candidate.build_hash,
        }
