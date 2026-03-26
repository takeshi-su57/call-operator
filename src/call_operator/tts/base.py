"""Abstract base class for TTS providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from call_operator.adapters.base import AudioChunk


class TTSProvider(ABC):
    """Interface for Text-to-Speech providers."""

    @abstractmethod
    async def synthesize(self, text: str) -> AudioChunk:
        """Convert text to speech audio.

        Returns an AudioChunk containing the synthesized speech.
        """
        ...


def get_tts(provider: str, **kwargs: str) -> TTSProvider:
    """Factory: return the configured TTS provider instance."""
    if provider == "openai":
        from call_operator.tts.openai_tts import OpenAITTS

        return OpenAITTS(**kwargs)
    elif provider == "elevenlabs":
        from call_operator.tts.elevenlabs_tts import ElevenLabsTTS

        return ElevenLabsTTS(**kwargs)
    elif provider == "google":
        from call_operator.tts.google_tts import GoogleTTS

        return GoogleTTS(**kwargs)
    else:
        msg = f"Unknown TTS provider: {provider}"
        raise ValueError(msg)
