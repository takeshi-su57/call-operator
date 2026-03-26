"""OpenAI TTS provider."""

from __future__ import annotations

import logging

from call_operator.adapters.base import AudioChunk
from call_operator.tts.base import TTSProvider

logger = logging.getLogger(__name__)


class OpenAITTS(TTSProvider):
    """Text-to-Speech using the OpenAI TTS API."""

    def __init__(self, api_key: str = "", voice: str = "alloy", **kwargs: str) -> None:
        self.api_key = api_key
        self.voice = voice

    async def synthesize(self, text: str) -> AudioChunk:
        """Convert text to speech using OpenAI TTS."""
        # TODO: Call OpenAI TTS API
        # TODO: Convert response audio to PCM format
        # TODO: Return AudioChunk
        logger.warning("OpenAITTS.synthesize() is not yet implemented.")
        return AudioChunk(data=b"", sample_rate=16000)
