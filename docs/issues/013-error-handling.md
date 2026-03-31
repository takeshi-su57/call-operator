# [Feature]: Error handling, resilience, and graceful degradation

## Description

Add comprehensive error handling across the entire pipeline: automatic reconnection when the meeting adapter disconnects, retry with exponential backoff for API calls (LLM, STT cloud, TTS), graceful degradation when providers fail (fall back to alternatives or skip), and structured error reporting.

## Motivation

In a real meeting, the agent must be resilient. Network blips, API rate limits, meeting disconnections, and provider outages will happen. The agent should recover automatically when possible and degrade gracefully when recovery is not possible — never crash silently or leave the meeting without explanation.

## Tasks

- [x] Define custom exception hierarchy in `src/call_operator/exceptions.py`:
  - `CallOperatorError` (base)
  - `AdapterError`, `AdapterDisconnectedError`, `AdapterTimeoutError`
  - `STTError`, `STTProviderUnavailableError`
  - `TTSError`, `TTSProviderUnavailableError`
  - `LLMError`, `LLMProviderUnavailableError`
  - `PipelineError`, `PipelineShutdownError`
- [x] Implement retry decorator `async_retry(max_retries, base_delay, max_delay, exceptions)`:
  - Exponential backoff with jitter (`random.uniform(0.5, 1.5)`)
  - Configurable retryable exception types
  - Logging on each retry attempt (WARNING level)
- [x] Add reconnection logic to `GoogleMeetAdapter`:
  - Detect disconnection (page crash, evaluate error, meeting ended)
  - `_reconnect()` method: disconnect + reconnect with exponential backoff (up to configurable attempts)
  - Auto-reconnect in `read_audio()` on error, continue read loop on success
  - Log reconnection attempts and success/failure
- [x] Add retry to LLM calls in `ConversationEngine.process_transcript()`:
  - Inline retry loop with exponential backoff + jitter
  - Configurable via `RETRY_MAX_ATTEMPTS`, `RETRY_BASE_DELAY`, `RETRY_MAX_DELAY`
  - Fall back to "I'm having trouble responding right now." on persistent failure
  - Fallback message appended to history as AIMessage
- [x] Add retry to cloud STT (`DeepgramSTT`):
  - Existing reconnect logic enhanced with jitter on backoff delays
  - `stt_stage` now wraps `provider.transcribe()` in try/except (was unprotected)
  - Failed chunks are skipped, pipeline continues
- [ ] Cloud STT fallback to local Whisper — **deferred**: requires `stt_stage` to hold a backup provider and swap at runtime (architectural change)
- [x] Add retry to TTS providers:
  - `_call_api_with_retry()` method added to all three providers (OpenAI, ElevenLabs, Google)
  - 3 retries with exponential backoff per API call
  - Raises `TTSError` after retries exhausted (caught by `tts_stage`)
- [ ] TTS fallback to alternative provider — **deferred**: requires `tts_stage` to know about multiple providers (architectural change)
- [x] Add circuit breaker pattern for external APIs:
  - `CircuitBreaker` class: CLOSED → OPEN after N failures, OPEN → HALF_OPEN after cooldown, success → CLOSED
  - Configurable via `CIRCUIT_BREAKER_THRESHOLD` and `CIRCUIT_BREAKER_COOLDOWN`
  - **Note**: class is implemented and tested but not yet wired into provider call paths
- [x] Improve pipeline error handling:
  - `stt_stage`: per-chunk try/except added (was unprotected)
  - `conversation_stage`: already had per-item error handling, now with retry before skip
  - `tts_stage`: already had per-item error handling
  - `_maybe_summarize()`: wrapped in try/except (summarization failure no longer crashes)
  - Pipeline `run()`: structured error logging with exception type awareness (`AdapterError` vs `CallOperatorError` vs generic)
- [x] Add structured error logging:
  - Pipeline logs stage name + exception type + message
  - Retry loops log attempt count, delay, and error
  - Adapter reconnection logs attempt number and delay

## Acceptance Criteria

