"""Tests for Pipeline class and pipeline orchestration."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from call_operator.adapters.base import AudioChunk, MeetingAdapter
from call_operator.config import Settings
from call_operator.pipeline import Pipeline
from call_operator.stt.base import STTProvider, Transcript
from call_operator.tts.base import TTSProvider

# ------------------------------------------------------------------
# Fakes for pipeline testing
# ------------------------------------------------------------------

_CHUNK = AudioChunk(data=b"\x00\x01" * 160, sample_rate=16000, duration_ms=10.0)


class FakeAdapter(MeetingAdapter):
    """Adapter that produces a few chunks then signals end-of-stream."""

    def __init__(self, chunks: int = 2) -> None:
        self._chunks_remaining = chunks
        self._connected = False
        self.played: list[AudioChunk] = []
        self.disconnected = False

    async def connect(self, url: str) -> None:
        self._connected = True

    async def read_audio(self) -> bytes | None:
        if self._chunks_remaining <= 0:
            return None
        self._chunks_remaining -= 1
        await asyncio.sleep(0)  # yield
        return _CHUNK.data

    async def play_audio(self, chunk: AudioChunk) -> None:
        self.played.append(chunk)

    async def disconnect(self) -> None:
        self._connected = False
        self.disconnected = True

    def is_connected(self) -> bool:
        return self._connected


class FakeSTT(STTProvider):
    """STT that converts every chunk into a transcript."""

    async def start(self) -> None:
        pass

    async def transcribe(self, chunk: AudioChunk) -> Transcript | None:
        return Transcript(text="hello", is_final=True)

    async def flush(self) -> Transcript | None:
        return None

    async def stop(self) -> None:
        pass


class FakeTTS(TTSProvider):
    """TTS that returns a fixed audio chunk."""

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def synthesize(self, text: str) -> AudioChunk:
        return _CHUNK


# ------------------------------------------------------------------
# Pipeline tests
# ------------------------------------------------------------------


class TestPipelineInit:
    @patch.dict("os.environ", {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test"})
    def test_creates_queues(self) -> None:
        settings = Settings()
        pipeline = Pipeline(settings)
        assert pipeline._audio_q.maxsize == settings.pipeline_queue_size
        assert pipeline._speech_q.maxsize == settings.pipeline_queue_size

    @patch.dict("os.environ", {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test"})
    def test_not_running_initially(self) -> None:
        settings = Settings()
        pipeline = Pipeline(settings)
        assert pipeline.is_running is False


class TestPipelineStart:
    @patch.dict("os.environ", {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test"})
    async def test_start_connects_adapter(self) -> None:
        settings = Settings()
        pipeline = Pipeline(settings)

        fake_adapter = FakeAdapter()
        with (
            patch(
                "call_operator.adapters.google_meet.GoogleMeetAdapter",
                return_value=fake_adapter,
            ),
            patch("call_operator.stt.base.get_stt", return_value=FakeSTT()),
            patch("call_operator.tts.base.get_tts", return_value=FakeTTS()),
        ):
            await pipeline.start("https://meet.google.com/test")

        assert fake_adapter.is_connected()
        assert pipeline._adapter is fake_adapter
        assert pipeline._stt is not None
        assert pipeline._tts is not None


class TestPipelineStop:
    @patch.dict("os.environ", {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test"})
    async def test_stop_disconnects_adapter(self) -> None:
        settings = Settings()
        pipeline = Pipeline(settings)

        fake_adapter = FakeAdapter()
        fake_adapter._connected = True
        pipeline._adapter = fake_adapter
        pipeline._running = True

        await pipeline.stop()

        assert fake_adapter.disconnected
        assert pipeline.is_running is False

    @patch.dict("os.environ", {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test"})
    async def test_stop_is_idempotent(self) -> None:
        settings = Settings()
        pipeline = Pipeline(settings)
        # stop() on a non-running pipeline should be a no-op
        await pipeline.stop()
        assert pipeline.is_running is False


class TestPipelineRun:
    @patch.dict("os.environ", {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "test"})
    async def test_raises_if_not_started(self) -> None:
        settings = Settings()
        pipeline = Pipeline(settings)
        with pytest.raises(RuntimeError, match="start.*must be called"):
            await pipeline.run()

    @patch.dict(
        "os.environ",
        {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "test",
            "CONVERSATION_DEBOUNCE_MS": "0",
        },
    )
    async def test_full_pipeline_with_fakes(self) -> None:
        """End-to-end test: fake adapter → VAD → fake STT → conversation → fake TTS → playback."""
        settings = Settings()
        pipeline = Pipeline(settings)

        fake_adapter = FakeAdapter(chunks=3)
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content="I hear you.")

        pipeline._adapter = fake_adapter
        pipeline._stt = FakeSTT()
        pipeline._tts = FakeTTS()

        with patch("call_operator.llm.conversation.get_llm", return_value=mock_llm):
            await pipeline.run()

        assert pipeline.is_running is False
        # Adapter should be disconnected after pipeline stops
        assert fake_adapter.disconnected


class TestPipelineSentinelCascade:
    @patch.dict(
        "os.environ",
        {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "test",
            "CONVERSATION_DEBOUNCE_MS": "0",
        },
    )
    async def test_sentinel_propagates_through_all_queues(self) -> None:
        """Put None on audio_q, verify it cascades to playback_q."""
        settings = Settings()
        pipeline = Pipeline(settings)

        fake_adapter = FakeAdapter(chunks=0)  # immediate end-of-stream
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content="test")

        pipeline._adapter = fake_adapter
        pipeline._stt = FakeSTT()
        pipeline._tts = FakeTTS()

        with patch("call_operator.llm.conversation.get_llm", return_value=mock_llm):
            await pipeline.run()

        # All stages should have completed (no hanging tasks)
        assert all(t.done() for t in pipeline._tasks)
