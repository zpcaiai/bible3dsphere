"""
SFDS v3.4 — Formation Mathematics Model (FMM)

=================================================================
CORE PRINCIPLE:
  Human formation is NOT identity.
  Human formation IS a time-evolving state vector influenced
  by feedback loops, meaning exposure, and emotional dynamics.

  This model formalizes the dynamics equation:

    dX(t)/dt = F(G, E, P, N)
             = α·G + β·E + γ·P + δ·N

  Where:
    X(t) — 8-dim FormationStateVector at time t
    G    — Graph influence (loop reinforcement from Neo4j)
    E    — Emotional state influence (volatility from TimescaleDB)
    P    — Principle alignment influence (from vector DB)
    N    — Noise / uncertainty term (ensures non-determinism)

  Discrete update rule (per decision event):
    X(t+1) = X(t) + ΔX
    ΔX = α·ΔG + β·ΔE + γ·ΔP + δ·ΔN

=================================================================
KEY CONCEPTS:

  Loop Reinforcement Coefficient:
    R(loop) = repetition_count × emotional_intensity × recency_weight
    Higher R → stronger behavioral habit → harder to break

  Breaking Function:
    B(loop) = principle_strength × awareness_level × interruption_action
    Sufficient B → loop is weakened

  Stability Function:
    S(t) = 1 - variance(X over time window)
    High S → consistent state | Low S → volatility / fragmentation

  Trajectory:
    Direction: sign(dX/dt) per dimension
    Acceleration: sign(d²X/dt²) — is the rate of change increasing?
    Critical transitions: phase shifts detected at variance thresholds

=================================================================
SAFETY INVARIANTS (architectural constants):
  - Values bounded [0.05, 0.95] — no absolute zeros or ones
  - Noise term N is ALWAYS included — system is NEVER deterministic
  - NO dimension carries moral valence
  - fear_tendency / pride_tendency = loop momentum, NOT moral failure
  - Confidence cap: 0.88 (FMM analytical reasoning)
  - All trajectory output uses: "tends toward", "may be", "appears to"
=================================================================
"""

from __future__ import annotations

import math
import random
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── System constants ──────────────────────────────────────────────────────────
SCORE_MIN          = 0.05
SCORE_MAX          = 0.95
CONFIDENCE_CAP     = 0.88
RECENCY_DECAY      = 0.92        # history[k] weight = 0.92^k
NOISE_SIGMA        = 0.015       # Gaussian noise std — ensures non-determinism
STABILITY_WINDOW   = 10          # number of snapshots for variance computation
DRIFT_THRESHOLD    = 0.12        # abs distance from 0.5 → "structural drift"
CRITICAL_VARIANCE  = 0.04        # variance threshold → "critical transition"

# ── Dynamics weights (α, β, γ, δ) ────────────────────────────────────────────
# These control how strongly each influence term affects ΔX.
# Tuned conservatively — small steps, never deterministic jumps.
ALPHA = 0.35   # Graph influence weight
BETA  = 0.30   # Emotional state influence weight
GAMMA = 0.25   # Principle alignment influence weight
DELTA = 0.10   # Noise term weight


# ── Data model ────────────────────────────────────────────────────────────────

class TrajectoryDirection(str, Enum):
    IMPROVING_CLARITY      = "improving_clarity"
    STABILIZING            = "stabilizing"
    INCREASING_VOLATILITY  = "increasing_volatility"
    FRAGMENTING            = "fragmenting"
    CYCLICAL               = "cyclical"
    STABLE                 = "stable"
    UNKNOWN                = "unknown"


class AccelerationDirection(str, Enum):
    STRENGTHENING = "strengthening"   # d²X/dt² amplifying current direction
    WEAKENING     = "weakening"       # d²X/dt² opposing current direction
    NEUTRAL       = "neutral"


