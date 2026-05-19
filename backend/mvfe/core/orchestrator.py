"""
ORCHESTRATOR (CRITICAL)
Deterministic pipeline: input → extraction → formation → reflection → persistence.
"""
import logging
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Optional, Dict, Any

from .context import ContextExtractor
from .emotion import EmotionExtractor, EmotionState
from .attention import AttentionExtractor, AttentionState
from .decision import DecisionClassifier, DecisionState
from .memory import MemoryStore
from .formation import FormationEngine, FormationResult
from .reflection import ReflectionGenerator, ReflectionOutput
from .graph import GraphModule
from .critic import CriticAgent
from .governance import ConstitutionLayer

logger = logging.getLogger(__name__)


class ProcessResult:
    """Full pipeline output."""

    def __init__(
        self,
        input_text: str,
        context: dict,
        emotion: dict,
        attention: dict,
        decision: dict,
        memories: list,
        formation: dict,
        graph_insight: dict,
        critic: dict,
        governance: dict,
        reflection: dict,
        event_id: str,
        timestamp: str,
    ):
        self.input_text = input_text
        self.context = context
        self.emotion = emotion
        self.attention = attention
        self.decision = decision
        self.memories = memories
        self.formation = formation
        self.graph_insight = graph_insight
        self.critic = critic
        self.governance = governance
        self.reflection = reflection
        self.event_id = event_id
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "input_text": self.input_text[:200],
            "context": self.context,
            "emotion": self.emotion,
            "attention": self.attention,
            "decision": self.decision,
            "memories": self.memories,
            "formation": self.formation,
            "graph_insight": self.graph_insight,
            "critic": self.critic,
            "governance": self.governance,
            "reflection": self.reflection,
        }


