import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import batch7_13_engine as engine
from routers.batch7_13 import init_batch7_13_router, router


@pytest.mark.no_db
def test_batch_registry_covers_7_to_13_and_52_skills():
    registry = engine.module_registry()

    batch_keys = {module["batch"] for module in registry["modules"]}
    assert set(range(7, 14)).issubset(batch_keys)
    assert registry["total_modules"] == 13
    assert registry["total_skills"] == 52
    assert len(registry["skills"]) == 52


@pytest.mark.no_db
def test_orchestrator_routes_safety_and_batch_specific_intents():
    assert engine.orchestrate(7, "I need an accountability partner")["skill"] == "accountability_group"
    assert engine.orchestrate(8, "Where should I serve?")["skill"] == "ministry_match"
    assert engine.orchestrate(9, "Tell me about David and Jesus")["skill"] == "bible_character_graph"
    assert engine.orchestrate(10, "Give me a recommendation")["skill"] == "formation_recommendation"
    assert engine.orchestrate(11, "Make a privacy audit")["skill"] == "safety_integrity_audit"
    assert engine.orchestrate(12, "Create a church tenant")["skill"] == "multi_tenant_church"
    assert engine.orchestrate(13, "Create the master build prompt")["skill"] == "master_build_prompt"

    crisis = engine.orchestrate(8, "I will kill myself tonight")
    assert crisis["route"] == "crisis_triage"
    assert crisis["blocked_normal_formation"] is True


@pytest.mark.no_db
def test_artifact_creation_per_batch_has_four_records_and_dashboards():
    for batch in range(7, 14):
        records = engine.create_artifacts(batch, "u@example.com")
        dash = engine.dashboard(batch, records)
        assert len(records) == 4
        assert dash["batch"] == batch
        assert dash["module_key"] == engine.BATCHES[batch].module_key
        assert sum(dash["record_counts"].values()) == 4


@pytest.mark.no_db
def test_bible_graph_and_roadmap_contracts():
    graph = engine.bible_graph_search("David")
    roadmap = engine.roadmap()

    assert graph["relationship_path"][0]["from"] == "David"
    assert graph["relationship_path"][0]["to"] == "Jesus"
    assert "definition_of_done" in roadmap
    assert any(phase["key"] == "enterprise" for phase in roadmap["phases"])


@pytest.mark.no_db
def test_router_fallback_memory_contract():
    init_batch7_13_router(get_session_user=lambda request: {"email": "u@example.com"})
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/api/formation-os/registry")
    assert response.status_code == 200
    assert response.json()["total_skills"] == 52

    response = client.post("/api/formation-os/batches/9/orchestrate", json={"intent_text": "Bible character David"})
    assert response.status_code == 200
    assert response.json()["route"]["skill"] == "bible_character_graph"

    response = client.post("/api/formation-os/batches/13/artifacts", json={"context": {}})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["records"]) == 4
    assert payload["dashboard"]["module_key"] == "master_build"

    response = client.get("/api/formation-os/records", params={"batch": 13})
    assert response.status_code == 200
    assert len(response.json()["records"]) >= 4

    response = client.get("/api/formation-os/batches/6/dashboard")
    assert response.status_code == 422


@pytest.mark.no_db
def test_migration_version_is_unique_after_existing_0104_files():
    from pathlib import Path

    migration_dir = Path(__file__).resolve().parents[1] / "migrations"
    versions = [path.name.split("_", 1)[0] for path in migration_dir.glob("*.sql")]

    assert len(versions) == len(set(versions))
    assert (migration_dir / "0108_batch7_13_formation_os.sql").exists()
