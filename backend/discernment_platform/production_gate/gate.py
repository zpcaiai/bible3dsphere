from __future__ import annotations

from .models import DomainResult, Finding, ReleaseStatus, Severity


def evaluate_release(
    domain_results: list[DomainResult],
    findings: list[Finding],
    target_scope: str,
    release_board_signed: bool,
    rollback_ready: bool,
    recertification_enabled: bool,
) -> dict:
    open_findings = [
        f for f in findings
        if f.status not in {"resolved", "mitigated"}
    ]
    severities = {f.severity for f in open_findings}
    failed_domains = [r.domain_id for r in domain_results if r.decision == "fail"]

    if Severity.C4 in severities or Severity.C3 in severities or failed_domains:
        return {
            "status": ReleaseStatus.BLOCKED,
            "reasons": ["critical_or_severe_findings", *failed_domains],
        }

    if target_scope == "production":
        if Severity.C2 in severities:
            return {
                "status": ReleaseStatus.BLOCKED,
                "reasons": ["C2_findings_block_production"],
            }
        if not release_board_signed:
            return {
                "status": ReleaseStatus.BLOCKED,
                "reasons": ["release_board_signature_missing"],
            }
        if not rollback_ready:
            return {
                "status": ReleaseStatus.BLOCKED,
                "reasons": ["rollback_not_ready"],
            }
        if not recertification_enabled:
            return {
                "status": ReleaseStatus.BLOCKED,
                "reasons": ["recertification_not_enabled"],
            }
        return {
            "status": ReleaseStatus.APPROVED_FOR_PRODUCTION,
            "reasons": [],
        }

    if target_scope == "pilot":
        if Severity.C2 in severities:
            return {
                "status": ReleaseStatus.CONDITIONAL_APPROVAL,
                "reasons": ["open_C2_requires_pilot_conditions"],
            }
        return {
            "status": ReleaseStatus.APPROVED_FOR_PILOT,
            "reasons": [],
        }

    return {
        "status": ReleaseStatus.CONDITIONAL_APPROVAL,
        "reasons": ["non_production_scope"],
    }
