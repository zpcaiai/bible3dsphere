"""Batch 01 orchestrator: wires the ten skills into the documented data flow."""

from __future__ import annotations

from . import claims as claims_skill
from . import desire as desire_skill
from . import gospel as gospel_skill
from . import intake as intake_skill
from . import pride as pride_skill
from . import report as report_skill
from . import safety as safety_skill
from . import socratic as socratic_skill
from . import trace as trace_skill
from . import worldview as worldview_skill
from .models import (
    CaseState,
    DiscernmentCase,
    FailureCode,
    RiskLevel,
    SkillFailure,
)
from .state import StateMachine


class DiscernmentOrchestrator:
    """Deterministic pure-function pipeline (LLM adapters plug in later)."""

    def __init__(self) -> None:
        self.machine = StateMachine()
        self.records: list = []

    def _trace(self, case_id, skill_id, version, payload_in, payload_out, **kw):
        self.records.append(
            trace_skill.record(
                case_id=case_id,
                skill_id=skill_id,
                skill_version=version,
                payload_in=payload_in,
                payload_out=payload_out,
                **kw,
            )
        )

    def run(self, case: DiscernmentCase, user_reaction: str = "") -> dict:
        machine = self.machine

        pre = safety_skill.precheck(case)
        self._trace(
            case.case_id,
            safety_skill.SKILL_ID,
            safety_skill.SKILL_VERSION,
            case.model_dump(mode="json"),
            pre.model_dump(mode="json"),
            safety_decisions=[pre.model_dump(mode="json")],
        )
        machine.to(CaseState.SAFETY_CHECKED)

        if pre.halt_normal_flow:
            machine.fail(FailureCode.HIGH_RISK_REVIEW)
            return self._safety_exit(case, pre)

        try:
            normalized = intake_skill.normalize(case)
        except SkillFailure as exc:
            machine.fail(exc.code)
            return self._failure_exit(case, pre, exc)
        self._trace(
            case.case_id,
            intake_skill.SKILL_ID,
            intake_skill.SKILL_VERSION,
            case.model_dump(mode="json"),
            normalized.model_dump(mode="json"),
        )
        machine.to(CaseState.NORMALIZED)

        found = claims_skill.extract(normalized)
        self._trace(
            case.case_id,
            claims_skill.SKILL_ID,
            claims_skill.SKILL_VERSION,
            normalized.model_dump(mode="json"),
            {"claims": [c.model_dump(mode="json") for c in found]},
            evidence_links=[c.claim_id for c in found if c.evidence_span],
        )
        machine.to(CaseState.CLAIMS_EXTRACTED)

        wv = worldview_skill.map_worldview(normalized, found)
        self._trace(
            case.case_id,
            worldview_skill.SKILL_ID,
            worldview_skill.SKILL_VERSION,
            {"claims": [c.claim_id for c in found]},
            wv.model_dump(mode="json"),
        )
        machine.to(CaseState.WORLDVIEW_MAPPED)

        if not case.consent_scope.allow_spiritual_analysis:
            machine.fail(FailureCode.USER_CONSENT_REQUIRED)
            return self._content_only_exit(case, pre, normalized, found, wv)

        hypotheses = pride_skill.detect(normalized, found, wv, user_reaction)
        self._trace(
            case.case_id,
            pride_skill.SKILL_ID,
            pride_skill.SKILL_VERSION,
            wv.model_dump(mode="json"),
            {"pride_hypotheses": [h.model_dump(mode="json") for h in hypotheses]},
        )
        machine.to(CaseState.PRIDE_HYPOTHESES_BUILT)

        desires = desire_skill.map_desires(normalized, wv, hypotheses, user_reaction)
        self._trace(
            case.case_id,
            desire_skill.SKILL_ID,
            desire_skill.SKILL_VERSION,
            {"hypotheses": [h.hypothesis_id for h in hypotheses]},
            {"desire_map": [d.model_dump(mode="json") for d in desires]},
        )
        machine.to(CaseState.DESIRES_MAPPED)

        questions = socratic_skill.plan(normalized, found, wv, hypotheses, desires)
        self._trace(
            case.case_id,
            socratic_skill.SKILL_ID,
            socratic_skill.SKILL_VERSION,
            {"desires": [d.chain_id for d in desires]},
            {"questions": [q.model_dump(mode="json") for q in questions]},
        )
        machine.to(CaseState.QUESTIONS_PLANNED)

        bridge = None
        try:
            bridge = gospel_skill.build(normalized, wv, hypotheses, desires)
            self._trace(
                case.case_id,
                gospel_skill.SKILL_ID,
                gospel_skill.SKILL_VERSION,
                {"worldview": wv.case_id},
                bridge.model_dump(mode="json"),
            )
            machine.to(CaseState.GOSPEL_BRIDGE_BUILT)
        except SkillFailure as exc:
            machine.failures.append(exc.code)

        try:
            composed = report_skill.compose(
                normalized, found, wv, hypotheses, desires, questions, bridge, pre
            )
        except SkillFailure as exc:
            machine.fail(exc.code)
            return self._failure_exit(case, pre, exc)

        self._trace(
            case.case_id,
            report_skill.SKILL_ID,
            report_skill.SKILL_VERSION,
            {"worldview": wv.case_id},
            composed.model_dump(mode="json"),
            safety_decisions=[pre.model_dump(mode="json")],
        )
        machine.to(CaseState.REPORT_COMPOSED)

        rendered = composed.model_dump_json()
        post = safety_skill.postcheck(case, rendered)
        self._trace(
            case.case_id,
            f"{safety_skill.SKILL_ID}:postcheck",
            safety_skill.SKILL_VERSION,
            {"rendered_len": len(rendered)},
            post.model_dump(mode="json"),
            safety_decisions=[post.model_dump(mode="json")],
        )

        needs_review = post.human_review_required or pre.human_review_required
        machine.to(CaseState.REVIEW_REQUIRED if needs_review else CaseState.READY)

        bundle = trace_skill.package(case.case_id, self.records)
        report_dict = composed.model_dump(mode="json")
        return {
            "state": machine.state.value,
            "report": report_dict,
            "trace_bundle": bundle.model_dump(mode="json"),
            "review_packet": trace_skill.review_packet(bundle, report_dict),
            "redacted_user_view": trace_skill.redacted_user_view(report_dict),
            "safety": {"precheck": pre.model_dump(mode="json"), "postcheck": post.model_dump(mode="json")},
            "production_ready": bundle.production_ready,
        }

    # --- exits ---------------------------------------------------------

    def _safety_exit(self, case: DiscernmentCase, pre) -> dict:
        bundle = trace_skill.package(case.case_id, self.records)
        return {
            "state": self.machine.state.value,
            "report": None,
            "failure": FailureCode.HIGH_RISK_REVIEW.value,
            "safety": {"precheck": pre.model_dump(mode="json")},
            "support_guidance": pre.support_guidance,
            "trace_bundle": bundle.model_dump(mode="json"),
            "production_ready": False,
        }

    def _failure_exit(self, case: DiscernmentCase, pre, exc: SkillFailure) -> dict:
        bundle = trace_skill.package(case.case_id, self.records)
        return {
            "state": self.machine.state.value,
            "report": None,
            "failure": exc.code.value,
            "message": exc.message,
            "safety": {"precheck": pre.model_dump(mode="json")},
            "support_guidance": pre.support_guidance,
            "trace_bundle": bundle.model_dump(mode="json"),
            "production_ready": False,
        }

    def _content_only_exit(self, case, pre, normalized, found, wv) -> dict:
        bundle = trace_skill.package(case.case_id, self.records)
        return {
            "state": self.machine.state.value,
            "report": None,
            "failure": FailureCode.USER_CONSENT_REQUIRED.value,
            "content_analysis": {
                "normalized_case": normalized.model_dump(mode="json"),
                "claims": [c.model_dump(mode="json") for c in found],
                "worldview_map": wv.model_dump(mode="json"),
            },
            "safety": {"precheck": pre.model_dump(mode="json")},
            "trace_bundle": bundle.model_dump(mode="json"),
            "production_ready": False,
        }
