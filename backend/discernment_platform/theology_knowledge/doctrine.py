from __future__ import annotations

from .models import DoctrineTier


class DoctrineGovernor:
    def evaluate(
        self,
        tier: DoctrineTier,
        tradition_scope: list[str],
        consensus_level: str,
        used_as_salvation_test: bool,
    ) -> dict:
        if tier == DoctrineTier.D1:
            return {"decision": "pass", "reason": "core_doctrine"}

        if not tradition_scope:
            return {"decision": "rewrite", "reason": "tradition_scope_missing"}

        if tier == DoctrineTier.D3 and used_as_salvation_test:
            return {"decision": "blocked", "reason": "secondary_issue_as_salvation_test"}

        if consensus_level == "ecumenical_core" and tier != DoctrineTier.D1:
            return {"decision": "rewrite", "reason": "tier_consensus_mismatch"}

        return {"decision": "pass", "reason": "scope_labeled"}