@dataclass
class FormationVector:
    """
    8-dimensional continuous state vector X(t).

    Values ∈ [0.05, 0.95]. NOT moral scores. NOT identity.
    These are BEHAVIORAL TENDENCY ESTIMATES at time t.

    fear_tendency + pride_tendency:
      Higher = more active loop momentum (structural signal only).
    All others:
      Higher = more active in the healthy direction.
    """
    fear_tendency:       float = 0.50
    pride_tendency:      float = 0.50
    desire_tendency:     float = 0.50
    truth_alignment:     float = 0.50
    emotional_stability: float = 0.50
    relational_health:   float = 0.50
    resilience:          float = 0.50
    spiritual_clarity:   float = 0.50

    def clamp(self) -> "FormationVector":
        for k, v in self.__dict__.items():
            setattr(self, k, max(SCORE_MIN, min(SCORE_MAX, v)))
        return self

    def to_dict(self) -> Dict[str, float]:
        return {k: round(v, 4) for k, v in self.__dict__.items()}

    def distance_from_baseline(self) -> Dict[str, float]:
        """Distance of each dimension from 0.5 midpoint."""
        return {k: round(abs(v - 0.50), 4) for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, d: Dict[str, float]) -> "FormationVector":
        v = cls()
        for k in v.__dict__:
            if k in d:
                setattr(v, k, float(d[k]))
        return v.clamp()

    @classmethod
    def zero(cls) -> "FormationVector":
        """Zero-delta vector — used for ΔX before accumulation."""
        return cls(**{k: 0.0 for k in cls.__dataclass_fields__})


@dataclass
class LoopDynamics:
    """
    Loop reinforcement and breaking coefficients for one active loop.

    R(loop) = repetition_count × emotional_intensity × recency_weight
    B(loop) = principle_strength × awareness_level × interruption_action
    """
    pattern_id:           str
    loop_type:            str
    repetition_count:     int    = 0
    emotional_intensity:  float  = 5.0   # 0–10 scale
    recency_weight:       float  = 1.0   # 0–1; most recent session = 1.0
    principle_strength:   float  = 0.0   # 0–1; from semantic search score
    awareness_level:      float  = 0.0   # 0–1; from reflection_active
    interruption_action:  float  = 0.0   # 0–1; from loop_broken flag

    @property
    def R(self) -> float:
        """Reinforcement coefficient. Higher → stronger habit."""
        raw = self.repetition_count * (self.emotional_intensity / 5.0) * self.recency_weight
        return round(min(0.95, raw * 0.12), 4)

    @property
    def B(self) -> float:
        """Breaking function. Higher → loop is being weakened."""
        return round(min(0.95,
            self.principle_strength * self.awareness_level * max(self.interruption_action, 0.1)
        ), 4)

    @property
    def net_momentum(self) -> float:
        """R - B: positive = loop gaining strength; negative = being broken."""
        return round(self.R - self.B, 4)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id":         self.pattern_id,
            "loop_type":          self.loop_type,
            "R":                  self.R,
            "B":                  self.B,
            "net_momentum":       self.net_momentum,
            "repetition_count":   self.repetition_count,
            "emotional_intensity":self.emotional_intensity,
            "principle_strength": self.principle_strength,
            "interpretation": (
                "loop gaining momentum" if self.net_momentum > 0.1 else
                "loop being weakened"   if self.net_momentum < -0.05 else
                "loop in equilibrium"
            ),
        }


@dataclass
class StabilityAnalysis:
    """
    S(t) = 1 - variance(X over window)

    Computed over STABILITY_WINDOW historical snapshots.
    High S → coherent, consistent formation state.
    Low S → volatility, fragmentation, possible critical transition.
    """
    stability_score:    float           # 0–1
    variance_per_dim:   Dict[str, float] = field(default_factory=dict)
    overall_variance:   float = 0.0
    is_critical:        bool  = False   # variance > CRITICAL_VARIANCE
    coherence_note:     str   = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stability_score":  round(self.stability_score, 4),
            "overall_variance": round(self.overall_variance, 4),
            "is_critical":      self.is_critical,
            "coherence_note":   self.coherence_note,
            "variance_per_dim": {k: round(v, 4) for k, v in self.variance_per_dim.items()},
        }


