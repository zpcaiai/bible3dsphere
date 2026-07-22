from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from formation_twin.formation_ontology import (
    CONTEXT_FIELD_ALLOWLISTS,
    NODE_TYPES,
    RELATIONS,
    STATEMENT_TYPES,
)
from formation_twin.formation_safety import (
    crisis_blocks_formation,
    review_generated_text,
    validate_model_candidate,
)
from formation_twin.spiritual_engine import build_formation_snapshot, build_minimal_chain, context_envelope


NOW = datetime(2026, 7, 17, tzinfo=timezone.utc)
pytestmark = pytest.mark.no_db


def node(node_id: str, node_type: str, source_kind: str, statement_type: str, **extra):
    return {
        "id": node_id,
        "node_type": node_type,
        "content": extra.pop("content", f"content-{node_id}"),
        "source_kind": source_kind,
        "statement_type": statement_type,
        "scope": "THIS_EVENT_ONLY",
        "user_review_status": extra.pop("user_review_status", "NOT_REQUIRED"),
        "processing_status": "ACTIVE",
        **extra,
    }


def test_closed_ontology_has_no_causal_verdict_or_spiritual_scoring_types():
    assert "CAUSED" not in RELATIONS
    assert "PROVED" not in RELATIONS
    assert "DETERMINED" not in RELATIONS
    forbidden = {"SALVATION_STATUS", "MATURITY_SCORE", "HOLINESS_SCORE", "SIN_SCORE", "IDOL_SCORE"}
    assert forbidden.isdisjoint(NODE_TYPES)
    assert {
        "USER_REPORTED_FACT", "OBSERVED_EVENT", "RULE_DERIVED_RELATION",
        "MODEL_FORMATION_HYPOTHESIS", "USER_CONFIRMED_FORMATION_PATTERN",
    }.issubset(STATEMENT_TYPES)


def test_rule_chain_links_only_existing_nodes_without_filling_missing_states():
    event = node("event", "LIFE_EVENT", "OBSERVATION", "OBSERVED_EVENT", sequence_order=0)
    emotion = node("emotion", "EMOTION", "USER_REPORT", "USER_REPORTED_FACT", sequence_order=5)
    chain = build_minimal_chain(event, [emotion])

    assert [item["id"] for item in chain["nodes"]] == ["event", "emotion"]
    assert [edge["relation_type"] for edge in chain["edges"]] == ["OBSERVED_IN_SAME_EVENT"]
    assert not {"BELIEF_STATEMENT", "DESIRE", "FEAR"}.intersection(item["node_type"] for item in chain["nodes"])


def test_snapshot_separates_sources_and_never_emits_a_score():
    nodes = [
        node("user", "BELIEF_STATEMENT", "USER_REPORT", "USER_REPORTED_FACT"),
        node("observed", "BEHAVIOR", "OBSERVATION", "OBSERVED_EVENT"),
        node("model", "DESIRE", "MODEL", "MODEL_FORMATION_HYPOTHESIS", user_review_status="PENDING", confidence=.62),
        node("confirmed", "DESIRE", "USER_CONFIRMED", "USER_CONFIRMED_FORMATION_PATTERN"),
        node("grace", "GRACE_EVIDENCE", "USER_REPORT", "USER_REPORTED_FACT"),
    ]
    snapshot = build_formation_snapshot(nodes=nodes, chains=[], window_start=NOW-timedelta(days=7), window_end=NOW)

    assert [item["id"] for item in snapshot["user_reported_items"]] == ["user", "grace"]
    assert [item["id"] for item in snapshot["observed_relations"]] == ["observed"]
    assert [item["id"] for item in snapshot["pending_hypotheses"]] == ["model"]
    assert [item["id"] for item in snapshot["confirmed_patterns"]] == ["confirmed"]
    serialized = json.dumps(snapshot, ensure_ascii=False).lower()
    for forbidden in ("maturity_score", "holiness_score", "salvation_score", "idol_score", "sin_score"):
        assert forbidden not in serialized


def test_snapshot_windows_use_event_time_instead_of_rebuild_time():
    recent = node("recent", "BEHAVIOR", "OBSERVATION", "OBSERVED_EVENT", occurred_at=(NOW-timedelta(days=2)).isoformat())
    old = node("old", "BEHAVIOR", "OBSERVATION", "OBSERVED_EVENT", occurred_at=(NOW-timedelta(days=20)).isoformat())
    weekly = build_formation_snapshot(nodes=[recent, old], chains=[], window_start=NOW-timedelta(days=7), window_end=NOW)
    monthly = build_formation_snapshot(nodes=[recent, old], chains=[], window_start=NOW-timedelta(days=30), window_end=NOW)
    assert [item["id"] for item in weekly["observed_relations"]] == ["recent"]
    assert {item["id"] for item in monthly["observed_relations"]} == {"recent", "old"}


@pytest.mark.parametrize("text", [
    "你尚未得救", "你的悔改不真实", "神告诉我你一定要去做这件事", "你真正的动机就是控制",
    "你的偶像就是成功", "这证明你拜偶像", "你患有焦虑症", "你就是一个讨好型人格",
    "你的属灵分数是 70", "这一定说明你的根本原因就是骄傲",
])
def test_theological_red_team_blocks_verdicts(text):
    result = review_generated_text(text)
    assert result.verdict == "BLOCK"
    assert result.flags


