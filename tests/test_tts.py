"""Tests for TTS provider factory, validation, and pipeline stage."""

from __future__ import annotations

import asyncio

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