- [x] Custom exceptions provide clear error messages with context
- [x] API calls retry with exponential backoff on transient failures
- [x] Adapter reconnects automatically on disconnection
- [x] Pipeline continues operating when a single API call fails
- [x] Circuit breaker prevents hammering a failing API (class implemented, not yet wired)
- [ ] TTS falls back to alternative provider on failure — **deferred**
- [ ] Cloud STT falls back to local Whisper on persistent failure — **deferred**
- [x] All error paths are logged with structured context
- [x] No unhandled exceptions crash the pipeline
- [x] All files pass `ruff check` and `mypy --strict`

## Implementation Notes

### Exception hierarchy

```
CallOperatorError(Exception)
├── AdapterError
│   ├── AdapterDisconnectedError
│   └── AdapterTimeoutError
├── STTError
│   └── STTProviderUnavailableError
├── TTSError
│   └── TTSProviderUnavailableError
├── LLMError
│   └── LLMProviderUnavailableError
└── PipelineError
    └── PipelineShutdownError
```

### Retry strategy

All retry uses inline loops (not the decorator) in provider methods for simplicity with `self` parameter under mypy strict. The `async_retry` decorator is available in `retry.py` for standalone functions.

Pattern: exponential backoff `min(base_delay * 2^attempt, max_delay)` with jitter `* random.uniform(0.5, 1.5)`.

### Config additions

| Setting | Default | Description |
|---------|---------|-------------|
| `RETRY_MAX_ATTEMPTS` | 3 | Max retry attempts for API calls |
| `RETRY_BASE_DELAY` | 1.0 | Base delay (seconds) for backoff |
| `RETRY_MAX_DELAY` | 30.0 | Max delay (seconds) cap |
| `CIRCUIT_BREAKER_THRESHOLD` | 5 | Consecutive failures to trip |
| `CIRCUIT_BREAKER_COOLDOWN` | 60.0 | Seconds before half-open |
| `ADAPTER_MAX_RECONNECT_ATTEMPTS` | 3 | Max adapter reconnect tries |

### Deferred items

Three items are deferred as they require architectural changes to stage functions:
1. **TTS provider fallback** — `tts_stage` would need to hold multiple providers
2. **STT cloud→local fallback** — `stt_stage` would need a backup provider
3. **Circuit breaker integration** — providers would need to check `is_open` before calls

The foundation (exception hierarchy, circuit breaker class, retry patterns) is in place for these.

### Testing

- **`tests/test_retry.py`** (NEW): 10 tests — async_retry (5) + CircuitBreaker (5)
- **`tests/test_conversation.py`**: 3 new tests — retry then succeed, retry exhausted fallback, summarization error handling
- **`tests/test_deepgram_cloud.py`**: updated backoff test for jitter ranges

## Dependencies

- 010 — Async Pipeline (pipeline must be functional to add resilience)

## Files Created/Modified

- `src/call_operator/exceptions.py` — NEW: 10 custom exception classes
- `src/call_operator/retry.py` — NEW: `async_retry` decorator + `CircuitBreaker` class
- `src/call_operator/config.py` — 6 new resilience settings
- `.env.example` — resilience env vars section
- `src/call_operator/llm/conversation.py` — LLM retry + fallback + summarization error handling
- `src/call_operator/tts/openai_tts.py` — `_call_api_with_retry`, raises `TTSError`
- `src/call_operator/tts/elevenlabs_tts.py` — same pattern
- `src/call_operator/tts/google_tts.py` — same pattern
- `src/call_operator/adapters/google_meet.py` — `_reconnect()`, auto-reconnect in `read_audio`
- `src/call_operator/pipeline.py` — structured error logging with exception types
- `src/call_operator/stt/__init__.py` — per-chunk try/except in `stt_stage`
- `src/call_operator/stt/deepgram_cloud.py` — jitter in reconnect backoff
- `tests/test_retry.py` — NEW: 10 tests
- `tests/test_conversation.py` — 3 new retry/fallback tests
- `tests/test_deepgram_cloud.py` — updated backoff test for jitter
