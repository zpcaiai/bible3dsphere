"""Graph-augmented retrieval over the unified PostgreSQL formation graph.

The engine deliberately separates three evidence types in its output:
semantic principle matches, traversed graph paths, and linked scriptures.  A
caller can therefore inspect what came from retrieval instead of treating the
assembled context as an opaque spiritual verdict.
"""
from __future__ import annotations

import logging
import os
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def configured_embedding_provider() -> Optional[str]:
    """Return the real embedding provider, never the pseudo-vector fallback."""
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if (
        os.getenv("GEMINI_API_CHAT_KEY") or os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    ):
        return "gemini"
    return None


@dataclass
class GraphRAGContext:
    matched_principles: List[Dict[str, Any]] = field(default_factory=list)
    causal_paths: List[Dict[str, Any]] = field(default_factory=list)
    scriptures: List[str] = field(default_factory=list)
    context_text: str = ""
    source_stats: Dict[str, Any] = field(default_factory=dict)
    ai_synthesis: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GraphRAGSynthesis(BaseModel):
    """Bounded reflection schema; deliberately avoids diagnosis or commands."""

    structural_reflection: str = Field(default="", max_length=1200)
    possible_causal_chain: str = Field(default="", max_length=800)
    scripture_connection: str = Field(default="", max_length=800)
    next_reflection_question: str = Field(default="", max_length=500)
    uncertainty_note: str = Field(default="", max_length=500)
    requires_human_support: bool = False


