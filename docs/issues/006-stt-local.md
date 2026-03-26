# [Feature]: Local speech-to-text using faster-whisper

## Description

Implement `WhisperLocalSTT` — a local speech-to-text provider using the `faster-whisper` library (CTranslate2-optimized Whisper). Define the base `STTProvider` abstract class. The provider buffers incoming audio chunks, runs transcription in a thread pool (to avoid blocking the async event loop), and yields `Transcript` objects with text, confidence, and timing.

## Motivation

Local STT provides zero-latency transcription without API costs or network dependency. faster-whisper is 4x faster than OpenAI's Whisper with the same accuracy. It is the default STT provider for development and low-latency scenarios. The base class ensures cloud providers (Deepgram) share the same interface.

## Tasks

- [ ] Create `src/call_operator/stt/__init__.py`
- [ ] Create `src/call_operator/stt/base.py` with abstract `STTProvider` class
- [ ] Define `Transcript` dataclass: `text` (str), `confidence` (float), `language` (str), `is_final` (bool), `timestamp` (float)
- [ ] Define abstract methods: `async transcribe(chunk: AudioChunk) -> Transcript | None`, `async start()`, `async stop()`
- [ ] Create `src/call_operator/stt/whisper_local.py` with `WhisperLocalSTT(STTProvider)`
- [ ] Load faster-whisper `WhisperModel` with configurable model size (`WHISPER_MODEL_SIZE`) and compute type (int8 for CPU)
- [ ] Implement audio buffering: accumulate chunks until a minimum duration (e.g., 1 second) before transcribing
- [ ] Run `model.transcribe()` via `asyncio.to_thread()` to avoid blocking the event loop
- [ ] Parse transcription result into `Transcript` object
- [ ] Implement `stt_stage(input_queue: asyncio.Queue[AudioChunk], output_queue: asyncio.Queue[Transcript], provider: STTProvider) -> None`
- [ ] The stage reads audio chunks, passes to provider, forwards non-empty transcripts
- [ ] Handle end-of-stream: flush remaining buffer, transcribe final segment, propagate sentinel
- [ ] Use `STT_LANGUAGE` from config for language hint

## Acceptance Criteria

- [ ] `WhisperLocalSTT` loads the model and transcribes audio to text
- [ ] Transcription runs in a background thread, not blocking the event loop
- [ ] Audio is buffered to avoid transcribing tiny fragments
- [ ] `Transcript` includes confidence score and timing
- [ ] `stt_stage()` correctly bridges the audio queue to the transcript queue
- [ ] End-of-stream flushes the buffer and transcribes remaining audio
- [ ] All files pass `ruff check` and `mypy --strict`

## Dependencies

- 005 — VAD Integration (receives speech-only audio chunks)

## Files to Create/Modify

- `src/call_operator/stt/__init__.py`
- `src/call_operator/stt/base.py`
- `src/call_operator/stt/whisper_local.py`
