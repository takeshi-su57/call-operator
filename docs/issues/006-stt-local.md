# [Feature]: Local speech-to-text using faster-whisper

## Description

Implement `WhisperLocalSTT` — a local speech-to-text provider using the `faster-whisper` library (CTranslate2-optimized Whisper). Define the base `STTProvider` abstract class with a chunk-at-a-time interface. The provider buffers incoming audio chunks, runs transcription in a thread pool (to avoid blocking the async event loop), and returns `Transcript` objects with text, confidence, language, and timing.

## Motivation

Local STT provides zero-latency transcription without API costs or network dependency. faster-whisper is 4x faster than OpenAI's Whisper with the same accuracy. It is the default STT provider for development and low-latency scenarios. The base class ensures cloud providers (Deepgram) share the same interface.

## Tasks

- [x] Create `src/call_operator/stt/__init__.py` with `stt_stage()` pipeline function
- [x] Revise `src/call_operator/stt/base.py` — chunk-at-a-time `STTProvider` interface (`start`, `transcribe`, `flush`, `stop`)
- [x] Define `Transcript` dataclass: `text` (str), `speaker` (str|None), `confidence` (float), `language` (str), `is_final` (bool), `metadata` (dict), `timestamp` (float)
- [x] Create `src/call_operator/stt/whisper_local.py` with `WhisperLocalSTT(STTProvider)`
- [x] Load faster-whisper `WhisperModel` with configurable model size (`STT_MODEL`, default "tiny") and compute type (int8 for CPU)
- [x] Implement audio buffering: accumulate chunks until minimum duration (1 second) before transcribing
- [x] Run `model.transcribe()` via `asyncio.to_thread()` to avoid blocking the event loop
- [x] Parse transcription result into `Transcript` object with confidence from `avg_logprob`
- [x] Implement `stt_stage(in_queue, out_queue, provider)` pipeline function
- [x] The stage reads audio chunks, passes to provider, forwards non-empty transcripts
- [x] Handle end-of-stream: flush remaining buffer, transcribe final segment, propagate sentinel
- [x] `WhisperLocalSTT` accepts `language` parameter (from `STT_LANGUAGE` config) as transcription hint
- [x] Update `DeepgramSTT` stub to match new chunk-at-a-time interface
- [x] Add logging rule (`.claude/rules/logging.md`) for LLM calls and pipeline stages
- [x] Add comprehensive unit tests for `WhisperLocalSTT` and `stt_stage`

## Acceptance Criteria

- [x] `WhisperLocalSTT` loads the model and transcribes audio to text
- [x] Transcription runs in a background thread, not blocking the event loop
- [x] Audio is buffered to avoid transcribing tiny fragments (1s minimum)
- [x] `Transcript` includes confidence score, language, and timing
- [x] `stt_stage()` correctly bridges the audio queue to the transcript queue
- [x] End-of-stream flushes the buffer and transcribes remaining audio
- [x] All files pass `ruff check` and `mypy --strict`
- [x] 22 tests passing (10 unit + 6 stage integration + 6 existing)

## Implementation Notes

- **Interface change**: Replaced `transcribe_stream(AsyncIterator) -> AsyncIterator` with chunk-at-a-time `transcribe(chunk) -> Transcript | None`. This matches the queue-based pipeline pattern used by `vad_stage` and avoids iterator threading issues.
- **`flush()` method**: Non-abstract with default `return None`. Providers override if they buffer audio (WhisperLocalSTT does, Deepgram may not need to).
- **Confidence mapping**: `math.exp(avg_logprob)` clamped to [0.0, 1.0]. A logprob of 0.0 → 1.0 confidence; -1.0 → ~0.37.
- **Duration fallback**: If `AudioChunk.duration_ms` is 0, computed from `len(data) / (2 * sample_rate) * 1000`.
- **Config wiring**: `get_stt()` factory accepts `**kwargs` — pipeline caller passes `model=settings.stt_model, language=settings.stt_language`. Full pipeline wiring is deferred to pipeline.py implementation.

## Dependencies

- 005 — VAD Integration (receives speech-only audio chunks)

## Files Created/Modified

- `src/call_operator/stt/__init__.py` — `stt_stage()` pipeline function
- `src/call_operator/stt/base.py` — Revised `STTProvider` ABC + extended `Transcript`
- `src/call_operator/stt/whisper_local.py` — Full `WhisperLocalSTT` implementation
- `src/call_operator/stt/deepgram_cloud.py` — Updated stub for new interface
- `tests/test_stt.py` — Extended with WhisperLocalSTT unit tests
- `tests/test_stt_stage.py` — New: stt_stage integration tests
- `.claude/rules/logging.md` — New: logging standards for pipeline and LLM calls
- `.claude/CLAUDE.md` — Added logging rule reference
