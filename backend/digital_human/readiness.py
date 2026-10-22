"""Configuration diagnostics, explicitly separate from provider execution."""
from __future__ import annotations

import os

from .registry import PREPARED_ANSWERS, catalog, catalog_artifact, content_review_state


def runtime_readiness(*, livespeak_configured: bool) -> dict[str, object]:
    profiles = catalog()
    review = content_review_state()
    assets = sum(profile.avatar.reviewState == "APPROVED" and profile.voice.reviewState == "APPROVED" for profile in profiles)
    livekit_configured = all(os.getenv(key, "").strip() for key in ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"))
    worker_declared = os.getenv("DIGITAL_HUMAN_LIVEKIT_AGENT_READY", "").lower() in {"true", "1", "yes"}
    requirements = [
        {"code": "CONTENT_REVIEW", "label": "独立人工内容审核与签名发布", "state": "APPROVED" if review == "APPROVED" else "PENDING_REVIEW"},
        {"code": "CHARACTER_ASSETS", "label": "角色模型、肖像、音色与授权", "state": "CONFIGURED" if assets == len(profiles) else "INCOMPLETE"},
        {"code": "LIVEKIT_PROJECT", "label": "实时语音项目配置", "state": "CONFIGURED" if livekit_configured else "MISSING"},
        {"code": "STT_WORKER", "label": "转写服务就绪声明", "state": "DECLARED" if worker_declared else "MISSING"},
        {"code": "LIVESPEAK", "label": "数字人播放服务配置", "state": "CONFIGURED" if livespeak_configured else "MISSING"},
        {"code": "REAL_VOICE_JOURNEY", "label": "真实设备语音与口型播放验收", "state": "NOT_VERIFIED"},
    ]
    return {
        "characterCount": len(profiles), "truthCaseCount": catalog_artifact()["truthCaseCount"],
        "preparedAnswerCount": len(PREPARED_ANSWERS),
        "preparedAnswerCharacterCount": len({item.character_id for item in PREPARED_ANSWERS}),
        "validatedAssetCharacterCount": assets,
        "runtimeReadyCharacterCount": sum(profile.runtimeReady for profile in profiles),
        "answerMode": "PREPARED_OR_EVIDENCE_ONLY", "contextMode": "CHARACTER_BOUND_TOPIC_IDS",
        "contextPersistence": "NONE_BY_SERVER", "providerExecution": "NOT_VERIFIED_BY_CONFIGURATION_CHECK",
        "productAssurance": "NOT_CERTIFIED", "requirements": requirements,
    }
