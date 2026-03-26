"""Google Cloud TTS provider."""

from __future__ import annotations

import logging

from call_operator.adapters.base import AudioChunk
from call_operator.tts.base import TTSProvider

logger = logging.getLogger(__name__)


class GoogleTTS(TTSProvider):
    """Text-to-Speech using Google Cloud Text-to-Speech API."""

    def __init__(self, voice: str = "en-US-Neural2-C", **kwargs: str) -> None:
        self.voice = voice

    async def synthesize(self, text: str) -> AudioChunk:
        """Convert text to speech using Google Cloud TTS."""
        # TODO: Call Google Cloud TTS API
        # TODO: Convert response audio to PCM format
        # TODO: Return AudioChunk
        logger.warning("GoogleTTS.synthesize() is not yet implemented.")
        return AudioChunk(data=b"", sample_rate=16000)