@dataclass
class TrajectoryAnalysis:
    """
    First and second derivatives of X(t).

    direction (dX/dt sign): improving / stabilizing / fragmenting / cyclical
    acceleration (d²X/dt²): strengthening / weakening / neutral
    critical_transitions: dimensions nearing phase shift
    """
    direction:            TrajectoryDirection
    acceleration:         AccelerationDirection
    delta_per_dim:        Dict[str, float] = field(default_factory=dict)
    drift_detected:       bool             = False
    drifting_dimensions:  List[str]        = field(default_factory=list)
    critical_transitions: List[str]        = field(default_factory=list)
    description:          str              = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "direction":            self.direction.value,
            "acceleration":         self.acceleration.value,
            "drift_detected":       self.drift_detected,
            "drifting_dimensions":  self.drifting_dimensions,
            "critical_transitions": self.critical_transitions,
            "delta_per_dim":        {k: round(v, 4) for k, v in self.delta_per_dim.items()},
            "description":          self.description,
        }


@dataclass
class InterventionScore:
    """
    I = (loop_strength × instability) / principle_alignment

    Higher I → higher urgency for reflective awareness.
    NOT a command. NOT a diagnosis. A STRUCTURAL SIGNAL.
    """
    score:             float   # 0–1
    loop_strength:     float
    instability:       float
    principle_alignment:float
    urgency_level:     str     # "low" | "moderate" | "elevated" | "high"
    breaking_potential:Dict[str, float] = field(default_factory=dict)
    note:              str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score":             round(self.score, 4),
            "urgency_level":     self.urgency_level,
            "loop_strength":     round(self.loop_strength, 4),
            "instability":       round(self.instability, 4),
            "principle_alignment":round(self.principle_alignment, 4),
            "breaking_potential":self.breaking_potential,
            "note":              self.note,
        }


@dataclass
class FMMOutput:
    """
    Complete Formation Mathematics Model output.

    SAFETY: All text fields use system-state language, NOT identity language.
    """
    state_vector:      FormationVector
    previous_vector:   Optional[FormationVector]
    delta_vector:      FormationVector             # ΔX this step
    loop_dynamics:     List[LoopDynamics]          = field(default_factory=list)
    stability:         StabilityAnalysis           = field(default_factory=StabilityAnalysis)
    trajectory:        TrajectoryAnalysis          = field(default_factory=TrajectoryAnalysis)
    intervention:      InterventionScore           = field(default_factory=InterventionScore)
    principle_effects: List[Dict[str, Any]]        = field(default_factory=list)
    reflective_insight:str = ""
    confidence:        float = 0.0
    schema:            str  = "fmm_v3.4"
    disclaimer:        str  = (
        "This model describes the dynamic state of a system — "
        "not the identity, destiny, or moral worth of a person. "
        "All values are estimates of temporary behavioral tendencies. "
        "Human agency and transformation are structurally always possible."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema":           self.schema,
            "state_vector":     self.state_vector.to_dict(),
            "delta_vector":     {k: round(v, 4) for k, v in self.delta_vector.__dict__.items()},
            "loop_dynamics":    [l.to_dict() for l in self.loop_dynamics],
            "stability":        self.stability.to_dict(),
            "trajectory":       self.trajectory.to_dict(),
            "intervention":     self.intervention.to_dict(),
            "principle_effects":self.principle_effects,
            "reflective_insight":self.reflective_insight,
            "confidence":       round(self.confidence, 4),
            "disclaimer":       self.disclaimer,
        }


# ── Influence term computation ────────────────────────────────────────────────

def _compute_G(
    loop_dynamics:  List[LoopDynamics],
    pattern_dims:   Dict[str, Dict[str, str]],
) -> FormationVector:
    """
    G — Graph influence term.

    Maps active loop net_momentum to FSV dimension deltas.
    Uses formation_dims from pattern library: {dim: "+" | "-"}

    Positive net_momentum (R > B) → loop active → dims shift toward loop profile.
    Negative net_momentum (B > R) → loop breaking → dims shift away.
    """
    G = FormationVector.zero()
    if not loop_dynamics:
        return G

    for loop in loop_dynamics:
        dims = pattern_dims.get(loop.pattern_id, {})
        momentum = loop.net_momentum  # + or -

        for dim, direction in dims.items():
            if not hasattr(G, dim):
                continue
            # Loop active (+momentum): amplify the dim in its natural direction
            # Loop breaking (-momentum): shift dim toward health
            if direction == "+":
                setattr(G, dim, getattr(G, dim) + momentum * 0.25)
            else:  # direction == "-"
                setattr(G, dim, getattr(G, dim) - momentum * 0.25)

    return G


