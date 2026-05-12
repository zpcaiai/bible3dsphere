"""
Graph Router — Neo4j structural analysis API.
"""

from fastapi import APIRouter, Depends, HTTPException  # noqa: F401 (HTTPException used by sub-routes)
from pydantic import BaseModel
from typing import Optional
from services.graph_service.service import GraphService, get_graph_service

router = APIRouter()


class GQERequest(BaseModel):
    user_id:  str
    emotion:  str
    motive:   str
    behavior: str
    category: str = "fear"
    mode:     str = "loop_simulation"   # structural_traversal | loop_simulation | breakpoint_detection | principle_activation
    question: Optional[str] = ""


@router.get("/patterns")
async def get_patterns(svc: GraphService = Depends(get_graph_service)):
    return await svc.get_patterns()


@router.get("/detect-loop/{user_id}")
async def detect_loop(user_id: str, svc: GraphService = Depends(get_graph_service)):
    return await svc.detect_loop(user_id)


@router.get("/root-cause/{behavior_type}")
async def root_cause(behavior_type: str, svc: GraphService = Depends(get_graph_service)):
    return await svc.trace_root_cause(behavior_type)


@router.get("/intervention-points/{user_id}")
async def intervention_points(user_id: str, svc: GraphService = Depends(get_graph_service)):
    return await svc.find_intervention_points(user_id)


@router.post("/reason")
async def graph_reason(body: dict, svc: GraphService = Depends(get_graph_service)):
    """
    6-layer Graph Reasoning Fusion Engine endpoint.
    """
    return await svc.reason(body)


@router.post("/gqe/reason")
async def gqe_reason(req: GQERequest, svc: GraphService = Depends(get_graph_service)):
    """
    GQE v3.3 — Graph Query Engine: 4-mode, 7-step graph reasoning pipeline.

    Modes:
      structural_traversal  — understand causal structure
      loop_simulation       — forward-propagate: what happens if unchanged?
      breakpoint_detection  — find highest-leverage intervention node
      principle_activation  — which principle structurally breaks this loop?

    Output: 7-step structured GQEOutput (structural_view, loop_analysis,
    simulation, breakpoint, principle_match, reflective_insight, confidence)

    Safety: All synthesis text uses probabilistic language.
    Never assigns identity labels or deterministic predictions.
    """
    return await svc.gqe_reason(
        user_id  = req.user_id,
        emotion  = req.emotion,
        motive   = req.motive,
        behavior = req.behavior,
        category = req.category,
        mode     = req.mode,
        question = req.question or "",
    )


@router.get("/gqe/modes")
async def gqe_modes():
    """Return available GQE reasoning modes and their descriptions."""
    return {
        "modes": [
            {
                "id":          "structural_traversal",
                "label":       "Structural Traversal",
                "description": "Understand the causal structure. What graph pattern is active?",
                "output_focus":"causal_chain, convergence_points",
            },
            {
                "id":          "loop_simulation",
                "label":       "Loop Simulation",
                "description": "Forward-propagate: what happens if no intervention occurs?",
                "output_focus":"loop_analysis, simulation.forward_chain",
            },
            {
                "id":          "breakpoint_detection",
                "label":       "Breakpoint Detection",
                "description": "Find the highest-leverage intervention point in the loop.",
                "output_focus":"breakpoint.node_type, breakpoint.leverage_score",
            },
            {
                "id":          "principle_activation",
                "label":       "Principle Activation",
                "description": "Which principle structurally breaks this loop?",
                "output_focus":"principle_match.principle_label, principle_match.breaks_node",
            },
        ],
        "pipeline_steps": [
            "1. Structural Parse",
            "2. Causal Interpretation",
            "3. Loop Identification",
            "4. Simulation",
            "5. Intervention Analysis",
            "6. Principle Matching",
            "7. Synthesis",
        ],
        "safety_note": (
            "GQE output describes structural tendencies only. "
            "Never assigns identity or deterministic predictions."
        ),
    }
