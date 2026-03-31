"""Live smoke tests for TTS providers — require real API keys.

Run with:
    uv run pytest tests/test_tts_live.py -v -s

Skip individual providers via env vars:
    SKIP_OPENAI_TTS=1    — skip OpenAI tests
    SKIP_ELEVENLABS_TTS=1 — skip ElevenLabs tests
    SKIP_GOOGLE_TTS=1     — skip Google Cloud tests

These tests are NOT run in CI. They call real APIs and cost money.
"""

from __future__ import annotations

import os

import pytest

from call_operator.adapters.base import AudioChunk

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_TEXT = "Hello, this is a smoke test for text to speech."
_MIN_PCM_BYTES = 100  # any real audio will be much larger


def _skip_if(env_var: str, reason: str) -> None:
    if os.environ.get(env_var):
        pytest.skip(reason)


def _assert_valid_audio(chunk: AudioChunk) -> None:
    assert isinstance(chunk, AudioChunk)
    assert len(chunk.data) > _MIN_PCM_BYTES, f"Audio too short: {len(chunk.data)} bytes"
    assert chunk.sample_rate == 16000
    assert chunk.channels == 1
    assert chunk.duration_ms > 0


# ---------------------------------------------------------------------------
# OpenAI TTS
# ---------------------------------------------------------------------------


class TestOpenAITTSLive:
    @pytest.fixture(autouse=True)
    def _guard(self) -> None:
        _skip_if("SKIP_OPENAI_TTS", "SKIP_OPENAI_TTS is set")
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            pytest.skip("OPENAI_API_KEY not set")

    async def test_synthesize_returns_audio(self) -> None:
        from call_operator.tts.openai_tts import OpenAITTS

        tts = OpenAITTS(api_key=os.environ["OPENAI_API_KEY"])
        await tts.start()
        try:
            chunk = await tts.synthesize(_SAMPLE_TEXT)
            _assert_valid_audio(chunk)
        finally:
            await tts.stop()

    async def test_voice_and_speed(self) -> None:
        from call_operator.tts.openai_tts import OpenAITTS

        tts = OpenAITTS(
            api_key=os.environ["OPENAI_API_KEY"],
            voice="nova",
            speed="1.25",
        )
        await tts.start()
        try:
            chunk = await tts.synthesize(_SAMPLE_TEXT)
            _assert_valid_audio(chunk)
        finally:
            await tts.stop()


# ---------------------------------------------------------------------------
# ElevenLabs TTS
# ---------------------------------------------------------------------------


class TestElevenLabsTTSLive:
    @pytest.fixture(autouse=True)
    def _guard(self) -> None:
        _skip_if("SKIP_ELEVENLABS_TTS", "SKIP_ELEVENLABS_TTS is set")
        api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        if not api_key:
            pytest.skip("ELEVENLABS_API_KEY not set")

    async def test_synthesize_returns_audio(self) -> None:
        from call_operator.tts.elevenlabs_tts import ElevenLabsTTS

        tts = ElevenLabsTTS(api_key=os.environ["ELEVENLABS_API_KEY"])
        await tts.start()
        try:
            chunk = await tts.synthesize(_SAMPLE_TEXT)
            _assert_valid_audio(chunk)
        finally:
            await tts.stop()

    async def test_voice_settings(self) -> None:
        from call_operator.tts.elevenlabs_tts import ElevenLabsTTS

        tts = ElevenLabsTTS(
            api_key=os.environ["ELEVENLABS_API_KEY"],
            stability="0.8",
            similarity_boost="0.9",
            style="0.3",
        )
        await tts.start()
        try:
            chunk = await tts.synthesize(_SAMPLE_TEXT)
            _assert_valid_audio(chunk)
        finally:
            await tts.stop()


# ---------------------------------------------------------------------------
# Google Cloud TTS
# ---------------------------------------------------------------------------


class TestGoogleTTSLive:
    @pytest.fixture(autouse=True)
    def _guard(self) -> None:
        _skip_if("SKIP_GOOGLE_TTS", "SKIP_GOOGLE_TTS is set")
        # Google uses ADC — check for credentials file or metadata server.
        if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") and not os.environ.get(
            "GOOGLE_CLOUD_PROJECT"
        ):
            pytest.skip("No Google Cloud credentials found")

    async def test_synthesize_returns_audio(self) -> None:
        from call_operator.tts.google_tts import GoogleTTS

        tts = GoogleTTS(voice="en-US-Neural2-C")
        await tts.start()
        try:
            chunk = await tts.synthesize(_SAMPLE_TEXT)
            _assert_valid_audio(chunk)
        finally:
            await tts.stop()

    async def test_ssml_input(self) -> None:
        from call_operator.tts.google_tts import GoogleTTS

        tts = GoogleTTS(voice="en-US-Neural2-C")
        await tts.start()
        try:
            ssml = '<speak>Hello, <break time="300ms"/> this is SSML.</speak>'
            chunk = await tts.synthesize(ssml)
            _assert_valid_audio(chunk)
        finally:
            await tts.stop()


# ---------------------------------------------------------------------------
# tts_stage end-to-end
# ---------------------------------------------------------------------------


class TestTTSStageLive:
    @pytest.fixture(autouse=True)
    def _guard(self) -> None:
        _skip_if("SKIP_OPENAI_TTS", "SKIP_OPENAI_TTS is set")
        if not os.environ.get("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set")

    async def test_stage_processes_queue(self) -> None:
        import asyncio

        from call_operator.tts import tts_stage
        from call_operator.tts.openai_tts import OpenAITTS

        provider = OpenAITTS(api_key=os.environ["OPENAI_API_KEY"])
        in_q: asyncio.Queue[str | None] = asyncio.Queue()
        out_q: asyncio.Queue[AudioChunk | None] = asyncio.Queue()

        await in_q.put("First sentence.")
        await in_q.put("Second sentence.")
        await in_q.put(None)

        await tts_stage(in_q, out_q, provider)

        results: list[AudioChunk | None] = []
        while not out_q.empty():
            results.append(out_q.get_nowait())

        # Two audio chunks + sentinel
        assert len(results) == 3
        _assert_valid_audio(results[0])  # type: ignore[arg-type]
        _assert_valid_audio(results[1])  # type: ignore[arg-type]
        assert results[2] is None
