"""Google Cloud TTS provider."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from call_operator.adapters.base import AudioChunk
from call_operator.tts.base import TTSProvider

logger = logging.getLogger(__name__)

_TARGET_SAMPLE_RATE = 16000
# Standard WAV header size (RIFF + fmt + data sub-chunk headers).
_WAV_HEADER_SIZE = 44


class GoogleTTS(TTSProvider):
    """Text-to-Speech using Google Cloud Text-to-Speech API.

    Uses Application Default Credentials (``GOOGLE_APPLICATION_CREDENTIALS``
    env var or ``gcloud auth application-default login``).
    """

    def __init__(
        self,
        voice: str = "en-US-Neural2-C",
        **kwargs: str,
    ) -> None:
        self.voice = voice
        self.language_code = "-".join(voice.split("-")[:2])
        self._client: Any = None

    async def start(self) -> None:
        """Create the async Google Cloud TTS client."""
        if self._client is not None:
            return

        from google.cloud import texttospeech_v1 as texttospeech

        self._client = texttospeech.TextToSpeechAsyncClient()
        logger.info(
            "GoogleTTS started (voice=%s, language=%s)",
            self.voice,
            self.language_code,
        )

    async def stop(self) -> None:
        """Release the Google Cloud TTS client."""
        self._client = None
        logger.info("GoogleTTS stopped")

    async def synthesize(self, text: str) -> AudioChunk:
        """Convert text to speech using Google Cloud TTS.

        Supports both plain text and SSML input (detected automatically
        when the text starts with ``<speak>``).  Requests LINEAR16 PCM
        at 16 kHz directly from the API.
        """
        if self._client is None:
            await self.start()

        logger.debug("GoogleTTS input: %s", text[:80])
        start_t = time.perf_counter()

        from google.cloud import texttospeech_v1 as texttospeech

        # Detect SSML input.
        stripped = text.strip()
        if stripped.startswith("<speak>"):
            synthesis_input = texttospeech.SynthesisInput(ssml=text)
        else:
            synthesis_input = texttospeech.SynthesisInput(text=text)

        voice_params = texttospeech.VoiceSelectionParams(
            language_code=self.language_code,
            name=self.voice,
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=_TARGET_SAMPLE_RATE,
        )

        pcm_data = await self._call_api_with_retry(synthesis_input, voice_params, audio_config)

        latency_ms = (time.perf_counter() - start_t) * 1000
        duration_ms = len(pcm_data) / (2 * _TARGET_SAMPLE_RATE) * 1000

        logger.info(
            "GoogleTTS synthesized: %.0fms latency, %.0fms audio",
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

    async def _call_api_with_retry(
        self, synthesis_input: Any, voice_params: Any, audio_config: Any, max_retries: int = 3
    ) -> bytes:
        """Call Google Cloud TTS API with retry on transient failures."""
        last_exc: Exception | None = None
        for attempt in range(max_retries):
            try:
                response = await self._client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice_params,
                    audio_config=audio_config,
                )
                raw_audio: bytes = response.audio_content
                if len(raw_audio) > _WAV_HEADER_SIZE:
                    return raw_audio[_WAV_HEADER_SIZE:]
                return raw_audio
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < max_retries - 1:
                    delay = min(1.0 * (2**attempt), 30.0)
                    logger.warning("Google TTS retry %d/%d: %s", attempt + 1, max_retries, exc)
                    await asyncio.sleep(delay)
        from call_operator.exceptions import TTSError

        msg = f"Google TTS failed after {max_retries} attempts"
        raise TTSError(msg) from last_exc
