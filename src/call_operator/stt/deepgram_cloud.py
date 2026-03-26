"""Cloud STT using Deepgram streaming WebSocket API."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
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

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[AudioChunk],
    ) -> AsyncIterator[Transcript]:
        """Transcribe audio via Deepgram's streaming WebSocket API."""
        # TODO: Open WebSocket connection to Deepgram
        # TODO: Stream audio chunks to the WebSocket
        # TODO: Receive transcription results
        # TODO: Yield Transcript objects (interim + final)
        logger.warning("DeepgramSTT.transcribe_stream() is not yet implemented.")
        return  # type: ignore[return-value]
        yield  # Make this an async generator
