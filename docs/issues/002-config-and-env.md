# [Feature]: Configuration system with Pydantic Settings and .env support

## Description

Implement centralized configuration management using Pydantic Settings. All runtime configuration (LLM provider keys, STT/TTS provider selection, browser settings, audio parameters) is loaded from environment variables with `.env` file support via python-dotenv. Provide a `get_settings()` factory with caching and a `.env.example` documenting every variable.

## Motivation

The audio pipeline, LLM providers, and browser automation all need configuration. Centralizing it in a typed Settings class prevents hardcoded values, makes testing easier (override via env), and documents all knobs in one place.

## Tasks

- [ ] Create `src/call_operator/config.py` with a `Settings` class extending `BaseSettings`
- [ ] Define LLM settings: `LLM_PROVIDER` (openai/anthropic/google), `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `LLM_MODEL` (model name override), `LLM_TEMPERATURE` (default 0.7)
- [ ] Define STT settings: `STT_PROVIDER` (whisper_local/deepgram), `DEEPGRAM_API_KEY`, `WHISPER_MODEL_SIZE` (default "base"), `STT_LANGUAGE` (default "en")
- [ ] Define TTS settings: `TTS_PROVIDER` (openai/elevenlabs/google), `ELEVENLABS_API_KEY`, `TTS_VOICE` (provider-specific voice ID), `TTS_SPEED` (default 1.0)
- [ ] Define browser settings: `BROWSER_HEADLESS` (default True), `BROWSER_TIMEOUT` (default 30000ms)
- [ ] Define audio settings: `AUDIO_SAMPLE_RATE` (default 16000), `AUDIO_CHANNELS` (default 1), `AUDIO_CHUNK_MS` (default 30), `VAD_THRESHOLD` (default 0.5)
- [ ] Define meeting settings: `MEETING_URL` (Google Meet URL), `BOT_NAME` (display name, default "AI Assistant")
- [ ] Implement `get_settings()` factory function with `@lru_cache` for singleton behavior
- [ ] Configure `model_config` with `env_file=".env"`, `env_file_encoding="utf-8"`, `case_sensitive=False`
- [ ] Create `.env.example` with all variables documented with comments and placeholder values
- [ ] Add validation: at least one LLM API key must be set for the chosen provider

## Acceptance Criteria

- [ ] `from call_operator.config import get_settings` works after install
- [ ] `get_settings()` loads values from environment variables
- [ ] `get_settings()` loads values from `.env` file when present
- [ ] All fields have sensible defaults where applicable
- [ ] Missing required API keys raise a clear validation error
- [ ] `.env.example` documents every setting with comments
- [ ] `mypy src/call_operator/config.py` passes strict

## Dependencies

- 001 — Project Setup (package must be installable)

## Files to Create/Modify

- `src/call_operator/config.py`
- `.env.example`
