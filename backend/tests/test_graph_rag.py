#!/usr/bin/env python3
"""
Tests for GraphRAG (Graph-Augmented Retrieval) engine.

Validates:
- GraphRAGEngine initialization
- Context building and formatting
- Offline mode graceful degradation
"""

import pytest
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

pytestmark = pytest.mark.no_db

class TestGraphRAGImports:
    """Verify GraphRAG module imports cleanly."""

    def test_import_graph_rag(self):
        from graph_rag import GraphRAGEngine, GraphRAGContext

    def test_import_functions(self):
        from graph_rag import get_rag_engine, init_rag_engine


class TestGraphRAGEngineOffline:
    """Test GraphRAGEngine in offline mode (no db_pool)."""

    def setup_method(self):
        from graph_rag import GraphRAGEngine
        self.engine = GraphRAGEngine(db_pool=None)

    def test_not_enabled(self):
        assert not self.engine.enabled

    def test_retrieve_returns_empty_context(self):
        ctx = self.engine.retrieve("user-1", "anxiety about career", top_k=3)
        assert ctx.context_text == ""
        assert ctx.matched_principles == []
        assert ctx.causal_paths == []

    def test_build_prompt_context_empty(self):
        from graph_rag import GraphRAGContext
        ctx = GraphRAGContext()
        text = self.engine.build_prompt_context(ctx)
        assert text == ""


class TestGraphRAGContextBuilding:
    """Test context text formatting."""

    def test_context_with_principles(self):
        from graph_rag import GraphRAGEngine, GraphRAGContext
        engine = GraphRAGEngine(db_pool=None)
        ctx = GraphRAGContext(
            matched_principles=[
                {"title": "Rest Before Decision", "text": "Don't decide when tired",
                 "similarity": 0.85, "scripture": "Matthew 6:25-27"},
                {"title": "Trust Over Control", "text": "Let go of control",
                 "similarity": 0.72},
            ]
        )
        text = engine.build_prompt_context(ctx)
        assert "Relevant Spiritual Principles" in text
        assert "Rest Before Decision" in text
        assert "0.85" in text
        assert "Matthew 6:25-27" in text

    def test_context_with_causal_paths(self):
        from graph_rag import GraphRAGEngine, GraphRAGContext
        engine = GraphRAGEngine(db_pool=None)
        ctx = GraphRAGContext(
            causal_paths=[{
                "anchor_principle": "test_principle",
                "anchor_score": 0.8,
                "causal_chain": [
                    {"node_type": "Emotion", "node_name": "anxiety", "edge_type": "CAUSES"},
                    {"node_type": "Behavior", "node_name": "overworking", "edge_type": "LEADS_TO"},
                ],
                "chain_length": 2,
            }]
        )
        text = engine.build_prompt_context(ctx)
        assert "Causal Structure" in text
        assert "test_principle" in text

    def test_context_with_active_loop(self):
        from graph_rag import GraphRAGEngine, GraphRAGContext
        engine = GraphRAGEngine(db_pool=None)
        ctx = GraphRAGContext(
            causal_paths=[{
                "anchor_principle": "Formation loop: anxiety",
                "anchor_score": 0.7,
                "causal_chain": [{"path": ["Emotion:anxiety", "Desire:control", "Behavior:overwork"]}],
                "chain_length": 3,
                "is_active_loop": True,
            }]
        )
        text = engine.build_prompt_context(ctx)
        assert "Active Formation Loop" in text

    def test_context_with_scriptures(self):
        from graph_rag import GraphRAGEngine, GraphRAGContext
        engine = GraphRAGEngine(db_pool=None)
        ctx = GraphRAGContext(
            scriptures=["Matthew 6:25-27", "Psalm 23:1"]
        )
        text = engine.build_prompt_context(ctx)
        assert "Supporting Scriptures" in text
        assert "Matthew 6:25-27" in text


class TestGraphRAGSingleton:
    """Test module-level singleton management."""

    def test_get_rag_engine_returns_instance(self):
        from graph_rag import get_rag_engine
        engine = get_rag_engine()
        assert engine is not None

    def test_init_rag_engine(self):
        from graph_rag import init_rag_engine
        engine = init_rag_engine(db_pool=None)
        assert engine is not None
        assert not engine.enabled