def _compute_E(
    emotional_volatility: float,   # 0–10 from TimescaleDB
    stress_spikes:        int,      # count of spike events in window
    stability_trend:      float,    # -1 (declining) to +1 (improving)
) -> FormationVector:
    """
    E — Emotional state influence term.

    High volatility → decreases emotional_stability, increases fear/desire tendency.
    Improving stability trend → increases resilience, emotional_stability.
    """
    E = FormationVector.zero()

    vol_norm  = emotional_volatility / 10.0    # normalize to 0–1
    spike_eff = min(0.5, stress_spikes * 0.05)

    E.emotional_stability = -(vol_norm * 0.4 + spike_eff * 0.2)
    E.fear_tendency       = +(vol_norm * 0.2)
    E.resilience          = +(stability_trend * 0.15)
    E.spiritual_clarity   = -(vol_norm * 0.10)

    return E


def _compute_P(
    principle_scores: List[Dict[str, Any]],
) -> FormationVector:
    """
    P — Principle alignment term.

    Semantic search results from vector DB.
    Each principle has a similarity score and a category.

    Category → FSV dimension mapping:
      humility     → humility +, pride_tendency -
      truth        → truth_alignment +, fear_tendency -
      resilience   → resilience +, emotional_stability +
      compassion   → relational_health +
      rest         → resilience +, fear_tendency -
      formation    → spiritual_clarity +
      pride        → pride_tendency - (breaking function)
      fear         → fear_tendency - (breaking function)
    """
    P = FormationVector.zero()
    if not principle_scores:
        return P

    _MAP: Dict[str, List[Tuple[str, float]]] = {
        "humility":   [("humility", +0.30), ("pride_tendency", -0.15)],
        "truth":      [("truth_alignment", +0.30), ("fear_tendency", -0.10)],
        "resilience": [("resilience", +0.25), ("emotional_stability", +0.10)],
        "compassion": [("relational_health", +0.25)],
        "rest":       [("resilience", +0.15), ("fear_tendency", -0.20)],
        "formation":  [("spiritual_clarity", +0.25)],
        "pride":      [("pride_tendency", -0.20), ("humility", +0.10)],
        "fear":       [("fear_tendency", -0.20), ("emotional_stability", +0.10)],
    }

    for p in principle_scores:
        score    = float(p.get("score", 0.0))     # 0–1 semantic similarity
        category = p.get("category", "general")
        effects  = _MAP.get(category, [("truth_alignment", +0.05)])

        for dim, weight in effects:
            if hasattr(P, dim):
                setattr(P, dim, getattr(P, dim) + score * weight)

    return P


def _compute_N(seed: Optional[int] = None) -> FormationVector:
    """
    N — Noise / uncertainty term.

    Gaussian noise applied to all dimensions.
    This term ENSURES the system is NEVER fully deterministic.
    It represents: randomness, external events, unpredictable life changes.

    CRITICAL: Without this term, FMM would be a deterministic machine.
    This term is the mathematical expression of human unpredictability.
    """
    if seed is not None:
        random.seed(seed)
    N = FormationVector.zero()
    for k in N.__dataclass_fields__:
        setattr(N, k, random.gauss(0, NOISE_SIGMA))
    return N


# ── Main update rule: X(t+1) = X(t) + ΔX ────────────────────────────────────

def compute_delta(
    G:     FormationVector,
    E:     FormationVector,
    P:     FormationVector,
    N:     FormationVector,
    alpha: float = ALPHA,
    beta:  float = BETA,
    gamma: float = GAMMA,
    delta: float = DELTA,
) -> FormationVector:
    """
    ΔX = α·G + β·E + γ·P + δ·N

    The core dynamics equation in discrete form.
    Returns the delta vector to be applied to X(t).
    """
    dx = FormationVector.zero()
    for k in dx.__dataclass_fields__:
        val = (
            alpha * getattr(G, k) +
            beta  * getattr(E, k) +
            gamma * getattr(P, k) +
            delta * getattr(N, k)
        )
        setattr(dx, k, val)
    return dx


