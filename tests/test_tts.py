"""Tests for TTS provider factory, validation, and pipeline stage."""

from __future__ import annotations

import asyncio
import struct
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from call_operator.adapters.base import AudioChunk
from call_operator.tts import tts_stage
from call_operator.tts.base import TTSProvider, get_tts
from call_operator.tts.elevenlabs_tts import ElevenLabsTTS
from call_operator.tts.google_tts import GoogleTTS
from call_operator.tts.openai_tts import OpenAITTS

# ------------------------------------------------------------------
# Factory tests
# ------------------------------------------------------------------


class TestTTSFactory:
    def test_returns_openai(self) -> None:
        provider = get_tts("openai", api_key="test-key")
        assert isinstance(provider, OpenAITTS)

    def test_returns_elevenlabs(self) -> None:
        provider = get_tts("elevenlabs", api_key="test-key")
        assert isinstance(provider, ElevenLabsTTS)

    def test_returns_google(self) -> None:
        provider = get_tts("google")
        assert isinstance(provider, GoogleTTS)

    def test_raises_on_unknown_provider(self) -> None:
        with pytest.raises(ValueError, match="Unknown TTS provider"):
            get_tts("unknown_provider")


# ------------------------------------------------------------------
# API key validation tests
# ------------------------------------------------------------------


class TestAPIKeyValidation:
    def test_openai_raises_without_api_key(self) -> None:
        with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
            OpenAITTS(api_key="")

    def test_elevenlabs_raises_without_api_key(self) -> None:
        with pytest.raises(ValueError, match="ELEVENLABS_API_KEY is required"):
            ElevenLabsTTS(api_key="")


# ------------------------------------------------------------------
# Fake TTS provider for stage tests
# ------------------------------------------------------------------

_FAKE_AUDIO = AudioChunk(data=b"\x00\x01" * 160, sample_rate=16000, channels=1, duration_ms=10.0)


class FakeTTS(TTSProvider):
    """Deterministic TTS provider for testing the pipeline stage."""

    def __init__(self, *, fail_on: str | None = None) -> None:
        self.started = False
        self.stopped = False
        self.calls: list[str] = []
        self._fail_on = fail_on

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def synthesize(self, text: str) -> AudioChunk:
        self.calls.append(text)
        if self._fail_on is not None and text == self._fail_on:
            msg = "deliberate failure"
            raise RuntimeError(msg)
        return _FAKE_AUDIO


# ------------------------------------------------------------------
# tts_stage tests
# ------------------------------------------------------------------


class TestTTSStage:
    async def test_forwards_audio_chunks(self) -> None:
        in_q: asyncio.Queue[str | None] = asyncio.Queue()
        out_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()
        provider = FakeTTS()

        await in_q.put("Hello")
        await in_q.put("World")
        await in_q.put(None)

        await tts_stage(in_q, out_q, provider)

        results: list[AudioChunk | None] = []
        while not out_q.empty():
            results.append(out_q.get_nowait())

        # Two audio chunks + sentinel
        assert len(results) == 3
        assert results[0] == _FAKE_AUDIO
        assert results[1] == _FAKE_AUDIO
        assert results[2] is None

    async def test_propagates_sentinel(self) -> None:
        in_q: asyncio.Queue[str | None] = asyncio.Queue()
        out_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()
        provider = FakeTTS()

        await in_q.put(None)
        await tts_stage(in_q, out_q, provider)

        assert out_q.get_nowait() is None

    async def test_calls_start_and_stop(self) -> None:
        in_q: asyncio.Queue[str | None] = asyncio.Queue()
        out_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()
        provider = FakeTTS()

        await in_q.put(None)
        await tts_stage(in_q, out_q, provider)

        assert provider.started is True
        assert provider.stopped is True

    async def test_empty_stream(self) -> None:
        in_q: asyncio.Queue[str | None] = asyncio.Queue()
        out_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()
        provider = FakeTTS()

        await in_q.put(None)
        await tts_stage(in_q, out_q, provider)

        assert provider.calls == []
        assert out_q.get_nowait() is None

    async def test_skips_on_synthesis_error(self) -> None:
        in_q: asyncio.Queue[str | None] = asyncio.Queue()
        out_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()
        provider = FakeTTS(fail_on="bad")

        await in_q.put("good")
        await in_q.put("bad")
        await in_q.put("also good")
        await in_q.put(None)

        await tts_stage(in_q, out_q, provider)

        results: list[AudioChunk | None] = []
        while not out_q.empty():
            results.append(out_q.get_nowait())

        # "good" + "also good" produced chunks; "bad" was skipped; then sentinel
        assert len(results) == 3
        assert results[0] == _FAKE_AUDIO
        assert results[1] == _FAKE_AUDIO
        assert results[2] is None
        assert provider.calls == ["good", "bad", "also good"]


