"""Abstract base class for STT providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from call_operator.adapters.base import AudioChunk


@dataclass
class Transcript:
    """A transcribed speech segment."""

    text: str
    speaker: str | None = None
    confidence: float = 0.0
    language: str = ""
    is_final: bool = True
    metadata: dict[str, str] = field(default_factory=dict)
    timestamp: float = 0.0


class STTProvider(ABC):
    """Interface for Speech-to-Text providers.

    Lifecycle: ``start()`` → ``transcribe()`` (repeated) → ``flush()`` → ``stop()``.
    """

    @abstractmethod
    async def start(self) -> None:
        """Initialize resources (e.g. load model, open connection)."""
        ...

    @abstractmethod
    async def transcribe(self, chunk: AudioChunk) -> Transcript | None:
        """Process one audio chunk.

        Returns a :class:`Transcript` when enough audio has been buffered,
        or ``None`` if still accumulating.
        """
        ...

    async def flush(self) -> Transcript | None:
        """Transcribe any remaining buffered audio.

        Called at end-of-stream. Default returns ``None`` (no buffering).
        """
        return None

    @abstractmethod
    async def stop(self) -> None:
        """Release resources."""
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