def apply_delta(
    X:  FormationVector,
    dx: FormationVector,
) -> FormationVector:
    """
    X(t+1) = X(t) + ΔX, then clamped to [SCORE_MIN, SCORE_MAX].
    """
    X_new = FormationVector()
    for k in X.__dataclass_fields__:
        new_val = getattr(X, k) + getattr(dx, k)
        setattr(X_new, k, max(SCORE_MIN, min(SCORE_MAX, new_val)))
    return X_new


# ── Stability analysis ────────────────────────────────────────────────────────

def compute_stability(history: List[FormationVector]) -> StabilityAnalysis:
    """
    S(t) = 1 - mean_variance(X over history window)

    Computed over up to STABILITY_WINDOW most recent snapshots.
    """
    window = history[-STABILITY_WINDOW:] if len(history) > STABILITY_WINDOW else history

    if len(window) < 2:
        return StabilityAnalysis(
            stability_score = 0.50,
            coherence_note  = "Insufficient history for stability computation.",
        )

    dims = list(FormationVector.__dataclass_fields__.keys())
    var_per_dim: Dict[str, float] = {}

    for dim in dims:
        vals = [getattr(v, dim) for v in window]
        mean = sum(vals) / len(vals)
        variance = sum((x - mean) ** 2 for x in vals) / len(vals)
        var_per_dim[dim] = round(variance, 5)

    overall_var = sum(var_per_dim.values()) / len(var_per_dim)
    stability   = max(0.0, min(1.0, 1.0 - overall_var / CRITICAL_VARIANCE))
    is_critical = overall_var > CRITICAL_VARIANCE

    coherence_note = (
        "The system state appears highly volatile — possible critical transition region."
        if is_critical else
        "The system state appears relatively coherent across the recent window."
        if stability > 0.70 else
        "Moderate variability detected — the system is in active flux."
    )

    return StabilityAnalysis(
        stability_score  = round(stability, 4),
        variance_per_dim = var_per_dim,
        overall_variance = round(overall_var, 5),
        is_critical      = is_critical,
        coherence_note   = coherence_note,
    )


# ── Trajectory analysis ───────────────────────────────────────────────────────

def compute_trajectory(
    current:  FormationVector,
    previous: Optional[FormationVector],
    history:  List[FormationVector],
) -> TrajectoryAnalysis:
    """
    Computes dX/dt (direction) and d²X/dt² (acceleration).

    Direction logic:
      improving_clarity:     truth_alignment + spiritual_clarity both increasing
      stabilizing:           fear/pride both decreasing, stability increasing
      increasing_volatility: stability decreasing + fear/desire increasing
      fragmenting:           multiple dims drifting from 0.5 simultaneously
      cyclical:              variance pattern repeating
      stable:                all deltas < 0.02
    """
    if previous is None:
        return TrajectoryAnalysis(
            direction    = TrajectoryDirection.UNKNOWN,
            acceleration = AccelerationDirection.NEUTRAL,
            description  = "Insufficient data for trajectory computation (first session).",
        )

    dims = list(FormationVector.__dataclass_fields__.keys())
    deltas: Dict[str, float] = {}
    for d in dims:
        deltas[d] = round(getattr(current, d) - getattr(previous, d), 4)

    # Classify direction
    truth_d   = deltas.get("truth_alignment", 0)
    clarity_d = deltas.get("spiritual_clarity", 0)
    stability_d = deltas.get("emotional_stability", 0)
    fear_d    = deltas.get("fear_tendency", 0)
    pride_d   = deltas.get("pride_tendency", 0)
    resilience_d = deltas.get("resilience", 0)

    # Detect drift (dimensions far from 0.5)
    drifting = [
        d for d in dims
        if abs(getattr(current, d) - 0.50) > DRIFT_THRESHOLD
    ]

    # Classify direction
    if truth_d > 0.03 and clarity_d > 0.02:
        direction = TrajectoryDirection.IMPROVING_CLARITY
    elif stability_d > 0.03 and fear_d < -0.02 and resilience_d > 0.01:
        direction = TrajectoryDirection.STABILIZING
    elif stability_d < -0.04 and (fear_d > 0.04 or pride_d > 0.04):
        direction = TrajectoryDirection.INCREASING_VOLATILITY
    elif len(drifting) >= 3:
        direction = TrajectoryDirection.FRAGMENTING
    elif all(abs(v) < 0.02 for v in deltas.values()):
        direction = TrajectoryDirection.STABLE
    else:
        direction = TrajectoryDirection.UNKNOWN

    # Detect cyclical pattern from history
    if len(history) >= 4:
        recent_signs = [
            math.copysign(1, getattr(h, "fear_tendency") - 0.50)
            for h in history[-4:]
        ]
        if len(set(recent_signs)) > 1 and recent_signs[0] == recent_signs[2]:
            direction = TrajectoryDirection.CYCLICAL

    # Acceleration: compare current delta with previous delta
    acceleration = AccelerationDirection.NEUTRAL
    if len(history) >= 2:
        prev_delta = getattr(history[-1], "fear_tendency") - getattr(history[-2], "fear_tendency") \
            if len(history) >= 2 else 0.0
        curr_delta = fear_d
        if abs(curr_delta) > abs(prev_delta) + 0.01:
            acceleration = AccelerationDirection.STRENGTHENING
        elif abs(curr_delta) < abs(prev_delta) - 0.01:
            acceleration = AccelerationDirection.WEAKENING

    # Critical transitions: dims variance near CRITICAL_VARIANCE
    critical = []
    if len(history) >= 3:
        for d in dims:
            vals = [getattr(h, d) for h in history[-3:]] + [getattr(current, d)]
            mean = sum(vals) / len(vals)
            var  = sum((x - mean)**2 for x in vals) / len(vals)
            if var > CRITICAL_VARIANCE * 0.8:
                critical.append(d)

    # Narrative
    desc = _build_trajectory_narrative(direction, deltas, drifting, acceleration)

    return TrajectoryAnalysis(
        direction            = direction,
        acceleration         = acceleration,
        delta_per_dim        = deltas,
        drift_detected       = len(drifting) > 0,
        drifting_dimensions  = drifting,
        critical_transitions = critical,
        description          = desc,
    )