# ------------------------------------------------------------------
# Mocked synthesize tests
# ------------------------------------------------------------------


class TestOpenAITTSSynthesize:
    async def test_returns_audio_chunk(self) -> None:
        tts = OpenAITTS(api_key="test-key", voice="alloy")

        # Mock the OpenAI client
        mock_response = MagicMock()
        # 24kHz PCM: 2400 samples = 100ms
        pcm_24k = struct.pack("<2400h", *([1000] * 2400))
        mock_response.read.return_value = pcm_24k

        mock_client = AsyncMock()
        mock_client.audio.speech.create = AsyncMock(return_value=mock_response)
        tts._client = mock_client

        chunk = await tts.synthesize("Hello")

        assert isinstance(chunk, AudioChunk)
        assert len(chunk.data) > 0
        assert chunk.sample_rate == 16000
        mock_client.audio.speech.create.assert_called_once()

    async def test_retry_on_failure(self) -> None:
        tts = OpenAITTS(api_key="test-key")

        mock_response = MagicMock()
        mock_response.read.return_value = struct.pack("<2400h", *([0] * 2400))

        mock_client = AsyncMock()
        mock_client.audio.speech.create = AsyncMock(
            side_effect=[RuntimeError("transient"), mock_response]
        )
        tts._client = mock_client

        with patch("call_operator.tts.openai_tts.asyncio.sleep", new_callable=AsyncMock):
            chunk = await tts.synthesize("Hello")

        assert isinstance(chunk, AudioChunk)
        assert mock_client.audio.speech.create.call_count == 2


class TestElevenLabsTTSSynthesize:
    async def test_returns_audio_chunk(self) -> None:
        tts = ElevenLabsTTS(api_key="test-key", voice="test-voice-id")

        # Mock the client — convert() is sync and returns an async iterator
        pcm_data = b"\x00\x01" * 1600  # 1600 samples

        async def _async_iter() -> AsyncMock:
            yield pcm_data  # type: ignore[misc]

        mock_client = MagicMock()
        mock_client.text_to_speech.convert.return_value = _async_iter()
        tts._client = mock_client

        chunk = await tts.synthesize("Hello")

        assert isinstance(chunk, AudioChunk)
        assert len(chunk.data) > 0
        assert chunk.sample_rate == 16000


class TestGoogleTTSSynthesize:
    async def test_returns_audio_chunk(self) -> None:
        tts = GoogleTTS(voice="en-US-Neural2-C")

        # Mock the Google client
        # Google returns WAV (44-byte header + PCM)
        pcm_data = b"\x00\x01" * 800
        wav_data = b"\x00" * 44 + pcm_data

        mock_response = MagicMock()
        mock_response.audio_content = wav_data

        mock_client = AsyncMock()
        mock_client.synthesize_speech = AsyncMock(return_value=mock_response)
        tts._client = mock_client

        chunk = await tts.synthesize("Hello")

        assert isinstance(chunk, AudioChunk)
        assert chunk.data == pcm_data
        assert chunk.sample_rate == 16000

    async def test_detects_ssml_input(self) -> None:
        tts = GoogleTTS(voice="en-US-Neural2-C")

        mock_response = MagicMock()
        mock_response.audio_content = b"\x00" * 44 + b"\x01" * 100

        mock_client = AsyncMock()
        mock_client.synthesize_speech = AsyncMock(return_value=mock_response)
        tts._client = mock_client

        await tts.synthesize('<speak>Hello <break time="200ms"/> world</speak>')

        call_args = mock_client.synthesize_speech.call_args
        synthesis_input = call_args.kwargs.get("input") or call_args[1].get("input")
        assert synthesis_input.ssml is not None
