"""Tests for TTS provider factory."""

from __future__ import annotations

import pytest

from call_operator.tts.base import get_tts
from call_operator.tts.elevenlabs_tts import ElevenLabsTTS
from call_operator.tts.google_tts import GoogleTTS
from call_operator.tts.openai_tts import OpenAITTS


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