class GraphRAGEngine:
    """Fuse pgvector/semantic results with PostgreSQL recursive graph paths."""

    def __init__(
        self,
        db_pool=None,
        graph_module=None,
        vector_search_fn: Optional[Callable[[str, int], List[Any]]] = None,
        embedding_fn: Optional[Callable[[str], List[float]]] = None,
    ):
        self._pool = db_pool
        self._graph = graph_module
        self._vector_search_fn = vector_search_fn
        self._embedding_fn = embedding_fn

    @property
    def enabled(self) -> bool:
        return bool(self._pool is not None and self._graph is not None and self._graph.enabled)

    def retrieve(
        self,
        user_id: str,
        query_text: str,
        top_k: int = 5,
        graph_depth: int = 2,
        precomputed_principles: Optional[List[Dict[str, Any]]] = None,
    ) -> GraphRAGContext:
        """Return semantic matches plus auditable causal paths (never conclusions)."""
        top_k = max(1, min(int(top_k), 20))
        graph_depth = max(1, min(int(graph_depth), 4))
        principles = self._normalise_many(
            precomputed_principles
            if precomputed_principles is not None
            else self._vector_search(query_text, top_k)
        )[:top_k]
        ctx = GraphRAGContext(matched_principles=principles)

        for principle in principles:
            scripture = principle.get("scripture", "")
            if scripture and scripture not in ctx.scriptures:
                ctx.scriptures.append(scripture)

        anchors: List[Dict[str, Any]] = []
        if self._graph is not None and self._graph.enabled:
            anchors = self._graph.find_semantic_anchors(
                user_id, query_text, principles=principles, limit=min(top_k, 8)
            )
            for anchor in anchors:
                graph_user_id = anchor.get("graph_user_id") or user_id
                neighbours = self._graph.get_neighbourhood(
                    graph_user_id,
                    anchor["node_id"],
                    max_depth=graph_depth,
                )
                props = anchor.get("properties") or {}
                scripture = props.get("scripture", "")
                if scripture and scripture not in ctx.scriptures:
                    ctx.scriptures.append(scripture)
                ctx.causal_paths.append({
                    "anchor_node": {
                        "id": anchor["node_id"],
                        "node_type": anchor.get("node_type", ""),
                        "node_name": anchor.get("node_name", ""),
                        "scope": "user" if graph_user_id == user_id else "canonical",
                    },
                    "anchor_principle": anchor.get("node_name", ""),
                    "anchor_score": float(anchor.get("strength", 1.0)),
                    "causal_chain": neighbours,
                    "chain_length": len(neighbours),
                })

            for loop in self._graph.detect_loops(user_id)[:2]:
                ctx.causal_paths.append({
                    "anchor_principle": f"Formation loop: {loop.get('loop_anchor', 'unknown')}",
                    "anchor_score": loop.get("loop_strength", 0.5),
                    "causal_chain": [{"path": loop.get("path", [])}],
                    "chain_length": loop.get("loop_depth", 0),
                    "is_active_loop": True,
                })

        ctx.context_text = self.build_prompt_context(ctx)
        ctx.source_stats = {
            "vector_matches": len(ctx.matched_principles),
            "semantic_anchors": len(anchors),
            "graph_paths": len(ctx.causal_paths),
            "scriptures": len(ctx.scriptures),
            "graph_depth": graph_depth,
            "graph_available": bool(self._graph is not None and self._graph.enabled),
        }
        return ctx

    def build_prompt_context(self, ctx: GraphRAGContext) -> str:
        """Format bounded, source-labelled context for an AI diagnosis prompt."""
        if not (ctx.matched_principles or ctx.causal_paths or ctx.scriptures):
            return ""
        parts: List[str] = [
            "GRAPH-AUGMENTED CONTEXT (evidence for reflection, not spiritual authority)"
        ]
        if ctx.matched_principles:
            parts.append("\n[Relevant Spiritual Principles — semantic matches]")
            for index, principle in enumerate(ctx.matched_principles[:5], 1):
                score = float(principle.get("similarity", 0.0))
                parts.append(
                    f"{index}. [{score:.2f}] {principle.get('title', 'principle')}: "
                    f"{principle.get('text', '')}"
                )
                if principle.get("scripture"):
                    parts.append(f"   Scripture: {principle['scripture']}")

        if ctx.causal_paths:
            parts.append("\n[Causal Structure — PostgreSQL graph paths]")
            for index, path in enumerate(ctx.causal_paths[:8], 1):
                if path.get("is_active_loop"):
                    parts.append(f"{index}. Active Formation Loop (possible): {path.get('anchor_principle', '')}")
                    for item in path.get("causal_chain", []):
                        if item.get("path"):
                            parts.append("   " + " -> ".join(item["path"][:8]))
                    continue
                anchor = path.get("anchor_node") or {}
                parts.append(
                    f"{index}. Anchor [{anchor.get('node_type', '')}] "
                    f"{anchor.get('node_name') or path.get('anchor_principle', '')} "
                    f"({anchor.get('scope', 'user')})"
                )
                for node in path.get("causal_chain", [])[:8]:
                    parts.append(
                        f"   -{node.get('edge_type', '')}-> "
                        f"[{node.get('node_type', '')}] {node.get('node_name', '')}"
                    )

        if ctx.scriptures:
            parts.append("\n[Supporting Scriptures — linked evidence]")
            parts.extend(f"- {scripture}" for scripture in ctx.scriptures[:8])
        return "\n".join(parts)

    def synthesize(
        self,
        user_id: str,
        query_text: str,
        ctx: GraphRAGContext,
    ) -> Dict[str, Any]:
        """Send the structured paths to the real LLM, with fail-closed provenance."""
        if not ctx.context_text:
            return {"status": "NOT_RUN", "source": "no_graph_context"}
        try:
            try:
                from backend import llm_provider, theological_safety
            except Exception:
                import llm_provider  # type: ignore
                import theological_safety  # type: ignore

            configured = getattr(llm_provider, "_real_configured", lambda: False)()
            if not configured:
                return {
                    "status": "NOT_RUN",
                    "source": "real_llm_not_configured",
                    "note": "Graph paths remain available as auditable retrieval evidence.",
                }

            system_prompt = (
                "你是一个基督教灵性形成反思助手。只依据给出的语义检索与 PostgreSQL 图路径，"
                "用可能性语言总结结构，不得宣称神的旨意，不得定义用户身份，不得作医学诊断，"
                "不得羞辱或操控。经文必须来自已提供的 linked scriptures；若证据不足要明确说不确定。"
                "输出一个开放式反思问题，保留用户自主，并在需要时建议联系真实的牧者、可信同伴或专业帮助。"
            )
            model = llm_provider.generate_json(
                system_prompt,
                {
                    "user_question": query_text[:1000],
                    "graph_augmented_context": ctx.context_text[:9000],
                    "evidence_counts": ctx.source_stats,
                },
                GraphRAGSynthesis,
                temperature=0.2,
                max_tokens=900,
                email=user_id if "@" in user_id else None,
                agent_name="GraphRAGFormationAgent",
                skill_name="sfds.graph_rag",
            )
            result = model.model_dump()
            crisis = theological_safety.detect_crisis(query_text)
            if crisis.get("risk_level") in ("high", "critical"):
                result["requires_human_support"] = True
            review = theological_safety.TheologicalSafetyService().review(
                str(result),
                agent_name="GraphRAGFormationAgent",
                skill_name="sfds.graph_rag",
                email=user_id if "@" in user_id else None,
                user_risk_hint=crisis.get("risk_level", "low"),
            )
            if not review.ok:
                return {
                    "status": "BLOCKED",
                    "source": "theological_safety",
                    "safety_verdict": review.verdict,
                }
            return {
                "status": "COMPLETED",
                "source": "real_llm_graph_rag",
                "safety_verdict": review.verdict,
                **result,
            }
        except Exception as exc:
            logger.warning("[graph-rag] AI synthesis unavailable: %s", exc)
            return {"status": "NOT_RUN", "source": "llm_error", "error": str(exc)[:200]}

    def _vector_search(self, query_text: str, top_k: int) -> List[Any]:
        if self._vector_search_fn is not None:
            try:
                return self._vector_search_fn(query_text, top_k) or []
            except Exception as exc:
                logger.warning("[graph-rag] injected vector search failed: %s", exc)
                return []
        if self._pool is None:
            return []

        conn = self._pool.getconn()
        try:
            try:
                provider_name = configured_embedding_provider()
                if not provider_name:
                    return self._lexical_search(conn, query_text, top_k)
                if self._embedding_fn is None:
                    from mvfe.db import vector as vector_module
                    self._embedding_fn = vector_module.get_embedding_fn()
                embedding = self._embedding_fn(query_text)
                if provider_name == "gemini":
                    from mvfe.db import vector as vector_module
                    if vector_module._gemini_embed_failed:
                        return self._lexical_search(conn, query_text, top_k)
                vector_literal = "[" + ",".join(f"{float(value):.9g}" for value in embedding) + "]"
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, principle_text, scripture_reference, category,
                               1 - (embedding <=> %s::vector) AS similarity
                        FROM sfds_spiritual_principles
                        WHERE COALESCE(is_active, TRUE)=TRUE
                          AND embedding IS NOT NULL
                          AND embedding_provider=%s
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                        """,
                        (vector_literal, provider_name, vector_literal, top_k),
                    )
                    rows = cur.fetchall()
                    if rows:
                        return [
                            {
                                "id": str(row[0]), "title": row[3] or "principle",
                                "text": row[1] or "", "scripture": row[2] or "",
                                "category": row[3] or "general",
                                "similarity": float(row[4] or 0.0),
                            }
                            for row in rows
                        ]
                    return self._lexical_search(conn, query_text, top_k)
            except Exception as exc:
                conn.rollback()
                logger.warning("[graph-rag] pgvector search degraded to lexical search: %s", exc)
                return self._lexical_search(conn, query_text, top_k)
        except Exception as exc:
            conn.rollback()
            logger.warning("[graph-rag] semantic retrieval unavailable: %s", exc)
            return []
        finally:
            self._pool.putconn(conn)

    @staticmethod
    def _lexical_search(conn, query_text: str, top_k: int) -> List[Dict[str, Any]]:
        aliases = {
            "焦虑": ["anxiety", "fear", "忧虑", "挂虑"],
            "恐惧": ["fear", "害怕", "惧怕"],
            "逃避": ["avoidance", "回避"],
            "控制": ["control", "交托"],
            "羞耻": ["shame", "羞愧"],
            "愤怒": ["anger", "饶恕"],
            "骄傲": ["pride", "humility", "谦卑"],
            "孤独": ["loneliness", "群体"],
        }
        normalized = "".join(
            char if char.isalnum() or "\u3400" <= char <= "\u9fff" else " "
            for char in (query_text or "").lower()
        )
        terms = {term[:80] for term in normalized.split() if len(term) >= 2}
        for marker, values in aliases.items():
            if marker in normalized:
                terms.update(values)
        patterns = [f"%{term}%" for term in sorted(terms)[:24]]
        if not patterns:
            return []
        pattern_text = chr(31).join(patterns)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, principle_text, scripture_reference, category
                FROM sfds_spiritual_principles
                WHERE COALESCE(is_active, TRUE)=TRUE
                  AND EXISTS (
                      SELECT 1
                      FROM unnest(string_to_array(%s, CHR(31))) AS search(pattern)
                      WHERE principle_text ILIKE search.pattern
                         OR COALESCE(category, '') ILIKE search.pattern
                  )
                ORDER BY updated_at DESC, created_at DESC
                LIMIT %s
                """,
                (pattern_text, top_k),
            )
            return [
                {
                    "id": str(row[0]), "title": row[3] or "principle",
                    "text": row[1] or "", "scripture": row[2] or "",
                    "category": row[3] or "general", "similarity": 0.25,
                    "retrieval_mode": "lexical_fallback",
                }
                for row in cur.fetchall()
            ]

    @classmethod
    def _normalise_many(cls, values: List[Any]) -> List[Dict[str, Any]]:
        return [item for item in (cls._normalise(value) for value in values or []) if item]

    @staticmethod
    def _normalise(value: Any) -> Dict[str, Any]:
        if is_dataclass(value):
            value = asdict(value)
        elif not isinstance(value, dict):
            value = getattr(value, "__dict__", {})
        if not value:
            return {}
        return {
            "id": str(value.get("id") or value.get("principle_id") or ""),
            "principle_id": str(value.get("principle_id") or value.get("id") or ""),
            "title": value.get("title") or value.get("category") or value.get("principle_id") or "principle",
            "text": value.get("text") or value.get("content") or value.get("principle_text") or "",
            "scripture": value.get("scripture") or value.get("scripture_reference") or "",
            "category": value.get("category") or "general",
            "similarity": float(value.get("similarity", value.get("relevance_score", value.get("score", 0.0))) or 0.0),
        }


_rag_engine: Optional[GraphRAGEngine] = None


def get_rag_engine() -> GraphRAGEngine:
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = GraphRAGEngine()
    return _rag_engine


def init_rag_engine(db_pool, graph_module=None, **kwargs) -> GraphRAGEngine:
    global _rag_engine
    _rag_engine = GraphRAGEngine(db_pool=db_pool, graph_module=graph_module, **kwargs)
    return _rag_engine
