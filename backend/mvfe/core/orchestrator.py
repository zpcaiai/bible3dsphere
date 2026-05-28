"""
ORCHESTRATOR (CRITICAL)
Deterministic pipeline: input → extraction → formation → reflection → persistence.
"""
import concurrent.futures
import logging
import time
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
from user_tag_system import tag_extractor, get_tag_store

logger = logging.getLogger(__name__)

# Lazy tracer factory -- safe to call before setup_telemetry()
def _tracer():
    try:
        from telemetry import get_tracer
        return get_tracer("mvfe.orchestrator")
    except ImportError:
        from telemetry import _NoOpTracer  # type: ignore
        return _NoOpTracer()



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

        tracer = _tracer()
        with tracer.start_as_current_span("mvfe.process") as root_span:
            root_span.set_attribute("mvfe.event_id",    event_id)
            root_span.set_attribute("mvfe.user_prefix", user_id_str[:8])
            root_span.set_attribute("mvfe.text_len",    len(text))
            return self._run_pipeline(
                tracer=tracer,
                event_id=event_id,
                timestamp=timestamp,
                user_id=user_id,
                user_id_str=user_id_str,
                text=text,
            )

    def _run_pipeline(self, tracer, event_id, timestamp, user_id, user_id_str, text):
        _t_pipeline_start = time.perf_counter()
        # 1. Parse input
        input_text = text.strip()

        # 2. Context framing
        with tracer.start_as_current_span("mvfe.context_extract") as span:
            context_state = self._context.extract(input_text)
            context_dict = self._context.to_dict(context_state)
            span.set_attribute("mvfe.context_keys", str(list(context_dict.keys()))[:120])

        # 3-5. Parallel extraction with one OTel span per extractor
        _t_par_start = time.perf_counter()
        with tracer.start_as_current_span("mvfe.parallel_extract") as par_span:
            try:
                from opentelemetry import context as _otel_ctx
                _parent_ctx = _otel_ctx.get_current()
            except ImportError:
                _parent_ctx = None

            def _run_with_span(name, fn, arg, pctx):
                tok = None
                if pctx is not None:
                    try:
                        from opentelemetry import context as _c
                        tok = _c.attach(pctx)
                    except Exception:
                        pass
                try:
                    with tracer.start_as_current_span(name):
                        return fn(arg)
                finally:
                    if tok is not None:
                        try:
                            from opentelemetry import context as _c
                            _c.detach(tok)
                        except Exception:
                            pass

            with concurrent.futures.ThreadPoolExecutor(max_workers=3, thread_name_prefix="mvfe-extract") as _pool:
                _emo_fut = _pool.submit(_run_with_span, "mvfe.emotion_extract",   self._emotion.extract,   input_text, _parent_ctx)
                _att_fut = _pool.submit(_run_with_span, "mvfe.attention_extract", self._attention.extract, input_text, _parent_ctx)
                _dec_fut = _pool.submit(_run_with_span, "mvfe.decision_extract",  self._decision.extract,  input_text, _parent_ctx)
                emotion_state   = _emo_fut.result()
                attention_state = _att_fut.result()
                decision_state  = _dec_fut.result()

        _t_par_ms = (time.perf_counter() - _t_par_start) * 1000
        par_span.set_attribute("mvfe.parallel_ms", round(_t_par_ms, 1))
        logger.info(f"[orchestrator] parallel extraction done in {_t_par_ms:.0f}ms")

        emotion_dict   = self._emotion.to_dict(emotion_state)
        attention_dict = self._attention.to_dict(attention_state)
        # 6. Memory retrieval
        memories = []
        with tracer.start_as_current_span("mvfe.memory_search") as _mem_span:
            if self._memory:
                try:
                    mem_items = self._memory.search(user_id, input_text, top_k=5)
                    memories = [
                        {"content": m.content, "similarity": m.similarity, "timestamp": m.timestamp}
                        for m in mem_items
                    ]
                    _mem_span.set_attribute("mvfe.memory_count", len(memories))
                except Exception as e:
                    logger.warning(f"[orchestrator] memory search failed: {e}")
                    _mem_span.set_attribute("mvfe.memory_error", str(e)[:120])

        # 7. Graph update (rich causal loop)
        with tracer.start_as_current_span("mvfe.graph_update"):
            self._graph.update(user_id, emotion_dict, attention_dict, decision_dict)
            self._graph.update_rich(user_id, emotion_dict, attention_dict, decision_dict, context_dict)

        # 7b. Graph-based formation insight (loop detection)
        print(f"[orchestrator] calling get_formation_insight: emotion={emotion_dict}, decision_type={decision_dict.get('type')}, fear={decision_dict.get('drivers',{}).get('fear')}", flush=True)
        graph_insight = self._graph.get_formation_insight(user_id, emotion_dict, decision_dict)
        print(f"[orchestrator] graph_insight result: {graph_insight}", flush=True)

        # 8. Formation computation — load previous EMA from DB to seed cross-session tracking
        prev_ema = 0.0
        prev_sessions = 0
        if self._db_pool:
            try:
                _conn = self._db_pool.getconn()
                try:
                    with _conn.cursor() as _cur:
                        _cur.execute(
                            "SELECT formation_score_ema, session_count "
                            "FROM mvfe_formation_state WHERE user_id = %s",
                            (user_id_str,),
                        )
                        _row = _cur.fetchone()
                        if _row and _row[0] is not None:
                            prev_ema = float(_row[0])
                            prev_sessions = int(_row[1] or 0)
                finally:
                    self._db_pool.putconn(_conn)
            except Exception as _e:
                logger.warning(f"[orchestrator] EMA load failed: {_e}")

        with tracer.start_as_current_span("mvfe.formation_compute") as _fs:
            formation_result = self._formation.compute(
                user_id, emotion_state, attention_state, decision_state,
                previous_ema=prev_ema,
                previous_session_count=prev_sessions,
            )
            formation_dict = self._formation.to_dict(formation_result)
            _fs.set_attribute("mvfe.formation_score", round(float(formation_result.formation_score), 4))
            _fs.set_attribute("mvfe.formation_ema",   round(float(formation_result.formation_score_ema), 4))
            _fs.set_attribute("mvfe.session_count",   int(formation_result.session_count))

        # 9. Reflection generation (first pass)
        with tracer.start_as_current_span("mvfe.reflection_generate"):
            reflection_output = self._reflection.generate(
                emotion_state, attention_state, decision_state, formation_result
            )
            reflection_text = reflection_output.state_interpretation
        # 10. Critic challenge
        with tracer.start_as_current_span("mvfe.critic_challenge") as _cs:
            critic_report = self._critic.challenge(
                input_text, reflection_text, emotion_dict, attention_dict, decision_dict, formation_dict
            )
            critic_dict = self._critic.to_dict(critic_report)
            adjusted_confidence = self._critic.adjust_confidence(
                1.0 - emotion_state.uncertainty, critic_report
            )
            reflection_output.confidence = round(max(0.0, min(1.0, adjusted_confidence)), 3)
            _cs.set_attribute("mvfe.critic_risk",      str(getattr(critic_report, "overall_risk", ""))[:40])
            _cs.set_attribute("mvfe.confidence_final", reflection_output.confidence)
            logger.info(f"[orchestrator] critic confidence adjusted to {adjusted_confidence:.3f}")


        # 11. Governance audit
        with tracer.start_as_current_span("mvfe.governance_audit") as _gs:
            governance_report = self._governance.audit(reflection_text, formation_dict)
            governance_dict = {
                "passed": governance_report.passed,
                "violations": governance_report.violations,
                "warnings": governance_report.warnings,
                "formation_danger": governance_report.formation_danger_flag,
                "categories": governance_report.categories,
                "risk_level": governance_report.risk_level,
            }
            _gs.set_attribute("mvfe.governance_passed", governance_report.passed)
            _gs.set_attribute("mvfe.governance_risk",   str(governance_report.risk_level)[:20])
            if not governance_report.passed:
                reflection_output.state_interpretation = self._governance.sanitize(
                    reflection_text, governance_report
                )
                logger.warning(f"[orchestrator] governance violations: {governance_report.violations}")

        reflection_dict = self._reflection.to_dict(reflection_output)

        # 12. Store everything
        with tracer.start_as_current_span("mvfe.persist"):
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
                reflection=reflection_dict,
                timestamp=timestamp,
            )

        # Store as memory for future retrieval
        if self._memory:
            try:
                self._memory.insert(user_id, input_text)
            except Exception as e:
                logger.warning(f"[orchestrator] memory insert failed: {e}")

        # 12b. Extract and store user personal tags
        try:
            tag_store = get_tag_store()
            if tag_store:
                # 构建 MVFE 结果字典
                mvfe_result = {
                    'emotion': emotion_dict,
                    'attention': attention_dict,
                    'decision': decision_dict,
                    'formation': formation_dict
                }
                # 提取标签
                extracted_tags = tag_extractor.extract_from_mvfe_result(mvfe_result, input_text)
                if extracted_tags:
                    # 保存标签
                    tag_ids = tag_store.add_or_update_tags(user_id, extracted_tags, event_id)
                    logger.info(f"[orchestrator] extracted {len(extracted_tags)} tags, saved {len(tag_ids)}")
        except Exception as e:
            logger.warning(f"[orchestrator] tag extraction failed: {e}")

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
        # 13b. Record pipeline metrics for observability
        _pipeline_ms = (time.perf_counter() - _t_pipeline_start) * 1000
        if self._db_pool:
            try:
                from mvfe.metrics import record_pipeline_run  # type: ignore
                record_pipeline_run(
                    self._db_pool,
                    user_id=str(user_id),
                    event_id=event_id,
                    pipeline_latency_ms=_pipeline_ms,
                    formation=formation_dict,
                    critic=critic_dict,
                    governance=governance_dict,
                    emotion=emotion_dict,
                )
            except Exception as _met_err:
                logger.debug(f"[orchestrator] metrics record skipped: {_met_err}")

        logger.info(f"[orchestrator] DONE event={event_id[:8]} latency={_pipeline_ms:.0f}ms")
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
                       (user_id, emotion, attention, decision, context,
                        formation_score, drift_score, stability_score,
                        formation_score_ema, session_count,
                        trajectory_vector, loop_detected, loop_type, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (user_id) DO UPDATE SET
                         emotion = EXCLUDED.emotion,
                         attention = EXCLUDED.attention,
                         decision = EXCLUDED.decision,
                         context = EXCLUDED.context,
                         formation_score = EXCLUDED.formation_score,
                         drift_score = EXCLUDED.drift_score,
                         stability_score = EXCLUDED.stability_score,
                         formation_score_ema = EXCLUDED.formation_score_ema,
                         session_count = EXCLUDED.session_count,
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
                        kwargs["formation"].get("formation_score_ema", 0.0),
                        kwargs["formation"].get("session_count", 0),
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