class TestGraphRAGFusion:
    """Exercise semantic-result normalisation and PostgreSQL path fusion."""

    @dataclass
    class Principle:
        id: str
        principle_text: str
        scripture_reference: str
        category: str
        relevance_score: float

    class Graph:
        enabled = True

        def find_semantic_anchors(self, user_id, query_text, principles, limit):
            assert principles[0]["text"]
            return [{
                "node_id": "anchor-1", "graph_user_id": "__system__",
                "node_type": "Principle", "node_name": "trust_over_control",
                "properties": {"scripture": "马太福音 6:25-27"}, "strength": 0.9,
            }]

        def get_neighbourhood(self, user_id, node_id, max_depth):
            assert user_id == "__system__"
            assert max_depth == 2
            return [{
                "source": "anchor-1", "target": "behavior-1", "depth": 1,
                "edge_type": "BREAKS", "node_name": "avoidance", "node_type": "Behavior",
            }]

        def detect_loops(self, user_id):
            return [{
                "loop_anchor": "anxiety", "loop_strength": 0.72,
                "loop_depth": 4, "path": ["Emotion:anxiety", "Behavior:avoidance"],
            }]

    def test_fuses_dataclass_semantics_graph_paths_and_scripture(self):
        from graph_rag import GraphRAGEngine
        principle = self.Principle(
            id="p1", principle_text="在焦虑中学习交托",
            scripture_reference="腓立比书 4:6-7", category="anxiety",
            relevance_score=0.88,
        )
        engine = GraphRAGEngine(
            db_pool=object(), graph_module=self.Graph(),
            vector_search_fn=lambda query, top_k: [principle],
        )
        ctx = engine.retrieve("user-1", "焦虑与逃避", top_k=3, graph_depth=2)

        assert ctx.matched_principles[0]["id"] == "p1"
        assert ctx.source_stats["semantic_anchors"] == 1
        assert ctx.source_stats["graph_paths"] == 2
        assert "腓立比书 4:6-7" in ctx.scriptures
        assert "马太福音 6:25-27" in ctx.scriptures
        assert "BREAKS" in ctx.context_text
        assert "Active Formation Loop" in ctx.context_text

    def test_precomputed_principles_avoid_a_second_vector_query(self):
        from graph_rag import GraphRAGEngine
        vector_search = MagicMock(return_value=[])
        engine = GraphRAGEngine(
            db_pool=object(), graph_module=self.Graph(), vector_search_fn=vector_search,
        )
        ctx = engine.retrieve(
            "user-1", "焦虑", precomputed_principles=[{
                "id": "p2", "principle_text": "不要忧虑",
                "scripture_reference": "马太福音 6:34", "relevance_score": 0.8,
            }],
        )
        vector_search.assert_not_called()
        assert ctx.matched_principles[0]["text"] == "不要忧虑"

    def test_ai_synthesis_is_explicitly_not_run_without_real_provider(self, monkeypatch):
        import backend.llm_provider as llm_provider
        from graph_rag import GraphRAGContext, GraphRAGEngine

        monkeypatch.setattr(llm_provider, "_real_configured", lambda: False)
        engine = GraphRAGEngine(db_pool=object(), graph_module=self.Graph())
        result = engine.synthesize(
            "user-1", "焦虑与逃避",
            GraphRAGContext(context_text="[Causal Structure] anxiety -> avoidance"),
        )
        assert result["status"] == "NOT_RUN"
        assert result["source"] == "real_llm_not_configured"

    def test_missing_real_embedding_provider_uses_lexical_retrieval(self, monkeypatch):
        from graph_rag import GraphRAGEngine

        for key in (
            "OPENAI_API_KEY", "GEMINI_API_CHAT_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY",
        ):
            monkeypatch.delenv(key, raising=False)
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.__exit__.return_value = False
        cursor.fetchall.return_value = [
            ("p1", "在焦虑中学习交托", "腓立比书 4:6-7", "焦虑"),
        ]
        connection = MagicMock()
        connection.cursor.return_value = cursor
        pool = MagicMock()
        pool.getconn.return_value = connection

        rows = GraphRAGEngine(db_pool=pool)._vector_search("焦虑", 3)

        assert rows[0]["retrieval_mode"] == "lexical_fallback"
        assert "<=>" not in cursor.execute.call_args.args[0]
        pool.putconn.assert_called_once_with(connection)


def test_formation_pipeline_exposes_graph_rag_context(monkeypatch):
    from formation_pipeline import FormationPipeline, PipelineInput
    from graph_rag import GraphRAGContext

    class Rag:
        def retrieve(self, **kwargs):
            assert kwargs["graph_depth"] == 2
            return GraphRAGContext(
                matched_principles=[{"id": "p1", "text": "交托", "similarity": 0.9}],
                context_text="auditable graph path",
                source_stats={"graph_paths": 1},
            )

        def synthesize(self, user_id, query_text, ctx):
            return {"status": "NOT_RUN", "source": "test"}

    class Failing:
        def analyze(self, *args, **kwargs):
            raise RuntimeError("optional layer unavailable")

        def analyze_sync(self, *args, **kwargs):
            raise RuntimeError("optional layer unavailable")

    monkeypatch.setattr("formation_pipeline.get_formation_engine", lambda pool: Failing())
    pipeline = FormationPipeline(
        graph_service=Failing(), temporal_engine=Failing(), v2_engine=Failing(),
        reasoning_engine=Failing(), graph_rag_engine=Rag(), db_pool=None,
    )
    output = pipeline.run(PipelineInput(
        user_id="user-1", title="焦虑与逃避",
        semantic_principles=[{"id": "p1", "principle_text": "交托"}],
    ))

    assert output.graph_rag["context_text"] == "auditable graph path"
    layer = next(item for item in output.pipeline_layers if item.layer == "graph_rag")
    assert layer.success is True