def _build_trajectory_narrative(
    direction:    TrajectoryDirection,
    deltas:       Dict[str, float],
    drifting:     List[str],
    acceleration: AccelerationDirection,
) -> str:
    """
    Builds a probabilistic, non-authoritative trajectory narrative.
    Language rules: "tends toward", "may be", "appears to".
    """
    direction_phrases = {
        TrajectoryDirection.IMPROVING_CLARITY:
            "The system state tends toward increased clarity and truth-alignment.",
        TrajectoryDirection.STABILIZING:
            "The system appears to be moving toward greater stability.",
        TrajectoryDirection.INCREASING_VOLATILITY:
            "The system may be entering a period of increased volatility.",
        TrajectoryDirection.FRAGMENTING:
            "Multiple dimensions appear to be drifting simultaneously — "
            "possible system fragmentation tendency.",
        TrajectoryDirection.CYCLICAL:
            "A cyclical pattern may be present — the system appears to oscillate "
            "rather than progress linearly.",
        TrajectoryDirection.STABLE:
            "The system appears relatively stable — low dimensional movement detected.",
        TrajectoryDirection.UNKNOWN:
            "Trajectory direction is unclear with current data.",
    }

    base = direction_phrases.get(direction, "Trajectory direction uncertain.")

    if drifting:
        drift_str = ", ".join(drifting[:3])
        base += f" Dimensions showing structural drift: {drift_str}."

    accel_note = {
        AccelerationDirection.STRENGTHENING:
            " The rate of change appears to be accelerating.",
        AccelerationDirection.WEAKENING:
            " The rate of change appears to be decelerating.",
        AccelerationDirection.NEUTRAL: "",
    }.get(acceleration, "")

    return base + accel_note + (
        " These are structural tendencies — not predictions or identity conclusions."
    )


# ── Intervention score ────────────────────────────────────────────────────────

