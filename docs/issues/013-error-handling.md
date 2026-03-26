# [Feature]: Error handling, resilience, and graceful degradation

## Description

Add comprehensive error handling across the entire pipeline: automatic reconnection when the meeting adapter disconnects, retry with exponential backoff for API calls (LLM, STT cloud, TTS), graceful degradation when providers fail (fall back to alternatives or skip), and structured error reporting.

## Motivation

In a real meeting, the agent must be resilient. Network blips, API rate limits, meeting disconnections, and provider outages will happen. The agent should recover automatically when possible and degrade gracefully when recovery is not possible — never crash silently or leave the meeting without explanation.

## Tasks

- [ ] Define custom exception hierarchy in `src/call_operator/exceptions.py`:
  - `CallOperatorError` (base)
  - `AdapterError`, `AdapterDisconnectedError`, `AdapterTimeoutError`
  - `STTError`, `STTProviderUnavailableError`
  - `TTSError`, `TTSProviderUnavailableError`
  - `LLMError`, `LLMProviderUnavailableError`
  - `PipelineError`, `PipelineShutdownError`
- [ ] Implement retry decorator `async_retry(max_retries, base_delay, max_delay, exceptions)`:
  - Exponential backoff with jitter
  - Configurable retryable exception types
  - Logging on each retry attempt
- [ ] Add reconnection logic to `GoogleMeetAdapter`:
  - Detect disconnection (WebSocket close, page crash, removed from meeting)
  - Attempt to rejoin the meeting automatically (up to 3 attempts)
  - Emit events on reconnection success/failure
- [ ] Add retry to LLM calls in `ConversationEngine.process_transcript()`:
  - Retry on rate limit (429), server error (500+), and timeout
  - Fall back to a shorter response on persistent failure ("I'm having trouble responding right now")
- [ ] Add retry to cloud STT (`DeepgramSTT`):
  - Reconnect WebSocket on disconnection
  - Buffer audio during reconnection to avoid data loss
  - Fall back to local Whisper if cloud STT is persistently unavailable
- [ ] Add retry to TTS providers:
  - Retry on API errors
  - Fall back to a different TTS provider if the primary fails
  - Fall back to text-only (log the response instead of speaking) as last resort
- [ ] Add circuit breaker pattern for external APIs:
  - After N consecutive failures, stop calling the API for a cooldown period
  - Automatically retry after cooldown
- [ ] Improve pipeline error handling:
  - If a non-critical stage fails, continue with remaining stages
  - If capture stage fails, attempt adapter reconnection before shutting down
  - If conversation stage fails, log the error and skip the response (don't crash)
- [ ] Add structured error logging: include stage name, error type, retry count, context

## Acceptance Criteria

- [ ] Custom exceptions provide clear error messages with context
- [ ] API calls retry with exponential backoff on transient failures
- [ ] Adapter reconnects automatically on disconnection
- [ ] Pipeline continues operating when a single API call fails
- [ ] Circuit breaker prevents hammering a failing API
- [ ] TTS falls back to alternative provider on failure
- [ ] Cloud STT falls back to local Whisper on persistent failure
- [ ] All error paths are logged with structured context
- [ ] No unhandled exceptions crash the pipeline
- [ ] All files pass `ruff check` and `mypy --strict`

## Dependencies

- 010 — Async Pipeline (pipeline must be functional to add resilience)

## Files to Create/Modify

- `src/call_operator/exceptions.py`
- `src/call_operator/pipeline.py` (error handling in run loop)
- `src/call_operator/adapters/google_meet.py` (reconnection)
- `src/call_operator/stt/deepgram_cloud.py` (retry + fallback)
- `src/call_operator/tts/openai_tts.py` (retry)
- `src/call_operator/tts/elevenlabs_tts.py` (retry)
- `src/call_operator/tts/google_tts.py` (retry)
- `src/call_operator/llm/conversation.py` (retry)
