import json
import logging
import os
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query, Request

from core.ratelimit import limiter
from digital_human.contracts import DigitalHumanTurnRequest, IdentityResolveRequest, LiveKitTokenRequest, ProviderTelemetryEvent
from digital_human.identity import resolve_identity
from digital_human.livekit import mint_token, runtime_configured
from digital_human.metrics import metrics
from digital_human.registry import CONTENT_SHA256, CONTENT_VERSION, catalog, catalog_artifact, character_profile, content_review_state
from digital_human.retrieval import get_retriever
from digital_human.service import DigitalHumanService
from telemetry import get_tracer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/digital-human", tags=["digital-human"])
_state: dict[str, Any] = {}
_service = DigitalHumanService()
_tracer = get_tracer(__name__)


def init_digital_human_router(*, get_session_user, get_db=None, release_db=None, is_admin=None) -> None:
    _state.update(get_session_user=get_session_user, get_db=get_db, release_db=release_db, is_admin=is_admin)


def _require_user(request: Request) -> dict[str, Any]:
    getter = _state.get("get_session_user")
    user = getter(request) if getter else None
    if not user or not user.get("email"):
        raise HTTPException(status_code=401, detail="请先登录")
    return user


def _require_admin(request: Request) -> dict[str, Any]:
    user = _require_user(request)
    checker = _state.get("is_admin")
    if not checker or not checker(str(user["email"])):
        raise HTTPException(status_code=403, detail="需要平台管理员权限")
    return user


def _public_livespeak_config() -> tuple[str | None, str | None]:
    embed_url = os.getenv("DIGITAL_HUMAN_LIVESPEAK_EMBED_URL", "").strip()
    if not embed_url:
        return None, None
    parsed = urlparse(embed_url)
    allowed = {item.strip() for item in os.getenv("DIGITAL_HUMAN_LIVESPEAK_ALLOWED_ORIGINS", "https://metaperson.avatarsdk.com").split(",") if item.strip()}
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if parsed.scheme != "https" or origin not in allowed:
        logger.error("digital-human LiveSpeak URL rejected by origin policy")
        return None, None
    return embed_url, origin


def _write_audit(email: str, envelope) -> None:
    get_db = _state.get("get_db")
    release_db = _state.get("release_db")
    if not get_db or not release_db:
        return
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.user_email', %s, true)", (email,))
            cur.execute(
                """INSERT INTO digital_human_turn_audit
                   (owner_email,session_id,turn_id,trace_id,character_id,result_state,
                    grounding_level,reason_codes_json,references_json,latency_ms)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s)""",
                (
                    email, envelope.sessionId, envelope.turnId, envelope.traceId,
                    envelope.response.characterId, envelope.state, envelope.response.groundingLevel,
                    json.dumps(envelope.response.warnings, ensure_ascii=False),
                    json.dumps([item.model_dump() for item in envelope.response.references], ensure_ascii=False),
                    envelope.latencyMs,
                ),
            )
        conn.commit()
    except Exception as exc:
        if conn:
            conn.rollback()
        logger.warning("digital-human audit persistence unavailable: %s", type(exc).__name__)
    finally:
        if conn:
            release_db(conn)


@router.get("/catalog")
@limiter.limit("60/minute")
def get_catalog(request: Request) -> dict[str, Any]:
    _require_user(request)
    artifact = catalog_artifact()
    return {
        "characters": [item.model_dump() for item in catalog()],
        "characterCount": artifact["characterCount"],
        "truthCaseCount": artifact["truthCaseCount"],
        "sourceManifestSha256": artifact["sourceManifestSha256"],
        "contentVersion": CONTENT_VERSION,
        "contentSha256": CONTENT_SHA256,
        "contentReviewState": content_review_state(),
    }


@router.post("/identity/resolve")
@limiter.limit("60/minute")
def resolve_character_identity(payload: IdentityResolveRequest, request: Request) -> dict[str, Any]:
    _require_user(request)
    artifact = catalog_artifact()
    resolution = resolve_identity(
        surface=payload.surface,
        explicit_character_id=payload.explicitCharacterId,
        current_character_id=payload.currentCharacterId,
        characters=artifact["characters"],
        ambiguous=artifact["identity"]["ambiguous"],
        stable_labels=artifact["identity"]["stableLabels"],
    )
    return resolution.model_dump()