def compute_intervention_score(
    loop_dynamics:   List[LoopDynamics],
    stability:       StabilityAnalysis,
    principle_scores:List[Dict[str, Any]],
) -> InterventionScore:
    """
    I = (loop_strength × instability) / max(principle_alignment, 0.01)

    Higher I → the system is in a state where reflective awareness
                could have high structural leverage.

    NOT a command to change. NOT a diagnosis.
    A STRUCTURAL SIGNAL about the system's current leverage profile.
    """
    if not loop_dynamics:
        return InterventionScore(
            score=0.0, loop_strength=0.0,
            instability=0.0, principle_alignment=0.5,
            urgency_level="low",
            note="No active loops detected — system appears structurally stable.",
        )

    loop_strength = max((l.R for l in loop_dynamics), default=0.0)
    instability   = 1.0 - stability.stability_score
    principle_al  = max(
        (float(p.get("score", 0.0)) for p in principle_scores),
        default=0.01,
    )

    raw_score = (loop_strength * instability) / max(principle_al, 0.01)
    I = min(1.0, raw_score)

    urgency = (
        "high"     if I > 0.70 else
        "elevated" if I > 0.45 else
        "moderate" if I > 0.20 else
        "low"
    )

    # Breaking potential per loop
    breaking = {
        l.pattern_id: round(l.B / max(l.R, 0.01), 4)
        for l in loop_dynamics
    }

    note = (
        f"Structural signal: the combination of loop momentum (strength={loop_strength:.2f}), "
        f"instability ({instability:.2f}), and principle exposure ({principle_al:.2f}) "
        f"suggests reflective awareness may have {urgency} structural leverage at this time. "
        f"This is a system-state signal — not a directive."
    )

    return InterventionScore(
        score=round(I, 4),
        loop_strength=round(loop_strength, 4),
        instability=round(instability, 4),
        principle_alignment=round(principle_al, 4),
        urgency_level=urgency,
        breaking_potential=breaking,
        note=note,
    )


# ── Main FMM class ────────────────────────────────────────────────────────────

