"""Abstract base class for meeting platform adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class AudioChunk:
    """A chunk of raw PCM audio data."""

    data: bytes
    sample_rate: int = 16000
    channels: int = 1


class MeetingAdapter(ABC):
    """Interface for meeting platform adapters.

    Each adapter handles joining a specific platform (Google Meet, Zoom, etc.),
    capturing audio from participants, and playing audio back into the meeting.
    """

    @abstractmethod
    async def join(self, url: str) -> None:
        """Join a meeting at the given URL."""
        ...

    @abstractmethod
    async def capture_audio(self) -> AsyncIterator[AudioChunk]:
        """Yield audio chunks captured from the meeting."""
        ...

    @abstractmethod
    async def play_audio(self, audio: AudioChunk) -> None:
        """Play an audio chunk into the meeting."""
        ...

    @abstractmethod
    async def leave(self) -> None:
        """Leave the meeting and clean up resources."""
        ...
