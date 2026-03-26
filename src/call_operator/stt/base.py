"""Abstract base class for STT providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from call_operator.adapters.base import AudioChunk


@dataclass
class Transcript:
    """A transcribed speech segment."""

    text: str
    speaker: str | None = None
    confidence: float = 0.0
    is_final: bool = True
    metadata: dict[str, str] = field(default_factory=dict)


class STTProvider(ABC):
    """Interface for Speech-to-Text providers."""

    @abstractmethod
    def transcribe_stream(
        self,
        audio_stream: AsyncIterator[AudioChunk],
    ) -> AsyncIterator[Transcript]:
        """Transcribe a stream of audio chunks into text.

        Yields Transcript objects as speech is recognized.
        """
        ...


def get_stt(provider: str, **kwargs: str) -> STTProvider:
    """Factory: return the configured STT provider instance."""
    if provider == "whisper_local":
        from call_operator.stt.whisper_local import WhisperLocalSTT

        return WhisperLocalSTT(**kwargs)
    elif provider == "deepgram":
        from call_operator.stt.deepgram_cloud import DeepgramSTT

        return DeepgramSTT(**kwargs)
    else:
        msg = f"Unknown STT provider: {provider}"
        raise ValueError(msg)