class Orchestrator:
    """
    Deterministic pipeline execution.

    FLOW (EXACT ORDER):
    1. parse input
    2. context framing
    3. emotion extraction
    4. attention extraction
    5. decision classification
    6. memory retrieval
    7. graph update
    8. formation computation
    9. critic challenge
    10. reflection generation
    11. governance audit
    12. store everything
    13. return response
    """

    def __init__(
        self,
        context_extractor: ContextExtractor,
        emotion_extractor: EmotionExtractor,
        attention_extractor: AttentionExtractor,
        decision_classifier: DecisionClassifier,
        memory_store: Optional[MemoryStore],
        formation_engine: FormationEngine,
        critic_agent: CriticAgent,
        reflection_generator: ReflectionGenerator,
        governance_layer: ConstitutionLayer,
        graph_module: GraphModule,
        db_pool=None,
    ):
        self._context = context_extractor
        self._emotion = emotion_extractor
        self._attention = attention_extractor
        self._decision = decision_classifier
        self._memory = memory_store
        self._formation = formation_engine
        self._critic = critic_agent
        self._reflection = reflection_generator
        self._governance = governance_layer
        self._graph = graph_module
        self._db_pool = db_pool

    def process(self, user_id: str, text: str) -> ProcessResult:
        """Execute the full pipeline."""
        event_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        user_id_str = str(user_id)

        print(f"[orchestrator-NEW] process() called user={user_id_str[:8]} text_len={len(text)}", flush=True)
        logger.info(f"[orchestrator] START event={event_id[:8]} user={user_id_str[:8]}")

        # 1. Parse input
        input_text = text.strip()

        # 2. Context framing
        context_state = self._context.extract(input_text)
        context_dict = self._context.to_dict(context_state)

        # 3. Emotion extraction
        emotion_state = self._emotion.extract(input_text)
        emotion_dict = self._emotion.to_dict(emotion_state)

        # 4. Attention extraction
        attention_state = self._attention.extract(input_text)
        attention_dict = self._attention.to_dict(attention_state)

        # 5. Decision classification
        decision_state = self._decision.extract(input_text)
        decision_dict = self._decision.to_dict(decision_state)

        # 6. Memory retrieval
        memories = []
        if self._memory:
            try:
                mem_items = self._memory.search(user_id, input_text, top_k=5)
                memories = [
                    {"content": m.content, "similarity": m.similarity, "timestamp": m.timestamp}
                    for m in mem_items
                ]
            except Exception as e:
                logger.warning(f"[orchestrator] memory search failed: {e}")

        # 7. Graph update (rich causal loop)
        self._graph.update(user_id, emotion_dict, attention_dict, decision_dict)
        self._graph.update_rich(user_id, emotion_dict, attention_dict, decision_dict, context_dict)

        # 7b. Graph-based formation insight (loop detection)
        print(f"[orchestrator] calling get_formation_insight: emotion={emotion_dict}, decision_type={decision_dict.get('type')}, fear={decision_dict.get('drivers',{}).get('fear')}", flush=True)
        graph_insight = self._graph.get_formation_insight(user_id, emotion_dict, decision_dict)
        print(f"[orchestrator] graph_insight result: {graph_insight}", flush=True)

        # 8. Formation computation
        formation_result = self._formation.compute(
            user_id, emotion_state, attention_state, decision_state
        )
        formation_dict = self._formation.to_dict(formation_result)

        # 9. Reflection generation (first pass)
        reflection_output = self._reflection.generate(
            emotion_state, attention_state, decision_state, formation_result
        )
        reflection_text = reflection_output.state_interpretation

        # 10. Critic challenge — adversarial review
        critic_report = self._critic.challenge(
            input_text, reflection_text, emotion_dict, attention_dict, decision_dict, formation_dict
        )
        critic_dict = self._critic.to_dict(critic_report)

        # Adjust reflection confidence based on critic
        adjusted_confidence = self._critic.adjust_confidence(
            1.0 - emotion_state.uncertainty, critic_report
        )
        logger.info(f"[orchestrator] critic confidence adjusted to {adjusted_confidence:.3f}")

        # 11. Governance audit
        governance_report = self._governance.audit(reflection_text, formation_dict)
        governance_dict = {
            "passed": governance_report.passed,
            "violations": governance_report.violations,
            "warnings": governance_report.warnings,
            "formation_danger": governance_report.formation_danger_flag,
        }
        if not governance_report.passed:
            reflection_output.state_interpretation = self._governance.sanitize(
                reflection_text, governance_report
            )
            logger.warning(f"[orchestrator] governance violations: {governance_report.violations}")

        reflection_dict = self._reflection.to_dict(reflection_output)

        # 12. Store everything
        self._persist(
            event_id=event_id,
            user_id=user_id,
            input_text=input_text,
            context=context_dict,
            emotion=emotion_dict,
            attention=attention_dict,
            decision=decision_dict,
            formation=formation_dict,
            graph_insight=graph_insight,
            timestamp=timestamp,
        )

        # Store as memory for future retrieval
        if self._memory:
            try:
                self._memory.insert(user_id, input_text)
            except Exception as e:
                logger.warning(f"[orchestrator] memory insert failed: {e}")

        # 13. Return response
        result = ProcessResult(
            input_text=input_text,
            context=context_dict,
            emotion=emotion_dict,
            attention=attention_dict,
            decision=decision_dict,
            memories=memories,
            formation=formation_dict,
            graph_insight=graph_insight,
            critic=critic_dict,
            governance=governance_dict,
            reflection=reflection_dict,
            event_id=event_id,
            timestamp=timestamp,
        )
        logger.info(f"[orchestrator] DONE event={event_id[:8]}")
        return result

    def _persist(self, **kwargs):
        """Persist event and formation state to database."""
        if not self._db_pool:
            return
        import json

        conn = self._db_pool.getconn()
        try:
            with conn.cursor() as cur:
                # Insert event
                cur.execute(
                    """INSERT INTO mvfe_events (id, user_id, type, payload, created_at)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (
                        kwargs["event_id"],
                        kwargs["user_id"],
                        "process",
                        json.dumps({
                            "input": kwargs["input_text"][:500],
                            "emotion": kwargs["emotion"],
                            "attention": kwargs["attention"],
                            "decision": kwargs["decision"],
                            "formation_score": kwargs.get("formation", {}).get("formation_score"),
                            "drift_score": kwargs.get("formation", {}).get("drift_score"),
                            "stability_score": kwargs.get("formation", {}).get("stability_score"),
                            "formation": kwargs.get("formation"),
                            "graph_insight": kwargs.get("graph_insight"),
                            "reflection": kwargs.get("reflection"),
                        }),
                        kwargs["timestamp"],
                    ),
                )

                # Upsert formation state with graph insight
                graph = kwargs.get("graph_insight", {})
                cur.execute(
                    """INSERT INTO mvfe_formation_state
                       (user_id, emotion, attention, decision, context, formation_score, drift_score, stability_score, trajectory_vector, loop_detected, loop_type, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (user_id) DO UPDATE SET
                         emotion = EXCLUDED.emotion,
                         attention = EXCLUDED.attention,
                         decision = EXCLUDED.decision,
                         context = EXCLUDED.context,
                         formation_score = EXCLUDED.formation_score,
                         drift_score = EXCLUDED.drift_score,
                         stability_score = EXCLUDED.stability_score,
                         trajectory_vector = EXCLUDED.trajectory_vector,
                         loop_detected = EXCLUDED.loop_detected,
                         loop_type = EXCLUDED.loop_type,
                         updated_at = EXCLUDED.updated_at""",
                    (
                        kwargs["user_id"],
                        json.dumps(kwargs["emotion"]),
                        json.dumps(kwargs["attention"]),
                        json.dumps(kwargs["decision"]),
                        json.dumps(kwargs.get("context", {})),
                        kwargs["formation"]["formation_score"],
                        kwargs["formation"]["drift_score"],
                        kwargs["formation"].get("stability_score", 0.0),
                        json.dumps({"graph": graph}),
                        graph.get("loop_detected", False),
                        graph.get("loop_type"),
                        kwargs["timestamp"],
                    ),
                )
                # Insert loop history record for time-series analysis
                gi = kwargs.get("graph_insight", {})
                em = kwargs.get("emotion", {})
                dc = kwargs.get("decision", {})
                try:
                    cur.execute(
                        """INSERT INTO mvfe_loop_history
                           (user_id, loop_detected, loop_type, loop_strength,
                            emotion_primary, emotion_intensity, decision_type, recorded_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            kwargs["user_id"],
                            gi.get("loop_detected", False),
                            gi.get("loop_type"),
                            gi.get("loop_strength", 0.0),
                            em.get("primary_emotion"),
                            em.get("intensity"),
                            dc.get("type"),
                            kwargs["timestamp"],
                        ),
                    )
                except Exception as loop_err:
                    logger.warning(f"[orchestrator] loop_history insert skipped: {loop_err}")

                conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[orchestrator] persist failed: {e}")
        finally:
            self._db_pool.putconn(conn)
