"""OpenAI TTS provider."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from call_operator.adapters.base import AudioChunk
from call_operator.tts.base import TTSProvider

logger = logging.getLogger(__name__)

# OpenAI TTS returns 24 kHz PCM; we downsample to 16 kHz.
_OPENAI_PCM_SAMPLE_RATE = 24000
_TARGET_SAMPLE_RATE = 16000


class OpenAITTS(TTSProvider):
    """Text-to-Speech using the OpenAI TTS API."""

    def __init__(
        self,
        api_key: str = "",
        voice: str = "alloy",
        speed: str = "1.0",
        model: str = "tts-1",
        **kwargs: str,
    ) -> None:
        if not api_key:
            msg = "OPENAI_API_KEY is required when TTS_PROVIDER=openai"
            raise ValueError(msg)

        self.api_key = api_key
        self.voice = voice
        self.speed = float(speed)
        self.model = model
        self._client: Any = None

    async def start(self) -> None:
        """Create the async OpenAI client."""
        if self._client is not None:
            return

        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=self.api_key)
        logger.info(
            "OpenAITTS started (voice=%s, model=%s, speed=%.1f)",
            self.voice,
            self.model,
            self.speed,
        )

    async def stop(self) -> None:
        """Close the OpenAI client."""
        if self._client is not None:
            await self._client.close()
            self._client = None
        logger.info("OpenAITTS stopped")

    async def synthesize(self, text: str) -> AudioChunk:
        """Convert text to speech using OpenAI TTS.

        Requests raw PCM at 24 kHz and downsamples to 16 kHz.
        """
        if self._client is None:
            await self.start()

        logger.debug("OpenAITTS input: %s", text[:80])
        start_t = time.perf_counter()

        audio_data = await self._call_api_with_retry(text)

        pcm_16k = _downsample_24k_to_16k(audio_data)
        latency_ms = (time.perf_counter() - start_t) * 1000
        duration_ms = len(pcm_16k) / (2 * _TARGET_SAMPLE_RATE) * 1000

        logger.info(
            "OpenAITTS synthesized: %.0fms latency, %.0fms audio",
            latency_ms,
            duration_ms,
        )

        return AudioChunk(
            data=pcm_16k,
            sample_rate=_TARGET_SAMPLE_RATE,
            channels=1,
            timestamp=time.time(),
            duration_ms=duration_ms,
        )

    async def _call_api_with_retry(self, text: str, max_retries: int = 3) -> bytes:
        """Call OpenAI TTS API with retry on transient failures."""
        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                response = await self._client.audio.speech.create(
                    model=self.model,
                    voice=self.voice,
                    input=text,
                    response_format="pcm",
                    speed=self.speed,
                )
                return response.read()  # type: ignore[no-any-return]
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < max_retries - 1:
                    delay = min(1.0 * (2**attempt), 30.0)
                    logger.warning("OpenAI TTS retry %d/%d: %s", attempt + 1, max_retries, exc)
                    await asyncio.sleep(delay)
        from call_operator.exceptions import TTSError

        msg = f"OpenAI TTS failed after {max_retries} attempts"
        raise TTSError(msg) from last_exc


def _downsample_24k_to_16k(pcm_24k: bytes) -> bytes:
    """Downsample 24 kHz 16-bit PCM to 16 kHz using linear interpolation."""
    import numpy as np

    samples_24k = np.frombuffer(pcm_24k, dtype=np.int16)
    num_samples_16k = int(len(samples_24k) * _TARGET_SAMPLE_RATE / _OPENAI_PCM_SAMPLE_RATE)
    indices = np.linspace(0, len(samples_24k) - 1, num_samples_16k).astype(np.int64)
    samples_16k = samples_24k[indices]
    return samples_16k.astype(np.int16).tobytes()
