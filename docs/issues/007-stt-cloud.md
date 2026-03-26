# [Feature]: Cloud speech-to-text using Deepgram streaming API

## Description

Implement `DeepgramSTT` — a cloud-based speech-to-text provider using Deepgram's real-time streaming WebSocket API. Audio chunks are streamed to Deepgram over a persistent WebSocket connection, and transcription results are received as they become available. This provides an alternative to local Whisper with potentially better accuracy for real-time streaming.

## Motivation

Cloud STT is essential for production deployments where GPU is unavailable or where Deepgram's Nova-2 model provides better accuracy than local Whisper. Deepgram's streaming API has best-in-class latency for cloud STT (~300ms). Having both local and cloud STT options gives flexibility based on deployment constraints.

## Tasks

- [ ] Create `src/call_operator/stt/deepgram_cloud.py` with `DeepgramSTT(STTProvider)`
- [ ] Initialize Deepgram SDK client with `DEEPGRAM_API_KEY` from config
- [ ] Implement `start()`: open a streaming WebSocket connection to Deepgram with live transcription options
- [ ] Configure Deepgram options: model ("nova-2"), language (`STT_LANGUAGE`), smart_format (True), interim_results (True), endpointing (300ms), encoding (linear16), sample_rate from config
- [ ] Implement `transcribe(chunk: AudioChunk) -> Transcript | None`: send audio bytes over WebSocket, receive and parse transcription events
- [ ] Handle both interim (partial) and final transcription results
- [ ] Map Deepgram response to `Transcript` dataclass (text, confidence, is_final)
- [ ] Implement `stop()`: send close signal to WebSocket, clean up connection
- [ ] Handle WebSocket disconnection: log error, attempt reconnection
- [ ] Handle Deepgram errors: quota exceeded, authentication failure, rate limiting
- [ ] Implement keepalive: send periodic keepalive messages to prevent timeout

## Acceptance Criteria

- [ ] `DeepgramSTT` connects to Deepgram's streaming API on `start()`
- [ ] Audio chunks are streamed in real-time over WebSocket
- [ ] Interim and final transcriptions are correctly parsed into `Transcript` objects
- [ ] Missing or invalid `DEEPGRAM_API_KEY` raises a clear error at init time
- [ ] WebSocket disconnection is handled with reconnection logic
- [ ] `stop()` cleanly closes the WebSocket connection
- [ ] Compatible with the `STTProvider` interface — works as a drop-in replacement for `WhisperLocalSTT`
- [ ] All files pass `ruff check` and `mypy --strict`

## Dependencies

- 004 — Audio Capture (`AudioChunk` dataclass)

## Files to Create/Modify

- `src/call_operator/stt/deepgram_cloud.py`
