"""Tests for configuration loading."""

from __future__ import annotations

from unittest.mock import patch

from call_operator.config import Settings


class TestSettings:
    def test_defaults(self) -> None:
        settings = Settings()
        assert settings.llm_provider == "openai"
        assert settings.stt_provider == "whisper_local"
        assert settings.tts_provider == "openai"
        assert settings.browser_headless is True
        assert settings.audio_sample_rate == 16000

    @patch.dict("os.environ", {"LLM_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "test-key"})
    def test_loads_from_env(self) -> None:
        settings = Settings()
        assert settings.llm_provider == "anthropic"
        assert settings.anthropic_api_key == "test-key"

    @patch.dict("os.environ", {"VAD_THRESHOLD": "0.7"})
    def test_vad_threshold_from_env(self) -> None:
        settings = Settings()
        assert settings.vad_threshold == 0.7
