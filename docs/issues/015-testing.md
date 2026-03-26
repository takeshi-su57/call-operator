# [Feature]: Comprehensive test suite

## Description

Build a thorough test suite covering all components: unit tests for each provider and stage, integration tests for the pipeline with mocked providers, and end-to-end tests for the full audio flow. All external I/O (LLM APIs, STT APIs, TTS APIs, Playwright browser) must be mocked in tests.

## Motivation

The pipeline has many moving parts — audio capture, VAD, STT, LLM, TTS, playback — and they must all work together. Without tests, changes to one stage can silently break others. Mocked tests run fast and are deterministic, enabling confident refactoring and CI integration.

## Tasks

- [ ] Create `tests/conftest.py` with shared fixtures:
  - `sample_audio_chunk` — `AudioChunk` with realistic PCM data
  - `sample_transcript` — `Transcript` with test text
  - `mock_adapter` — `AsyncMock` implementing `MeetingAdapter`
  - `mock_llm` — `MagicMock` returning predictable responses
  - `mock_settings` — `Settings` with test values (no real API keys)
- [ ] Create `tests/test_config.py`:
  - Test `Settings` loads from env vars
  - Test default values are applied
  - Test validation catches missing required keys
  - Test `get_settings()` caching
- [ ] Create `tests/test_audio_capture.py`:
  - Test `AudioChunk` dataclass creation and immutability
  - Test `capture_stage` reads from adapter and populates queue
  - Test end-of-stream sentinel propagation
  - Test adapter disconnection handling
- [ ] Create `tests/test_vad.py`:
  - Test `VoiceActivityDetector` loads model (mocked torch.hub)
  - Test `detect()` returns probability
  - Test `vad_stage` forwards speech, drops silence
  - Test speech segment buffering
- [ ] Create `tests/test_stt.py`:
  - Test `WhisperLocalSTT` transcribes audio (mocked faster-whisper)
  - Test audio buffering behavior
  - Test `DeepgramSTT` sends audio over WebSocket (mocked Deepgram SDK)
  - Test `stt_stage` bridges audio to transcript queue
- [ ] Create `tests/test_tts.py`:
  - Test `OpenAITTS.synthesize()` returns AudioChunk (mocked OpenAI)
  - Test `ElevenLabsTTS.synthesize()` returns AudioChunk (mocked ElevenLabs)
  - Test `GoogleTTS.synthesize()` returns AudioChunk (mocked Google)
  - Test `get_tts_provider()` factory
  - Test `tts_stage` bridges text to AudioChunk queue
- [ ] Create `tests/test_conversation.py`:
  - Test `ConversationEngine` maintains history
  - Test `process_transcript()` calls LLM and returns response
  - Test context window management (history trimming)
  - Test `conversation_stage` processes only final transcripts
- [ ] Create `tests/test_llm_provider.py`:
  - Test `get_llm()` returns correct provider type for each config
  - Test missing API key raises error
  - Test unknown provider raises error
- [ ] Create `tests/test_pipeline.py` (integration):
  - Test `Pipeline` initialization with mocked providers
  - Test `start()` and `stop()` lifecycle
  - Test data flows through all queues with mocked stages
  - Test graceful shutdown on task failure
  - Test `KeyboardInterrupt` handling
- [ ] Create `tests/test_google_meet_adapter.py`:
  - Test `connect()` launches browser (mocked Playwright)
  - Test pre-join UI handling (mocked page interactions)
  - Test `read_audio()` returns bytes
  - Test `disconnect()` cleans up
- [ ] Ensure all tests are async-compatible using `pytest-asyncio`
- [ ] Add `pytest.ini` or `pyproject.toml` pytest config: asyncio_mode = "auto"
- [ ] Verify `pytest --cov=call_operator` shows coverage report

## Acceptance Criteria

- [ ] `pytest` runs all tests and passes
- [ ] No test makes real API calls or launches a real browser
- [ ] All async tests use `pytest-asyncio`
- [ ] Coverage is at least 70% across the package
- [ ] Each module has at least one corresponding test file
- [ ] Fixtures are reusable and defined in `conftest.py`
- [ ] Tests are deterministic — no flaky tests due to timing
- [ ] All test files pass `ruff check` and `mypy --strict`

## Dependencies

- 010 — Async Pipeline (all components must exist to test)

## Files to Create/Modify

- `tests/conftest.py`
- `tests/test_config.py`
- `tests/test_audio_capture.py`
- `tests/test_vad.py`
- `tests/test_stt.py`
- `tests/test_tts.py`
- `tests/test_conversation.py`
- `tests/test_llm_provider.py`
- `tests/test_pipeline.py`
- `tests/test_google_meet_adapter.py`
- `pyproject.toml` (pytest config section)
