"""
System Router — SICL + Safety Constitution + HIDOS system endpoints.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# ── Safety Constitution ───────────────────────────────────────────────────────

@router.get("/constitution")
async def get_constitution():
    """
    Return the full 15-article HIDOS Safety Constitution.

    These articles are immutable and enforced at runtime on every HIDOS output.
    """
    from ai.constitution.safety_constitution import get_constitution_summary
    return get_constitution_summary()


@router.post("/constitution/check")
async def constitution_check(body: Dict[str, Any]):
    """
    Check any HIDOS output dict against the 15-article Safety Constitution.

    Returns ConstitutionResult with full violation analysis.
    Used for auditing and testing pipeline outputs.
    """
    from ai.constitution.safety_constitution import get_constitution_checker
    checker = get_constitution_checker()
    result  = checker.check(body)
    return result.to_dict()


# ── SICL ──────────────────────────────────────────────────────────────────────

class SICLRunRequest(BaseModel):
    recent_outputs: List[Dict[str, Any]]
    cycle_id:       Optional[str] = ""


@router.post("/sicl/run")
async def run_sicl_cycle(req: SICLRunRequest):
    """
    Run one SELF-IMPROVING COGNITIVE LOOP (SICL v3.6) cycle.

    Processes recent HIDOS outputs and returns:
      - Performance metrics (IAS, IRS, SDS, TPS, FCS, ΔS)
      - Detected system weaknesses
      - Improvement proposals (with guardrail check results)
      - Validation results

    BOUNDARY: SICL optimizes system understanding only.
    It NEVER targets human behavior, outcomes, or identity.
    """
    from ai.self_improvement.sicl import SelfImprovingCognitiveLoop
    sicl   = SelfImprovingCognitiveLoop()
    output = sicl.run_cycle(
        recent_outputs = req.recent_outputs,
        cycle_id       = req.cycle_id or "",
    )
    return output.to_dict()


@router.get("/sicl/metrics-schema")
async def sicl_metrics_schema():
    """Return the SICL performance metrics schema and improvement function definition."""
    return {
        "schema":     "sicl_v3.6",
        "delta_S":    "Weighted mean of IAS, IRS, SDS, TPS, FCS",
        "metrics": {
            "IAS": {
                "name":        "Insight Accuracy Score",
                "description": "How well system reflects actual behavioral patterns",
                "weight":      0.25,
            },
            "IRS": {
                "name":        "Intervention Relevance Score",
                "description": "How relevant principle suggestions are to active loops",
                "weight":      0.20,
            },
            "SDS": {
                "name":        "Structural Detection Score",
                "description": "Accuracy of loop detection in graph structure",
                "weight":      0.25,
            },
            "TPS": {
                "name":        "Temporal Prediction Score",
                "description": "Consistency of time-series trend interpretation",
                "weight":      0.15,
            },
            "FCS": {
                "name":        "Formation Consistency Score",
                "description": "Stability of long-term formation trajectory modeling",
                "weight":      0.15,
            },
        },
        "improvement_function": "ΔS = 0.25·IAS + 0.20·IRS + 0.25·SDS + 0.15·TPS + 0.15·FCS",
        "boundary":   (
            "SICL optimizes system reasoning accuracy only. "
            "Human behavior, outcomes, and identity are NEVER optimization targets."
        ),
        "guardrails": [
            "modifies_user_model → auto-rejected",
            "adds_moral_judgment → auto-rejected",
            "increases_certainty → auto-rejected",
            "targets_human_outcome → auto-rejected",
            "prompt_refinement → requires human review (never auto-applied)",
        ],
    }


# ── HIDOS System status ───────────────────────────────────────────────────────

@router.get("/status")
async def system_status():
    """HIDOS v3.8 system status and layer availability."""
    return {
        "system":  "HIDOS v3.8",
        "schema":  "hidos_master_v3.8",
        "layers": {
            "graph":      "GraphQueryEngine v3.3 (Neo4j + pattern library fallback)",
            "time":       "TimescaleDB temporal engine",
            "vector":     "pgvector semantic engine",
            "formation":  "FormationMathematicsModel v3.4",
            "orchestrator":"HIDOSOrchestrator v3.5",
            "sicl":       "SelfImprovingCognitiveLoop v3.6",
            "constitution":"SafetyConstitution v3.7 (15 articles, immutable)",
        },
        "constitution_active": True,
        "constitution_articles": 15,
        "self_improving": True,
        "definition": (
            "HIDOS v3.8 = A constrained self-improving cognitive system that models "
            "human inner dynamics across structure, time, meaning, and formation, "
            "while preserving human autonomy as its highest invariant principle."
        ),
    }