def test_model_hypothesis_requires_evidence_alternatives_scope_review_and_expiry():
    candidate = {
        "node_type": "BELIEF_STATEMENT",
        "content": "也许你当时把失败理解为失去价值",
        "statement_type": "MODEL_FORMATION_HYPOTHESIS",
        "source_kind": "MODEL",
        "confidence": .58,
        "evidence": [{"start_offset": 0, "end_offset": 4}],
        "alternatives": ["也可能只是当时很疲惫"],
        "scope": "THIS_EVENT_ONLY",
        "user_review_status": "PENDING",
        "expires_at": (NOW + timedelta(days=30)).isoformat(),
    }
    assert validate_model_candidate(candidate, now=NOW) == []
    candidate["alternatives"] = []
    candidate["evidence"] = []
    assert {"evidence_required", "alternative_explanations_required"}.issubset(validate_model_candidate(candidate, now=NOW))


def test_context_requires_per_target_consent_and_excludes_pending_hypotheses():
    snapshot = build_formation_snapshot(
        nodes=[
            node("confirmed", "SPIRITUAL_PRACTICE", "USER_CONFIRMED", "USER_CONFIRMED_FORMATION_PATTERN"),
            node("model", "BELIEF_STATEMENT", "MODEL", "MODEL_FORMATION_HYPOTHESIS", user_review_status="PENDING"),
        ], chains=[], window_start=NOW-timedelta(days=7), window_end=NOW,
    )
    assert context_envelope(snapshot, "prayer", consent=False)["reason"] == "CONSENT_REQUIRED"
    allowed = context_envelope(snapshot, "prayer", consent=True)
    assert allowed["available"] is True
    assert "pending_hypotheses" not in allowed["context"]
    assert set(allowed["context"]).issubset(CONTEXT_FIELD_ALLOWLISTS["prayer"])
    assert allowed["context"]["user_confirmed_prayer_context"][0]["id"] == "confirmed"


def test_crisis_always_blocks_formation_processing():
    assert crisis_blocks_formation({"safety_level": "ELEVATED"}, "ACCEPTED")
    assert crisis_blocks_formation({"safety_level": "NONE"}, "ROUTED_TO_CRISIS")
    assert not crisis_blocks_formation({"safety_level": "NONE"}, "ACCEPTED")


def test_migration_has_owner_rls_and_no_score_columns():
    sql = (Path(__file__).parents[1] / "migrations" / "0214_formation_twin_spiritual_formation.sql").read_text()
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "app.current_user_email" in sql
    assert "formation_twin_formation_nodes" in sql
    assert "formation_twin_formation_chains" in sql
    assert "formation_twin_formation_snapshots" in sql
    lowered = sql.lower()
    for column in ("maturity_score ", "holiness_score ", "salvation_score ", "sin_score ", "idol_score "):
        assert column not in lowered


def test_router_exposes_batch_4_review_and_control_contracts():
    from routers.formation_twin_formation import router

    routes = {(method, route.path) for route in router.routes for method in route.methods}
    required = {
        ("GET", "/api/v1/formation-twin/formation-state/current"),
        ("POST", "/api/v1/formation-twin/formation-state/rebuild"),
        ("POST", "/api/v1/formation-twin/formation-nodes/{node_id}/confirm"),
        ("POST", "/api/v1/formation-twin/formation-nodes/{node_id}/reject"),
        ("POST", "/api/v1/formation-twin/formation-nodes/{node_id}/change-scope"),
        ("POST", "/api/v1/formation-twin/formation-chains/{chain_id}/duplicate-alternative"),
        ("GET", "/api/v1/formation-twin/formation-review-queue"),
        ("GET", "/api/v1/formation-twin/formation-context/{target}"),
    }
    assert required.issubset(routes)


def test_existing_export_and_erase_cover_batch_4_records_in_fk_safe_order():
    source = (Path(__file__).parents[1] / "routers" / "formation_twin.py").read_text()
    for name in ("formation_nodes", "formation_chains", "formation_snapshots"):
        assert f'"{name}"' in source
    ordered_tables = [
        "formation_twin_graph_syncs", "formation_twin_formation_reviews", "formation_twin_chain_edges",
        "formation_twin_chain_nodes", "formation_twin_formation_edges", "formation_twin_formation_evidence",
        "formation_twin_formation_snapshots", "formation_twin_formation_chains", "formation_twin_formation_nodes",
        "formation_twin_formation_settings",
    ]
    positions = [source.index(f'DELETE FROM {table} WHERE email=%s') for table in ordered_tables]
    assert positions == sorted(positions)


def test_graph_projection_is_metadata_only_and_owner_scoped():
    source = (Path(__file__).parents[1] / "formation_twin" / "formation_graph.py").read_text()
    assert "WHERE user_id = %s" in source
    assert "properties->>'profile_id' = %s" in source
    assert "content_hash" in source
    assert "get_neo4j_driver" not in source
    assert "n.content=" not in source
    assert "evidence_json" not in source
    assert "alternatives_json" not in source
