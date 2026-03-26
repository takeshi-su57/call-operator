"""Configuration via Pydantic Settings + environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    llm_temperature: float = 0.7
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    openrouter_api_key: str = ""

    # STT
    stt_provider: str = "whisper_local"
    stt_model: str = "tiny"
    stt_language: str = "en"
    deepgram_api_key: str = ""

    # TTS
    tts_provider: str = "openai"
    tts_voice: str = "alloy"
    tts_speed: float = 1.0
    elevenlabs_api_key: str = ""

    # Browser
    browser_headless: bool = True
    browser_timeout: int = 30000

    # Logging
    log_level: str = "INFO"

    # Audio
    audio_sample_rate: int = 16000
    vad_threshold: float = 0.5
    record_audio: bool = False
    audio_chunk_ms: int = 30

    # Bot
    bot_name: str = "AI Assistant"

    @model_validator(mode="after")
    def _check_llm_api_key(self) -> Settings:
        provider_key_map: dict[str, str] = {
            "openai": "openai_api_key",
            "anthropic": "anthropic_api_key",
            "google": "google_api_key",
            "openrouter": "openrouter_api_key",
        }
        key_field = provider_key_map.get(self.llm_provider)
        if key_field is not None and not getattr(self, key_field):
            msg = f"{key_field.upper()} is required when LLM_PROVIDER={self.llm_provider}"
            raise ValueError(msg)
        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
