"""Local STT using faster-whisper (runs on CPU)."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from call_operator.stt.base import STTProvider, Transcript

if TYPE_CHECKING:
    from call_operator.adapters.base import AudioChunk

logger = logging.getLogger(__name__)


class WhisperLocalSTT(STTProvider):
    """faster-whisper based STT — runs locally on CPU.

    Uses the 'tiny' or 'base' model by default for low latency.
    """

    def __init__(self, model: str = "tiny", **kwargs: str) -> None:
        self.model_name = model
        self._model = None  # Lazy-loaded

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[AudioChunk],
    ) -> AsyncIterator[Transcript]:
        """Transcribe audio chunks using faster-whisper."""
        # TODO: Load faster-whisper model (lazy, first call)
        # TODO: Buffer audio chunks into segments
        # TODO: Run transcription via asyncio.to_thread() (CPU-bound)
        # TODO: Yield Transcript objects
        logger.warning("WhisperLocalSTT.transcribe_stream() is not yet implemented.")
        return  # type: ignore[return-value]
        yield  # Make this an async generator
