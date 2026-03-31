"""Google Cloud TTS provider."""

from __future__ import annotations

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

        response = await self._client.synthesize_speech(
            input=synthesis_input,
            voice=voice_params,
            audio_config=audio_config,
        )

        # LINEAR16 responses include a 44-byte WAV header; strip it.
        raw_audio: bytes = response.audio_content
        pcm_data = raw_audio[_WAV_HEADER_SIZE:] if len(raw_audio) > _WAV_HEADER_SIZE else raw_audio

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
