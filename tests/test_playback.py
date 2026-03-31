"""Tests for playback_stage."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from call_operator.adapters.base import AudioChunk
from call_operator.audio.playback import playback_stage

_CHUNK = AudioChunk(data=b"\x00\x01" * 160, sample_rate=16000, channels=1, duration_ms=10.0)


class TestPlaybackStage:
    async def test_plays_chunks_and_counts(self) -> None:
        adapter = AsyncMock()
        q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()
        await q.put(_CHUNK)
        await q.put(_CHUNK)
        await q.put(None)

        with patch("call_operator.audio.playback.asyncio.sleep", new_callable=AsyncMock):
            await playback_stage(q, adapter)

        assert adapter.play_audio.call_count == 2

    async def test_sentinel_exits_cleanly(self) -> None:
        adapter = AsyncMock()
        q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()
        await q.put(None)

        await playback_stage(q, adapter)

        adapter.play_audio.assert_not_called()

    async def test_skips_on_play_error(self) -> None:
        adapter = AsyncMock()
        adapter.play_audio.side_effect = [RuntimeError("fail"), None]

        q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()
        await q.put(_CHUNK)
        await q.put(_CHUNK)
        await q.put(None)

        with patch("call_operator.audio.playback.asyncio.sleep", new_callable=AsyncMock):
            await playback_stage(q, adapter)

        assert adapter.play_audio.call_count == 2

    async def test_pacing_sleeps_for_duration(self) -> None:
        adapter = AsyncMock()
        chunk = AudioChunk(data=b"\x00" * 320, sample_rate=16000, channels=1, duration_ms=100.0)
        q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()
        await q.put(chunk)
        await q.put(None)

        sleep_mock = AsyncMock()
        with patch("call_operator.audio.playback.asyncio.sleep", sleep_mock):
            await playback_stage(q, adapter)

        sleep_mock.assert_called_once_with(0.1)
