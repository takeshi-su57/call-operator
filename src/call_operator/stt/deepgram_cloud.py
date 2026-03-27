"""Cloud STT using Deepgram streaming WebSocket API."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from call_operator.stt.base import STTProvider, Transcript

if TYPE_CHECKING:
    from call_operator.adapters.base import AudioChunk

logger = logging.getLogger(__name__)


class DeepgramSTT(STTProvider):
    """Deepgram streaming STT — low latency cloud transcription."""

    def __init__(self, api_key: str = "", model: str = "nova-2", **kwargs: str) -> None:
        self.api_key = api_key
        self.model = model

    async def start(self) -> None:
        """Open WebSocket connection to Deepgram."""
        # TODO: Open WebSocket connection to Deepgram
        logger.warning("DeepgramSTT.start() is not yet implemented.")

    async def transcribe(self, chunk: AudioChunk) -> Transcript | None:
        """Stream an audio chunk to Deepgram and return any result."""
        # TODO: Send audio chunk via WebSocket, receive transcription
        logger.warning("DeepgramSTT.transcribe() is not yet implemented.")
        return None

    async def stop(self) -> None:
        """Close WebSocket connection."""
        # TODO: Close WebSocket connection
        logger.warning("DeepgramSTT.stop() is not yet implemented.")