@router.get("/characters/{character_id}")
@limiter.limit("60/minute")
def get_character(character_id: str, request: Request) -> dict[str, Any]:
    _require_user(request)
    profile = character_profile(character_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="未知圣经人物")
    return {"character": profile.model_dump()}


@router.get("/runtime")
@limiter.limit("60/minute")
def get_runtime(request: Request) -> dict[str, Any]:
    user = _require_user(request)
    embed_url, origin = _public_livespeak_config()
    return {
        "liveKitEnabled": runtime_configured(), "liveSpeakEnabled": bool(embed_url),
        "liveSpeakEmbedUrl": embed_url, "liveSpeakOrigin": origin,
        "turnPolicy": "HALF_DUPLEX", "rawAudioStored": False,
        "transcriptPersistence": "NONE", "contentReviewState": content_review_state(),
        "contentSha256": CONTENT_SHA256,
        "retrievalMode": "HYBRID_DENSE_LEXICAL_GRAPH" if get_retriever().dense_enabled else "LEXICAL_GRAPH_DEGRADED",
        "operationsDashboardEnabled": bool(_state.get("is_admin") and _state["is_admin"](str(user["email"]))),
    }


@router.post("/turns")
@limiter.limit("20/minute")
def create_turn(payload: DigitalHumanTurnRequest, request: Request) -> dict[str, Any]:
    user = _require_user(request)
    try:
        with _tracer.start_as_current_span("digital_human.turn") as span:
            span.set_attribute("digital_human.character_id", payload.characterId)
            envelope = _service.answer(
                character_id=payload.characterId, question=payload.question,
                session_id=payload.sessionId, turn_id=payload.turnId,
            )
            span.set_attribute("digital_human.result_state", envelope.state)
            span.set_attribute("digital_human.grounding_level", envelope.response.groundingLevel)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="未知圣经人物") from exc
    metrics.record_turn(state=envelope.state, latency_ms=envelope.latencyMs)
    _write_audit(str(user["email"]), envelope)
    return envelope.model_dump()


@router.get("/characters/{character_id}/retrieval")
@limiter.limit("30/minute")
def inspect_retrieval(
    character_id: str, request: Request, q: str = Query(min_length=1, max_length=1200),
    top_k: int = Query(default=5, ge=1, le=12),
) -> dict[str, object]:
    _require_user(request)
    try:
        return get_retriever().retrieve(character_id, q, top_k=top_k)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="未知圣经人物") from exc


@router.get("/characters/{character_id}/graph")
@limiter.limit("30/minute")
def get_character_graph(character_id: str, request: Request, q: str = Query(default="", max_length=1200)) -> dict[str, object]:
    _require_user(request)
    artifact = catalog_artifact()
    if character_id not in {item["id"] for item in artifact["characters"]}:
        raise HTTPException(status_code=404, detail="未知圣经人物")
    paths = get_retriever().graph.retrieve(character_id, q, max_depth=2, limit=24)
    return {"characterId": character_id, "paths": [item.to_dict() for item in paths], "maxDepth": 2}


@router.post("/telemetry/provider", status_code=202)
@limiter.limit("30/minute")
def record_provider_telemetry(payload: ProviderTelemetryEvent, request: Request) -> dict[str, bool]:
    _require_user(request)
    metrics.record_provider(provider=payload.provider, state=payload.state, latency_ms=payload.latencyMs)
    return {"accepted": True}


@router.get("/operations/metrics")
@limiter.limit("30/minute")
def get_operations_metrics(request: Request, window_seconds: int = Query(default=900, ge=60, le=86400)) -> dict[str, object]:
    _require_admin(request)
    return metrics.snapshot(window_seconds)


@router.post("/livekit/token")
@limiter.limit("10/minute")
def create_livekit_token(payload: LiveKitTokenRequest, request: Request) -> dict[str, object]:
    user = _require_user(request)
    if character_profile(payload.characterId) is None:
        raise HTTPException(status_code=404, detail="未知圣经人物")
    try:
        result = mint_token(email=str(user["email"]), session_id=payload.sessionId, character_id=payload.characterId)
        metrics.record_provider(provider="livekit", state="READY")
        return result
    except RuntimeError as exc:
        metrics.record_provider(provider="livekit", state="FALLBACK")
        raise HTTPException(status_code=503, detail="实时语音代理尚未就绪") from exc
