"""Configuration via Pydantic Settings + environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    openrouter_api_key: str = ""

    # STT
    stt_provider: str = "whisper_local"
    stt_model: str = "tiny"
    deepgram_api_key: str = ""

    # TTS
    tts_provider: str = "openai"
    tts_voice: str = "alloy"
    elevenlabs_api_key: str = ""

    # Browser
    browser_headless: bool = True

    # Logging
    log_level: str = "INFO"

    # Audio
    audio_sample_rate: int = 16000
    vad_threshold: float = 0.5
    record_audio: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
