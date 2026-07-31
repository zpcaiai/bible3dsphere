from __future__ import annotations

from typing import Any

from .registry import DiscernmentRegistry, get_registry
from .safety import precheck


BRIEF_SEGMENTS = {
    "creation_order", "sin_and_idolatry", "christ_and_atonement",
    "justification_by_faith", "union_with_christ", "sanctification_by_spirit",
    "eschatological_hope",
}


class GospelPathEngine:
    def __init__(self, registry: DiscernmentRegistry | None = None) -> None:
        self.registry = registry or get_registry()

    def build(
        self,
        *,
        case_id: str,
        presenting_issue: str,
        faith_context: str,
        consent_scope: dict[str, Any],
        pride_hypotheses: list[dict[str, Any]],
        desire_map: list[dict[str, Any]],
        sensitivity: str = "normal",
        preferred_depth: str = "standard",
        church_context: str = "",
    ) -> dict[str, Any]:
        if not consent_scope.get("allow_gospel_bridge", False):
            return {
                "review_status": "blocked",
                "reason": "gospel_consent_required",
                "invitation": "你愿意看看基督如何回应这个困境吗？",
                "segments": [],
            }

        safety = precheck(presenting_issue, subject_type="self_reflection", sensitivity=sensitivity)
        if safety.status in {"blocked", "safety_hold"}:
            return {
                "review_status": safety.status,
                "reasons": safety.reasons,
                "safety_actions": safety.actions,
                "segments": [],
            }

        packs = self.registry.ordered_doctrine_packs()
        if preferred_depth == "brief":
            packs = [pack for pack in packs if pack["id"] in BRIEF_SEGMENTS]

        pattern_ids = [item.get("pattern_id", "") for item in pride_hypotheses]
        entry_point = self._entry_point(pattern_ids)
        issue = presenting_issue[:240]
        segments = []
        for index, pack in enumerate(packs):
            claims = list(pack.get("core_claims", []))
            applications = list(pack.get("pastoral_applications", []))
            explanation_claims = claims if preferred_depth == "deep" else claims[:2]
            explanation = " ".join(explanation_claims)
            if index == 0:
                explanation = f"针对“{issue}”：{explanation}"
            questions = pack.get("socratic_entries", [])
            segments.append({
                "segment_id": f"{case_id}-{index + 1}",
                "doctrine_pack_id": pack["id"],
                "pack_version": pack["version"],
                "name": pack["name_zh"],
                "tier": pack["tier"],
                "purpose": pack.get("path_role", "在完整福音路径中说明这一教义段落。"),
                "personalized_explanation": explanation,
                "socratic_question": questions[0].get("question") if questions else None,
                "scripture_refs": list(pack.get("scripture_refs", [])),
                "misconception_guards": list(pack.get("common_distortions", [])),
                "pastoral_applications": applications,
                "transition": packs[index + 1]["id"] if index + 1 < len(packs) else "response",
                "requires_consent": True,
                "evidence_or_source_status": "versioned_pack",
            })

        ids = {segment["doctrine_pack_id"] for segment in segments}
        standard_complete = preferred_depth == "brief" or len(ids) == 10
        balance = {
            "law_functions_present": "uses_of_law" in ids,
            "christ_person_and_work_present": "christ_and_atonement" in ids,
            "cross_and_resurrection_present": "christ_and_atonement" in ids,
            "justification_by_grace_through_faith": "justification_by_faith" in ids,
            "justification_sanctification_separated": {"justification_by_faith", "sanctification_by_spirit"}.issubset(ids),
            "church_present": "church_community" in ids or preferred_depth == "brief",
            "resurrection_and_new_creation_present": "eschatological_hope" in ids,
            "moralism_risk": "low",
            "cheap_grace_risk": "low",
            "decision": "pass" if standard_complete else "rewrite",
        }
        practices = []
        for segment in segments:
            for application in segment["pastoral_applications"][:1]:
                practices.append({
                    "source_pack": segment["doctrine_pack_id"],
                    "action": application,
                    "acceptance_basis": "这是蒙恩后的生命果子，不是赚取接纳或称义的条件。",
                })
        return {
            "plan_id": f"gospel-{case_id}",
            "case_id": case_id,
            "faith_context": faith_context,
            "preferred_depth": preferred_depth,
            "entry_point": entry_point,
            "segments": segments,
            "law_gospel_balance": balance,
            "denominational_notes": [note for pack in packs for note in pack.get("denominational_notes", [])],
            "church_context": church_context,
            "practice_plan": practices[:5],
            "desires_addressed": [item.get("desire", "") for item in desire_map[:3]],
            "safety_actions": safety.actions,
            "review_status": "ready" if balance["decision"] == "pass" else "human_review_required",
            "trace": [
                {"pack_id": segment["doctrine_pack_id"], "version": segment["pack_version"], "tier": segment["tier"]}
                for segment in segments
            ],
        }

    @staticmethod
    def _entry_point(pattern_ids: list[str]) -> str:
        if "competence_justification" in pattern_ids or "moral_self_righteousness" in pattern_ids:
            return "justification_by_faith"
        if "control_sovereignty" in pattern_ids:
            return "creation_order"
        if "victimhood_innocence" in pattern_ids:
            return "christ_and_atonement"
        if "spiritual_pride" in pattern_ids:
            return "union_with_christ"
        return "creation_order"
