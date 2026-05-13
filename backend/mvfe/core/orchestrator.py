"""
ORCHESTRATOR (CRITICAL)
Deterministic pipeline: input → extraction → formation → reflection → persistence.
"""
import logging
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Optional, Dict, Any

from .emotion import EmotionExtractor, EmotionState
from .attention import AttentionExtractor, AttentionState
from .decision import DecisionClassifier, DecisionState
from .memory import MemoryStore
from .formation import FormationEngine, FormationResult
from .reflection import ReflectionGenerator, ReflectionOutput
from .graph import GraphModule

logger = logging.getLogger(__name__)


class ProcessResult:
    """Full pipeline output."""

    def __init__(
        self,
        input_text: str,
        emotion: dict,
        attention: dict,
        decision: dict,
        memories: list,
        formation: dict,
        reflection: dict,
        event_id: str,
        timestamp: str,
    ):
        self.input_text = input_text
        self.emotion = emotion
        self.attention = attention
        self.decision = decision
        self.memories = memories
        self.formation = formation
        self.reflection = reflection
        self.event_id = event_id
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "input_text": self.input_text[:200],
            "emotion": self.emotion,
            "attention": self.attention,
            "decision": self.decision,
            "memories": self.memories,
            "formation": self.formation,
            "reflection": self.reflection,
        }


class Orchestrator:
    """
    Deterministic pipeline execution.

    FLOW (EXACT ORDER):
    1. parse input
    2. emotion extraction
    3. attention extraction
    4. decision classification
    5. memory retrieval
    6. graph update
    7. formation computation
    8. reflection generation
    9. store everything
    10. return response
    """

    def __init__(
        self,
        emotion_extractor: EmotionExtractor,
        attention_extractor: AttentionExtractor,
        decision_classifier: DecisionClassifier,
        memory_store: Optional[MemoryStore],
        formation_engine: FormationEngine,
        reflection_generator: ReflectionGenerator,
        graph_module: GraphModule,
        db_pool=None,
    ):
        self._emotion = emotion_extractor
        self._attention = attention_extractor
        self._decision = decision_classifier
        self._memory = memory_store
        self._formation = formation_engine
        self._reflection = reflection_generator
        self._graph = graph_module
        self._db_pool = db_pool

    def process(self, user_id: str, text: str) -> ProcessResult:
        """Execute the full pipeline."""
        event_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        logger.info(f"[orchestrator] START event={event_id[:8]} user={user_id[:8]}")

        # 1. Parse input (already a string)
        input_text = text.strip()

        # 2. Emotion extraction
        emotion_state = self._emotion.extract(input_text)
        emotion_dict = self._emotion.to_dict(emotion_state)

        # 3. Attention extraction
        attention_state = self._attention.extract(input_text)
        attention_dict = self._attention.to_dict(attention_state)

        # 4. Decision classification
        decision_state = self._decision.extract(input_text)
        decision_dict = self._decision.to_dict(decision_state)

        # 5. Memory retrieval
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

        # 6. Graph update
        self._graph.update(user_id, emotion_dict, attention_dict, decision_dict)

        # 7. Formation computation
        formation_result = self._formation.compute(
            user_id, emotion_state, attention_state, decision_state
        )
        formation_dict = self._formation.to_dict(formation_result)

        # 8. Reflection generation
        reflection_output = self._reflection.generate(
            emotion_state, attention_state, decision_state, formation_result
        )
        reflection_dict = self._reflection.to_dict(reflection_output)

        # 9. Store everything
        self._persist(
            event_id=event_id,
            user_id=user_id,
            input_text=input_text,
            emotion=emotion_dict,
            attention=attention_dict,
            decision=decision_dict,
            formation=formation_dict,
            timestamp=timestamp,
        )

        # Store as memory for future retrieval
        if self._memory:
            try:
                self._memory.insert(user_id, input_text)
            except Exception as e:
                logger.warning(f"[orchestrator] memory insert failed: {e}")

        # 10. Return response
        result = ProcessResult(
            input_text=input_text,
            emotion=emotion_dict,
            attention=attention_dict,
            decision=decision_dict,
            memories=memories,
            formation=formation_dict,
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
                        }),
                        kwargs["timestamp"],
                    ),
                )

                # Upsert formation state
                cur.execute(
                    """INSERT INTO mvfe_formation_state
                       (user_id, emotion, attention, decision, formation_score, drift_score, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (user_id) DO UPDATE SET
                         emotion = EXCLUDED.emotion,
                         attention = EXCLUDED.attention,
                         decision = EXCLUDED.decision,
                         formation_score = EXCLUDED.formation_score,
                         drift_score = EXCLUDED.drift_score,
                         updated_at = EXCLUDED.updated_at""",
                    (
                        kwargs["user_id"],
                        json.dumps(kwargs["emotion"]),
                        json.dumps(kwargs["attention"]),
                        json.dumps(kwargs["decision"]),
                        kwargs["formation"]["formation_score"],
                        kwargs["formation"]["drift_score"],
                        kwargs["timestamp"],
                    ),
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"[orchestrator] persist failed: {e}")
        finally:
            self._db_pool.putconn(conn)
