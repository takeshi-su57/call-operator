"""ElevenLabs TTS provider."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from call_operator.adapters.base import AudioChunk
from call_operator.tts.base import TTSProvider

logger = logging.getLogger(__name__)

_TARGET_SAMPLE_RATE = 16000


class ElevenLabsTTS(TTSProvider):
    """Text-to-Speech using the ElevenLabs API."""

    def __init__(
        self,
        api_key: str = "",
        voice: str = "Rachel",
        stability: str = "0.5",
        similarity_boost: str = "0.75",
        style: str = "0.0",
        model_id: str = "eleven_monolingual_v1",
        **kwargs: str,
    ) -> None:
        if not api_key:
            msg = "ELEVENLABS_API_KEY is required when TTS_PROVIDER=elevenlabs"
            raise ValueError(msg)

        self.api_key = api_key
        self.voice = voice
        self.stability = float(stability)
        self.similarity_boost = float(similarity_boost)
        self.style = float(style)
        self.model_id = model_id
        self._client: Any = None

    async def start(self) -> None:
        """Create the async ElevenLabs client."""
        if self._client is not None:
            return

        from elevenlabs.client import AsyncElevenLabs

        self._client = AsyncElevenLabs(api_key=self.api_key)
        logger.info("ElevenLabsTTS started (voice=%s, model=%s)", self.voice, self.model_id)

    async def stop(self) -> None:
        """Close the ElevenLabs client."""
        self._client = None
        logger.info("ElevenLabsTTS stopped")

    async def synthesize(self, text: str) -> AudioChunk:
        """Convert text to speech using ElevenLabs.

        Requests PCM 16 kHz output directly from the API.
        """
        if self._client is None:
            await self.start()

        logger.debug("ElevenLabsTTS input: %s", text[:80])
        start_t = time.perf_counter()

        pcm_data = await self._call_api_with_retry(text)

        latency_ms = (time.perf_counter() - start_t) * 1000
        duration_ms = len(pcm_data) / (2 * _TARGET_SAMPLE_RATE) * 1000

        logger.info(
            "ElevenLabsTTS synthesized: %.0fms latency, %.0fms audio",
            latency_ms,
            duration_ms,
        )

        return AudioChunk(
            data=pcm_data,
            sample_rate=_TARGET_SAMPLE_RATE,
            channels=1,
            timestamp=time.time(),
            duration_ms=duration_ms,
        )

    async def _call_api_with_retry(self, text: str, max_retries: int = 3) -> bytes:
        """Call ElevenLabs API with retry on transient failures."""
        from elevenlabs import VoiceSettings

        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                response = self._client.text_to_speech.convert(
                    voice_id=self.voice,
                    text=text,
                    model_id=self.model_id,
                    voice_settings=VoiceSettings(
                        stability=self.stability,
                        similarity_boost=self.similarity_boost,
                        style=self.style,
                    ),
                    output_format="pcm_16000",
                )
                audio_parts: list[bytes] = []
                async for chunk in response:
                    audio_parts.append(chunk)
                return b"".join(audio_parts)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < max_retries - 1:
                    delay = min(1.0 * (2**attempt), 30.0)
                    logger.warning("ElevenLabs TTS retry %d/%d: %s", attempt + 1, max_retries, exc)
                    await asyncio.sleep(delay)
        from call_operator.exceptions import TTSError

        msg = f"ElevenLabs TTS failed after {max_retries} attempts"
        raise TTSError(msg) from last_exc
