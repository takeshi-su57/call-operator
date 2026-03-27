# [Feature]: Audio capture stage with AudioChunk dataclass and async queue

## Description

Implement the first stage of the audio pipeline: capturing raw audio from a meeting adapter and pushing `AudioChunk` objects into an `asyncio.Queue`. Define the `AudioChunk` dataclass that represents a chunk of PCM audio with metadata. Define the base `MeetingAdapter` abstract class that all meeting adapters implement. Implement `capture_stage()` as an async function that reads from the adapter and writes to the next queue.

## Motivation

Audio capture is the entry point of the entire pipeline. Every downstream stage (VAD, STT, LLM, TTS) depends on a steady stream of audio chunks. The adapter abstraction allows supporting Google Meet now and other platforms later.

## Tasks

- [x] Create `src/call_operator/audio/__init__.py`
- [x] Create `src/call_operator/audio/capture.py`
- [x] Define `AudioChunk` frozen dataclass with fields: `data` (bytes), `sample_rate` (int, default 16000), `channels` (int, default 1), `timestamp` (float, default 0.0), `duration_ms` (float, default 0.0)
- [x] Implement `capture_stage(adapter: MeetingAdapter, output_queue: asyncio.Queue[AudioChunk | None]) -> None`
- [x] The stage loops: calls `adapter.read_audio()`, wraps result in `AudioChunk` with calculated `timestamp` (monotonic) and `duration_ms`, puts on queue
- [x] Handle adapter disconnection gracefully — log error, check `is_connected()`, continue or exit
- [x] Use a sentinel value (`None`) on the queue to signal end-of-stream
- [x] Create `src/call_operator/adapters/__init__.py`
- [x] Create `src/call_operator/adapters/base.py` with abstract `MeetingAdapter` class
- [x] Define abstract methods: `async connect(url: str)`, `async read_audio() -> bytes | None`, `async play_audio(chunk: AudioChunk)`, `async disconnect()`, `is_connected() -> bool`
- [x] Add `__aenter__` and `__aexit__` to `MeetingAdapter` for context manager support
- [x] Update `GoogleMeetAdapter` stub to match new `MeetingAdapter` interface
- [x] Add 9 tests in `tests/test_capture.py` covering AudioChunk, MeetingAdapter, and capture_stage

## Acceptance Criteria

- [x] `AudioChunk` can be instantiated with all fields and is immutable (frozen dataclass)
- [x] `MeetingAdapter` is abstract and cannot be instantiated directly
- [x] `capture_stage()` reads from adapter and populates the output queue
- [x] When `read_audio()` returns `None`, capture stage puts sentinel and exits
- [x] Queue backpressure is handled (bounded queue with configurable max size)
- [x] All files pass `ruff check` and `mypy --strict`

## Dependencies

- 001 — Project Setup (package structure must exist)

## Files Created/Modified

- `src/call_operator/audio/__init__.py` (already existed)
- `src/call_operator/audio/capture.py` — `capture_stage()` implementation
- `src/call_operator/adapters/__init__.py` (already existed)
- `src/call_operator/adapters/base.py` — `AudioChunk` frozen dataclass + `MeetingAdapter` ABC
- `src/call_operator/adapters/google_meet.py` — updated stub to new interface
- `tests/conftest.py` — updated `sample_audio_chunk` fixture with new fields
- `tests/test_capture.py` — 9 tests for AudioChunk, MeetingAdapter, capture_stage
