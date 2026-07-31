"""Product adapters for Spiritual Planet discernment Batches 07-10."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from .formation_twin import (
    FormationEvent,
    IdentityMigration,
    RelapseState,
    RelapseStateMachine,
    RelationshipRepair,
    build_chain,
    evaluate_identity_migration,
    review_window,
    verify_repair,
)
from .production_gate import (
    CertificationControl,
    DomainResult,
    EvidenceItem,
    Finding,
    ProductionReleaseGate,
    ReleaseCandidate,
    ReleaseStatus,
    Severity,
    issue_certificate,
    required_domains_for_trigger,
)
from .registry import DiscernmentRegistry, get_registry
from .theology_knowledge import (
    CitationRecord,
    DoctrineGovernor,
    DoctrineTier,
    RagQuery,
    RightsPolicy,
    SourceDocument,
    TheologyKnowledgeOrchestrator,
    build_evidence_graph,
    detect_misuse,
    verify_citation,
)


def canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class FormationTwinService:
    """Builds multidimensional, evidence-limited longitudinal artifacts."""

    def ingest(self, *, event_id: str, email: str, payload: dict[str, Any]) -> dict[str, Any]:
        event = FormationEvent(
            event_id=event_id,
            user_id=email,
            consent_scope={"allow_longitudinal_tracking": payload.pop("consent_to_tracking")},
            **payload,
        )
        if not event.consent_scope["allow_longitudinal_tracking"]:
            return {"review_status": "blocked", "reason": "tracking_consent_required"}
        from .formation_twin import FormationSafetyGuardian

        safety = FormationSafetyGuardian().review(" ".join([
            event.context, event.trigger, event.automatic_interpretation, event.outcome,
        ]))
        if safety.status != "ready":
            return {"review_status": safety.status, "reasons": safety.reasons, "actions": safety.actions}
        return {
            "review_status": "ready",
            "event": event.model_dump(mode="json"),
            "chain": build_chain(event).model_dump(mode="json"),
            "quality_gates": {
                "consent_valid": True,
                "fact_inference_separated": event.source_type != "system_inference" or event.evidence_quality.value == "E1",
                "no_single_maturity_score": True,
                "relapse_not_identity_cancellation": True,
            },
        }

    def snapshot(self, *, email: str, events: list[dict[str, Any]]) -> dict[str, Any]:
        parsed = [FormationEvent.model_validate(event) for event in events]
        trigger_counts = Counter(event.trigger for event in parsed if event.trigger)
        contexts = sorted({event.context for event in parsed if event.context})
        qualities = Counter(event.evidence_quality.value for event in parsed)
        unique = lambda values: list(dict.fromkeys(value for group in values for value in group if value))[:20]
        dimensions = {
            "identity_gospel": {
                "gospel_truths_recalled": unique(event.gospel_truth_recalled for event in parsed),
                "evidence_events": sum(bool(event.gospel_truth_recalled) for event in parsed),
            },
            "attention_truth": {
                "interpretation_habits": list(dict.fromkeys(event.automatic_interpretation for event in parsed if event.automatic_interpretation))[:20],
                "evidence_events": sum(bool(event.automatic_interpretation) for event in parsed),
            },
            "desire_worship": {
                "desires_and_fears": unique(event.desire_or_fear for event in parsed),
                "active_beliefs": unique(event.active_belief for event in parsed),
            },
            "emotion_embodiment": {
                "emotions": unique(event.emotion for event in parsed),
                "body_signals": unique(event.body_signal for event in parsed),
            },
            "action_habit": {
                "chosen_actions": unique(event.chosen_action for event in parsed),
                "avoided_actions": unique(event.avoided_action for event in parsed),
            },
            "relationship_repair": {
                "relationship_effects": unique(event.relationship_effect for event in parsed),
                "repair_actions": unique(event.repair_action for event in parsed),
            },
            "vocation_stewardship": {"contexts": [item for item in contexts if any(key in item for key in ("工作", "学习", "服侍"))]},
            "church_hope_endurance": {"contexts": [item for item in contexts if any(key in item for key in ("教会", "小组", "团契"))]},
        }
        limitations = []
        if len(parsed) < 3:
            limitations.append("Sparse event evidence; no stable formation conclusion is allowed.")
        if len(contexts) < 2:
            limitations.append("Cross-context transfer has not been established.")
        if not parsed:
            limitations.append("No longitudinal events are available.")
        return {
            "snapshot_id": f"snapshot-{canonical_hash([event.event_id for event in parsed])[:16]}",
            "user_id": email,
            "event_count": len(parsed),
            "common_triggers": [{"trigger": key, "count": count} for key, count in trigger_counts.most_common(10)],
            "contexts": contexts,
            "dimensions": dimensions,
            "evidence_quality_distribution": dict(qualities),
            "uncertainty": "high" if len(parsed) < 3 else "medium" if len(contexts) < 2 else "bounded",
            "limitations": limitations,
            "prohibited_interpretations": ["overall_maturity_score", "salvation_status", "deterministic_personality_prediction"],
            "quality_gates": {"no_single_maturity_score": True, "relationship_fruit_included": True, "pressure_transfer_required": True},
        }

    def window_review(self, *, email: str, events: list[dict[str, Any]], window_days: int) -> dict[str, Any]:
        result = review_window(email, [FormationEvent.model_validate(event) for event in events], window_days)
        result["growth_and_relapse_can_coexist"] = True
        result["no_salvation_inference"] = True
        return result

    @staticmethod
    def repair(payload: dict[str, Any]) -> dict[str, Any]:
        result = verify_repair(RelationshipRepair.model_validate(payload))
        result["trust_restoration_not_guaranteed"] = True
        result["safety_over_contact"] = True
        return result

    @staticmethod
    def identity(payload: dict[str, Any]) -> dict[str, Any]:
        return evaluate_identity_migration(IdentityMigration.model_validate(payload))

    @staticmethod
    def relapse(current: str, target: str) -> dict[str, Any]:
        state = RelapseStateMachine().transition(RelapseState(current), RelapseState(target))
        return {"state": state.value, "gospel_identity_cancelled": False}


class TheologyEvidenceService:
    """Creates rights-filtered, auditable evidence graphs without inventing sources."""

    def __init__(self) -> None:
        self.orchestrator = TheologyKnowledgeOrchestrator()
        self.rights = RightsPolicy()
        self.doctrine = DoctrineGovernor()

    def query(self, *, query_id: str, payload: dict[str, Any], sources: list[dict[str, Any]]) -> dict[str, Any]:
        query = RagQuery(
            query_id=query_id,
            question=payload["question"],
            intent=payload["intent"],
            allowed_rights=payload["allowed_rights"],
            required_source_types=payload["required_source_types"],
            scripture_refs=payload.get("scripture_refs", []),
            tradition_scope=payload.get("tradition_scope", []),
            depth=payload.get("depth", "standard"),
            human_review_level=payload.get("human_review_level", "R0"),
        )
        parsed_sources = [SourceDocument.model_validate(source) for source in sources]
        filtered = self.orchestrator.filter_sources(query, parsed_sources)
        allowed_by_id = {source["source_id"]: SourceDocument.model_validate(source) for source in filtered["allowed"]}
        citation_results = []
        passages = []
        claims = []
        for index, raw in enumerate(payload.get("citations", []), start=1):
            source = allowed_by_id.get(raw["source_id"])
            if source is None:
                citation_results.append({"citation_id": raw.get("citation_id", f"citation-{index}"), "valid": False, "issues": ["source_not_allowed"]})
                continue
            citation = CitationRecord.model_validate({**raw, "rights_status": source.rights_status.value})
            check = verify_citation(citation, source)
            if not self.rights.can_quote(source.rights_status):
                check = {**check, "valid": False, "issues": [*check["issues"], "quotation_not_allowed"]}
            citation_results.append({"citation_id": citation.citation_id, **check})
            if not check["valid"]:
                continue
            passage_id = f"passage-{index}"
            claim_id = f"claim-{index}"
            passages.append({
                "passage_id": passage_id, "source_id": source.source_id, "locator": citation.locator,
                "quote_text": citation.quote_text, "verification_status": citation.verification_status,
            })
            claims.append({
                "claim_id": claim_id, "claim_text": "Verified cited passage available for contextual review.",
                "supporting_passage_ids": [passage_id], "contradicting_passage_ids": [],
            })

        context = payload.get("scripture_context", {})
        context_gates = {
            "reference_resolved": bool(payload.get("scripture_refs")) or payload["intent"] != "scripture_exegesis",
            "paragraph_context_present": bool(context.get("paragraph")) or payload["intent"] != "scripture_exegesis",
            "book_context_present": bool(context.get("book")) or payload["intent"] != "scripture_exegesis",
            "genre_present": bool(context.get("genre")) or payload["intent"] != "scripture_exegesis",
            "speaker_and_audience_present": bool(context.get("speaker") and context.get("audience")) or payload["intent"] != "scripture_exegesis",
        }
        tier = DoctrineTier(payload.get("doctrine_tier", "D3"))
        doctrine = self.doctrine.evaluate(
            tier=tier,
            tradition_scope=payload.get("tradition_scope", []),
            consensus_level=payload.get("consensus_level", "open_question"),
            used_as_salvation_test=payload.get("used_as_salvation_test", False),
        )
        misuse = detect_misuse(payload["question"] + " " + payload.get("proposed_application", ""))
        sufficient = bool(claims) and all(context_gates.values()) and doctrine["decision"] == "pass"
        generated = [{
            "statement_id": "statement-1",
            "text": f"{len(claims)} verified citation(s) are available; interpretation remains bounded by the supplied context.",
            "claim_ids": [claim["claim_id"] for claim in claims],
        }] if sufficient else []
        graph = build_evidence_graph(query_id, filtered["allowed"], passages, claims, generated).model_dump(mode="json")
        graph["retrieval_metadata"] = {"mode": "submitted-source-audit", "counter_evidence_requested": True}
        graph["model_metadata"] = {"generator": "deterministic", "prompt_version": "none", "batch": "0.9.0"}
        graph["limitations"] = [
            "No source or page number is invented; only submitted, rights-allowed citations are represented.",
            "Original-language notes remain unverified unless backed by a licensed corpus and qualified review.",
        ]
        return {
            "query_id": query_id,
            "review_status": "human_review_required" if misuse["human_review_required"] or tier in {DoctrineTier.D1, DoctrineTier.D2} else "ready" if sufficient else "insufficient_evidence",
            "answer_status": "evidence_ready" if sufficient else "insufficient_evidence",
            "source_filter": filtered,
            "citation_checks": citation_results,
            "scripture_context_gates": context_gates,
            "doctrine_governance": doctrine,
            "misuse_detection": misuse,
            "evidence_graph": graph,
            "rights_statement": "Unknown or prohibited rights never permit full-text embedding or generation.",
        }


class CertificationService:
    """Evaluates all 58 controls and fails closed when evidence is incomplete."""

    REQUIRED_BOARD_ROLES = {"engineering", "security", "privacy_legal", "theology", "safeguarding"}

    def __init__(self, registry: DiscernmentRegistry | None = None) -> None:
        self.registry = registry or get_registry()
        self.gate = ProductionReleaseGate()

    def controls(self) -> list[CertificationControl]:
        return [
            CertificationControl.model_validate(control)
            for pack in self.registry.certification_packs.values()
            for control in pack["controls"]
        ]

    def evaluate(self, *, release_id: str, body: dict[str, Any]) -> dict[str, Any]:
        candidate = ReleaseCandidate(
            release_id=release_id,
            build_hash=body["build_hash"],
            batch_manifests=list(self.registry.manifests.values()),
            model_versions=body.get("model_versions", []),
            prompt_versions=body.get("prompt_versions", []),
            policy_versions=body.get("policy_versions", []),
            knowledge_versions=body.get("knowledge_versions", []),
            target_scope=body["target_scope"],
            jurisdictions=body.get("jurisdictions", []),
            enabled_features=body.get("enabled_features", []),
            disabled_features=body.get("disabled_features", []),
        )
        controls = self.controls()
        evidence = [EvidenceItem.model_validate(item) for item in body.get("evidence", [])]
        control_results = self.gate.evaluate_controls(controls, evidence)
        findings = [Finding.model_validate(item) for item in body.get("findings", [])]
        domain_results: list[DomainResult] = []
        for pack in sorted(self.registry.certification_packs.values(), key=lambda item: item["id"]):
            results = [result for result in control_results if any(control.control_id == result["control_id"] and control.domain_id == pack["id"] for control in controls)]
            missing_controls = [result["control_id"] for result in results if not result["valid"]]
            domain_results.append(DomainResult(
                result_id=f"result-{release_id}-{pack['id']}", domain_id=pack["id"], control_results=results,
                critical_blockers=missing_controls, score=round(100 * sum(result["valid"] for result in results) / max(1, len(results)), 2),
                decision="pass" if not missing_controls else "fail",
                limitations=[] if not missing_controls else ["Required evidence is incomplete or expired."],
            ))
        for control, result in zip(controls, control_results):
            if not result["valid"]:
                findings.append(Finding(
                    finding_id=f"missing-{control.control_id}", control_id=control.control_id,
                    severity=control.severity, title="missing_evidence",
                    description="Required evidence is incomplete, expired, or unlocatable.", release_blocking=control.severity in {Severity.C2, Severity.C3, Severity.C4},
                ))
        board_roles = {item.get("role") for item in body.get("signatories", []) if item.get("signed")}
        release_board_signed = self.REQUIRED_BOARD_ROLES <= board_roles
        result = self.gate.evaluate(
            candidate, domain_results, findings,
            release_board_signed=release_board_signed,
            rollback_ready=bool(body.get("rollback_ready")),
            recertification_enabled=bool(body.get("recertification_enabled")),
        )
        response = {
            **result,
            "candidate": candidate.model_dump(mode="json"),
            "domain_results": [item.model_dump(mode="json") for item in domain_results],
            "findings": [item.model_dump(mode="json") for item in findings],
            "release_board_signed": release_board_signed,
            "certification_counts": {"domains": len(domain_results), "controls": len(controls), "valid_controls": sum(item["valid"] for item in control_results)},
            "production_claim_boundary": "Local evidence evaluation is not a deployment, legal opinion, or external production certification.",
        }
        if result["status"] in {ReleaseStatus.APPROVED_FOR_PILOT.value, ReleaseStatus.APPROVED_FOR_PRODUCTION.value}:
            certificate = issue_certificate(
                certificate_id=f"cert-{release_id}", release_id=release_id, status=ReleaseStatus(result["status"]),
                expires_at=body["expires_at"], scope={"target": body["target_scope"], "jurisdictions": body.get("jurisdictions", [])},
                domain_results=response["domain_results"], open_findings=[item.finding_id for item in findings if item.status == "open"],
                accepted_risks=body.get("accepted_risks", []), feature_restrictions=body.get("feature_restrictions", []),
                rollback_target=body.get("rollback_target", ""), recertification_triggers=body.get("recertification_triggers", []),
                signatories=body.get("signatories", []),
            )
            response["certificate"] = certificate.model_dump(mode="json")
        return response

    @staticmethod
    def recertification(trigger_type: str) -> dict[str, Any]:
        return {"trigger_type": trigger_type, "required_domains": required_domains_for_trigger(trigger_type), "status": "RECERTIFICATION_REQUIRED"}
