"""Tests for configuration loading."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from call_operator.config import Settings


class TestSettings:
    def test_defaults(self) -> None:
        settings = Settings(openai_api_key="test-key", _env_file=None)
        assert settings.llm_provider == "openai"
        assert settings.stt_provider == "whisper_local"
        assert settings.tts_provider == "openai"
        assert settings.browser_headless is True
        assert settings.audio_sample_rate == 16000

    def test_new_field_defaults(self) -> None:
        settings = Settings(openai_api_key="test-key", _env_file=None)
        assert settings.llm_temperature == 0.7
        assert settings.stt_language == "en"
        assert settings.tts_speed == 1.0
        assert settings.browser_timeout == 30000
        assert settings.audio_chunk_ms == 30
        assert settings.bot_name == "AI Assistant"

    @patch.dict("os.environ", {"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "test-key"})
    def test_loads_from_env(self) -> None:
        settings = Settings(_env_file=None)
        assert settings.llm_provider == "anthropic"
        assert settings.anthropic_api_key == "test-key"

    @patch.dict("os.environ", {"VAD_THRESHOLD": "0.7", "OPENAI_API_KEY": "test-key"})
    def test_vad_threshold_from_env(self) -> None:
        settings = Settings(_env_file=None)
        assert settings.vad_threshold == 0.7

    def test_raises_when_llm_api_key_missing(self) -> None:
        with pytest.raises(ValidationError, match="OPENAI_API_KEY"):
            Settings(llm_provider="openai", openai_api_key="", _env_file=None)

    def test_raises_for_anthropic_without_key(self) -> None:
        with pytest.raises(ValidationError, match="ANTHROPIC_API_KEY"):
            Settings(llm_provider="anthropic", anthropic_api_key="", _env_file=None)

    def test_passes_when_llm_api_key_provided(self) -> None:
        settings = Settings(llm_provider="openai", openai_api_key="sk-xxx", _env_file=None)
        assert settings.openai_api_key == "sk-xxx"
