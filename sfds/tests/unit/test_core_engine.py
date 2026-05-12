"""
Unit Tests — Core Engine (with mocked services)
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.core_engine.engine import CoreEngine
from packages.shared_types.decision import DecisionRequest


def make_req(**kwargs):
    defaults = {"user_id": "test_user", "description": "Should I take this job?"}
    defaults.update(kwargs)
    return DecisionRequest(**defaults)


@pytest.fixture
def mock_engine():
    graph  = AsyncMock()
    graph.analyze.return_value = {"loops": [], "pattern_labels": [], "pattern_categories": []}
    vector = AsyncMock()
    vector.get_principles.return_value = {"principles": []}
    time   = AsyncMock()
    time.analyze.return_value = {"trends": {}}

    from backend.formation_engine import FormationEngine
    formation = FormationEngine(db_pool=None)

    return CoreEngine(graph=graph, vector=vector, timeseries=time, formation=formation)


class TestCoreEnginePipeline:
    @pytest.mark.asyncio
    async def test_analyze_returns_all_layers(self, mock_engine):
        req    = make_req()
        result = await mock_engine.analyze(req)

        assert "semantic"   in result
        assert "structural" in result
        assert "temporal"   in result
        assert "formation"  in result
        assert result["user_id"] == "test_user"
        assert result["schema"]  == "v3.1"

    @pytest.mark.asyncio
    async def test_graceful_degradation_on_graph_failure(self, mock_engine):
        mock_engine.graph.analyze.side_effect = RuntimeError("Neo4j down")
        req    = make_req()
        result = await mock_engine.analyze(req)
        assert result["structural"] == {}
        assert "formation" in result   # formation still runs

    @pytest.mark.asyncio
    async def test_formation_always_present(self, mock_engine):
        req = make_req(emotions=[{"type": "fear", "intensity": 8}])
        result = await mock_engine.analyze(req)
        assert "state_vector" in result["formation"] or "formation" in result
