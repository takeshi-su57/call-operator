"""Local STT using faster-whisper (runs on CPU)."""

from __future__ import annotations

import asyncio
import logging
import math
import time
from typing import TYPE_CHECKING, Any

from call_operator.stt.base import STTProvider, Transcript

if TYPE_CHECKING:
    import numpy as np
    from faster_whisper import WhisperModel

    from call_operator.adapters.base import AudioChunk

logger = logging.getLogger(__name__)

# Minimum buffered audio duration before running transcription.
_MIN_BUFFER_MS = 1000.0


class WhisperLocalSTT(STTProvider):
    """faster-whisper based STT — runs locally on CPU.

    Audio chunks are buffered until at least :data:`_MIN_BUFFER_MS` of audio
    has accumulated, then transcription is run in a background thread via
    :func:`asyncio.to_thread` to avoid blocking the event loop.
    """

    def __init__(self, model: str = "tiny", language: str = "en", **kwargs: str) -> None:
        self.model_name = model
        self.language = language
        self._model: WhisperModel | None = None
        self._buffer: list[bytes] = []
        self._buffer_duration_ms: float = 0.0
        self._sample_rate: int = 16000

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Load the faster-whisper model in a background thread."""
        if self._model is not None:
            return
        self._model = await asyncio.to_thread(self._load_model)
        logger.info(
            "WhisperLocalSTT model loaded (model=%s, language=%s)",
            self.model_name,
            self.language,
        )

    def _load_model(self) -> WhisperModel:
        from faster_whisper import WhisperModel as _WhisperModel

        return _WhisperModel(self.model_name, device="cpu", compute_type="int8")

    async def stop(self) -> None:
        """Release model and clear buffers."""
        self._model = None
        self._buffer.clear()
        self._buffer_duration_ms = 0.0
        logger.info("WhisperLocalSTT stopped")

    # ------------------------------------------------------------------
    # Transcription
    # ------------------------------------------------------------------

    async def transcribe(self, chunk: AudioChunk) -> Transcript | None:
        """Buffer *chunk* and transcribe when enough audio has accumulated."""
        if self._model is None:
            await self.start()

        self._buffer.append(chunk.data)
        self._buffer_duration_ms += self._chunk_duration_ms(chunk)

        if self._buffer_duration_ms < _MIN_BUFFER_MS:
            return None

        return await self._run_transcription()

    async def flush(self) -> Transcript | None:
        """Transcribe whatever audio remains in the buffer."""
        if not self._buffer:
            return None
        return await self._run_transcription()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _run_transcription(self) -> Transcript | None:
        """Concatenate buffer, run Whisper in a thread, return result."""
        import numpy as _np

        audio_bytes = b"".join(self._buffer)
        self._buffer.clear()
        self._buffer_duration_ms = 0.0

        audio_array = _np.frombuffer(audio_bytes, dtype=_np.int16).astype(_np.float32) / 32768.0

        segments, info = await asyncio.to_thread(self._transcribe_sync, audio_array)

        if not segments:
            return None

        text_parts: list[str] = []
        logprob_sum = 0.0
        for seg in segments:
            text_parts.append(seg.text)
            logprob_sum += seg.avg_logprob

        combined_text = " ".join(text_parts).strip()
        if not combined_text:
            return None

        avg_logprob = logprob_sum / len(segments)
        confidence = min(max(math.exp(avg_logprob), 0.0), 1.0)

        return Transcript(
            text=combined_text,
            confidence=confidence,
            language=info.language,
            is_final=True,
            timestamp=time.time(),
        )

    def _transcribe_sync(self, audio: np.ndarray) -> tuple[list[Any], Any]:
        """Run transcription synchronously (called via :func:`asyncio.to_thread`).

        Both ``model.transcribe()`` and segment iteration happen in the same
        thread because the segment generator is tied to the CTranslate2 context.
        """
        assert self._model is not None  # noqa: S101
        segments_gen, info = self._model.transcribe(audio, language=self.language)
        return list(segments_gen), info

    @staticmethod
    def _chunk_duration_ms(chunk: AudioChunk) -> float:
        """Return chunk duration in milliseconds."""
        if chunk.duration_ms > 0:
            return chunk.duration_ms
        # 2 bytes per sample for 16-bit PCM mono
        return len(chunk.data) / (2 * chunk.sample_rate) * 1000
