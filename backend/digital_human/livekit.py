from __future__ import annotations

import hashlib
import os
from datetime import timedelta

from livekit import api

AGENT_NAME = "spiritual-planet-digital-human"


def runtime_configured() -> bool:
    return all((os.getenv("LIVEKIT_URL", "").strip(), os.getenv("LIVEKIT_API_KEY", "").strip(), os.getenv("LIVEKIT_API_SECRET", "").strip())) and os.getenv("DIGITAL_HUMAN_LIVEKIT_AGENT_READY", "").lower() in {"1", "true", "yes"}


def mint_token(*, email: str, session_id: str, character_id: str) -> dict[str, object]:
    if not runtime_configured():
        raise RuntimeError("digital-human LiveKit agent is not ready")
    ttl = min(max(int(os.getenv("DIGITAL_HUMAN_LIVEKIT_TOKEN_TTL", "300")), 60), 900)
    room = f"dh_{session_id}"
    identity = "dh_" + hashlib.sha256(f"{email}:{session_id}".encode()).hexdigest()[:24]
    metadata = json_metadata(character_id)
    token = (
        api.AccessToken(os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"])
        .with_identity(identity)
        .with_name("Bible learner")
        .with_metadata(metadata)
        .with_ttl(timedelta(seconds=ttl))
        .with_grants(api.VideoGrants(room=room, room_join=True, can_publish=True, can_subscribe=True, can_publish_data=True))
        .with_room_config(api.RoomConfiguration(agents=[api.RoomAgentDispatch(agent_name=AGENT_NAME, metadata=metadata)]))
    )
    return {
        "token": token.to_jwt(),
        "url": os.environ["LIVEKIT_URL"], "room": room, "expiresIn": ttl,
        "turnPolicy": "HALF_DUPLEX", "rawAudioRetention": "NONE_BY_APPLICATION",
    }


def json_metadata(character_id: str) -> str:
    return '{"purpose":"digital-human","characterId":"%s"}' % character_id
