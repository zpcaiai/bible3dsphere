"""Bounded deterministic orchestration; no agent-to-agent recursion."""
from __future__ import annotations

from typing import Any

from .arbitration import arbitrate_recommendations
from .contracts import OrchestrationRequest
from .safety import safety_gate


def run_workflow(request: OrchestrationRequest, *, active_action_count: int = 0) -> dict[str, Any]:
    steps: list[str] = ["RESOLVE_USER_INTENT", "CHECK_SAFETY"]
    safety = safety_gate(request.safety_state, "DAILY_MIRROR")
    if not safety.allowed:
        result = arbitrate_recommendations(request.candidate_recommendations, safety_state=request.safety_state, active_action_count=active_action_count)
        return {
            "status": "STOPPED_FOR_SAFETY",
            "correlation_id": str(request.correlation_id),
            "steps": steps + ["ROUTE_TO_CRISIS_AUTHORITY"],
            "model_calls_used": 0,
            "safety": {"route": safety.route, "reason_codes": list(safety.reason_codes)},
            "arbitration": result.model_dump(mode="json"),
        }
    steps.extend(["RESOLVE_CAPACITY", "ARBITRATE_CANDIDATES", "PRESENT_UNIFIED_RESULT"])
    if len(steps) > request.max_nodes:
        return {"status": "DEGRADED_LIMIT_REACHED", "correlation_id": str(request.correlation_id), "steps": steps[:request.max_nodes], "model_calls_used": 0, "arbitration": None}
    candidates = [item.model_copy(update={"capacity_mode": request.capacity_mode}) for item in request.candidate_recommendations]
    result = arbitrate_recommendations(candidates, safety_state=request.safety_state, active_action_count=active_action_count)
    return {
        "status": "COMPLETED",
        "correlation_id": str(request.correlation_id),
        "steps": steps,
        "model_calls_used": 0,
        "safety": {"route": safety.route, "reason_codes": list(safety.reason_codes)},
        "arbitration": result.model_dump(mode="json"),
    }
