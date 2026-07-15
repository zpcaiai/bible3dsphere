"""Mission OS cross-batch integration & consistency tests.

Verifies the whole module is logically coherent: the lifecycle pipeline gates
stages correctly, every domain module imports, every batch router is registered
in the FastAPI app, and there is no dangling non-existent-batch reference.
"""
import importlib
from pathlib import Path
import pytest
from mission_os import pipeline as pl

pytestmark = pytest.mark.no_db
BACKEND = Path(__file__).parents[1]


# ---- lifecycle pipeline ties the batches together --------------------------
def test_pipeline_stage_order_is_linear_and_terminal():
    assert pl.STAGES[0] == "calling_discernment"
    assert pl.STAGES[-1] == "deployment_planning"
    assert pl.next_stage("deployment_readiness_gate") == "deployment_planning"
    assert pl.next_stage("deployment_planning") is None
    # each stage maps to a batch 3..6
    assert set(pl.STAGE_BATCH.values()) <= {3, 4, 5, 6}


def test_pipeline_gates_downstream_on_upstream_state():
    # cannot reach sending application without a deployment_candidate readiness
    with pytest.raises(ValueError):
        pl.assert_can_enter("sending_application", {"readiness_assessment": "foundational_development"})
    pl.assert_can_enter("sending_application", {"readiness_assessment": "deployment_candidate"})

    # cannot enter deployment prep without an approved sending decision
    with pytest.raises(ValueError):
        pl.assert_can_enter("deployment_preparation", {"sending_committee_decision": "declined_current_application"})
    pl.assert_can_enter("deployment_preparation", {"sending_committee_decision": "approved_for_next_stage"})

    # cannot enter deployment planning without a Ready gate
    with pytest.raises(ValueError):
        pl.assert_can_enter("deployment_planning", {"deployment_readiness_gate": "blocked"})
    pl.assert_can_enter("deployment_planning", {"deployment_readiness_gate": "ready_for_deployment_planning"})


def test_no_stage_marks_worker_deployed():
    assert pl.deployment_activates_worker() is False


# ---- every mission_os domain module imports cleanly ------------------------
DOMAIN_MODULES = [
    "ai_boundaries", "calling", "certification", "claims", "classification",
    "deployment", "field", "finance", "health_family", "identity", "knowledge_graph",
    "partnership", "pipeline", "practicum", "readiness", "sending", "sensitive_export",
    "team", "training",
]


@pytest.mark.parametrize("mod", DOMAIN_MODULES)
def test_domain_module_imports(mod):
    importlib.import_module(f"mission_os.{mod}")


# ---- every batch router module imports and exposes a router ----------------
ROUTER_MODULES = [
    "mission_field_classification", "mission_sensitive_export", "mission_fields",
    "mission_claims", "mission_calling", "mission_readiness", "mission_training",
    "mission_certification", "mission_sending", "mission_partnership",
    "mission_finance", "mission_deployment", "mission_roadmap",
]


@pytest.mark.parametrize("mod", ROUTER_MODULES)
def test_router_module_imports(mod):
    m = importlib.import_module(f"routers.{mod}")
    # each module exposes at least one APIRouter attribute
    from fastapi import APIRouter
    assert any(isinstance(getattr(m, a), APIRouter) for a in dir(m)), f"{mod} exposes no APIRouter"


def test_all_batch_routers_registered_in_main():
    """Guards against a router being built but never wired into the app."""
    main_src = (BACKEND / "main.py").read_text()
    for mod in ROUTER_MODULES:
        assert f"from routers.{mod} import" in main_src, f"{mod} not imported in main.py"
    # spot-check include_router wiring for the batch-1..6 routers
    for token in ("mission_field_classification_router", "mission_fields_router",
                  "mission_calling_router", "mission_training_router",
                  "mission_sending_router", "mission_financial_plans_router",
                  "mission_gate_router", "mission_roadmap_router"):
        assert f"app.include_router({token})" in main_src, f"{token} not included in app"


def test_no_dangling_batch7_reference_in_mission_os():
    """There is no Batch 7 — mission_os code must not depend on one."""
    for p in (BACKEND / "mission_os").glob("*.py"):
        text = p.read_text()
        assert "batch7" not in text.lower().replace(" ", ""), f"dangling batch7 reference in {p.name}"


