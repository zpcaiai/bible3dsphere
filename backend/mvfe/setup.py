"""
MVFE Setup & Initialization
Wires all modules together and provides the FastAPI router.
"""
import os
import logging

from .core.context import ContextExtractor
from .core.emotion import EmotionExtractor
from .core.attention import AttentionExtractor
from .core.decision import DecisionClassifier
from .core.memory import MemoryStore
from .core.formation import FormationEngine
from .core.reflection import ReflectionGenerator
from .core.postgres_graph import PostgresGraphModule   # replaces Neo4j GraphModule
from .core.critic import CriticAgent
from .core.governance import ConstitutionLayer
from .core.orchestrator import Orchestrator
from .db.postgres import init_mvfe_tables
from .db.vector import get_embedding_fn
from .prompt_engine.engine import PromptEngine
from .api.routes import router as mvfe_router, init_mvfe_router

logger = logging.getLogger(__name__)


def _get_llm_fn():
    """Get LLM inference function. Uses Gemini API."""
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        logger.warning("[mvfe] GEMINI_API_KEY not set, using mock LLM")
        return _mock_llm

    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    try:
        from query_emotion_verses import post_with_retry, chat_url_and_headers, GEMINI_CHAT_MODEL

        def llm_fn(prompt: str) -> str:
            _url, _headers = chat_url_and_headers()
            resp = post_with_retry(
                _url,
                {
                    "model": GEMINI_CHAT_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 500,
                    "temperature": 0.7,
                },
                _headers,
            )
            return resp.get("choices", [{}])[0].get("message", {}).get("content", "")

        logger.info("[mvfe] LLM: Gemini via query_emotion_verses")
        return llm_fn
    except Exception as e:
        logger.warning(f"[mvfe] Failed to load Gemini LLM: {e}, using mock")
        return _mock_llm


def _mock_llm(prompt: str) -> str:
    """Mock LLM for when no API is available."""
    import json
    # Check more specific prompts first to avoid false matches
    if "contextual frame" in prompt.lower() or "life stage" in prompt.lower()[:100]:
        return json.dumps({
            "life_stage": "mid_career",
            "situational_background": "Navigating professional uncertainty with family responsibilities.",
            "identity_anchors": ["professional", "parent"],
            "relationship_context": "Stable but under pressure.",
            "temporal_urgency": 0.5,
        })
    elif "emotional content" in prompt.lower() or "emotion" in prompt.lower()[:100]:
        return json.dumps({
            "primary_emotion": "anxiety",
            "intensity": 0.6,
            "secondary_emotions": ["sadness", "hope"],
            "uncertainty": 0.3,
        })
    elif "attention" in prompt.lower()[:100]:
        return json.dumps({
            "focus": "current situation",
            "fixation_score": 0.5,
            "drift_risk": 0.4,
            "anchor_object": "unresolved concern",
        })
    elif "decision" in prompt.lower()[:100]:
        return json.dumps({
            "type": "avoidance",
            "drivers": {"fear": 0.4, "ego": 0.3, "love": 0.3},
            "confidence": 0.5,
        })
    elif "reflect" in prompt.lower()[:200]:
        return json.dumps({
            "state_interpretation": "The person appears to be processing complex emotions with moderate intensity.",
            "loop_detection": "No clear repetitive loop detected at this time.",
            "risk_assessment": "Moderate attentional fixation warrants continued observation.",
            "reflective_question": "What would it look like to simply be present with what you're feeling?",
        })
    elif "adversarial critic" in prompt.lower() or "false coherence" in prompt.lower()[:200]:
        return json.dumps({
            "coherence_score": 0.6,
            "overfit_risk": 0.4,
            "alternative_hypotheses": [
                "The anxiety may be situational rather than pattern-based.",
                "Attention fixation might be temporary due to recent events.",
            ],
            "challenge_summary": "The system may be over-interpreting a temporary state as a persistent pattern.",
            "confidence_adjustment": -0.1,
        })
    return "{}"


def init_mvfe(db_pool) -> bool:
    """
    Initialize the full MVFE system.
    Returns True if successful.
    """
    logger.info("[mvfe] Initializing MVFE Formation Engine...")

    # 1. Init database tables
    if db_pool:
        if not init_mvfe_tables(db_pool):
            logger.warning("[mvfe] DB init failed, continuing without persistence")
            db_pool = None

    # 2. Get LLM function
    llm_fn = _get_llm_fn()

    # 3. Get embedding function
    embedding_fn = get_embedding_fn()

    # 4. Build PostgreSQL-backed graph module (replaces Neo4j)
    graph_module = PostgresGraphModule(db_pool)

    # 5. Build LLM-driven modules
    context_extractor    = ContextExtractor(llm_fn)
    emotion_extractor    = EmotionExtractor(llm_fn)
    attention_extractor  = AttentionExtractor(llm_fn)
    decision_classifier  = DecisionClassifier(llm_fn)
    formation_engine     = FormationEngine()
    critic_agent         = CriticAgent(llm_fn)
    reflection_generator = ReflectionGenerator(llm_fn)
    governance_layer     = ConstitutionLayer()
    prompt_engine        = PromptEngine(db_pool)


    memory_store = None
    if db_pool:
        try:
            memory_store = MemoryStore(db_pool, embedding_fn)
        except Exception as e:
            logger.warning(f"[mvfe] Memory store init failed: {e}")

    # 7. Build orchestrator
    orchestrator = Orchestrator(
        context_extractor=context_extractor,
        emotion_extractor=emotion_extractor,
        attention_extractor=attention_extractor,
        decision_classifier=decision_classifier,
        memory_store=memory_store,
        formation_engine=formation_engine,
        critic_agent=critic_agent,
        reflection_generator=reflection_generator,
        governance_layer=governance_layer,
        graph_module=graph_module,
        db_pool=db_pool,
    )

    # 8. Wire API
    init_mvfe_router(orchestrator, db_pool, prompt_engine)

    logger.info("[mvfe] MVFE Formation Engine initialized successfully")
    return True
