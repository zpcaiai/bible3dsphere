from fastapi.routing import APIRoute
import pytest

from mission_os.roadmap import build_roadmap
from routers.mission_roadmap import router


pytestmark = pytest.mark.no_db


def test_roadmap_starts_with_calling_and_never_claims_deployment():
    roadmap = build_roadmap({})
    assert roadmap["summary"]["currentStageKey"] == "calling"
    assert roadmap["summary"]["progress"] == 0
    assert [stage["key"] for stage in roadmap["stages"]] == [
        "calling", "readiness", "training", "sending", "team", "preparation", "gate"
    ]
    assert "自动激活部署" in roadmap["stages"][-1]["eyebrow"]


def test_roadmap_is_evidence_backed_and_preserves_hard_blocks():
    roadmap = build_roadmap({
        "calling": {"status": "ready_for_readiness_assessment", "reflections": 2, "evidence": 2, "hasCommunityEvidence": True},
        "readiness": {"status": "completed", "level": "deployment_candidate", "dimensions": 15},
        "training": {"status": "active", "requiredModules": 4, "completedModules": 3, "blockingGaps": 1},
    })
    assert roadmap["stages"][0]["status"] == "complete"
    assert roadmap["stages"][1]["status"] == "complete"
    assert roadmap["stages"][2]["status"] == "blocked"
    assert roadmap["summary"]["currentStageKey"] == "training"
    assert roadmap["summary"]["blockedItems"] == 2


def test_ready_gate_only_completes_final_roadmap_stage():
    roadmap = build_roadmap({"gate": {"status": "ready_for_deployment_planning", "blockingFindings": []}})
    gate = roadmap["stages"][-1]
    assert gate["status"] == "complete"
    assert all(item["status"] == "complete" for item in gate["items"])
    assert roadmap["summary"]["currentStageKey"] == "calling"


def test_roadmap_api_contract_exists():
    routes = {(route.path, method) for route in router.routes if isinstance(route, APIRoute) for method in route.methods}
    assert ("/api/v1/mission/roadmap", "GET") in routes
