"""Shared test fixtures for call-operator."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from call_operator.adapters.base import AudioChunk
from call_operator.config import Settings
from call_operator.stt.base import Transcript


@pytest.fixture
def sample_audio_chunk() -> AudioChunk:
    """A sample audio chunk with dummy PCM data."""
    # 30ms of silence at 16kHz mono (480 samples * 2 bytes)
    return AudioChunk(
        data=b"\x00" * 960,
        sample_rate=16000,
        channels=1,
        timestamp=0.0,
        duration_ms=30.0,
    )


@pytest.fixture
def sample_transcript() -> Transcript:
    """A sample transcript for testing."""
    return Transcript(
        text="Hello, can everyone hear me?",
        speaker="participant_1",
        confidence=0.95,
        is_final=True,
    )


@pytest.fixture
def mock_settings() -> Settings:
    """Settings configured for testing (no real API keys)."""
    with patch.dict(
        "os.environ",
        {
            "LLM_PROVIDER": "openai",
            "LLM_MODEL": "gpt-4o",
            "OPENAI_API_KEY": "test-key-not-real",
            "STT_PROVIDER": "whisper_local",
            "STT_MODEL": "tiny",
            "TTS_PROVIDER": "openai",
            "TTS_VOICE": "alloy",
            "BROWSER_HEADLESS": "true",
            "LOG_LEVEL": "DEBUG",
        },
    ):
        yield Settings()
