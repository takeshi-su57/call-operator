# [Feature]: Audio capture stage with AudioChunk dataclass and async queue

## Description

Implement the first stage of the audio pipeline: capturing raw audio from a meeting adapter and pushing `AudioChunk` objects into an `asyncio.Queue`. Define the `AudioChunk` dataclass that represents a chunk of PCM audio with metadata. Define the base `MeetingAdapter` abstract class that all meeting adapters implement. Implement `capture_stage()` as an async function that reads from the adapter and writes to the next queue.

## Motivation

Audio capture is the entry point of the entire pipeline. Every downstream stage (VAD, STT, LLM, TTS) depends on a steady stream of audio chunks. The adapter abstraction allows supporting Google Meet now and other platforms later.

## Tasks

- [ ] Create `src/call_operator/audio/__init__.py`
- [ ] Create `src/call_operator/audio/capture.py`
- [ ] Define `AudioChunk` dataclass with fields: `data` (bytes), `sample_rate` (int), `channels` (int), `timestamp` (float), `duration_ms` (float)
- [ ] Implement `capture_stage(adapter: MeetingAdapter, output_queue: asyncio.Queue[AudioChunk]) -> None`
- [ ] The stage loops: calls `adapter.read_audio()`, wraps result in `AudioChunk`, puts on queue
- [ ] Handle adapter disconnection gracefully — log and attempt to continue
- [ ] Use a sentinel value (`None`) on the queue to signal end-of-stream
- [ ] Create `src/call_operator/adapters/__init__.py`
- [ ] Create `src/call_operator/adapters/base.py` with abstract `MeetingAdapter` class
- [ ] Define abstract methods: `async connect(url: str)`, `async read_audio() -> bytes | None`, `async play_audio(chunk: AudioChunk)`, `async disconnect()`, `is_connected() -> bool`
- [ ] Add `__aenter__` and `__aexit__` to `MeetingAdapter` for context manager support

## Acceptance Criteria

- [ ] `AudioChunk` can be instantiated with all fields and is immutable (frozen dataclass)
- [ ] `MeetingAdapter` is abstract and cannot be instantiated directly
- [ ] `capture_stage()` reads from adapter and populates the output queue
- [ ] When `read_audio()` returns `None`, capture stage puts sentinel and exits
- [ ] Queue backpressure is handled (bounded queue with configurable max size)
- [ ] All files pass `ruff check` and `mypy --strict`

## Dependencies

- 001 — Project Setup (package structure must exist)

## Files to Create/Modify

- `src/call_operator/audio/__init__.py`
- `src/call_operator/audio/capture.py`
- `src/call_operator/adapters/__init__.py`
- `src/call_operator/adapters/base.py`
