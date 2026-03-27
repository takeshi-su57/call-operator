"""Tests for the stt_stage pipeline function."""

from __future__ import annotations

import asyncio

import pytest

from call_operator.adapters.base import AudioChunk
from call_operator.stt import stt_stage
from call_operator.stt.base import STTProvider, Transcript

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_chunk(duration_ms: float = 32.0) -> AudioChunk:
    num_samples = int(16000 * duration_ms / 1000)
    return AudioChunk(
        data=b"\x00" * (num_samples * 2),
        sample_rate=16000,
        channels=1,
        duration_ms=duration_ms,
    )


async def _collect(queue: asyncio.Queue[Transcript | None]) -> list[Transcript]:
    """Drain non-None items from the queue until the sentinel."""
    items: list[Transcript] = []
    while True:
        item = await asyncio.wait_for(queue.get(), timeout=2.0)
        if item is None:
            break
        items.append(item)
    return items


# ------------------------------------------------------------------
# Fake provider for testing
# ------------------------------------------------------------------


class FakeSTT(STTProvider):
    """Deterministic STT provider for testing the stage wiring."""

    def __init__(
        self,
        transcribe_results: list[Transcript | None] | None = None,
        flush_result: Transcript | None = None,
    ) -> None:
        self.transcribe_results = list(transcribe_results or [])
        self.flush_result = flush_result
        self._call_index = 0
        self.started = False
        self.stopped = False
        self.transcribe_calls = 0
        self.flush_called = False

    async def start(self) -> None:
        self.started = True

    async def transcribe(self, chunk: AudioChunk) -> Transcript | None:
        self.transcribe_calls += 1
        if self._call_index < len(self.transcribe_results):
            result = self.transcribe_results[self._call_index]
            self._call_index += 1
            return result
        return None

    async def flush(self) -> Transcript | None:
        self.flush_called = True
        return self.flush_result

    async def stop(self) -> None:
        self.stopped = True


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


class TestSttStage:
    @pytest.mark.asyncio
    async def test_forwards_transcripts(self) -> None:
        t1 = Transcript(text="hello")
        t2 = Transcript(text="world")
        provider = FakeSTT(transcribe_results=[t1, t2])

        in_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()
        out_q: asyncio.Queue[Transcript | None] = asyncio.Queue()

        await in_q.put(_make_chunk())
        await in_q.put(_make_chunk())
        await in_q.put(None)

        await stt_stage(in_q, out_q, provider)
        results = await _collect(out_q)

        assert len(results) == 2
        assert results[0].text == "hello"
        assert results[1].text == "world"

    @pytest.mark.asyncio
    async def test_skips_none_results(self) -> None:
        t1 = Transcript(text="only one")
        provider = FakeSTT(transcribe_results=[None, t1, None])

        in_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()
        out_q: asyncio.Queue[Transcript | None] = asyncio.Queue()

        await in_q.put(_make_chunk())
        await in_q.put(_make_chunk())
        await in_q.put(_make_chunk())
        await in_q.put(None)

        await stt_stage(in_q, out_q, provider)
        results = await _collect(out_q)

        assert len(results) == 1
        assert results[0].text == "only one"

    @pytest.mark.asyncio
    async def test_propagates_sentinel(self) -> None:
        provider = FakeSTT()

        in_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()
        out_q: asyncio.Queue[Transcript | None] = asyncio.Queue()

        await in_q.put(_make_chunk())
        await in_q.put(None)

        await stt_stage(in_q, out_q, provider)

        # The sentinel (None) must appear in the output
        items: list[Transcript | None] = []
        while not out_q.empty():
            items.append(out_q.get_nowait())
        assert None in items

    @pytest.mark.asyncio
    async def test_flushes_on_end_of_stream(self) -> None:
        flush_transcript = Transcript(text="flushed")
        provider = FakeSTT(flush_result=flush_transcript)

        in_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()
        out_q: asyncio.Queue[Transcript | None] = asyncio.Queue()

        await in_q.put(_make_chunk())
        await in_q.put(None)

        await stt_stage(in_q, out_q, provider)

        assert provider.flush_called
        results = await _collect(out_q)
        assert len(results) == 1
        assert results[0].text == "flushed"

    @pytest.mark.asyncio
    async def test_calls_start_and_stop(self) -> None:
        provider = FakeSTT()

        in_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()
        out_q: asyncio.Queue[Transcript | None] = asyncio.Queue()

        await in_q.put(None)

        await stt_stage(in_q, out_q, provider)

        assert provider.started
        assert provider.stopped

    @pytest.mark.asyncio
    async def test_empty_stream(self) -> None:
        """Only a sentinel in — only a sentinel out, no transcripts."""
        provider = FakeSTT()

        in_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()
        out_q: asyncio.Queue[Transcript | None] = asyncio.Queue()

        await in_q.put(None)

        await stt_stage(in_q, out_q, provider)

        assert provider.transcribe_calls == 0
        assert provider.flush_called
        # Output should contain only the sentinel
        item = out_q.get_nowait()
        assert item is None
        assert out_q.empty()
