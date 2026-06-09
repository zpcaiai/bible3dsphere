"""
Verse retrieval & AI generation router.
Covers: /api/query, /api/guidance, /api/biblical-example, /api/verse-prayer,
        /api/meditation-questions, /api/translate, /api/sermon, /api/faith-qa,
        /api/tts, /api/punctuation
"""
from __future__ import annotations
import logging
logger = logging.getLogger(__name__)

import asyncio
import time
import traceback
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from core.ratelimit import limiter
from fastapi.responses import Response
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["verse"])

_state: dict[str, Any] = {}


def init_verse_router(
    *,
    query_emotion_verses,
    assess_psychological_state,
    fetch_biblical_example,
    generate_sermon,
    generate_faith_qa,
    generate_faith_qa_fn=None,
    call_chat,
    save_history_entry,
    get_session_user,
    get_user_tags,
    build_user_context_prompt,
    startup_check,
    handle_exc,
    features_file,
    matches_file,
    embedding_cache_file,
    root_dir,
    debug: bool = False,
    google_tts_api_key: str = "",
    elevenlabs_api_key: str = "",
    elevenlabs_voice_id: str = "XrExE9yKIg1WjnnlVkGX",
    elevenlabs_model: str = "eleven_multilingual_v2",
    default_rerank_candidates: int = 20,
    default_rerank_weight: float = 0.7,
) -> None:
    _state.update(locals())


# ── Request models ────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    topFeatures: int = Field(default=5, ge=1, le=20)
    topVerses: int = Field(default=5, ge=1, le=20)
    languageFilter: str = Field(default="both")
    includeGuidance: bool = False
    enableRerank: bool = False
    rerankCandidates: int = Field(default=20, ge=5, le=50)
    rerankWeight: float = Field(default=0.7, ge=0.0, le=1.0)
    rerankMode: str = Field(default="llm")


class GuidanceRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class SermonRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class FaithQARequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class VersePrayerRequest(BaseModel):
    reference: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=1000)


class MeditationQuestionsRequest(BaseModel):
    reference: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=2000)


class TranslateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    target_language: str = Field(default="zh-Hans")


class PunctuationRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)


class TTSRequest(BaseModel):
    text: str = Field(..., max_length=5000)
    language_code: str = Field(default="cmn-CN")
    voice_name: str = Field(default="zh-CN-XiaoxiaoNeural")


# ── Routes ────────────────────────────────────────────────────────────────────

def _wants_english(request: Request) -> bool:
    return (request.headers.get("X-Lang") or "zh").lower().startswith("en")


def _with_language_instruction(text: str, request: Request, *, bible_refs: bool = False) -> str:
    if not _wants_english(request):
        return text
    suffix = "Please respond entirely in natural English."
    if bible_refs:
        suffix += " Use standard English Bible references."
    return f"{text}\n\n({suffix})"


@router.post("/query")
async def post_query(payload: QueryRequest, request: Request) -> dict:
    query_text = payload.query.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Missing query")
    _state["startup_check"]()
    user = _state["get_session_user"](request)
    enriched_query = query_text
    if user and user.get("email"):
        tags = _state["get_user_tags"](user["email"])
        if tags:
            ctx = _state["build_user_context_prompt"](tags)
            enriched_query = f"{ctx}\n\n【用户当前提问】\n{query_text}"
    enriched_query = _with_language_instruction(enriched_query, request, bible_refs=True)
    try:
        t0 = time.perf_counter()
        # Personalised retrieval: load user preference vector if available
        _pref_vec = None
        if user:
            try:
                from preference_vector import get_user_preference_vector
                from core.deps import get_db_pool
                _uid = str(user.get("user_id") or user.get("email") or "")
                _pref_vec = get_user_preference_vector(_uid, get_db_pool())
            except Exception as _pv_err:
                logger.debug(f"[verse] preference vector unavailable: {_pv_err}")
        result = await asyncio.to_thread(
            _state["query_emotion_verses"],
            enriched_query,
            payload.topFeatures, payload.topVerses,
            _state["features_file"],
            str(_state["root_dir"] / "emotion_exemplar_verse_matches.json"),
            str(_state["root_dir"] / "emotion_feature_embedding_cache.json"),
            False,
            payload.enableRerank, payload.rerankCandidates,
            payload.rerankWeight, payload.rerankMode,
            _pref_vec,
        )
        result["query_latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        await asyncio.to_thread(
            _state["save_history_entry"],
            query_text, payload.topFeatures, payload.topVerses,
            payload.languageFilter, result,
        )
        # Attach cache status as response header for observability
        cache_status = result.pop("_cache", "MISS")
        from fastapi.responses import JSONResponse as _JSONResponse
        return _JSONResponse(
            content=result,
            headers={"X-Cache": cache_status},
        )
    except Exception as exc:
        _state["handle_exc"](exc)
        detail = {"error": str(exc), "traceback": traceback.format_exc()} if _state["debug"] else str(exc)
        raise HTTPException(status_code=500, detail=detail) from exc


