# [Feature]: Configuration system with Pydantic Settings and .env support

## Description

Extend the centralized configuration to cover all runtime knobs needed by the pipeline. The `Settings` class and `get_settings()` factory already exist from issue 001. This issue adds missing settings fields, API key validation, and ensures `.env.example` stays in sync.

## Motivation

Pipeline stages (audio capture, VAD, STT, LLM, TTS) need tuning knobs beyond just provider selection. Adding `LLM_TEMPERATURE`, `STT_LANGUAGE`, `TTS_SPEED`, `BROWSER_TIMEOUT`, `AUDIO_CHUNK_MS`, and `BOT_NAME` now prevents ad-hoc config sprawl later. Validating API keys at startup avoids cryptic errors mid-pipeline.

## Already Done (from issue 001)

- [x] `Settings` class extending `BaseSettings` in `config.py`
- [x] `get_settings()` with `@lru_cache`
- [x] `model_config` with `env_file=".env"`, `env_file_encoding="utf-8"`
- [x] LLM settings: `LLM_PROVIDER`, `LLM_MODEL`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `OPENROUTER_API_KEY`
- [x] STT settings: `STT_PROVIDER`, `STT_MODEL`, `DEEPGRAM_API_KEY`
- [x] TTS settings: `TTS_PROVIDER`, `TTS_VOICE`, `ELEVENLABS_API_KEY`
- [x] Browser settings: `BROWSER_HEADLESS`
- [x] Audio settings: `AUDIO_SAMPLE_RATE`, `VAD_THRESHOLD`, `RECORD_AUDIO`
- [x] Logging: `LOG_LEVEL`
- [x] `.env.example` with all current variables documented
- [x] Tests: defaults, env loading, VAD threshold override

## Remaining Tasks

- [x] Add `llm_temperature: float = 0.7` to Settings
- [x] Add `stt_language: str = "en"` to Settings
- [x] Add `tts_speed: float = 1.0` to Settings
- [x] Add `browser_timeout: int = 30000` to Settings (ms)
- [x] Add `audio_chunk_ms: int = 30` to Settings (VAD frame size)
- [x] Add `bot_name: str = "AI Assistant"` to Settings (display name in meetings)
- [x] Add `@model_validator` that checks the chosen LLM provider has a non-empty API key
- [x] Update `.env.example` with the new variables
- [x] Update `docs/guide/developer.md` env vars table
- [x] Update `README.md` env vars table
- [x] Add tests for new fields and validation error

## Acceptance Criteria

- [x] All new fields have correct defaults and load from env vars
- [x] `Settings(llm_provider="openai", openai_api_key="")` raises `ValidationError`
- [x] `.env.example` documents every setting
- [x] `uv run ruff check src/ tests/` exits 0
- [x] `uv run mypy src/` exits 0 strict
- [x] All tests pass

## Dependencies

- 001 — Project Setup (done)

## Files to Modify

- `src/call_operator/config.py`
- `.env.example`
- `README.md` (env vars table)
- `docs/guide/developer.md` (env vars table)
- `tests/test_config.py`
