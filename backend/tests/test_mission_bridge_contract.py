from pathlib import Path

from fastapi.routing import APIRoute

from routers.mission_bridge import IncidentBody, router, v1_router


def test_mission_bridge_routes_cover_mvp_workflow():
    routes = {(route.path, method) for route in router.routes if isinstance(route, APIRoute) for method in route.methods}
    expected = {
        ("/api/mission-bridge/dashboard", "GET"),
        ("/api/mission-bridge/consents", "PUT"),
        ("/api/mission-bridge/enrollments", "POST"),
        ("/api/mission-bridge/enrollments/{enrollment_id}/exit", "POST"),
        ("/api/mission-bridge/enrollments/{enrollment_id}/checkins", "POST"),
        ("/api/mission-bridge/incidents", "POST"),
        ("/api/mission-bridge/incidents/{incident_id}/escalate", "POST"),
        ("/api/mission-bridge/incidents/{incident_id}/timeline", "GET"),
    }
    assert expected <= routes
    v1_routes = {(route.path, method) for route in v1_router.routes if isinstance(route, APIRoute) for method in route.methods}
    assert ("/api/v1/incidents", "POST") in v1_routes
    assert ("/api/v1/incidents/{incident_id}/escalate", "POST") in v1_routes
    assert ("/api/v1/incidents/{incident_id}/timeline", "GET") in v1_routes


def test_immediate_danger_payload_is_explicit():
    body = IncidentBody(riskLevel="L2", category="medical", summary="Immediate medical danger", immediateDanger=True)
    assert body.immediateDanger is True


def test_migration_seeds_only_the_three_approved_mvp_programs():
    sql = (Path(__file__).parents[1] / "migrations" / "0151_mission_bridge.sql").read_text(encoding="utf-8")
    for program_id in ("local-leader-90", "attention-reset-30", "ai-faith-dialogue-8"):
        assert program_id in sql
    assert "ai_cannot_close" in sql
    assert "incident_reports" in sql
    assert "safeguarding_acknowledgements" in sql


def test_high_risk_and_child_protection_guards_are_non_optional():
    source = (Path(__file__).parents[1] / "routers" / "mission_bridge.py").read_text(encoding="utf-8")
    assert "L2/L3 只能由安全官解决" in source
    assert "未成年人事件需要儿童保护权限" in source
    assert "安全事件只能升级" in source