@router.post("/guidance")
def get_guidance(payload: GuidanceRequest, request: Request) -> dict:
    try:
        return _state["assess_psychological_state"](
            payload.query.strip(),
            language="en" if _wants_english(request) else "zh",
        )
    except Exception as exc:
        _state["handle_exc"](exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/biblical-example")
def get_biblical_example(payload: GuidanceRequest, request: Request) -> dict:
    try:
        return _state["fetch_biblical_example"](
            _with_language_instruction(payload.query.strip(), request, bible_refs=True)
        )
    except Exception as exc:
        _state["handle_exc"](exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/verse-prayer")
def generate_verse_prayer(payload: VersePrayerRequest, request: Request) -> dict:
    try:
        from query_emotion_verses import generate_verse_prayer as _gen  # type: ignore
        language = "en" if _wants_english(request) else "zh"
        return _gen(payload.reference.strip(), payload.text.strip(), language=language)
    except Exception as exc:
        _state["handle_exc"](exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/meditation-questions")
async def get_meditation_questions(payload: MeditationQuestionsRequest, request: Request) -> dict:
    try:
        from query_emotion_verses import generate_meditation_questions as _gen  # type: ignore
        language = "en" if _wants_english(request) else "zh"
        result = await asyncio.to_thread(_gen, payload.reference.strip(), payload.text.strip(), language=language)
        return result
    except Exception as exc:
        _state["handle_exc"](exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/translate")
@limiter.limit("60/minute")
async def translate_text(payload: TranslateRequest, request: Request) -> dict:
    try:
        result = await asyncio.to_thread(
            _state["call_chat"],
            f"You are a professional translator. Translate the user's text into {payload.target_language}. "
            f"Return only the translation itself, with no explanation, quotes, or extra commentary.",
            payload.text,
        )
        return {"translation": result}
    except Exception as exc:
        _state["handle_exc"](exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/sermon")
async def post_sermon(payload: SermonRequest, request: Request) -> dict:
    query_text = payload.query.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Missing query")
    query_text = _with_language_instruction(query_text, request, bible_refs=True)
    try:
        t0 = time.perf_counter()
        result = await asyncio.to_thread(_state["generate_sermon"], query_text)
        result["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        return result
    except Exception as exc:
        _state["handle_exc"](exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/faith-qa")
async def post_faith_qa(payload: FaithQARequest, request: Request) -> dict:
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Missing question")
    question = _with_language_instruction(question, request, bible_refs=True)
    try:
        t0 = time.perf_counter()
        result = await asyncio.to_thread(_state["generate_faith_qa"], question)
        result["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        return result
    except Exception as exc:
        _state["handle_exc"](exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/punctuation")
@limiter.limit("30/minute")
async def add_punctuation(payload: PunctuationRequest, request: Request) -> dict:
    try:
        result = await asyncio.to_thread(
            _state["call_chat"],
            "你是中文标点助手。请为用户提供的文本添加标点符号，保持原文意思不变，只返回添加标点后的文本，不要解释。",
            payload.text,
        )
        return {"text": result}
    except Exception as exc:
        _state["handle_exc"](exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── TTS 文本清洗：去掉 markdown/emoji/多余空白，把换行变成自然停顿，
# 让任何引擎读起来都更像真人朗读而非"播报符号"。────────────────────────────
import re as _re_tts

_TTS_EMOJI_RE = _re_tts.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF\u2190-\u21FF\u2300-\u23FF\uFE0F]"
)

def _is_english_text(text: str) -> bool:
    """中文字符占比很低则判为英文（EN 模式内容）。"""
    if not text:
        return False
    cjk = len(_re_tts.findall(r"[\u4e00-\u9fff]", text))
    total = len(_re_tts.sub(r"\s", "", text)) or 1
    return (cjk / total) < 0.15


def _clean_for_tts(text: str) -> str:
    if not text:
        return text
    t = text
    t = _re_tts.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", t)   # [文字](url) → 文字
    t = _re_tts.sub(r"[#>`*_~|]+", "", t)                       # markdown 符号
    t = _re_tts.sub(r"(?m)^\s*[-•·]\s*", "", t)               # 列表项符号
    t = _TTS_EMOJI_RE.sub("", t)
    t = t.replace("——", "，").replace("—", "，").replace("--", "，")
    t = _re_tts.sub(r"[ \t]+", " ", t)
    t = _re_tts.sub(r"\n{2,}", "。", t)                         # 空行 → 句末停顿
    t = _re_tts.sub(r"\n", "，", t)                             # 换行 → 轻停顿
    t = _re_tts.sub(r"\s+([，。！？、；：,.!?;:])", r"\1", t)
    t = _re_tts.sub(r"([，。！？、；：])\1+", r"\1", t)          # 合并重复标点
    return t.strip()


@router.post("/tts")
@limiter.limit("30/minute")
async def text_to_speech(payload: TTSRequest, request: Request) -> Response:
    """TTS endpoint —— 多级配音，越靠前越像真人。

    1) ElevenLabs（配置 ELEVENLABS_API_KEY 时优先）—— 最接近真人的优美嗓音。
    2) Microsoft Edge TTS（edge-tts，免费，温柔女声，轻放慢语速）。
    3) Google Cloud TTS（需 GOOGLE_TTS_API_KEY）。
    所有引擎读的都是清洗后的文本（去 markdown/emoji、换行转自然停顿）。
    """
    speak_text = _clean_for_tts(payload.text) or payload.text

    # ── 引擎 1：ElevenLabs（最像真人，有 key 才启用）─────────────────────────
    el_key = _state.get("elevenlabs_api_key", "")
    if el_key:
        try:
            import os
            import httpx
            voice_id = _state.get("elevenlabs_voice_id") or "XrExE9yKIg1WjnnlVkGX"
            el_model = _state.get("elevenlabs_model") or "eleven_multilingual_v2"
            # 韵律可用环境变量微调，无需改代码；默认偏温暖、有情感、稳定。
            def _f(name, dflt):
                try:
                    return float(os.environ.get(name, dflt))
                except Exception:
                    return dflt
            el_url = (
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
                "?output_format=mp3_44100_128"
            )
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(
                    el_url,
                    headers={
                        "xi-api-key": el_key,
                        "accept": "audio/mpeg",
                        "content-type": "application/json",
                    },
                    json={
                        "text": speak_text,
                        "model_id": el_model,
                        "voice_settings": {
                            "stability": _f("ELEVENLABS_STABILITY", 0.45),
                            "similarity_boost": _f("ELEVENLABS_SIMILARITY", 0.8),
                            "style": _f("ELEVENLABS_STYLE", 0.35),
                            "use_speaker_boost": True,
                        },
                    },
                )
                r.raise_for_status()
                if r.content:
                    logger.debug("[tts] elevenlabs ok voice=%s bytes=%d", voice_id, len(r.content))
                    return Response(content=r.content, media_type="audio/mpeg")
            logger.warning("[tts] elevenlabs returned empty audio, falling back to edge-tts")
        except Exception as _el_err:  # noqa: BLE001
            logger.warning("[tts] elevenlabs failed (%s), falling back to edge-tts", _el_err)

    # ── 引擎 2：edge-tts（Microsoft Neural，免费，温柔慢读）──────────────────
    voice = payload.voice_name or "zh-CN-XiaoxiaoNeural"
    is_en = _is_english_text(speak_text)
    # Normalise Google-style voice names → Edge TTS names
    _VOICE_MAP = {
        "cmn-CN-Wavenet-A": "zh-CN-XiaoxiaoNeural",
        "cmn-CN-Wavenet-B": "zh-CN-YunxiNeural",
        "cmn-CN-Neural2-A": "zh-CN-XiaoxiaoNeural",
        "cmn-CN-Neural2-C": "zh-CN-XiaohanNeural",
    }
    edge_voice = _VOICE_MAP.get(voice, voice)
    # EN 模式内容：用温暖的英文女声，别把英文喂给中文/无效嗓音。
    if is_en and not str(edge_voice).lower().startswith("en-"):
        edge_voice = "en-US-AriaNeural"
    try:
        import edge_tts  # type: ignore
        import io
        communicate = edge_tts.Communicate(
            speak_text,
            edge_voice,
            rate="-8%",   # 略放慢，更温柔自然，不像播报腔
            volume="+0%",
            pitch="+0Hz",
        )
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        audio_bytes = buf.getvalue()
        if audio_bytes:
            logger.debug("[tts] edge-tts ok voice=%s bytes=%d", edge_voice, len(audio_bytes))
            return Response(content=audio_bytes, media_type="audio/mpeg")
        logger.warning("[tts] edge-tts returned empty audio, falling back to Google TTS")
    except ImportError:
        logger.info("[tts] edge-tts not installed, falling back to Google TTS")
    except Exception as _edge_err:
        logger.warning("[tts] edge-tts failed (%s), falling back to Google TTS", _edge_err)

    # ── 引擎 3：gTTS（Google 翻译 TTS，免费·无需 key，与 edge-tts 不同网络路径）──
    try:
        import io
        from gtts import gTTS  # type: ignore
        def _gtts_bytes():
            buf = io.BytesIO()
            gTTS(text=speak_text, lang=("en" if is_en else "zh-CN")).write_to_fp(buf)
            return buf.getvalue()
        audio_bytes = await asyncio.to_thread(_gtts_bytes)
        if audio_bytes:
            logger.debug("[tts] gTTS ok lang=%s bytes=%d", "en" if is_en else "zh-CN", len(audio_bytes))
            return Response(content=audio_bytes, media_type="audio/mpeg")
        logger.warning("[tts] gTTS returned empty audio, falling back to Google Cloud TTS")
    except ImportError:
        logger.info("[tts] gTTS not installed, falling back to Google Cloud TTS")
    except Exception as _gtts_err:  # noqa: BLE001
        logger.warning("[tts] gTTS failed (%s), falling back to Google Cloud TTS", _gtts_err)

    # ── Fallback: Google Cloud TTS ────────────────────────────────────────────
    api_key = _state.get("google_tts_api_key", "")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="TTS unavailable: edge-tts failed and Google TTS API Key not configured.",
        )
    try:
        import base64
        import httpx
        # Map Edge voice names back to Google names for fallback
        _GOOGLE_VOICE_MAP = {
            "zh-CN-XiaoxiaoNeural": "cmn-CN-Wavenet-A",
            "zh-CN-XiaohanNeural": "cmn-CN-Wavenet-A",
        }
        if is_en:
            google_lang, google_voice = "en-US", "en-US-Neural2-F"
        else:
            google_lang = "cmn-CN"
            google_voice = _GOOGLE_VOICE_MAP.get(voice, voice if voice.startswith("cmn-") else "cmn-CN-Wavenet-A")
        url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"
        body = {
            "input": {"text": speak_text},
            "voice": {
                "languageCode": google_lang,
                "name": google_voice,
                "ssmlGender": "FEMALE",
            },
            "audioConfig": {"audioEncoding": "MP3", "speakingRate": 0.9},
        }
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=body)
            r.raise_for_status()
            audio_b64 = r.json().get("audioContent", "")
        audio_bytes = base64.b64decode(audio_b64)
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except httpx.HTTPStatusError as exc:
        logger.warning("Google TTS request failed with status %s", exc.response.status_code)
        raise HTTPException(status_code=503, detail="TTS is temporarily unavailable.") from exc
    except httpx.RequestError as exc:
        logger.warning("Google TTS request failed: %s", exc.__class__.__name__)
        raise HTTPException(status_code=503, detail="TTS is temporarily unavailable.") from exc
    except Exception as exc:
        _state["handle_exc"](exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
