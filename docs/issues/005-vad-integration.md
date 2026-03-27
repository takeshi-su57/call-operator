# [Feature]: Voice Activity Detection using Silero VAD

## Description

Integrate the Silero VAD (Voice Activity Detection) model to distinguish speech from silence in the audio stream. Implement `vad_stage()` that reads `AudioChunk` objects from an input queue, runs them through the VAD model, and forwards only speech-containing segments to the output queue. This prevents sending silence to the STT engine, reducing latency and cost.

## Motivation

Without VAD, the STT engine would process silence, background noise, and non-speech audio, wasting compute and producing garbage transcriptions. VAD acts as a gatekeeper — only speech reaches downstream stages. Silero VAD is lightweight, runs on CPU, and has excellent accuracy.

## Tasks

- [x] Create `src/call_operator/audio/vad.py`
- [x] Implement `VoiceActivityDetector` class
- [x] Load Silero VAD model via `torch.hub.load()` with `trust_repo=True`
- [x] Cache the model instance (load once, reuse)
- [x] Implement `detect(chunk: AudioChunk) -> float` — returns speech probability (0.0 to 1.0)
- [x] Implement `vad_stage(input_queue: asyncio.Queue[AudioChunk], output_queue: asyncio.Queue[AudioChunk], threshold: float) -> None`
- [x] The stage loops: reads from input queue, runs VAD, forwards chunks where probability >= threshold
- [x] Implement speech segment buffering: accumulate consecutive speech chunks into segments, forward complete segments
- [x] Add silence padding: include a small buffer of audio before and after detected speech to avoid clipping
- [x] Handle end-of-stream sentinel: propagate `None` to output queue
- [x] Use `VAD_THRESHOLD` from config (default 0.5)
- [x] Ensure audio is converted to correct format for Silero (16kHz, mono, float32 tensor)
- [x] Log VAD statistics periodically: speech ratio, chunks processed

## Acceptance Criteria

- [x] `VoiceActivityDetector` loads the Silero model without errors
- [x] `detect()` returns a float between 0.0 and 1.0
- [x] `vad_stage()` only forwards chunks exceeding the threshold
- [x] Speech segments include pre/post padding to avoid word clipping
- [x] End-of-stream sentinel is propagated correctly
- [x] Audio format conversion (bytes to float32 tensor) is handled internally
- [x] All files pass `ruff check` and `mypy --strict`

## Implementation Notes

- Silero VAD requires exactly 512 samples at 16kHz (32ms chunks). The `detect()` method handles mismatched chunk sizes via zero-padding or truncation.
- Default `audio_chunk_ms` updated from 30 to 32 to match Silero's 512-sample requirement.
- VAD inference runs via `asyncio.to_thread()` to avoid blocking the event loop.
- Pre-padding (3 chunks) and post-padding (3 chunks) prevent clipping words at speech boundaries.
- Added `torch.*` to mypy overrides in `pyproject.toml` to work around torch stub issues.
- 14 tests cover: model loading, detect output, tensor conversion, reset, speech forwarding, silence dropping, sentinel propagation, pre/post padding, continuous speech, and stats logging.

## Dependencies

- 004 — Audio Capture (`AudioChunk` dataclass and queue pattern)

## Files Created/Modified

- `src/call_operator/audio/vad.py` — full implementation
- `tests/test_vad.py` — 14 comprehensive tests
- `src/call_operator/config.py` — `audio_chunk_ms` default 30 → 32
- `tests/test_config.py` — updated test to match new default
- `pyproject.toml` — added `torch.*` to mypy overrides