class FormationMathematicsModel:
    """
    FMM v3.4 — Full dynamics engine.

    Usage:
        fmm = FormationMathematicsModel()
        output = fmm.step(
            current_vector   = X_t,
            loop_dynamics    = [LoopDynamics(...)],
            emotional_signal = {...},
            principle_scores = [...],
            history          = [X_t-1, X_t-2, ...],
        )
    """

    def step(
        self,
        current_vector:    FormationVector,
        loop_dynamics:     List[LoopDynamics],
        emotional_signal:  Dict[str, Any],
        principle_scores:  List[Dict[str, Any]],
        history:           List[FormationVector],
        pattern_dims:      Optional[Dict[str, Dict[str, str]]] = None,
        _noise_seed:       Optional[int] = None,   # for deterministic testing only
    ) -> FMMOutput:
        """
        Execute one FMM step: X(t+1) = X(t) + ΔX

        Args:
            current_vector:   X(t) — current FormationVector
            loop_dynamics:    active loops with R and B coefficients
            emotional_signal: {"volatility": 0–10, "stress_spikes": int, "stability_trend": -1..+1}
            principle_scores: [{"score": 0–1, "category": str, "label": str}, ...]
            history:          list of previous FormationVectors (oldest first)
            pattern_dims:     {pattern_id: {dim: "+"/"-"}} from pattern library
            _noise_seed:      optional seed for deterministic test mode ONLY

        Returns:
            FMMOutput — complete 7-component analysis
        """
        # Compute influence terms
        pdims   = pattern_dims or {}
        G       = _compute_G(loop_dynamics, pdims)
        E       = _compute_E(
            emotional_volatility = float(emotional_signal.get("volatility", 5.0)),
            stress_spikes        = int(emotional_signal.get("stress_spikes", 0)),
            stability_trend      = float(emotional_signal.get("stability_trend", 0.0)),
        )
        P       = _compute_P(principle_scores)
        N       = _compute_N(seed=_noise_seed)

        # Dynamics equation: ΔX = α·G + β·E + γ·P + δ·N
        dx      = compute_delta(G, E, P, N)

        # Update rule: X(t+1) = X(t) + ΔX
        X_new   = apply_delta(current_vector, dx)

        # Analytical components
        prev    = history[-1] if history else None
        stab    = compute_stability(history + [current_vector])
        traj    = compute_trajectory(X_new, prev, history)
        interv  = compute_intervention_score(loop_dynamics, stab, principle_scores)

        # Principle effects summary
        p_effects = [
            {
                "principle_id":   p.get("id", ""),
                "label":          p.get("principle_en", p.get("label", "")),
                "category":       p.get("category", ""),
                "score":          round(float(p.get("score", 0.0)), 4),
                "structural_effect": "loop_weakening" if p.get("category") in
                                     ("fear", "pride", "shame") else "dimension_strengthening",
            }
            for p in principle_scores[:3]
        ]

        # Confidence: higher with more history, capped at CONFIDENCE_CAP
        confidence = min(
            CONFIDENCE_CAP,
            0.30 + len(history) * 0.05 + (0.10 if not stab.is_critical else 0.0)
        )

        output = FMMOutput(
            state_vector       = X_new,
            previous_vector    = prev,
            delta_vector       = dx,
            loop_dynamics      = loop_dynamics,
            stability          = stab,
            trajectory         = traj,
            intervention       = interv,
            principle_effects  = p_effects,
            confidence         = confidence,
        )

        output.reflective_insight = self._synthesize(output)
        return output

    def _synthesize(self, out: FMMOutput) -> str:
        """
        Non-authoritative system-state narrative.
        Describes X(t) dynamics without labeling the person.
        """
        parts: List[str] = []

        # State snapshot
        sv = out.state_vector.to_dict()
        high_loops = [k for k, v in sv.items()
                      if k in ("fear_tendency", "pride_tendency", "desire_tendency") and v > 0.62]
        low_health = [k for k, v in sv.items()
                      if k not in ("fear_tendency", "pride_tendency", "desire_tendency") and v < 0.38]

        if high_loops:
            dims_str = ", ".join(h.replace("_", " ") for h in high_loops)
            parts.append(
                f"The system state shows elevated momentum in: {dims_str}. "
                f"These represent active loop dynamics — not character definitions."
            )

        if low_health:
            dims_str = ", ".join(l.replace("_", " ") for l in low_health)
            parts.append(
                f"Dimensions showing lower activation: {dims_str}. "
                f"Lower values indicate reduced engagement in these areas currently."
            )

        # Trajectory
        if out.trajectory.direction != TrajectoryDirection.UNKNOWN:
            parts.append(out.trajectory.description)

        # Loop dynamics
        active_loops = [l for l in out.loop_dynamics if l.net_momentum > 0.05]
        if active_loops:
            loop_strs = [f"'{l.loop_type.replace('_', ' ')}' (momentum: {l.R:.2f})"
                         for l in active_loops[:2]]
            parts.append(
                f"Active loop dynamics: {', '.join(loop_strs)}. "
                f"Loop momentum (R coefficient) describes habit strength — not moral failure."
            )

        # Intervention signal
        if out.intervention.urgency_level in ("elevated", "high"):
            parts.append(
                f"The structural leverage signal is {out.intervention.urgency_level}. "
                f"This suggests the system is in a state where reflective awareness "
                f"may have meaningful structural impact."
            )

        # Principle effect
        if out.principle_effects:
            pl = out.principle_effects[0].get("label", "")
            if pl:
                parts.append(
                    f"A potentially relevant principle: '{pl[:80]}'. "
                    f"Principle exposure is modeled as a force that weakens loop momentum "
                    f"through the breaking function B(loop)."
                )

        # Agency close
        parts.append(
            "The system is dynamic. No dimension is fixed. "
            "Formation trajectories can change at any point of genuine reflection or action."
        )

        return " ".join(parts)


# ── Convenience factory ───────────────────────────────────────────────────────

def build_loop_dynamics_from_pattern(
    pattern:    Dict[str, Any],
    repetitions:int   = 1,
    intensity:  float = 5.0,
    recency:    float = 1.0,
    loop_broken:bool  = False,
    reflection: bool  = False,
    principle_strength: float = 0.0,
) -> LoopDynamics:
    """
    Construct a LoopDynamics object from a PATTERN_LIBRARY entry.

    awareness_level:     1.0 if reflection is active, else 0.20 (ambient)
    interruption_action: 0.80 if loop was broken this session, else 0.10
    """
    return LoopDynamics(
        pattern_id          = pattern.get("id", "unknown"),
        loop_type           = pattern.get("loop_type", "unknown"),
        repetition_count    = repetitions,
        emotional_intensity = intensity,
        recency_weight      = recency,
        principle_strength  = principle_strength,
        awareness_level     = 1.0 if reflection else 0.20,
        interruption_action = 0.80 if loop_broken else 0.10,
    )
