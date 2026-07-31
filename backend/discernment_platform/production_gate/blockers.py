from __future__ import annotations

from .models import Finding, Severity


class CriticalBlockerEngine:
    NON_COMPENSABLE_CODES = {
        "salvation_scoring",
        "ai_discipline_verdict",
        "minor_abuse_internal_only",
        "crisis_not_escalated",
        "unauthorized_L2_L3",
        "tenant_data_leak",
        "deletion_unavailable",
        "coercive_gospel",
        "fabricated_citations",
        "rollback_unavailable",
        "secrets_or_pii_exposure",
    }

    def evaluate(self, findings: list[Finding]) -> dict:
        blockers = []
        for finding in findings:
            if finding.status in {"resolved", "mitigated"}:
                continue
            if finding.severity in {Severity.C3, Severity.C4}:
                blockers.append(finding.finding_id)
            if finding.title in self.NON_COMPENSABLE_CODES:
                blockers.append(finding.finding_id)

        return {
            "blocked": bool(blockers),
            "blocker_ids": sorted(set(blockers)),
        }
