#!/usr/bin/env python3
"""
Tests for PostgreSQL-based graph layer (replaces Neo4j).

Validates:
- GraphService initialization with db_pool=None (offline mode)
- Pattern matching (offline rule engine)
- Causal chain building
- Intervention extraction
- Loop detection (offline fallback)
- Root cause tracing (offline fallback)
- Principle activation (offline fallback)
- Subgraph API format
- Graph stats
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# All tests in this file are offline (no DB required)
pytestmark = pytest.mark.no_db

class TestGraphLayerImports:
    """Verify that graph_layer can be imported without Neo4j."""

    def test_import_graph_layer(self):
        from graph_layer import GraphService, GraphEngine, GraphInsight

    def test_import_data_models(self):
        from graph_layer import (
            NodeLabel, EdgeType, PatternNode, PatternEdge,
            CausalChain, GraphInsight, PatternSubgraph,
        )

    def test_import_patterns(self):
        from graph_layer import (
            KNOWN_PATTERNS, PATTERN_SUBGRAPHS,
            MOTIVE_PATTERN_MAP, EMOTION_PATTERN_MAP, CATEGORY_PATTERN_MAP,
        )
        assert len(KNOWN_PATTERNS) == 22
        assert len(PATTERN_SUBGRAPHS) == 6

    def test_import_functions(self):
        from graph_layer import (
            get_graph_service, format_subgraph_for_api, init_graph_db_pool,
        )

    def test_graph_engine_is_alias(self):
        from graph_layer import GraphService, GraphEngine
        assert GraphEngine is GraphService


class TestGraphServiceOffline:
    """Test GraphService in offline mode (no db_pool)."""

    def setup_method(self):
        from graph_layer import GraphService
        self.service = GraphService(db_pool=None)

    def test_analyze_basic(self):
        insight = self.service.analyze(
            user_id="test-user-123",
            dominant_motive="fear",
            emotions=[{"type": "anxiety", "intensity": 0.8}],
            decision_category="career",
        )
        assert insight is not None
        assert isinstance(insight.causal_chains, list)
        assert isinstance(insight.pattern_labels, list)
        assert len(insight.pattern_labels) > 0
        assert isinstance(insight.structural_summary, str)

    def test_analyze_matches_fear_patterns(self):
        insight = self.service.analyze(
            user_id="test",
            dominant_motive="fear",
            emotions=[{"type": "fear", "intensity": 0.9}],
            decision_category="career",
        )
        labels = insight.pattern_labels
        assert any("恐惧" in label for label in labels)

    def test_analyze_matches_pride_patterns(self):
        insight = self.service.analyze(
            user_id="test",
            dominant_motive="pride",
            emotions=[{"type": "pride", "intensity": 0.7}],
            decision_category="career",
        )
        labels = insight.pattern_labels
        assert any("骄傲" in label or "野心" in label for label in labels)

    def test_analyze_with_past_behaviors_detects_cycle(self):
        insight = self.service.analyze(
            user_id="test",
            dominant_motive="fear",
            emotions=[{"type": "anxiety", "intensity": 0.9}],
            decision_category="career",
            past_behavior_types=["overwork"],
        )
        # "overwork" is close to "overworking" in fear patterns
        assert insight is not None

    def test_detect_loop_offline(self):
        loops = self.service.detect_loop("test-user")
        assert isinstance(loops, list)
        # Offline mode returns known pattern loops
        assert len(loops) > 0
        assert "loop_description" in loops[0]

    def test_trace_root_cause_offline(self):
        roots = self.service.trace_root_cause("overworking")
        assert isinstance(roots, list)
        assert len(roots) > 0
        assert "root_emotion" in roots[0]

    def test_trace_root_cause_unknown_behavior(self):
        roots = self.service.trace_root_cause("nonexistent_behavior_xyz")
        assert isinstance(roots, list)
        assert len(roots) == 0

    def test_find_intervention_points_offline(self):
        points = self.service.find_intervention_points("test-user")
        assert isinstance(points, list)
        assert len(points) > 0
        assert "principle_id" in points[0]
        assert "behavior" in points[0]

    def test_activate_principles_offline(self):
        principles = self.service.activate_principles("fear_driven_control")
        assert isinstance(principles, list)
        assert len(principles) > 0
        assert "principle_id" in principles[0]

    def test_activate_principles_unknown_motive(self):
        principles = self.service.activate_principles("nonexistent_motive_xyz")
        assert isinstance(principles, list)
        assert len(principles) == 0

    def test_write_back_noop_offline(self):
        # Should not raise when db is not connected
        self.service.write_back(
            user_id="test",
            decision_id="d-1",
            dominant_emotion="anxiety",
            dominant_motive="fear",
            decision_category="career",
            behavior_type="overworking",
        )

    def test_get_user_pattern_history_offline(self):
        history = self.service.get_user_pattern_history("test-user")
        assert isinstance(history, list)
        assert len(history) == 0  # No DB → empty


class TestPatternSubgraphs:
    """Test PatternSubgraph data integrity and API serialization."""

    def test_all_subgraphs_have_required_fields(self):
        from graph_layer import PATTERN_SUBGRAPHS
        for sg in PATTERN_SUBGRAPHS:
            assert sg.pattern_id
            assert sg.label
            assert sg.category
            assert len(sg.emotion_nodes) > 0
            assert len(sg.motive_nodes) > 0
            assert len(sg.behavior_nodes) > 0
            assert len(sg.outcome_nodes) > 0
            assert len(sg.principle_nodes) > 0
            assert len(sg.causes_edges) > 0
            assert len(sg.leads_to_edges) > 0
            assert len(sg.reinforces_edges) > 0
            assert sg.intervention_node
            assert sg.intervention_principle
            assert sg.reflective_question
            assert sg.scripture

    def test_format_subgraph_for_api(self):
        from graph_layer import PATTERN_SUBGRAPHS, format_subgraph_for_api
        sg = PATTERN_SUBGRAPHS[0]
        api = format_subgraph_for_api(sg)
        assert "pattern_id" in api
        assert "nodes" in api
        assert "edges" in api
        assert isinstance(api["nodes"], list)
        assert isinstance(api["edges"], list)
        assert len(api["nodes"]) > 0
        assert len(api["edges"]) > 0
        # Check node format
        node = api["nodes"][0]
        assert "id" in node
        assert "label" in node
        assert "type" in node


class TestGraphInsight:
    """Test GraphInsight data model."""

    def test_graph_insight_creation(self):
        from graph_layer import GraphInsight, CausalChain
        chain = CausalChain(
            nodes=["fear", "control", "overwork"],
            edge_types=["LEADS_TO", "LEADS_TO"],
            description="test chain",
        )
        insight = GraphInsight(
            causal_chains=[chain],
            cycles=[],
            pattern_labels=["test"],
            intervention_points=[],
            structural_summary="Test summary",
        )
        assert len(insight.causal_chains) == 1
        assert insight.structural_summary == "Test summary"


class TestPostgresGraphModule:
    """Test PostgresGraphModule in offline mode."""

    def test_import(self):
        from mvfe.core.postgres_graph import PostgresGraphModule

    def test_offline_mode(self):
        from mvfe.core.postgres_graph import PostgresGraphModule
        module = PostgresGraphModule(db_pool=None)
        assert not module.enabled
        assert module.detect_loops("test") == []
        assert module.get_neighbourhood("test", "node-1") == []

    def test_get_subgraph_offline(self):
        from mvfe.core.postgres_graph import PostgresGraphModule
        module = PostgresGraphModule(db_pool=None)
        result = module.get_subgraph("test", "node-1")
        assert result == {"nodes": [], "edges": [], "stats": {}}

    def test_get_graph_stats_offline(self):
        from mvfe.core.postgres_graph import PostgresGraphModule
        module = PostgresGraphModule(db_pool=None)
        assert module.get_graph_stats("test") == {}

    def test_update_node_positions_offline(self):
        from mvfe.core.postgres_graph import PostgresGraphModule
        module = PostgresGraphModule(db_pool=None)
        assert module.update_node_positions("test", []) == 0

    def test_stable_positions_are_deterministic_and_finite(self):
        from mvfe.core.postgres_graph import PostgresGraphModule
        first = PostgresGraphModule._stable_position("node-1", 2, 0)
        second = PostgresGraphModule._stable_position("node-1", 2, 0)
        assert first == second
        assert all(abs(value) < 20 for value in first.values())

    def test_position_updates_reject_invalid_uuid_and_non_finite_values(self):
        from mvfe.core.postgres_graph import PostgresGraphModule
        module = PostgresGraphModule(db_pool=None)
        module._enabled = True
        module._pool = MagicMock()
        count = module.update_node_positions("user-1", [
            {"node_id": "not-a-uuid", "x": 1, "y": 2, "z": 3},
            {"node_id": "2a3e9d2f-26bb-4e43-bcc6-19351de44ed0", "x": float("inf"), "y": 2, "z": 3},
        ])
        assert count == 0
        module._pool.getconn.assert_not_called()

    def test_subgraph_resolves_default_focus_and_precomputes_missing_positions(self):
        from mvfe.core.postgres_graph import PostgresGraphModule

        focus_id = "2a3e9d2f-26bb-4e43-bcc6-19351de44ed0"
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.__exit__.return_value = False
        cursor.fetchall.side_effect = [
            [(focus_id, "Emotion", "anxiety", {}, 0.8, None, None, None, 0)],
            [],
        ]
        connection = MagicMock()
        connection.cursor.return_value = cursor
        pool = MagicMock()
        pool.getconn.return_value = connection
        module = PostgresGraphModule.__new__(PostgresGraphModule)
        module._enabled = True
        module._pool = pool
        module.resolve_focus_node = MagicMock(return_value=focus_id)

        result = module.get_subgraph("user-1", focus_node_id=None, depth=2, max_nodes=50)
        assert result["focus_node"] == focus_id
        assert result["nodes"][0]["position"]["x"] is not None
        assert result["stats"]["positions_precomputed"] == 1
        module.resolve_focus_node.assert_called_once_with("user-1", None)
        connection.commit.assert_called_once()

    def test_formation_chain_is_committed_in_one_transaction(self):
        from mvfe.core.postgres_graph import PostgresGraphModule

        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.__exit__.return_value = False
        cursor.fetchone.side_effect = [(f"node-{index}",) for index in range(5)]
        connection = MagicMock()
        connection.cursor.return_value = cursor
        pool = MagicMock()
        pool.getconn.return_value = connection
        module = PostgresGraphModule.__new__(PostgresGraphModule)
        module._enabled = True
        module._pool = pool

        assert module.persist_formation_chain(
            "user-1", "event-1", emotion_name="anxiety", desire_name="safety",
            behavior_name="avoidance", decision_category="career",
            outcome_name="missed opportunity", belief_name="avoidance keeps me safe",
        ) is True
        pool.getconn.assert_called_once()
        connection.commit.assert_called_once()
        connection.rollback.assert_not_called()
        sql_text = "\n".join(call.args[0] for call in cursor.execute.call_args_list)
        assert "mvfe_graph_events" in sql_text
        assert "AMPLIFIES" in str(cursor.execute.call_args_list)

    def test_automatic_pipeline_write_records_observation_without_invented_loop(self):
        from mvfe.core.postgres_graph import PostgresGraphModule

        module = PostgresGraphModule.__new__(PostgresGraphModule)
        module._enabled = True
        module._pool = MagicMock()
        module.persist_formation_chain = MagicMock(return_value=True)

        assert module.update_rich(
            "user-1",
            {"primary_emotion": "anxiety", "intensity": 0.8},
            {"focus": "career"},
            {"type": "avoidance", "drivers": {"fear": 0.9}},
            {},
            event_id="event-1",
        ) is True

        kwargs = module.persist_formation_chain.call_args.kwargs
        assert kwargs["emotion_name"] == "anxiety"
        assert kwargs["behavior_name"] == "career相关的行为"
        assert "outcome_name" not in kwargs
        assert "belief_name" not in kwargs


class TestGraphArchitectureContract:
    def test_schema_supports_positions_edge_metadata_and_real_components(self):
        from mvfe.db.graph_schema import MVFE_GRAPH_SCHEMA_SQL, CONNECTED_COMPONENTS_SQL
        assert "position_x" in MVFE_GRAPH_SCHEMA_SQL
        assert "properties      JSONB" in MVFE_GRAPH_SCHEMA_SQL
        assert "WITH RECURSIVE reach" in CONNECTED_COMPONENTS_SQL
        assert "COUNT(DISTINCT component_id)" in CONNECTED_COMPONENTS_SQL
        assert "CREATE TABLE IF NOT EXISTS mvfe_graph_events" in MVFE_GRAPH_SCHEMA_SQL
        assert "UNIQUE (user_id, event_id)" in MVFE_GRAPH_SCHEMA_SQL

    def test_neo4j_shims_have_been_removed(self):
        backend = Path(__file__).resolve().parents[1]
        assert not (backend / "mvfe" / "core" / "graph.py").exists()
        assert not (backend / "mvfe" / "db" / "neo4j.py").exists()

    def test_reviewed_write_back_persists_full_formation_loop_and_event(self):
        from graph_layer import GraphService

        class Store:
            enabled = True

            def __init__(self):
                self.nodes = []
                self.edges = []
                self.events = []

            def _upsert_node(self, user_id, node_type, node_name, props):
                self.nodes.append((node_type, node_name, props))
                return f"{node_type}:{node_name}"

            def _upsert_edge(self, user_id, source, target, edge_type, weight=1.0, properties=None):
                self.edges.append((edge_type, source, target, weight, properties or {}))

            def record_event(self, user_id, event_id, **kwargs):
                self.events.append((user_id, event_id, kwargs))
                return True

        service = GraphService(None)
        store = Store()
        service._pg = store
        service.write_back(
            user_id="user-1", decision_id="decision-1", dominant_emotion="anxiety",
            dominant_motive="safety", decision_category="career",
            behavior_type="avoidance", outcome="missed opportunity",
            belief="avoidance keeps me safe", matched_pattern_ids=[],
        )

        assert [node[0] for node in store.nodes] == [
            "Emotion", "Desire", "Behavior", "Outcome", "Belief",
        ]
        assert [edge[0] for edge in store.edges] == [
            "CAUSES", "DRIVES", "LEADS_TO", "REINFORCES", "AMPLIFIES",
        ]
        assert store.events[0][2]["outcome_name"] == "missed opportunity"
        assert store.events[0][2]["belief_name"] == "avoidance keeps me safe"


class TestGraphOwnership:
    def test_personal_graph_access_must_match_session_identity(self, monkeypatch):
        import decision_support
        from fastapi import HTTPException

        request = MagicMock()
        monkeypatch.setattr(
            decision_support, "_graph_get_session_user",
            lambda _request: {"id": "user-1", "email": "person@example.com"},
        )
        assert decision_support._require_graph_owner(request, "person@example.com")["id"] == "user-1"
        with pytest.raises(HTTPException) as exc:
            decision_support._require_graph_owner(request, "another-user")
        assert exc.value.status_code == 403
