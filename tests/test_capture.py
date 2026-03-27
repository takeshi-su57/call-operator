"""Tests for AudioChunk, MeetingAdapter, and capture_stage."""

from __future__ import annotations

import asyncio
from dataclasses import FrozenInstanceError
from unittest.mock import AsyncMock

import pytest

from call_operator.adapters.base import AudioChunk, MeetingAdapter
from call_operator.audio.capture import capture_stage

# ---------------------------------------------------------------------------
# AudioChunk tests
# ---------------------------------------------------------------------------


class TestAudioChunk:
    def test_fields(self) -> None:
        chunk = AudioChunk(
            data=b"\x00" * 960,
            sample_rate=16000,
            channels=1,
            timestamp=1.0,
            duration_ms=30.0,
        )
        assert chunk.data == b"\x00" * 960
        assert chunk.sample_rate == 16000
        assert chunk.channels == 1
        assert chunk.timestamp == 1.0
        assert chunk.duration_ms == 30.0

    def test_defaults(self) -> None:
        chunk = AudioChunk(data=b"\x01\x02")
        assert chunk.sample_rate == 16000
        assert chunk.channels == 1
        assert chunk.timestamp == 0.0
        assert chunk.duration_ms == 0.0

    def test_frozen(self) -> None:
        chunk = AudioChunk(data=b"\x00")
        with pytest.raises(FrozenInstanceError):
            chunk.data = b"\xff"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# MeetingAdapter tests
# ---------------------------------------------------------------------------


class TestMeetingAdapter:
    def test_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            MeetingAdapter()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# capture_stage tests
# ---------------------------------------------------------------------------


def _make_adapter(
    audio_reads: list[bytes | None],
    *,
    connected: bool = True,
) -> MeetingAdapter:
    """Create a mock MeetingAdapter that returns *audio_reads* in sequence."""
    adapter = AsyncMock(spec=MeetingAdapter)
    adapter.read_audio = AsyncMock(side_effect=audio_reads)
    adapter.is_connected = lambda: connected
    # Expose sample_rate / channels so capture_stage helpers can read them.
    adapter.sample_rate = 16000
    adapter.channels = 1
    return adapter


class TestCaptureStage:
    @pytest.mark.asyncio
    async def test_reads_and_queues_chunks(self) -> None:
        raw = b"\x00" * 960  # 30 ms at 16 kHz mono 16-bit
        adapter = _make_adapter([raw, raw, None])
        queue: asyncio.Queue[AudioChunk | None] = asyncio.Queue(maxsize=10)

        await capture_stage(adapter, queue)

        items: list[AudioChunk | None] = []
        while not queue.empty():
            items.append(queue.get_nowait())

        # Two real chunks + sentinel
        assert len(items) == 3
        assert items[0] is not None and items[0].data == raw
        assert items[1] is not None and items[1].data == raw
        assert items[2] is None  # sentinel

    @pytest.mark.asyncio
    async def test_sentinel_on_immediate_none(self) -> None:
        adapter = _make_adapter([None])
        queue: asyncio.Queue[AudioChunk | None] = asyncio.Queue(maxsize=10)

        await capture_stage(adapter, queue)

        assert queue.get_nowait() is None
        assert queue.empty()

    @pytest.mark.asyncio
    async def test_duration_ms_calculated(self) -> None:
        # 480 samples * 2 bytes = 960 bytes → 30 ms at 16 kHz mono
        raw = b"\x00" * 960
        adapter = _make_adapter([raw, None])
        queue: asyncio.Queue[AudioChunk | None] = asyncio.Queue(maxsize=10)

        await capture_stage(adapter, queue)

        chunk = queue.get_nowait()
        assert chunk is not None
        assert chunk.duration_ms == pytest.approx(30.0)

    @pytest.mark.asyncio
    async def test_handles_adapter_error_and_continues(self) -> None:
        raw = b"\x00" * 960
        adapter = _make_adapter([RuntimeError("boom"), raw, None])
        queue: asyncio.Queue[AudioChunk | None] = asyncio.Queue(maxsize=10)

        await capture_stage(adapter, queue)

        items: list[AudioChunk | None] = []
        while not queue.empty():
            items.append(queue.get_nowait())

        # Error skipped, one real chunk + sentinel
        assert len(items) == 2
        assert items[0] is not None and items[0].data == raw
        assert items[1] is None

    @pytest.mark.asyncio
    async def test_stops_when_adapter_disconnects_on_error(self) -> None:
        adapter = _make_adapter(
            [RuntimeError("disconnected")],
            connected=False,
        )
        queue: asyncio.Queue[AudioChunk | None] = asyncio.Queue(maxsize=10)

        await capture_stage(adapter, queue)

        # Only sentinel
        assert queue.get_nowait() is None
        assert queue.empty()
