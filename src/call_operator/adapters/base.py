"""Abstract base class for meeting platform adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import TracebackType


@dataclass(frozen=True)
class AudioChunk:
    """A chunk of raw PCM audio data.

    Immutable value object representing a segment of audio captured
    from or to be played into a meeting.
    """

    data: bytes
    sample_rate: int = 16000
    channels: int = 1
    timestamp: float = 0.0
    duration_ms: float = 0.0


class MeetingAdapter(ABC):
    """Interface for meeting platform adapters.

    Each adapter handles connecting to a specific platform (Google Meet, Zoom, etc.),
    reading audio from participants, and playing audio back into the meeting.

    Supports async context manager usage::

        async with SomeAdapter(settings) as adapter:
            data = await adapter.read_audio()
    """

    @abstractmethod
    async def connect(self, url: str) -> None:
        """Connect to a meeting at the given URL."""
        ...

    @abstractmethod
    async def read_audio(self) -> bytes | None:
        """Read the next chunk of raw PCM audio from the meeting.

        Returns raw bytes of PCM audio data, or ``None`` to signal
        end-of-stream (e.g. meeting ended or adapter disconnected).
        """
        ...

    @abstractmethod
    async def play_audio(self, chunk: AudioChunk) -> None:
        """Play an audio chunk into the meeting."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Leave the meeting and clean up resources."""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Return whether the adapter is currently connected to a meeting."""
        ...

    async def __aenter__(self) -> MeetingAdapter:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.disconnect()
