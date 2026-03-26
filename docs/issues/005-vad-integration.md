# [Feature]: Voice Activity Detection using Silero VAD

## Description

Integrate the Silero VAD (Voice Activity Detection) model to distinguish speech from silence in the audio stream. Implement `vad_stage()` that reads `AudioChunk` objects from an input queue, runs them through the VAD model, and forwards only speech-containing segments to the output queue. This prevents sending silence to the STT engine, reducing latency and cost.

## Motivation

Without VAD, the STT engine would process silence, background noise, and non-speech audio, wasting compute and producing garbage transcriptions. VAD acts as a gatekeeper — only speech reaches downstream stages. Silero VAD is lightweight, runs on CPU, and has excellent accuracy.

## Tasks

- [ ] Create `src/call_operator/audio/vad.py`
- [ ] Implement `VoiceActivityDetector` class
- [ ] Load Silero VAD model via `torch.hub.load()` with `trust_repo=True`
- [ ] Cache the model instance (load once, reuse)
- [ ] Implement `detect(chunk: AudioChunk) -> float` — returns speech probability (0.0 to 1.0)
- [ ] Implement `vad_stage(input_queue: asyncio.Queue[AudioChunk], output_queue: asyncio.Queue[AudioChunk], threshold: float) -> None`
- [ ] The stage loops: reads from input queue, runs VAD, forwards chunks where probability >= threshold
- [ ] Implement speech segment buffering: accumulate consecutive speech chunks into segments, forward complete segments
- [ ] Add silence padding: include a small buffer of audio before and after detected speech to avoid clipping
- [ ] Handle end-of-stream sentinel: propagate `None` to output queue
- [ ] Use `VAD_THRESHOLD` from config (default 0.5)
- [ ] Ensure audio is converted to correct format for Silero (16kHz, mono, float32 tensor)
- [ ] Log VAD statistics periodically: speech ratio, chunks processed

## Acceptance Criteria

- [ ] `VoiceActivityDetector` loads the Silero model without errors
- [ ] `detect()` returns a float between 0.0 and 1.0
- [ ] `vad_stage()` only forwards chunks exceeding the threshold
- [ ] Speech segments include pre/post padding to avoid word clipping
- [ ] End-of-stream sentinel is propagated correctly
- [ ] Audio format conversion (bytes to float32 tensor) is handled internally
- [ ] All files pass `ruff check` and `mypy --strict`

## Dependencies

- 004 — Audio Capture (`AudioChunk` dataclass and queue pattern)

## Files to Create/Modify

- `src/call_operator/audio/vad.py`
