"""LiveKit transcription-only worker for the Digital Human browser journey.

Audio is transcribed in the room and forwarded through LiveKit's standard
``lk.transcription`` text stream. Domain retrieval, review gating and Avatar
speech remain in the authenticated application path, preventing the realtime
worker from becoming a second theological authority.
"""
from __future__ import annotations

import os

from livekit import agents
from livekit.agents import Agent, AgentServer, AgentSession
from livekit.agents.voice import room_io

AGENT_NAME = "spiritual-planet-digital-human"


def agent_settings() -> dict[str, object]:
    stt_model = os.getenv("DIGITAL_HUMAN_STT_MODEL", "deepgram/nova-3:multi").strip()
    return {
        "stt": stt_model or "deepgram/nova-3:multi",
        "turn_handling": {
            "turn_detection": "stt",
            "endpointing": {"min_delay": 0.45, "max_delay": 2.5},
            "interruption": {"enabled": False, "discard_audio_if_uninterruptible": True},
            "preemptive_generation": {"enabled": False},
            "user_turn_limit": {"max_words": 240, "max_duration": 60.0},
        },
        "transcription_timeout": 8.0,
        "user_away_timeout": 60.0,
    }


class TranscriptionBoundaryAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Transcribe the linked participant only. Do not generate answers, spiritual advice, "
                "persona speech, TTS, or tool calls; the authenticated domain service owns all responses."
            ),
            llm=None,
            tts=None,
        )

    async def llm_node(self, _chat_ctx, _tools, _model_settings):
        # Keep this an async generator so AgentSession completes a turn without
        # invoking an LLM or emitting an agent-authored transcript.
        if False:  # pragma: no cover - establishes async-generator semantics
            yield ""


async def digital_human_session(ctx: agents.JobContext) -> None:
    """Module-level entrypoint so SDK forkserver workers can deserialize it."""
    await ctx.connect()
    session = AgentSession(**agent_settings())
    await session.start(
        room=ctx.room,
        agent=TranscriptionBoundaryAgent(),
        room_options=room_io.RoomOptions(
            text_input=False,
            audio_input=room_io.AudioInputOptions(
                sample_rate=24000, num_channels=1, frame_size_ms=50,
                pre_connect_audio=True, pre_connect_audio_timeout=3.0,
            ),
            video_input=False,
            audio_output=False,
            text_output=room_io.TextOutputOptions(sync_transcription=False),
            close_on_disconnect=True,
            delete_room_on_close=True,
        ),
        record=False,
    )


def create_server() -> AgentServer:
    prometheus_port = int(os.getenv("DIGITAL_HUMAN_AGENT_PROMETHEUS_PORT", "9091"))
    server = AgentServer(prometheus_port=prometheus_port)
    server.rtc_session(digital_human_session, agent_name=AGENT_NAME)
    return server


if __name__ == "__main__":
    agents.cli.run_app(create_server())
