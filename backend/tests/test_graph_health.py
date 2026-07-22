#!/usr/bin/env python3
"""
Tests for Graph Health Checker (Phase 4 data governance).

Validates:
- GraphHealthChecker initialization
- Offline mode graceful degradation
- GraphHealthReport data model
- Edge weight update function signature
"""

import pytest
from unittest.mock import MagicMock

pytestmark = pytest.mark.no_db

class TestGraphHealthImports:
    """Verify graph_health module imports cleanly."""

    def test_import_health_checker(self):
        from graph_health import GraphHealthChecker, GraphHealthReport

    def test_import_functions(self):
        from graph_health import (
            get_health_checker, init_health_checker,
            update_edge_weight_on_interaction,
        )


class TestGraphHealthCheckerOffline:
    """Test GraphHealthChecker in offline mode."""

    def setup_method(self):
        from graph_health import GraphHealthChecker
        self.checker = GraphHealthChecker(db_pool=None)

    def test_not_enabled(self):
        assert not self.checker.enabled

    def test_find_isolated_nodes_offline(self):
        result = self.checker.find_isolated_nodes()
        assert result == []

    def test_find_dangling_edges_offline(self):
        result = self.checker.find_dangling_edges()
        assert result == []

    def test_count_components_offline(self):
        result = self.checker.count_connected_components("test-user")
        assert result == 0

    def test_auto_repair_offline(self):
        result = self.checker.auto_repair()
        assert result["repaired"] is False

    def test_full_report_offline(self):
        report = self.checker.full_report()
        assert report.status == "disabled"
        assert report.total_nodes == 0


class TestGraphHealthReport:
    """Test GraphHealthReport data model."""

    def test_to_dict(self):
        from graph_health import GraphHealthReport
        report = GraphHealthReport(
            timestamp="2025-01-01T00:00:00Z",
            total_nodes=100,
            total_edges=200,
            isolated_nodes=[{"id": "n1", "node_type": "test", "node_name": "test", "user_id": "u1"}],
            dangling_edges=[],
            connected_components=3,
            status="healthy",
        )
        d = report.to_dict()
        assert d["total_nodes"] == 100
        assert d["total_edges"] == 200
        assert d["isolated_node_count"] == 1
        assert d["dangling_edge_count"] == 0
        assert d["connected_components"] == 3
        assert d["status"] == "healthy"

    def test_to_dict_caps_isolated_nodes(self):
        from graph_health import GraphHealthReport
        many_nodes = [{"id": f"n{i}", "node_type": "t", "node_name": f"n{i}", "user_id": "u"} for i in range(30)]
        report = GraphHealthReport(isolated_nodes=many_nodes)
        d = report.to_dict()
        assert len(d["isolated_nodes"]) == 20  # Capped at 20
        assert d["isolated_node_count"] == 30


class TestEdgeWeightUpdate:
    """Test edge weight update function."""

    def test_no_pool_returns_false(self):
        from graph_health import update_edge_weight_on_interaction
        result = update_edge_weight_on_interaction(
            None, "user-1", "source-1", "target-1", "click"
        )
        assert result is False

    def test_interaction_type_weights(self):
        # Verify the weight map exists (tested via import, no DB needed)
        from graph_health import update_edge_weight_on_interaction
        # Just verify the function exists and handles None pool
        for itype in ["click", "hover", "expand", "bookmark", "unknown"]:
            result = update_edge_weight_on_interaction(None, "u", "s", "t", itype)
            assert result is False

    def test_click_updates_only_the_users_exact_edge(self):
        from graph_health import update_edge_weight_on_interaction

        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.__exit__.return_value = False
        cursor.fetchone.return_value = ("edge-id",)
        connection = MagicMock()
        connection.cursor.return_value = cursor
        pool = MagicMock()
        pool.getconn.return_value = connection

        assert update_edge_weight_on_interaction(
            pool, "user-1", "source-1", "target-1", "click"
        ) is True
        sql, params = cursor.execute.call_args.args
        assert "user_id = %s" in sql
        assert "source_id = %s::uuid" in sql
        assert params == (0.1, "user-1", "source-1", "target-1")
        connection.commit.assert_called_once()


class TestGraphHealthRepair:
    def test_auto_repair_scopes_changes_and_only_restores_deterministic_edges(self):
        from graph_health import GraphHealthChecker

        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.__exit__.return_value = False
        rowcounts = iter([2, 1, 3])

        def execute(*_args, **_kwargs):
            cursor.rowcount = next(rowcounts)

        cursor.execute.side_effect = execute
        connection = MagicMock()
        connection.cursor.return_value = cursor
        pool = MagicMock()
        pool.getconn.return_value = connection

        result = GraphHealthChecker(pool).auto_repair("user-1")
        assert result["dangling_edges_removed"] == 2
        assert result["deterministic_edges_restored"] == 1
        assert result["isolated_nodes_marked"] == 3
        assert result["repairs_made"] == 6
        assert cursor.execute.call_args_list[0].args[1] == ("user-1", "user-1")
        assert cursor.execute.call_args_list[1].args[1] == ("user-1", "user-1")
        assert "MATCHED_PATTERN" in cursor.execute.call_args_list[1].args[0]
        assert "auto_repaired" in cursor.execute.call_args_list[1].args[0]


class TestGraphHealthSingleton:
    """Test module-level singleton management."""

    def test_get_health_checker(self):
        from graph_health import get_health_checker
        checker = get_health_checker()
        assert checker is not None

    def test_init_health_checker(self):
        from graph_health import init_health_checker
        checker = init_health_checker(db_pool=None)
        assert checker is not None
        assert not checker.enabled
