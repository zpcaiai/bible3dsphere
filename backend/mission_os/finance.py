"""Skill 61/62/63/64: budget & cash flow, support raising, fund governance, anti-fraud.

Encoded invariants:
  * a pledge is never a receipt; a one-time gift is never annualized;
  * baseline + conservative + support-loss scenarios are required (evacuation too
    for high-risk fields); a reserve below its minimum blocks the plan;
  * financial readiness reports many signals, never a single "funded %";
  * a support pledge grants no governance; coercive fundraising is rejected;
  * an expense requester cannot approve their own expense; one person cannot hold
    request + approve + pay + reconcile; restricted funds cannot be repurposed;
  * an AI anomaly finding is never a proven-fraud verdict; the investigated party
    cannot investigate themselves.
"""
from __future__ import annotations

# ---- Skill 61: budget & cash flow -----------------------------------------
SCENARIO_TYPES = frozenset({
    "baseline", "conservative", "high_inflation", "currency_depreciation",
    "support_loss", "medical_event", "family_emergency", "education_cost_increase",
    "early_return", "evacuation", "delayed_start", "single_income_loss",
})
REQUIRED_SCENARIOS = frozenset({"baseline", "conservative", "support_loss"})
RESERVE_TYPES = frozenset({
    "operating", "medical", "emergency", "evacuation", "reentry",
    "home_assignment", "tax", "education", "equipment_replacement",
})
INCOME_KINDS = frozenset({"committed", "probable", "historical", "pledged_uncollected"})


def assert_scenarios_complete(scenario_types, *, high_risk_field: bool, has_children: bool) -> None:
    types = set(scenario_types)
    missing = REQUIRED_SCENARIOS - types
    if missing:
        raise ValueError(f"missing required budget scenarios: {sorted(missing)}")
    if high_risk_field and "evacuation" not in types:
        raise ValueError("high-risk field requires an evacuation scenario")
    if has_children and "education_cost_increase" not in types:
        raise ValueError("family plan requires an education cost scenario")


def annualize_income(*, amount: float, recurrence_type: str) -> float:
    """A one-time gift contributes 0 to annual recurring income."""
    if recurrence_type == "one_time":
        return 0.0
    factors = {"weekly": 52, "monthly": 12, "quarterly": 4, "annual": 1}
    if recurrence_type not in factors:
        raise ValueError(f"unknown recurrence type: {recurrence_type!r}")
    return amount * factors[recurrence_type]


def committed_income(pledges: list[dict]) -> float:
    """Only collected/committed pledges count; probable/uncollected do not."""
    total = 0.0
    for p in pledges:
        if p.get("kind") == "committed" and p.get("received"):
            total += float(p.get("amount", 0))
    return total


def pledge_is_not_receipt(*, pledge_status: str, received: bool) -> None:
    if pledge_status in {"pledged", "active"} and not received:
        # documents that a pledge is not income until received
        return
    if received and pledge_status not in {"active", "completed"}:
        raise ValueError("a receipt must correspond to an active/completed pledge")


def reserve_ok(*, reserve_type: str, current_amount: float, minimum_required: float) -> bool:
    if reserve_type not in RESERVE_TYPES:
        raise ValueError(f"unknown reserve type: {reserve_type!r}")
    return current_amount >= minimum_required


def financial_readiness(*, startup_pct: float, monthly_coverage_pct: float,
                        reserve_months: float, insurance_gap: bool,
                        blocking: list[str]) -> dict:
    """Return independent signals — never a single funded percentage."""
    return {
        "startup_pct": max(0.0, min(1.0, startup_pct)),
        "monthly_coverage_pct": max(0.0, min(1.0, monthly_coverage_pct)),
        "reserve_months": reserve_months,
        "insurance_gap": insurance_gap,
        "blocked": bool(blocking),
        "blocking": sorted(set(blocking)),
    }


# ---- Skill 62: support raising --------------------------------------------
FORBIDDEN_FUNDRAISING = frozenset({
    "guilt_pressure", "spiritual_ranking", "fear_urgency", "fake_deadline",
    "unverified_statistic", "suffering_exploitation", "reward_for_giving",
})
FORBIDDEN_CAMPAIGN_KEYS = frozenset({
    "minor_story", "sensitive_location", "local_partner_identity", "beneficiary_photo_unconsented",
})


def scan_campaign(*, tactics, content_keys) -> list[str]:
    findings = sorted(set(tactics) & FORBIDDEN_FUNDRAISING)
    findings += sorted(set(content_keys) & FORBIDDEN_CAMPAIGN_KEYS)
    return findings


def pledge_grants_no_governance(requested_permission: str) -> None:
    if requested_permission in {"governance", "decision", "personnel", "content_control",
                                "direct_command", "view_candidate_sensitive"}:
        raise ValueError("a support pledge grants no governance or control")


# ---- Skill 63: fund governance --------------------------------------------
AUTHORIZATION_TYPES = frozenset({
    "view_summary", "request_expense", "approve_expense", "release_funds",
    "reconcile", "manage_restrictions", "emergency_release", "audit",
})
_SOD_CONFLICTS = ("request_expense", "approve_expense", "release_funds", "reconcile")


def assert_expense_approval(*, requester_id: str, approver_id: str, amount: float,
                            approvals: int, dual_threshold: float) -> None:
    if requester_id == approver_id:
        raise ValueError("an expense requester cannot approve their own expense")
    if amount >= dual_threshold and approvals < 2:
        raise ValueError("expenses above threshold require dual approval")


def assert_separation_of_duties(authorizations) -> None:
    held = set(authorizations)
    if set(_SOD_CONFLICTS) <= held:
        raise ValueError("one person cannot hold request+approve+release+reconcile")


def assert_restricted_transfer(*, source_restriction: str, dest_restriction: str) -> None:
    if source_restriction == "restricted" and dest_restriction != "restricted":
        raise ValueError("restricted funds cannot be transferred to a less-restricted fund")


# ---- Skill 64: anti-fraud -------------------------------------------------
ANOMALY_RULES = frozenset({
    "duplicate_expense", "split_transaction_to_avoid_limit", "same_requester_and_approver",
    "unusual_cash_use", "restricted_fund_mismatch", "payment_to_related_party",
    "missing_receipt_pattern", "rapid_fund_transfer", "unreconciled_variance",
    "supporter_designated_personal_control", "expense_outside_budget",
    "emergency_fund_repeated_use", "expired_authorization", "multiple_payments_same_invoice",
})


def finding_is_not_verdict(finding_type: str) -> str:
    """An anomaly finding is a signal for human review, never a proven verdict."""
    if finding_type not in ANOMALY_RULES:
        raise ValueError(f"unknown anomaly rule: {finding_type!r}")
    return "requires_human_investigation"


def assert_investigator_independent(*, subject_id: str, investigator_id: str) -> None:
    if subject_id == investigator_id:
        raise ValueError("the investigated party cannot investigate themselves")
