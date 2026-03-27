"""Tests for STT provider factory, Transcript, and WhisperLocalSTT."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from call_operator.adapters.base import AudioChunk
from call_operator.stt.base import Transcript, get_stt
from call_operator.stt.deepgram_cloud import DeepgramSTT
from call_operator.stt.whisper_local import WhisperLocalSTT

# ------------------------------------------------------------------
# Factory
# ------------------------------------------------------------------


class TestSTTFactory:
    def test_returns_whisper_local(self) -> None:
        provider = get_stt("whisper_local", model="tiny")
        assert isinstance(provider, WhisperLocalSTT)

    def test_returns_deepgram(self) -> None:
        provider = get_stt("deepgram", api_key="test-key")
        assert isinstance(provider, DeepgramSTT)

    def test_raises_on_unknown_provider(self) -> None:
        with pytest.raises(ValueError, match="Unknown STT provider"):
            get_stt("unknown_provider")


# ------------------------------------------------------------------
# Transcript
# ------------------------------------------------------------------


class TestTranscript:
    def test_default_values(self) -> None:
        t = Transcript(text="hello")
        assert t.text == "hello"
        assert t.speaker is None
        assert t.confidence == 0.0
        assert t.is_final is True

    def test_language_default(self) -> None:
        t = Transcript(text="hi")
        assert t.language == ""

    def test_timestamp_default(self) -> None:
        t = Transcript(text="hi")
        assert t.timestamp == 0.0

    def test_all_fields(self) -> None:
        t = Transcript(
            text="hello",
            speaker="alice",
            confidence=0.9,
            language="en",
            is_final=True,
            metadata={"key": "val"},
            timestamp=12345.0,
        )
        assert t.text == "hello"
        assert t.speaker == "alice"
        assert t.confidence == 0.9
        assert t.language == "en"
        assert t.is_final is True
        assert t.metadata == {"key": "val"}
        assert t.timestamp == 12345.0


# ------------------------------------------------------------------
# WhisperLocalSTT
# ------------------------------------------------------------------


def _make_chunk(duration_ms: float = 32.0, sample_rate: int = 16000) -> AudioChunk:
    """Create a chunk with the correct byte count for the given duration."""
    num_samples = int(sample_rate * duration_ms / 1000)
    return AudioChunk(
        data=b"\x00" * (num_samples * 2),
        sample_rate=sample_rate,
        channels=1,
        timestamp=0.0,
        duration_ms=duration_ms,
    )


def _fake_segment(text: str = "hello", avg_logprob: float = -0.3) -> SimpleNamespace:
    return SimpleNamespace(text=text, avg_logprob=avg_logprob)


def _fake_info(language: str = "en") -> SimpleNamespace:
    return SimpleNamespace(language=language)


class TestWhisperLocalSTT:
    @pytest.mark.asyncio
    async def test_start_loads_model(self) -> None:
        stt = WhisperLocalSTT(model="tiny", language="en")
        mock_model = MagicMock()

        with patch.object(stt, "_load_model", return_value=mock_model):
            await stt.start()

        assert stt._model is mock_model

    @pytest.mark.asyncio
    async def test_start_is_idempotent(self) -> None:
        stt = WhisperLocalSTT()
        stt._model = MagicMock()  # already loaded

        with patch.object(stt, "_load_model") as mock_load:
            await stt.start()

        mock_load.assert_not_called()

    @pytest.mark.asyncio
    async def test_transcribe_buffers_until_min_duration(self) -> None:
        stt = WhisperLocalSTT()
        stt._model = MagicMock()

        # 32ms chunk — well below the 1000ms minimum
        chunk = _make_chunk(duration_ms=32.0)
        result = await stt.transcribe(chunk)
        assert result is None
        assert stt._buffer_duration_ms == pytest.approx(32.0)

    @pytest.mark.asyncio
    async def test_transcribe_runs_when_buffer_full(self) -> None:
        stt = WhisperLocalSTT()
        mock_model = MagicMock()
        segments = [_fake_segment("hello world")]
        info = _fake_info("en")
        mock_model.transcribe.return_value = (iter(segments), info)
        stt._model = mock_model

        # Feed a single large chunk (1100ms)
        chunk = _make_chunk(duration_ms=1100.0)
        result = await stt.transcribe(chunk)

        assert result is not None
        assert result.text == "hello world"
        assert result.language == "en"
        assert result.is_final is True
        assert result.confidence > 0.0
        assert result.timestamp > 0.0

    @pytest.mark.asyncio
    async def test_transcribe_returns_none_for_empty_segments(self) -> None:
        stt = WhisperLocalSTT()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = (iter([]), _fake_info())
        stt._model = mock_model

        chunk = _make_chunk(duration_ms=1100.0)
        result = await stt.transcribe(chunk)
        assert result is None

    @pytest.mark.asyncio
    async def test_flush_transcribes_remaining_buffer(self) -> None:
        stt = WhisperLocalSTT()
        mock_model = MagicMock()
        segments = [_fake_segment("final words")]
        mock_model.transcribe.return_value = (iter(segments), _fake_info())
        stt._model = mock_model

        # Buffer a small chunk (below threshold)
        chunk = _make_chunk(duration_ms=200.0)
        await stt.transcribe(chunk)
        assert stt._buffer  # still buffered

        result = await stt.flush()
        assert result is not None
        assert result.text == "final words"
        assert not stt._buffer

    @pytest.mark.asyncio
    async def test_flush_returns_none_when_empty(self) -> None:
        stt = WhisperLocalSTT()
        stt._model = MagicMock()
        result = await stt.flush()
        assert result is None

    @pytest.mark.asyncio
    async def test_stop_clears_state(self) -> None:
        stt = WhisperLocalSTT()
        stt._model = MagicMock()
        stt._buffer = [b"\x00" * 100]
        stt._buffer_duration_ms = 500.0

        await stt.stop()

        assert stt._model is None
        assert stt._buffer == []
        assert stt._buffer_duration_ms == 0.0

    @pytest.mark.asyncio
    async def test_chunk_duration_computed_from_data_length(self) -> None:
        stt = WhisperLocalSTT()
        stt._model = MagicMock()

        # Chunk with duration_ms=0 — should compute from data length
        chunk = AudioChunk(
            data=b"\x00" * 3200,  # 1600 samples = 100ms at 16kHz
            sample_rate=16000,
            channels=1,
            timestamp=0.0,
            duration_ms=0.0,
        )
        await stt.transcribe(chunk)
        assert stt._buffer_duration_ms == pytest.approx(100.0)
