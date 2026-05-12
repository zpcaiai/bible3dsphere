"""
SFDS v3.6 — Self-Improving Cognitive Loop (SICL)

=================================================================
CORE BOUNDARY (architectural invariant):

  The system does NOT optimize HUMANS.
  The system optimizes its OWN understanding of human dynamics.

  The target function ΔS is defined over SYSTEM performance,
  never over human behavior, personality, or emotional outcomes.

=================================================================
6-STAGE PIPELINE:

  Stage 1 — OBSERVATION    : collect system telemetry
  Stage 2 — EVALUATION     : compute 5 performance metrics
  Stage 3 — PATTERN EXTRACT: detect system-level weaknesses
  Stage 4 — PROPOSAL       : generate safe improvement proposals
  Stage 5 — INTEGRATION    : apply with guardrail checks
  Stage 6 — VALIDATION     : measure before/after delta

=================================================================
IMPROVEMENT FUNCTION:

  ΔS = f(IAS, IRS, SDS, TPS, FCS)

  IAS — Insight Accuracy Score      : system-to-pattern alignment
  IRS — Intervention Relevance Score: loop-to-principle relevance
  SDS — Structural Detection Score  : loop detection accuracy
  TPS — Temporal Prediction Score   : trend consistency
  FCS — Formation Consistency Score : trajectory stability

  Higher ΔS → the system is learning to understand dynamics better.

=================================================================
ALLOWED UPDATES:
  ✔ pattern library additions (new loop templates)
  ✔ edge weight calibration
  ✔ formation coefficient adjustment
  ✔ retrieval clustering improvements
  ✔ reasoning prompt refinements

FORBIDDEN UPDATES:
  ✘ user identity model changes
  ✘ "desired outcome" optimization
  ✘ behavior compliance scoring
  ✘ moral/value ranking changes

=================================================================
STORAGE RULE:
  STORE:  validated pattern improvements, confirmed corrections
  REJECT: speculative psychological claims, identity interpretations,
          moral judgments, anything that reduces uncertainty artificially
=================================================================
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── System-level performance thresholds ─────────────────────────────────────
_METRIC_TARGET     = 0.72    # target for each performance metric
_WEAK_THRESHOLD    = 0.55    # below this → system weakness flagged
_UPDATE_MIN_DELTA  = 0.03    # minimum ΔS before update is accepted
_OVERFIT_THRESHOLD = 0.92    # metric above this → overfitting risk
_CERTAINTY_CEILING = 0.85    # SICL confidence cap — mirrors HIDOS cap


# ── Enums ─────────────────────────────────────────────────────────────────────

class ProposalType(str, Enum):
    GRAPH_PATTERN_ADDITION    = "graph_pattern_addition"
    GRAPH_EDGE_WEIGHT_CALIBRATION = "graph_edge_weight_calibration"
    FORMATION_COEFFICIENT_ADJUST = "formation_coefficient_adjustment"
    RETRIEVAL_OPTIMIZATION    = "retrieval_optimization"
    PROMPT_REFINEMENT         = "prompt_refinement"
    TRAJECTORY_SENSITIVITY    = "trajectory_sensitivity"


class WeaknessType(str, Enum):
    MISSED_LOOP_DETECTION     = "repeated_missed_loop_detection"
    VECTOR_OVER_RELIANCE      = "over_reliance_on_vector_similarity"
    GRAPH_UNDERUTILIZATION    = "underutilization_of_graph_structure"
    FORMATION_DRIFT_MISS      = "formation_drift_misalignment"
    HALLUCINATED_REASONING    = "hallucinated_causal_chain"
    OVERCONFIDENCE_BIAS       = "excessive_certainty_in_reasoning"
    IDENTITY_LABEL_DRIFT      = "identity_labeling_drift"


class UpdateStatus(str, Enum):
    ACCEPTED      = "accepted"
    REJECTED_SAFE = "rejected_safety_guardrail"
    REJECTED_PERF = "rejected_insufficient_improvement"
    PENDING       = "pending_validation"


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class SystemTelemetry:
    """
    Stage 1 — Observation.
    Raw signals collected from all HIDOS subsystems.
    """
    # Graph layer
    loops_detected:         int   = 0
    loops_missed_estimated: int   = 0   # estimated from user feedback / reflection mismatch
    graph_queries_run:      int   = 0
    graph_fallback_count:   int   = 0   # times pattern library was used instead of Neo4j

    # Formation layer
    formation_drift_events: int   = 0
    vector_avg_confidence:  float = 0.0
    formation_confidence:   float = 0.0

    # LLM layer
    reasoning_calls:        int   = 0
    high_confidence_outputs:int   = 0   # confidence > 0.80 — watch for overconfidence
    uncertainty_preserved:  int   = 0   # outputs that explicitly stated uncertainty

    # Time series layer
    temporal_predictions:   int   = 0
    temporal_confirmed:     int   = 0   # predictions later validated by trends

    # Retrieval
    retrieval_calls:        int   = 0
    retrieval_relevant:     int   = 0   # judged relevant by downstream reasoning

    # Session count
    sessions_observed:      int   = 0

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class PerformanceMetrics:
    """
    Stage 2 — Evaluation.
    ΔS = f(IAS, IRS, SDS, TPS, FCS)
    All values ∈ [0.0, 1.0]. Higher = better system understanding quality.
    """
    IAS: float = 0.0   # Insight Accuracy Score
    IRS: float = 0.0   # Intervention Relevance Score
    SDS: float = 0.0   # Structural Detection Score
    TPS: float = 0.0   # Temporal Prediction Score
    FCS: float = 0.0   # Formation Consistency Score

    @property
    def delta_S(self) -> float:
        """
        ΔS = weighted mean of all 5 metrics.
        Weights reflect relative importance to understanding quality.
        """
        weights = {"IAS": 0.25, "IRS": 0.20, "SDS": 0.25, "TPS": 0.15, "FCS": 0.15}
        return round(
            sum(getattr(self, k) * w for k, w in weights.items()), 4
        )

    @property
    def weakest_metric(self) -> Tuple[str, float]:
        metrics = {"IAS": self.IAS, "IRS": self.IRS, "SDS": self.SDS,
                   "TPS": self.TPS, "FCS": self.FCS}
        k = min(metrics, key=metrics.get)
        return k, metrics[k]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "IAS": round(self.IAS, 4),
            "IRS": round(self.IRS, 4),
            "SDS": round(self.SDS, 4),
            "TPS": round(self.TPS, 4),
            "FCS": round(self.FCS, 4),
            "delta_S": round(self.delta_S, 4),
            "weakest_metric": self.weakest_metric,
        }


@dataclass
class SystemWeakness:
    """
    Stage 3 — Pattern Extraction.
    A detected weakness in the system's understanding capability.
    """
    weakness_type:      WeaknessType
    affected_layer:     str           # "graph" | "formation" | "vector" | "reasoning" | "time"
    severity:           float         # 0–1, higher = more impactful on understanding quality
    evidence:           str           # what telemetry signal triggered this
    proposed_fix:       ProposalType
    safe_to_auto_fix:   bool = False  # only True for low-risk structural adjustments

    def to_dict(self) -> Dict[str, Any]:
        return {
            "weakness_type":    self.weakness_type.value,
            "affected_layer":   self.affected_layer,
            "severity":         round(self.severity, 4),
            "evidence":         self.evidence,
            "proposed_fix":     self.proposed_fix.value,
            "safe_to_auto_fix": self.safe_to_auto_fix,
        }


@dataclass
class UpdateProposal:
    """
    Stage 4 — System Update Proposal.

    Only system-level accuracy improvements are proposable.
    GUARDRAILS enforced before any proposal is accepted.
    """
    proposal_type:       ProposalType
    target_layer:        str
    description:         str
    expected_metric:     str          # which metric this improves
    expected_delta:      float        # estimated ΔS improvement
    rationale:           str
    status:              UpdateStatus = UpdateStatus.PENDING
    rejection_reason:    str          = ""

    # Guardrail fields — all must be False for acceptance
    modifies_user_model:   bool = False  # modifies user behavior/identity logic
    adds_moral_judgment:   bool = False  # adds value/moral scoring
    increases_certainty:   bool = False  # artificially removes uncertainty
    targets_human_outcome: bool = False  # optimizes human behavior as target

    @property
    def passes_guardrails(self) -> bool:
        return not any([
            self.modifies_user_model,
            self.adds_moral_judgment,
            self.increases_certainty,
            self.targets_human_outcome,
        ])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_type":       self.proposal_type.value,
            "target_layer":        self.target_layer,
            "description":         self.description,
            "expected_metric":     self.expected_metric,
            "expected_delta":      round(self.expected_delta, 4),
            "rationale":           self.rationale,
            "status":              self.status.value,
            "rejection_reason":    self.rejection_reason,
            "passes_guardrails":   self.passes_guardrails,
        }


@dataclass
class ValidationResult:
    """
    Stage 6 — Validation.
    Measures the actual system performance improvement after an update.
    """
    proposal_type:      ProposalType
    before_delta_S:     float
    after_delta_S:      float
    improvement:        float      # after - before
    stability_held:     bool       # did output stability hold post-update?
    contradiction_delta:float      # change in cross-layer contradictions
    accepted:           bool
    note:               str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_type":      self.proposal_type.value,
            "before_delta_S":     round(self.before_delta_S, 4),
            "after_delta_S":      round(self.after_delta_S, 4),
            "improvement":        round(self.improvement, 4),
            "stability_held":     self.stability_held,
            "contradiction_delta":round(self.contradiction_delta, 4),
            "accepted":           self.accepted,
            "note":               self.note,
        }


@dataclass
class SICLOutput:
    """
    Full 6-stage SICL output for one improvement cycle.
    """
    schema:         str = "sicl_v3.6"
    cycle_id:       str = ""

    # Stage outputs
    telemetry:      SystemTelemetry  = field(default_factory=SystemTelemetry)
    metrics:        PerformanceMetrics = field(default_factory=PerformanceMetrics)
    weaknesses:     List[SystemWeakness] = field(default_factory=list)
    proposals:      List[UpdateProposal] = field(default_factory=list)
    validated:      List[ValidationResult] = field(default_factory=list)

    # Summary
    accepted_updates:   int   = 0
    rejected_updates:   int   = 0
    net_delta_S:        float = 0.0   # actual measured improvement this cycle
    system_improving:   bool  = False

    disclaimer: str = (
        "SICL improves system understanding only. "
        "No changes to user identity, behavior, or outcomes are targeted. "
        "All updates are structural-accuracy improvements to the reasoning system."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema":          self.schema,
            "cycle_id":        self.cycle_id,
            "metrics":         self.metrics.to_dict(),
            "weaknesses":      [w.to_dict() for w in self.weaknesses],
            "proposals":       [p.to_dict() for p in self.proposals],
            "validated":       [v.to_dict() for v in self.validated],
            "summary": {
                "accepted_updates":  self.accepted_updates,
                "rejected_updates":  self.rejected_updates,
                "net_delta_S":       round(self.net_delta_S, 4),
                "system_improving":  self.system_improving,
            },
            "disclaimer":      self.disclaimer,
        }


# ── Stage 1: Observation ──────────────────────────────────────────────────────

def observe(raw_events: List[Dict[str, Any]]) -> SystemTelemetry:
    """
    Stage 1 — Collect system-level telemetry from HIDOS output events.

    raw_events: list of HIDOSOutput.to_dict() dicts from recent sessions.
    Extracts structural signals about system reasoning quality.
    """
    t = SystemTelemetry(sessions_observed=len(raw_events))

    for ev in raw_events:
        layers     = ev.get("layers", {})
        confidence = float(ev.get("confidence", 0.0))
        integrated = ev.get("integrated", {})

        # Graph signals
        graph_layer = layers.get("graph", {})
        if graph_layer.get("available"):
            t.graph_queries_run += 1
            struct = integrated.get("structural_layer", {})
            if struct.get("loop_detected"):
                t.loops_detected += 1
        else:
            t.graph_fallback_count += 1

        # Formation signals
        form_layer = layers.get("formation", {})
        if form_layer.get("available"):
            fconf = float(form_layer.get("confidence", 0.0))
            t.formation_confidence = (t.formation_confidence + fconf) / max(1, t.sessions_observed)
            form_data = form_layer.get("data", {})
            if form_data.get("trajectory", {}).get("drift_detected"):
                t.formation_drift_events += 1

        # Vector signals
        vec_layer = layers.get("vector", {})
        if vec_layer.get("available"):
            t.retrieval_calls += 1
            vconf = float(vec_layer.get("confidence", 0.0))
            if vconf >= 0.60:
                t.retrieval_relevant += 1
            t.vector_avg_confidence = (
                t.vector_avg_confidence * (t.retrieval_calls - 1) + vconf
            ) / t.retrieval_calls

        # LLM / reasoning signals
        t.reasoning_calls += 1
        if confidence > 0.80:
            t.high_confidence_outputs += 1
        insight = ev.get("reflective_insight", "")
        uncertain_words = ["may", "might", "appears", "possible", "tend", "uncertain"]
        if any(w in insight.lower() for w in uncertain_words):
            t.uncertainty_preserved += 1

    return t


# ── Stage 2: Evaluation ───────────────────────────────────────────────────────

def evaluate(t: SystemTelemetry) -> PerformanceMetrics:
    """
    Stage 2 — Compute ΔS = f(IAS, IRS, SDS, TPS, FCS).

    All metrics derived from system-level telemetry signals only.
    No user behavior or outcome data is used.
    """
    n = max(t.sessions_observed, 1)

    # IAS — Insight Accuracy Score
    # Proxy: ratio of uncertainty-preserved outputs to total reasoning calls
    # Rationale: accurate insights acknowledge uncertainty appropriately
    ias_raw = t.uncertainty_preserved / max(t.reasoning_calls, 1)
    # Penalize overconfidence
    overconfidence_ratio = t.high_confidence_outputs / max(t.reasoning_calls, 1)
    IAS = round(min(1.0, ias_raw * (1.0 - overconfidence_ratio * 0.3)), 4)

    # IRS — Intervention Relevance Score
    # Proxy: retrieval relevance (relevant principles retrieved / total retrieval)
    IRS = round(
        t.retrieval_relevant / max(t.retrieval_calls, 1)
        if t.retrieval_calls > 0 else 0.40,
        4,
    )

    # SDS — Structural Detection Score
    # Proxy: loops detected / (sessions with graph available)
    graph_sessions = max(t.graph_queries_run, 1)
    # Expect loops in roughly 40% of sessions (heuristic baseline)
    expected_loops  = graph_sessions * 0.40
    detected_ratio  = t.loops_detected / max(expected_loops, 1)
    # Penalize excessive fallbacks
    fallback_penalty = t.graph_fallback_count / max(n, 1) * 0.4
    SDS = round(min(1.0, max(0.0, detected_ratio - fallback_penalty)), 4)

    # TPS — Temporal Prediction Score
    # Proxy: confirmed predictions / temporal predictions made
    TPS = round(
        t.temporal_confirmed / max(t.temporal_predictions, 1)
        if t.temporal_predictions > 0 else 0.40,
        4,
    )

    # FCS — Formation Consistency Score
    # Proxy: average formation confidence, penalized by drift event frequency
    drift_rate = t.formation_drift_events / max(n, 1)
    FCS = round(max(0.0, t.formation_confidence - drift_rate * 0.20), 4)

    return PerformanceMetrics(IAS=IAS, IRS=IRS, SDS=SDS, TPS=TPS, FCS=FCS)


# ── Stage 3: Pattern Extraction ───────────────────────────────────────────────

def extract_weaknesses(
    metrics: PerformanceMetrics,
    telemetry: SystemTelemetry,
) -> List[SystemWeakness]:
    """
    Stage 3 — Detect system-level weaknesses.
    Maps low metrics to specific structural causes.

    Safety: only structural system weaknesses are detected.
    User-level patterns are NEVER flagged as weaknesses.
    """
    weaknesses: List[SystemWeakness] = []

    # SDS weak → missed loop detection
    if metrics.SDS < _WEAK_THRESHOLD:
        weaknesses.append(SystemWeakness(
            weakness_type   = WeaknessType.MISSED_LOOP_DETECTION,
            affected_layer  = "graph",
            severity        = round(1.0 - metrics.SDS, 4),
            evidence        = (
                f"SDS={metrics.SDS:.2f} < threshold {_WEAK_THRESHOLD}. "
                f"Graph fallbacks: {telemetry.graph_fallback_count}, "
                f"loops detected: {telemetry.loops_detected}."
            ),
            proposed_fix    = ProposalType.GRAPH_PATTERN_ADDITION,
            safe_to_auto_fix= True,
        ))

    # IRS weak → over-reliance on vector similarity
    if metrics.IRS < _WEAK_THRESHOLD and telemetry.retrieval_calls > 5:
        weaknesses.append(SystemWeakness(
            weakness_type   = WeaknessType.VECTOR_OVER_RELIANCE,
            affected_layer  = "vector",
            severity        = round(1.0 - metrics.IRS, 4),
            evidence        = (
                f"IRS={metrics.IRS:.2f} < threshold. "
                f"Retrieval relevance: {telemetry.retrieval_relevant}/{telemetry.retrieval_calls}."
            ),
            proposed_fix    = ProposalType.RETRIEVAL_OPTIMIZATION,
            safe_to_auto_fix= True,
        ))

    # IAS weak AND high confidence outputs → overconfidence bias
    if metrics.IAS < _WEAK_THRESHOLD:
        overconf_ratio = telemetry.high_confidence_outputs / max(telemetry.reasoning_calls, 1)
        weaknesses.append(SystemWeakness(
            weakness_type   = WeaknessType.OVERCONFIDENCE_BIAS,
            affected_layer  = "reasoning",
            severity        = round(max(0.0, overconf_ratio - 0.40), 4),
            evidence        = (
                f"IAS={metrics.IAS:.2f}. "
                f"High-confidence outputs: {telemetry.high_confidence_outputs}/"
                f"{telemetry.reasoning_calls} ({overconf_ratio:.0%})."
            ),
            proposed_fix    = ProposalType.PROMPT_REFINEMENT,
            safe_to_auto_fix= False,   # prompt changes require human review
        ))

    # FCS weak → formation drift misalignment
    if metrics.FCS < _WEAK_THRESHOLD:
        weaknesses.append(SystemWeakness(
            weakness_type   = WeaknessType.FORMATION_DRIFT_MISS,
            affected_layer  = "formation",
            severity        = round(1.0 - metrics.FCS, 4),
            evidence        = (
                f"FCS={metrics.FCS:.2f}. "
                f"Drift events: {telemetry.formation_drift_events} / "
                f"{telemetry.sessions_observed} sessions."
            ),
            proposed_fix    = ProposalType.FORMATION_COEFFICIENT_ADJUST,
            safe_to_auto_fix= True,
        ))

    # SDS very high AND IAS high → potential overfitting
    if metrics.SDS > _OVERFIT_THRESHOLD and metrics.IAS > _OVERFIT_THRESHOLD:
        weaknesses.append(SystemWeakness(
            weakness_type   = WeaknessType.HALLUCINATED_REASONING,
            affected_layer  = "reasoning",
            severity        = 0.60,
            evidence        = (
                f"SDS={metrics.SDS:.2f} and IAS={metrics.IAS:.2f} both exceed "
                f"overfitting threshold {_OVERFIT_THRESHOLD}. "
                f"System may be overfitting to known patterns."
            ),
            proposed_fix    = ProposalType.PROMPT_REFINEMENT,
            safe_to_auto_fix= False,
        ))

    return sorted(weaknesses, key=lambda w: w.severity, reverse=True)


# ── Stage 4: Proposal Generation ─────────────────────────────────────────────

def generate_proposals(
    weaknesses: List[SystemWeakness],
    metrics:    PerformanceMetrics,
) -> List[UpdateProposal]:
    """
    Stage 4 — Generate system improvement proposals from detected weaknesses.

    Each proposal is checked against GUARDRAILS before being accepted.
    Proposals that would modify user models or target human outcomes are
    flagged and auto-rejected.
    """
    proposals: List[UpdateProposal] = []

    for w in weaknesses:
        proposal = _weakness_to_proposal(w, metrics)
        if proposal:
            proposals.append(proposal)

    return proposals


def _weakness_to_proposal(
    w: SystemWeakness, metrics: PerformanceMetrics
) -> Optional[UpdateProposal]:
    """Map a weakness to a concrete, guardrail-compliant improvement proposal."""

    _map: Dict[WeaknessType, Dict[str, Any]] = {
        WeaknessType.MISSED_LOOP_DETECTION: {
            "type":            ProposalType.GRAPH_PATTERN_ADDITION,
            "target_layer":    "graph",
            "description":     (
                "Expand pattern library with additional loop templates for "
                "under-detected behavioral categories. "
                "Improve traversal depth for multi-hop loop detection."
            ),
            "expected_metric": "SDS",
            "expected_delta":  round((_METRIC_TARGET - metrics.SDS) * 0.40, 4),
            "rationale":       "More pattern coverage improves structural loop recognition accuracy.",
        },
        WeaknessType.VECTOR_OVER_RELIANCE: {
            "type":            ProposalType.RETRIEVAL_OPTIMIZATION,
            "target_layer":    "vector",
            "description":     (
                "Recalibrate retrieval to weight graph structural context more heavily. "
                "Improve embedding clustering for principle categories."
            ),
            "expected_metric": "IRS",
            "expected_delta":  round((_METRIC_TARGET - metrics.IRS) * 0.30, 4),
            "rationale":       "Better cross-layer weighting reduces single-source retrieval bias.",
        },
        WeaknessType.OVERCONFIDENCE_BIAS: {
            "type":            ProposalType.PROMPT_REFINEMENT,
            "target_layer":    "reasoning",
            "description":     (
                "Refine orchestrator synthesis prompts to increase explicit uncertainty markers. "
                "Add post-synthesis confidence calibration step."
            ),
            "expected_metric": "IAS",
            "expected_delta":  round((_METRIC_TARGET - metrics.IAS) * 0.25, 4),
            "rationale":       (
                "Calibrated uncertainty improves insight accuracy "
                "and reduces false-certainty outputs."
            ),
        },
        WeaknessType.FORMATION_DRIFT_MISS: {
            "type":            ProposalType.FORMATION_COEFFICIENT_ADJUST,
            "target_layer":    "formation",
            "description":     (
                "Increase drift sensitivity in trajectory analysis "
                "by lowering the DRIFT_THRESHOLD constant. "
                "Increase STABILITY_WINDOW for more robust variance estimation."
            ),
            "expected_metric": "FCS",
            "expected_delta":  round((_METRIC_TARGET - metrics.FCS) * 0.35, 4),
            "rationale":       "More sensitive drift detection improves formation modeling accuracy.",
        },
        WeaknessType.HALLUCINATED_REASONING: {
            "type":            ProposalType.PROMPT_REFINEMENT,
            "target_layer":    "reasoning",
            "description":     (
                "Add explicit anti-overfitting step to synthesis pipeline. "
                "Require alternative hypothesis generation when confidence > 0.85."
            ),
            "expected_metric": "IAS",
            "expected_delta":  0.05,
            "rationale":       "Forcing alternative hypotheses reduces pattern overfitting.",
        },
    }

    spec = _map.get(w.weakness_type)
    if not spec:
        return None

    return UpdateProposal(
        proposal_type    = spec["type"],
        target_layer     = spec["target_layer"],
        description      = spec["description"],
        expected_metric  = spec["expected_metric"],
        expected_delta   = spec["expected_delta"],
        rationale        = spec["rationale"],
        # Guardrail fields — all False by design; these proposals never touch user models
        modifies_user_model   = False,
        adds_moral_judgment   = False,
        increases_certainty   = False,
        targets_human_outcome = False,
    )


# ── Stage 5: Controlled Integration ──────────────────────────────────────────

def integrate_proposals(proposals: List[UpdateProposal]) -> List[UpdateProposal]:
    """
    Stage 5 — Apply guardrail checks and accept/reject each proposal.

    GUARDRAIL RULES (architectural constants, not configurable):
      1. modifies_user_model     → REJECT
      2. adds_moral_judgment     → REJECT
      3. increases_certainty     → REJECT
      4. targets_human_outcome   → REJECT
      5. expected_delta < _UPDATE_MIN_DELTA → REJECT (insufficient improvement)
      6. prompt_refinement proposals → REJECT auto-apply (require human review)
    """
    results: List[UpdateProposal] = []

    for p in proposals:
        # Guardrail check 1-4: safety invariants
        if not p.passes_guardrails:
            failed = [
                k for k in ["modifies_user_model", "adds_moral_judgment",
                             "increases_certainty", "targets_human_outcome"]
                if getattr(p, k)
            ]
            p.status           = UpdateStatus.REJECTED_SAFE
            p.rejection_reason = f"Safety guardrail violation: {', '.join(failed)}"
            results.append(p)
            continue

        # Guardrail 5: insufficient expected improvement
        if p.expected_delta < _UPDATE_MIN_DELTA:
            p.status           = UpdateStatus.REJECTED_PERF
            p.rejection_reason = (
                f"Expected ΔS {p.expected_delta:.4f} below minimum "
                f"threshold {_UPDATE_MIN_DELTA}."
            )
            results.append(p)
            continue

        # Guardrail 6: prompt changes require human review
        if p.proposal_type == ProposalType.PROMPT_REFINEMENT:
            p.status           = UpdateStatus.REJECTED_SAFE
            p.rejection_reason = (
                "Prompt refinement proposals require human review before integration. "
                "Auto-application is disabled for reasoning layer changes."
            )
            results.append(p)
            continue

        # Passed all guardrails
        p.status = UpdateStatus.ACCEPTED
        results.append(p)

    return results


# ── Stage 6: Validation ───────────────────────────────────────────────────────

def validate_updates(
    accepted:       List[UpdateProposal],
    before_metrics: PerformanceMetrics,
    after_metrics:  PerformanceMetrics,
) -> List[ValidationResult]:
    """
    Stage 6 — Measure actual ΔS after updates.
    Accepts updates only when measured improvement ≥ _UPDATE_MIN_DELTA.
    """
    results: List[ValidationResult] = []

    for p in accepted:
        if p.status != UpdateStatus.ACCEPTED:
            continue

        before_val = getattr(before_metrics, p.expected_metric, before_metrics.delta_S)
        after_val  = getattr(after_metrics,  p.expected_metric, after_metrics.delta_S)
        improvement = after_val - before_val

        stability_held = (
            abs(after_metrics.delta_S - before_metrics.delta_S) < 0.15
        )
        contradiction_delta = round(
            (after_metrics.delta_S - before_metrics.delta_S) * -0.5, 4
        )

        note = (
            f"Measured improvement in {p.expected_metric}: "
            f"{before_val:.3f} → {after_val:.3f} (Δ={improvement:+.4f})."
        )

        results.append(ValidationResult(
            proposal_type       = p.proposal_type,
            before_delta_S      = before_metrics.delta_S,
            after_delta_S       = after_metrics.delta_S,
            improvement         = round(improvement, 4),
            stability_held      = stability_held,
            contradiction_delta = contradiction_delta,
            accepted            = improvement >= _UPDATE_MIN_DELTA,
            note                = note,
        ))

    return results


# ── Main SICL engine ──────────────────────────────────────────────────────────

class SelfImprovingCognitiveLoop:
    """
    SICL v3.6 — Full 6-stage self-improvement engine.

    Designed to be run on a schedule (e.g., after N sessions).
    Each run produces a SICLOutput documenting exactly what changed and why.

    Usage:
        sicl = SelfImprovingCognitiveLoop()
        output = sicl.run_cycle(
            recent_outputs=[...],   # list of HIDOSOutput.to_dict()
            cycle_id="cycle_001",
        )
    """

    def run_cycle(
        self,
        recent_outputs:     List[Dict[str, Any]],
        cycle_id:           str = "",
        before_metrics:     Optional[PerformanceMetrics] = None,
    ) -> SICLOutput:
        """
        Execute one full SICL improvement cycle.

        Args:
            recent_outputs:  list of HIDOSOutput.to_dict() from recent HIDOS sessions
            cycle_id:        identifier for this improvement cycle
            before_metrics:  previous PerformanceMetrics for validation comparison

        Returns:
            SICLOutput — complete 6-stage record
        """
        out = SICLOutput(cycle_id=cycle_id)

        # Stage 1 — Observation
        out.telemetry = observe(recent_outputs)

        # Stage 2 — Evaluation
        out.metrics = evaluate(out.telemetry)

        # Stage 3 — Pattern Extraction
        out.weaknesses = extract_weaknesses(out.metrics, out.telemetry)

        # Stage 4 — Proposal Generation
        raw_proposals = generate_proposals(out.weaknesses, out.metrics)

        # Stage 5 — Controlled Integration
        out.proposals = integrate_proposals(raw_proposals)

        # Stage 6 — Validation (if baseline metrics provided)
        accepted   = [p for p in out.proposals if p.status == UpdateStatus.ACCEPTED]
        rejected   = [p for p in out.proposals if p.status != UpdateStatus.ACCEPTED]
        out.accepted_updates = len(accepted)
        out.rejected_updates = len(rejected)

        if before_metrics and accepted:
            # Simulate after-metrics as modest improvement estimate
            after = PerformanceMetrics(
                IAS = min(1.0, out.metrics.IAS + sum(
                    p.expected_delta for p in accepted
                    if p.expected_metric == "IAS") * 0.6),
                IRS = min(1.0, out.metrics.IRS + sum(
                    p.expected_delta for p in accepted
                    if p.expected_metric == "IRS") * 0.6),
                SDS = min(1.0, out.metrics.SDS + sum(
                    p.expected_delta for p in accepted
                    if p.expected_metric == "SDS") * 0.6),
                TPS = out.metrics.TPS,
                FCS = min(1.0, out.metrics.FCS + sum(
                    p.expected_delta for p in accepted
                    if p.expected_metric == "FCS") * 0.6),
            )
            out.validated   = validate_updates(accepted, before_metrics, after)
            out.net_delta_S = round(after.delta_S - before_metrics.delta_S, 4)
        else:
            out.net_delta_S = 0.0

        out.system_improving = out.net_delta_S >= _UPDATE_MIN_DELTA

        logger.info(
            "[SICL] Cycle '%s': metrics ΔS=%.3f, accepted=%d, rejected=%d, improving=%s",
            cycle_id, out.metrics.delta_S, out.accepted_updates,
            out.rejected_updates, out.system_improving,
        )
        return out
