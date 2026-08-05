"""Speech router — server-side STT proxy.

Keeps Deepgram credentials on the backend. Frontend clients upload a short audio
blob to /api/speech/transcribe and receive only the transcript.
"""
import logging
import os

import httpx
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from core.config import settings
from core.ratelimit import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/speech", tags=["speech"])

MAX_AUDIO_BYTES = int(os.getenv("SPEECH_TRANSCRIBE_MAX_BYTES", str(10 * 1024 * 1024)))
ALLOWED_PREFIXES = ("audio/",)
DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"
_legacy_key_warning_emitted = False

# Domain vocabulary is intentionally bounded well below Deepgram's keyterm
# limit. Nova-3 uses these as hints, not forced substitutions.
_BIBLE_KEYTERMS = {
    "zh-CN": [
        "耶稣基督", "耶和华", "圣灵", "圣经", "福音", "创世记", "出埃及记",
        "诗篇", "箴言", "以赛亚书", "马太福音", "马可福音", "路加福音",
        "约翰福音", "使徒行传", "罗马书", "哥林多前书", "哥林多后书",
        "加拉太书", "以弗所书", "腓立比书", "歌罗西书", "启示录",
        "亚伯拉罕", "以撒", "雅各", "摩西", "大卫", "所罗门", "保罗",
        "彼得", "约翰", "马利亚", "以色列", "耶路撒冷", "伯利恒",
        "加利利", "各各他", "复活", "救恩", "恩典", "祷告", "敬拜",
        "团契", "主日学",
    ],
    "en-US": [
        "Jesus Christ", "Yahweh", "Holy Spirit", "Scripture", "gospel",
        "Genesis", "Exodus", "Psalms", "Proverbs", "Isaiah", "Matthew",
        "Mark", "Luke", "John", "Acts", "Romans", "Corinthians",
        "Galatians", "Ephesians", "Philippians", "Colossians", "Revelation",
        "Abraham", "Isaac", "Jacob", "Moses", "David", "Solomon", "Paul",
        "Peter", "Mary", "Israel", "Jerusalem", "Bethlehem", "Galilee",
        "Golgotha", "resurrection", "salvation", "grace", "prayer",
        "worship", "fellowship", "Sunday school",
    ],
}


def _normalize_language(value: str | None) -> str | None:
    """Accept only the two languages exposed by the web application."""
    language = (value or "").strip().lower()
    if language in {"zh", "zh-cn", "zh-hans"}:
        return "zh-CN"
    if language in {"en", "en-us"}:
        return "en-US"
    return None


def _deepgram_key() -> str:
    """Resolve the server-only Deepgram key with a temporary legacy alias."""
    key = (os.getenv("DEEPGRAM_API_KEY", "") or getattr(settings, "deepgram_api_key", "")).strip()
    if key:
        return key

    legacy_key = os.getenv("VITE_DEEPGRAM_API_KEY", "").strip()
    if legacy_key:
        global _legacy_key_warning_emitted
        if not _legacy_key_warning_emitted:
            logger.warning(
                "[speech] VITE_DEEPGRAM_API_KEY is deprecated; rename the backend secret to DEEPGRAM_API_KEY"
            )
            _legacy_key_warning_emitted = True
    return legacy_key


def _extract_transcript(data: dict) -> tuple[str, str]:
    channel = (data.get("results") or {}).get("channels", [{}])[0] or {}
    alternative = (channel.get("alternatives") or [{}])[0] or {}
    transcript = str(alternative.get("transcript") or "").strip()
    detected_language = str(channel.get("detected_language") or "").strip()
    return transcript, detected_language


@router.post("/transcribe")
@limiter.limit("20/minute")
async def transcribe(
    request: Request,
    file: UploadFile = File(...),
    language: str | None = Form(default=None),
) -> dict:
    content_type = (file.content_type or "audio/webm").split(";")[0].strip().lower()
    if not any(content_type.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        raise HTTPException(status_code=415, detail="Only audio uploads are supported")

    audio = await file.read(MAX_AUDIO_BYTES + 1)
    if not audio:
        raise HTTPException(status_code=400, detail="Audio upload is empty")
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio upload is too large")

    return await transcribe_audio_bytes(
        audio,
        content_type=content_type,
        language=language,
    )


async def transcribe_audio_bytes(
    audio: bytes,
    *,
    content_type: str = "audio/webm",
    language: str | None = None,
) -> dict:
    """Transcribe already-bounded audio bytes without persisting the recording."""
    key = _deepgram_key()
    if not key:
        raise HTTPException(status_code=503, detail="Speech transcription is not configured")

    normalized_language = _normalize_language(language)
    params: dict[str, str | list[str]] = {
        "model": "nova-3",
        "punctuate": "true",
        "paragraphs": "true",
        "smart_format": "true",
    }
    if normalized_language:
        params["language"] = normalized_language
        params["keyterm"] = _BIBLE_KEYTERMS[normalized_language]
    else:
        # Non-web callers without a language hint retain automatic detection.
        params["detect_language"] = "true"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                DEEPGRAM_URL,
                params=params,
                headers={"Authorization": f"Token {key}", "Content-Type": content_type},
                content=audio,
            )
    except httpx.RequestError as exc:
        logger.warning("[speech] deepgram request failed: %s", exc)
        raise HTTPException(status_code=502, detail="Speech transcription failed") from exc

    if response.status_code >= 400:
        logger.warning("[speech] deepgram returned status=%s body=%s", response.status_code, response.text[:200])
        raise HTTPException(status_code=502, detail="Speech transcription failed")

    try:
        transcript, detected_language = _extract_transcript(response.json())
    except Exception as exc:
        logger.warning("[speech] deepgram response parse failed: %s", exc)
        raise HTTPException(status_code=502, detail="Speech transcription failed") from exc

    return {
        "ok": True,
        "transcript": transcript,
        "detected_language": detected_language or normalized_language,
        "provider": "deepgram",
    }
