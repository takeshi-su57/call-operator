# [Feature]: Cloud speech-to-text using Deepgram streaming API

## Description

Implement `DeepgramSTT` — a cloud-based speech-to-text provider using Deepgram's real-time streaming WebSocket API. Audio chunks are streamed to Deepgram over a persistent WebSocket connection, and transcription results are received as they become available. This provides an alternative to local Whisper with potentially better accuracy for real-time streaming.

## Motivation

Cloud STT is essential for production deployments where GPU is unavailable or where Deepgram's Nova-2 model provides better accuracy than local Whisper. Deepgram's streaming API has best-in-class latency for cloud STT (~300ms). Having both local and cloud STT options gives flexibility based on deployment constraints.

## Tasks

- [x] Create `src/call_operator/stt/deepgram_cloud.py` with `DeepgramSTT(STTProvider)`
- [x] Initialize Deepgram SDK client with `DEEPGRAM_API_KEY` from config
- [x] Implement `start()`: open a streaming WebSocket connection to Deepgram with live transcription options
- [x] Configure Deepgram options: model ("nova-2"), language (`STT_LANGUAGE`), smart_format (True), interim_results (True), endpointing (300ms), encoding (linear16), sample_rate from config
- [x] Implement `transcribe(chunk: AudioChunk) -> Transcript | None`: send audio bytes over WebSocket, receive and parse transcription events
- [x] Handle both interim (partial) and final transcription results
- [x] Map Deepgram response to `Transcript` dataclass (text, confidence, is_final)
- [x] Implement `stop()`: send close signal to WebSocket, clean up connection
- [x] Handle WebSocket disconnection: log error, attempt reconnection
- [x] Handle Deepgram errors: quota exceeded, authentication failure, rate limiting
- [x] Implement keepalive: send periodic keepalive messages to prevent timeout

## Acceptance Criteria

- [x] `DeepgramSTT` connects to Deepgram's streaming API on `start()`
- [x] Audio chunks are streamed in real-time over WebSocket
- [x] Interim and final transcriptions are correctly parsed into `Transcript` objects
- [x] Missing or invalid `DEEPGRAM_API_KEY` raises a clear error at init time
- [x] WebSocket disconnection is handled with reconnection logic
- [x] `stop()` cleanly closes the WebSocket connection
- [x] Compatible with the `STTProvider` interface — works as a drop-in replacement for `WhisperLocalSTT`
- [x] All files pass `ruff check` and `mypy --strict`

## Dependencies

- 004 — Audio Capture (`AudioChunk` dataclass)

## Files Created/Modified

- `src/call_operator/stt/deepgram_cloud.py` — full implementation (293 lines)
- `tests/test_deepgram_cloud.py` — 31 unit tests
- `scripts/test_deepgram_live.py` — manual integration test script

## Implementation Notes

- Built against `deepgram-sdk` v6.0.1 (Fern-generated SDK, significantly different from v3)
- Uses `AsyncDeepgramClient` with `api_key=` parameter (not `access_token=`, which uses Bearer auth instead of Token auth)
- Uses `client.listen.v1.connect()` async context manager for WebSocket lifecycle
- Background `start_listening()` task receives messages; `EventType.MESSAGE` handler parses `ListenV1Results`
- `asyncio.Queue` bridges async event callbacks to synchronous-per-chunk `transcribe()` interface
- Reconnection with exponential backoff (0.5s, 1s, 2s) up to 3 attempts
- Keepalive every 8 seconds via `send_keep_alive()`
- `flush()` sends `send_finalize()` and waits up to 2s for final results