def test_new_list_endpoints_exist():
    """B: read/list endpoints the console depends on are registered."""
    from fastapi.routing import APIRoute
    from routers.mission_fields import router as f
    from routers.mission_calling import router as c
    from routers.mission_readiness import router as r
    from routers.mission_finance import router as fin
    from routers.mission_deployment import gate_router as g
    def routes(rt):
        return {(x.path, m) for x in rt.routes if isinstance(x, APIRoute) for m in x.methods}
    assert ("/api/v1/mission/fields", "GET") in routes(f)
    assert ("/api/v1/mission/calling-journeys", "GET") in routes(c)
    assert ("/api/v1/mission/readiness-assessments", "GET") in routes(r)
    assert ("/api/v1/mission/financial-plans", "GET") in routes(fin)
    assert ("/api/v1/mission/deployment-readiness-gates", "GET") in routes(g)


def test_console_referenced_endpoints_all_registered():
    """Every endpoint the Mission OS 工作台 (missionApi.js) calls must exist on a
    registered mission router — guards frontend<->backend contract drift."""
    import importlib
    from fastapi import APIRouter
    from fastapi.routing import APIRoute
    modules = [
        "mission_fields", "mission_calling", "mission_readiness", "mission_training",
        "mission_sending", "mission_partnership", "mission_finance", "mission_deployment",
    ]
    routes = set()
    for name in modules:
        m = importlib.import_module(f"routers.{name}")
        for attr in dir(m):
            obj = getattr(m, attr)
            if isinstance(obj, APIRouter):
                for r in obj.routes:
                    if isinstance(r, APIRoute):
                        for meth in r.methods:
                            routes.add((meth, r.path))

    def has(method, path):
        # segment match with {param} wildcards
        want = [s for s in path.split('/') if s]
        for mth, p in routes:
            if mth != method:
                continue
            got = [s for s in p.split('/') if s]
            if len(got) != len(want):
                continue
            if all(g.startswith('{') or g == w for g, w in zip(got, want)):
                return True
        return False

    required = [
        ("GET", "/api/v1/mission/fields"), ("POST", "/api/v1/mission/fields"),
        ("POST", "/api/v1/mission/fields/{id}/assess"),
        ("GET", "/api/v1/mission/calling-journeys"), ("POST", "/api/v1/mission/calling-journeys"),
        ("GET", "/api/v1/mission/readiness-assessments"), ("POST", "/api/v1/mission/readiness-assessments"),
        ("GET", "/api/v1/mission/training-plans"), ("POST", "/api/v1/mission/training-plans"),
        ("GET", "/api/v1/mission/sending/applications"), ("POST", "/api/v1/mission/sending/applications"),
        ("GET", "/api/v1/mission/sending/committee-decisions"), ("POST", "/api/v1/mission/sending/committee-decisions"),
        ("GET", "/api/v1/mission/teams"), ("POST", "/api/v1/mission/teams"),
        ("GET", "/api/v1/mission/local-partners"), ("POST", "/api/v1/mission/local-partners"),
        ("GET", "/api/v1/mission/legal-identity-paths"), ("POST", "/api/v1/mission/legal-identity-paths"),
        ("GET", "/api/v1/mission/family-readiness-plans"), ("POST", "/api/v1/mission/family-readiness-plans"),
        ("GET", "/api/v1/mission/compliance-cases"), ("POST", "/api/v1/mission/compliance-cases"),
        ("GET", "/api/v1/mission/financial-plans"), ("POST", "/api/v1/mission/financial-plans"),
        ("GET", "/api/v1/mission/deployment-readiness-gates"), ("POST", "/api/v1/mission/deployment-readiness-gates/run"),
        ("POST", "/api/v1/mission/credentials"), ("POST", "/api/v1/mission/credentials/vault-session"),
        ("GET", "/api/v1/mission/credentials/{id}/secure-file"),
    ]
    missing = [(m, p) for m, p in required if not has(m, p)]
    assert not missing, f"console-referenced endpoints missing from backend: {missing}"
