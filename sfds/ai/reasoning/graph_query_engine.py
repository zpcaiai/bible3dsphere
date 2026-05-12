"""
SFDS v3.3 — Graph Query Engine (GQE)

=============================================================
CORE PRINCIPLE:
  Neo4j is NOT a database in this system.
  It is a COGNITIVE STRUCTURE MODEL of human behavior.

  The GQE does NOT:
    - simply query nodes
    - simply return paths
    - provide deterministic answers

  The GQE DOES:
    - traverse causal structures
    - simulate loop propagation
    - detect highest-leverage breakpoints
    - match structural patterns to principles
    - synthesize non-authoritative reflective insight

=============================================================
4 REASONING MODES:
  MODE 1 — Structural Traversal:  understand the graph shape
  MODE 2 — Loop Simulation:       forward-propagate what happens next
  MODE 3 — Breakpoint Detection:  find highest-leverage intervention
  MODE 4 — Principle Activation:  which truth interrupts this cycle

7-STEP PIPELINE (every query must pass through all 7):
  Step 1 — Structural Parse
  Step 2 — Causal Interpretation
  Step 3 — Loop Identification
  Step 4 — Simulation
  Step 5 — Intervention Analysis
  Step 6 — Principle Matching
  Step 7 — Synthesis (non-authoritative)

=============================================================
SAFETY INVARIANTS (architectural, not configurable):
  - NEVER describe graph output as deterministic fate
  - NEVER assign identity labels from structural patterns
  - NEVER claim absolute psychological truth
  - ALWAYS use probabilistic language in synthesis
  - ALWAYS emphasize changeability and human agency
  - Confidence cap: 0.85 (graph structural reasoning)
=============================================================
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Safety constants ──────────────────────────────────────────────────────────
_MAX_CONFIDENCE    = 0.85   # graph structural reasoning cap
_SIMULATION_STEPS  = 3      # max forward simulation hops
_MAX_LOOP_HOPS     = 5      # max hops to detect a loop closure
_LEVERAGE_LABELS   = {
    "PrincipleNode": 1.00,
    "EmotionNode":   0.95,
    "MotiveNode":    0.90,
    "SpiritualNode": 0.85,
    "BehaviorNode":  0.65,
    "OutcomeNode":   0.30,
}


# ── Data model ────────────────────────────────────────────────────────────────

class GQEMode(Enum):
    STRUCTURAL_TRAVERSAL = "structural_traversal"
    LOOP_SIMULATION      = "loop_simulation"
    BREAKPOINT_DETECTION = "breakpoint_detection"
    PRINCIPLE_ACTIVATION = "principle_activation"


@dataclass
class UserStateInput:
    """
    Current user cognitive state — the entry point for all GQE reasoning.

    emotion_node:    active emotion type (e.g. "fear", "shame")
    motive_node:     active motive type (e.g. "control_drive", "approval_seeking")
    behavior_node:   current behavioral expression (e.g. "overwork", "avoidance")
    user_id:         for retrieving user-specific subgraph history
    category:        dominant loop category for pattern library matching
    """
    emotion_node:  str
    motive_node:   str
    behavior_node: str
    user_id:       str = ""
    category:      str = "fear"


@dataclass
class StructuralView:
    """Step 1 + 2 output — what the graph structure IS."""
    causal_chain:        List[str] = field(default_factory=list)
    edge_types:          List[str] = field(default_factory=list)
    convergence_points:  List[Dict[str, Any]] = field(default_factory=list)
    pattern_id:          str = ""
    description:         str = ""   # human-readable structural interpretation


@dataclass
class LoopAnalysis:
    """Step 3 output — is this a cycle, and how entrenched?"""
    is_loop:          bool  = False
    loop_chain:       List[str] = field(default_factory=list)
    loop_closes_at:   str   = ""
    loop_type:        str   = ""
    loop_intensity:   float = 0.0   # 0.0–0.95
    pattern_id:       str   = ""
    description:      str   = ""
    formation_dims:   Dict[str, str] = field(default_factory=dict)  # e.g. {"fear_tendency": "+"}


@dataclass
class SimulationResult:
    """Step 4 output — forward propagation if no intervention."""
    forward_chain:       List[str] = field(default_factory=list)
    predicted_endpoint:  str  = ""
    steps_simulated:     int  = 0
    reinforcement_active:bool = False
    description:         str  = ""   # probabilistic language REQUIRED


@dataclass
class Breakpoint:
    """Step 5 output — highest-leverage intervention node."""
    node_type:      str   = ""
    node_label:     str   = ""   # EmotionNode / MotiveNode / BehaviorNode
    leverage_score: float = 0.0  # 0.0–1.0
    rationale:      str   = ""
    position_in_loop: str = ""   # "entry" | "mid" | "amplifier" | "reinforcer"


@dataclass
class PrincipleMatch:
    """Step 6 output — principle that breaks this loop structurally."""
    principle_id:            str   = ""
    principle_label:         str   = ""
    principle_category:      str   = ""
    breaks_node:             str   = ""
    structural_effectiveness:float = 0.0
    source_ref:              str   = ""


@dataclass
class GQEOutput:
    """
    Full 7-step GQE reasoning output.

    SAFETY: All text fields must use probabilistic language.
    No field may assign identity or claim determinism.
    """
    mode:                GQEMode
    user_state:          UserStateInput

    # Step 1+2: Structure
    structural_view:     StructuralView    = field(default_factory=StructuralView)

    # Step 3: Loop
    loop_analysis:       LoopAnalysis      = field(default_factory=LoopAnalysis)

    # Step 4: Simulation
    simulation:          SimulationResult  = field(default_factory=SimulationResult)

    # Step 5: Breakpoint
    breakpoint:          Breakpoint        = field(default_factory=Breakpoint)

    # Step 6: Principle
    principle_match:     PrincipleMatch    = field(default_factory=PrincipleMatch)

    # Step 7: Synthesis
    reflective_insight:  str  = ""
    confidence:          float = 0.0
    data_source:         str  = "pattern_library"  # "neo4j" | "pattern_library" | "offline"

    disclaimer: str = (
        "This structural analysis describes possible behavioral tendencies only. "
        "It is not a diagnosis, prediction, or authority statement. "
        "Human agency and change are always structurally possible."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode":        self.mode.value,
            "user_state": {
                "emotion":  self.user_state.emotion_node,
                "motive":   self.user_state.motive_node,
                "behavior": self.user_state.behavior_node,
            },
            "structural_view": {
                "causal_chain":       self.structural_view.causal_chain,
                "convergence_points": self.structural_view.convergence_points,
                "description":        self.structural_view.description,
            },
            "loop_analysis": {
                "is_loop":        self.loop_analysis.is_loop,
                "loop_chain":     self.loop_analysis.loop_chain,
                "loop_closes_at": self.loop_analysis.loop_closes_at,
                "loop_type":      self.loop_analysis.loop_type,
                "loop_intensity": round(self.loop_analysis.loop_intensity, 3),
                "description":    self.loop_analysis.description,
            },
            "simulation": {
                "forward_chain":        self.simulation.forward_chain,
                "predicted_endpoint":   self.simulation.predicted_endpoint,
                "steps_simulated":      self.simulation.steps_simulated,
                "reinforcement_active": self.simulation.reinforcement_active,
                "description":          self.simulation.description,
            },
            "breakpoint": {
                "node_type":       self.breakpoint.node_type,
                "node_label":      self.breakpoint.node_label,
                "leverage_score":  round(self.breakpoint.leverage_score, 3),
                "position":        self.breakpoint.position_in_loop,
                "rationale":       self.breakpoint.rationale,
            },
            "principle_match": {
                "principle_id":            self.principle_match.principle_id,
                "principle_label":         self.principle_match.principle_label,
                "breaks_node":             self.principle_match.breaks_node,
                "structural_effectiveness":round(self.principle_match.structural_effectiveness, 3),
            },
            "reflective_insight": self.reflective_insight,
            "confidence":         round(self.confidence, 3),
            "data_source":        self.data_source,
            "disclaimer":         self.disclaimer,
        }


# ── Pattern library fallback (used when Neo4j is offline) ────────────────────

def _load_pattern_library() -> List[Dict[str, Any]]:
    try:
        from graph.patterns._loops_part1 import _LOOPS_A_B_C
        from graph.patterns._loops_part2 import _LOOPS_D_E_F
        return _LOOPS_A_B_C + _LOOPS_D_E_F
    except ImportError:
        return []


def _find_pattern(
    library: List[Dict[str, Any]],
    emotion: str,
    motive:  str,
    behavior:str,
    category:str,
) -> Optional[Dict[str, Any]]:
    """
    Match current user state to the most likely pattern in the library.
    Priority: direct chain node match > category match > loop_type match.
    """
    nodes = {emotion, motive, behavior}

    # 1. Direct node match — pattern chain contains this exact node sequence
    scored: List[Tuple[int, Dict[str, Any]]] = []
    for p in library:
        chain_set = set(p.get("chain", []))
        score = len(nodes & chain_set)
        if score > 0:
            scored.append((score, p))

    if scored:
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    # 2. Category fallback
    cat_matches = [p for p in library if p.get("category") == category]
    if cat_matches:
        return cat_matches[0]

    # 3. Trigger emotion fallback
    trigger_matches = [p for p in library if p.get("trigger_emotion") == emotion]
    if trigger_matches:
        return trigger_matches[0]

    return None


# ── 7-Step Reasoning Pipeline ─────────────────────────────────────────────────

class GraphQueryEngine:
    """
    GQE v3.3 — Graph Query Engine.

    Transforms Neo4j from a data store into a reasoning system.
    Falls back gracefully to the pattern library when Neo4j is unavailable.

    Usage:
        gqe = GraphQueryEngine(driver=neo4j_driver)
        result = await gqe.reason(state, mode=GQEMode.LOOP_SIMULATION)
    """

    def __init__(self, driver: Any = None):
        self._driver  = driver
        self._library = _load_pattern_library()

    # ── Public interface ──────────────────────────────────────────────────────

    async def reason(
        self,
        state:    UserStateInput,
        mode:     GQEMode = GQEMode.LOOP_SIMULATION,
        question: str = "",
    ) -> GQEOutput:
        """
        Execute full 7-step reasoning pipeline for a given user state.

        Tries Neo4j first; falls back to pattern library on any failure.
        Never raises — always returns a populated GQEOutput.
        """
        output = GQEOutput(mode=mode, user_state=state)

        try:
            if self._driver:
                await self._run_neo4j_pipeline(state, mode, output)
                output.data_source = "neo4j"
            else:
                self._run_library_pipeline(state, mode, output)
                output.data_source = "pattern_library"
        except Exception as exc:
            logger.warning("[GQE] Pipeline failed, using library fallback: %s", exc)
            self._run_library_pipeline(state, mode, output)
            output.data_source = "pattern_library_fallback"

        # Step 7: Synthesis — always runs, always last
        output.reflective_insight = self._synthesize(output)
        output.confidence = min(_MAX_CONFIDENCE, output.loop_analysis.loop_intensity + 0.35)

        return output

    # ── Neo4j pipeline ────────────────────────────────────────────────────────

    async def _run_neo4j_pipeline(
        self, state: UserStateInput, mode: GQEMode, output: GQEOutput
    ) -> None:
        from graph.queries.gqe_cypher import GQL

        async with self._driver.session() as session:
            # Step 1+2: Structural parse + causal interpretation
            causal = await session.run(
                GQL.CAUSAL_CHAIN_FROM_EMOTION,
                emotion_type=state.emotion_node,
                max_hops=_MAX_LOOP_HOPS,
                include_loops=True,
                limit=3,
            )
            rows = [dict(r) async for r in causal]
            if rows:
                best = rows[0]
                output.structural_view.causal_chain = best.get("chain", [])
                output.structural_view.edge_types   = best.get("edge_types", [])
                output.structural_view.description  = self._describe_structure(
                    best.get("chain", [])
                )

            # Step 3: Loop identification
            if mode in (GQEMode.LOOP_SIMULATION, GQEMode.BREAKPOINT_DETECTION,
                        GQEMode.PRINCIPLE_ACTIVATION):
                loops = await session.run(
                    GQL.ACTIVE_LOOPS,
                    user_id=state.user_id,
                    max_hops=_MAX_LOOP_HOPS,
                )
                loop_rows = [dict(r) async for r in loops]
                if loop_rows:
                    top = loop_rows[0]
                    output.loop_analysis.is_loop        = True
                    output.loop_analysis.loop_chain     = top.get("loop_chain", [])
                    output.loop_analysis.loop_closes_at = top.get("loop_closes_at", "")
                    output.loop_analysis.loop_type      = top.get("loop_type", "")
                    output.loop_analysis.pattern_id     = top.get("pattern_id", "")
                    output.loop_analysis.loop_intensity = min(
                        0.95, top.get("loop_length", 3) * 0.12
                    )
                    output.loop_analysis.description    = self._describe_loop(
                        top.get("loop_chain", []), top.get("loop_closes_at", "")
                    )

            # Step 4: Simulation (MODE 2)
            if mode == GQEMode.LOOP_SIMULATION:
                sim = await session.run(
                    GQL.SIMULATE_FORWARD,
                    current_node_type=state.behavior_node,
                    steps=_SIMULATION_STEPS,
                    limit=3,
                )
                sim_rows = [dict(r) async for r in sim]
                if sim_rows:
                    top = sim_rows[0]
                    output.simulation.forward_chain      = top.get("forward_chain", [])
                    output.simulation.predicted_endpoint = top.get("predicted_endpoint", "")
                    output.simulation.steps_simulated    = top.get("steps_ahead", 0)
                    output.simulation.reinforcement_active = output.loop_analysis.is_loop
                    output.simulation.description = self._describe_simulation(
                        top.get("forward_chain", []),
                        top.get("predicted_endpoint", ""),
                        output.loop_analysis.is_loop,
                    )

            # Step 5: Breakpoint detection (MODE 3)
            if mode in (GQEMode.BREAKPOINT_DETECTION, GQEMode.PRINCIPLE_ACTIVATION):
                bp_rows_res = await session.run(
                    GQL.CONVERGENCE_POINTS,
                    pattern_id=output.loop_analysis.pattern_id or state.category,
                )
                bp_rows = [dict(r) async for r in bp_rows_res]
                if bp_rows:
                    top = bp_rows[0]
                    output.breakpoint.node_type      = top.get("node_type", "")
                    output.breakpoint.node_label     = top.get("node_label", "")
                    output.breakpoint.leverage_score = top.get("leverage_score", 0.5)
                    output.breakpoint.rationale      = self._describe_breakpoint(
                        top.get("node_type", ""), top.get("node_label", ""),
                        top.get("in_degree", 1)
                    )
                    output.breakpoint.position_in_loop = _classify_position(
                        top.get("node_type", ""), output.loop_analysis.loop_chain
                    )

            # Step 6: Principle activation (MODE 4)
            if mode == GQEMode.PRINCIPLE_ACTIVATION or output.loop_analysis.is_loop:
                pr_res = await session.run(
                    GQL.PRINCIPLES_THAT_BREAK,
                    pattern_id=output.loop_analysis.pattern_id or "",
                    loop_chain=output.loop_analysis.loop_chain or [state.behavior_node],
                )
                pr_rows = [dict(r) async for r in pr_res]
                if pr_rows:
                    top = pr_rows[0]
                    output.principle_match.principle_id            = top.get("principle_id", "")
                    output.principle_match.principle_label         = top.get("principle_label", "")
                    output.principle_match.principle_category      = top.get("principle_category", "")
                    output.principle_match.breaks_node             = top.get("breaks_node", "")
                    output.principle_match.structural_effectiveness= top.get("structural_effectiveness", 0.6)

    # ── Pattern library pipeline (offline / fallback) ────────────────────────

    def _run_library_pipeline(
        self, state: UserStateInput, mode: GQEMode, output: GQEOutput
    ) -> None:
        """
        Full 7-step pipeline executed against the in-memory pattern library.
        No Neo4j required. Used during development and as fallback.
        """
        pattern = _find_pattern(
            self._library,
            state.emotion_node, state.motive_node,
            state.behavior_node, state.category,
        )

        if not pattern:
            logger.warning("[GQE] No matching pattern found for state: %s", state)
            return

        chain      = pattern.get("chain", [])
        edges      = pattern.get("edges", [])
        loop_type  = pattern.get("loop_type", "")
        pattern_id = pattern.get("id", "")
        break_p    = pattern.get("break_principle", "")
        f_dims     = pattern.get("formation_dims", {})

        # ── Step 1+2: Structural parse + causal interpretation ────────────────
        output.structural_view.causal_chain = chain
        output.structural_view.edge_types   = [e[1] for e in edges]
        output.structural_view.pattern_id   = pattern_id
        output.structural_view.description  = self._describe_structure(chain)

        # ── Step 3: Loop identification ────────────────────────────────────────
        # A loop exists when any REINFORCES edge points back to the start
        reinforces = [(s, t) for (s, et, t) in edges if et == "REINFORCES"]
        has_loop   = len(reinforces) > 0

        if has_loop:
            _, loop_back = reinforces[0]
            loop_intensity = _compute_library_intensity(pattern, state)
            output.loop_analysis = LoopAnalysis(
                is_loop        = True,
                loop_chain     = chain,
                loop_closes_at = loop_back,
                loop_type      = loop_type,
                loop_intensity = loop_intensity,
                pattern_id     = pattern_id,
                description    = self._describe_loop(chain, loop_back),
                formation_dims = f_dims,
            )
        else:
            output.loop_analysis.description = (
                "A linear causal sequence appears active — "
                "no reinforcement edge detected in this pattern."
            )

        # ── Step 4: Simulation ─────────────────────────────────────────────────
        forward = _simulate_forward(chain, edges, state.behavior_node, _SIMULATION_STEPS)
        output.simulation = SimulationResult(
            forward_chain        = forward,
            predicted_endpoint   = forward[-1] if forward else "",
            steps_simulated      = len(forward),
            reinforcement_active = has_loop,
            description          = self._describe_simulation(
                forward, forward[-1] if forward else "", has_loop
            ),
        )

        # ── Step 5: Breakpoint detection ───────────────────────────────────────
        bp = _find_best_breakpoint(chain, edges)
        if bp:
            node_type, node_label = bp
            output.breakpoint = Breakpoint(
                node_type       = node_type,
                node_label      = node_label,
                leverage_score  = _LEVERAGE_LABELS.get(node_label, 0.5),
                rationale       = self._describe_breakpoint(node_type, node_label, 2),
                position_in_loop= _classify_position(node_type, chain),
            )

        # ── Step 6: Principle activation ───────────────────────────────────────
        break_edges = pattern.get("break_edges", [])
        if break_edges:
            pid, _, target = break_edges[0]
            output.principle_match = PrincipleMatch(
                principle_id            = pid,
                principle_label         = break_p,
                principle_category      = state.category,
                breaks_node             = target,
                structural_effectiveness= _LEVERAGE_LABELS.get(
                    _node_label_from_type(target), "BehaviorNode"
                ),
            )
        elif break_p:
            output.principle_match = PrincipleMatch(
                principle_id            = f"lib_{pattern_id}",
                principle_label         = break_p,
                principle_category      = state.category,
                breaks_node             = chain[1] if len(chain) > 1 else chain[0],
                structural_effectiveness= 0.75,
            )

    # ── Step 7: Synthesis ─────────────────────────────────────────────────────

    def _synthesize(self, out: GQEOutput) -> str:
        """
        Generate a non-authoritative reflective insight from all 6 prior steps.

        SAFETY RULES (enforced structurally):
          - No "you are X" language
          - No "this will happen" language
          - No moral judgment
          - Always include possibility of change
          - Always use "may", "appears", "a pattern seems"
        """
        s   = out.structural_view
        la  = out.loop_analysis
        sim = out.simulation
        bp  = out.breakpoint
        pr  = out.principle_match

        parts: List[str] = []

        # Structural description
        if s.causal_chain:
            chain_str = " → ".join(s.causal_chain)
            parts.append(
                f"Structurally, a pattern appears to be active: {chain_str}."
            )

        # Loop observation
        if la.is_loop:
            parts.append(
                f"This pattern may be forming a self-reinforcing loop "
                f"that closes at '{la.loop_closes_at}'. "
                f"The loop type appears consistent with '{la.loop_type.replace('_', ' ')}'."
            )
        else:
            parts.append(
                "This appears to be a linear causal sequence "
                "rather than a closed loop at this point."
            )

        # Simulation (probabilistic language required)
        if sim.forward_chain and len(sim.forward_chain) > 1:
            sim_str = " → ".join(sim.forward_chain[:3])
            parts.append(
                f"If the current pattern continues without interruption, "
                f"a possible trajectory might be: {sim_str}."
            )

        # Breakpoint
        if bp.node_type:
            parts.append(
                f"The highest-leverage point for possible change "
                f"may be at the '{bp.node_type}' node "
                f"(leverage score: {bp.leverage_score:.0%})."
            )

        # Principle
        if pr.principle_label:
            parts.append(
                f"A principle that may structurally interrupt this pattern: "
                f"'{pr.principle_label}'."
            )

        # Always close with agency statement
        parts.append(
            "Patterns describe tendencies — not destiny. "
            "Change is structurally possible at any node in this chain."
        )

        return " ".join(parts)

    # ── Narration helpers (Step descriptions) ────────────────────────────────

    def _describe_structure(self, chain: List[str]) -> str:
        if not chain:
            return "No structural chain detected."
        chain_str = " → ".join(chain)
        return (
            f"A causal sequence appears active: {chain_str}. "
            f"This is a structural tendency — not a fixed identity or inevitable outcome."
        )

    def _describe_loop(self, chain: List[str], closes_at: str) -> str:
        if not chain:
            return "No closed loop detected."
        chain_str = " → ".join(chain)
        return (
            f"A possible self-reinforcing loop may be active: {chain_str} → {closes_at}. "
            f"Each cycle through this pattern may increase the momentum of the loop. "
            f"However, reinforcement is not irreversibility — the loop can be interrupted."
        )

    def _describe_simulation(
        self, forward: List[str], endpoint: str, has_loop: bool
    ) -> str:
        if not forward:
            return "Insufficient data for forward simulation."
        fwd_str = " → ".join(forward[:3])
        loop_note = (
            " Because a reinforcement edge appears active, "
            "this sequence may repeat rather than resolve."
            if has_loop else ""
        )
        return (
            f"If the current pattern continues without a structural interruption, "
            f"a possible forward trajectory may be: {fwd_str}.{loop_note} "
            f"This is a probabilistic structural tendency, not a prediction."
        )

    def _describe_breakpoint(
        self, node_type: str, node_label: str, in_degree: int
    ) -> str:
        label_desc = {
            "MotiveNode":    "the motivational layer (highest leverage — motives shape behavior)",
            "EmotionNode":   "the emotional trigger layer (high leverage — entry point of the loop)",
            "PrincipleNode": "the principle layer (maximum leverage — directly breaks the loop)",
            "BehaviorNode":  "the behavioral expression layer (moderate leverage — most visible point)",
            "OutcomeNode":   "the outcome layer (lower leverage — downstream of the loop structure)",
        }.get(node_label, "an active node in the causal chain")
        return (
            f"The node '{node_type}' ({label_desc}) "
            f"may represent a high-leverage intervention point. "
            f"It appears in {in_degree} causal pathways, suggesting structural centrality."
        )


# ── Pipeline utility functions ────────────────────────────────────────────────

def _simulate_forward(
    chain: List[str],
    edges: List[Tuple[str, str, str]],
    start_node: str,
    steps: int,
) -> List[str]:
    """
    Walk LEADS_TO and CAUSES edges forward from start_node.
    Returns ordered sequence of visited nodes.
    """
    adj: Dict[str, str] = {}
    for (src, et, tgt) in edges:
        if et in ("CAUSES", "LEADS_TO"):
            adj[src] = tgt

    visited: List[str] = []
    current = start_node

    # find start position in chain if start_node not in adj
    if current not in adj and current in chain:
        idx = chain.index(current)
        if idx + 1 < len(chain):
            current = chain[idx + 1]

    for _ in range(steps):
        nxt = adj.get(current)
        if not nxt or nxt in visited:
            break
        visited.append(nxt)
        current = nxt

    return visited or chain[1:min(1 + steps, len(chain))]


def _find_best_breakpoint(
    chain: List[str],
    edges: List[Tuple[str, str, str]],
) -> Optional[Tuple[str, str]]:
    """
    Find the highest-leverage breakpoint in the pattern.
    Priority: MotiveNode > EmotionNode > earliest BehaviorNode.
    Returns (node_type, node_label).
    """
    emotions = {"fear", "anxiety", "shame", "pride", "guilt", "grief",
                "joy", "peace", "loneliness", "spiritual_dryness",
                "confusion", "discomfort", "love", "desire"}
    motives  = {"control_drive", "approval_seeking", "self_sufficiency",
                "need_to_win", "avoidance", "truth_seeking", "overconfidence",
                "perfectionism", "image_management", "discipline_avoidance"}

    for node in chain:
        if node in motives:
            return (node, "MotiveNode")
    for node in chain:
        if node in emotions:
            return (node, "EmotionNode")
    if len(chain) >= 2:
        return (chain[1], "BehaviorNode")
    return None


def _classify_position(node_type: str, loop_chain: List[str]) -> str:
    if not loop_chain or node_type not in loop_chain:
        return "unknown"
    idx = loop_chain.index(node_type)
    n   = len(loop_chain)
    if idx == 0:
        return "entry"
    if idx == n - 1:
        return "reinforcer"
    if idx <= n // 2:
        return "mid"
    return "amplifier"


def _compute_library_intensity(
    pattern: Dict[str, Any], state: UserStateInput
) -> float:
    """
    Estimate loop intensity from pattern structure alone (no history).
    Higher = more nodes in chain, more formation_dims affected.
    """
    chain_len = len(pattern.get("chain", []))
    dims_affected = len(pattern.get("formation_dims", {}))
    base = min(0.50, chain_len * 0.08 + dims_affected * 0.05)
    return round(base, 3)


def _node_label_from_type(node_type: str) -> str:
    emotions = {"fear", "anxiety", "shame", "pride", "guilt",
                "loneliness", "spiritual_dryness", "confusion", "love", "desire"}
    motives  = {"control_drive", "approval_seeking", "avoidance",
                "self_sufficiency", "need_to_win"}
    if node_type in emotions:   return "EmotionNode"
    if node_type in motives:    return "MotiveNode"
    if node_type.startswith("principle_"): return "PrincipleNode"
    return "BehaviorNode"
