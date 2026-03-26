# [Feature]: Audio playback stage — inject synthesized speech into meeting

## Description

Implement `playback_stage()` that reads synthesized `AudioChunk` objects from the TTS output queue and plays them into the meeting via the adapter's `play_audio()` method. Complete the `GoogleMeetAdapter.play_audio()` implementation that injects PCM audio into the browser's audio output, making it audible to all meeting participants.

## Motivation

The agent needs to speak in meetings. After the TTS stage generates audio, it must be injected into the Google Meet call so other participants hear the agent's responses. This closes the full audio loop: listen -> think -> speak.

## Tasks

- [ ] Create `src/call_operator/audio/playback.py`
- [ ] Implement `playback_stage(input_queue: asyncio.Queue[AudioChunk], adapter: MeetingAdapter) -> None`
  - Loop: read `AudioChunk` from queue, call `adapter.play_audio(chunk)`
  - Handle end-of-stream sentinel
  - Respect audio timing: pace playback to match chunk duration (avoid playing too fast)
- [ ] Implement `GoogleMeetAdapter.play_audio(chunk: AudioChunk)` in `adapters/google_meet.py`:
  - Inject JavaScript that creates an `AudioBufferSourceNode`
  - Convert PCM bytes to a JavaScript `AudioBuffer`
  - Connect the source to the `AudioContext.destination` (meeting audio output)
  - Play the buffer
  - Wait for playback to complete before returning
- [ ] Handle concurrent playback: queue audio buffers in the browser to avoid gaps or overlaps
- [ ] Implement audio format conversion if needed: resample TTS output to match meeting audio format
- [ ] Add a small crossfade between consecutive audio chunks to prevent clicks/pops
- [ ] Handle browser disconnection during playback gracefully
- [ ] Log playback events: chunk played, duration, queue depth

## Acceptance Criteria

- [ ] `playback_stage()` reads from the queue and calls `adapter.play_audio()`
- [ ] `GoogleMeetAdapter.play_audio()` injects audio into the browser
- [ ] Audio is audible to other meeting participants
- [ ] Playback timing matches audio duration (no speed-up or gaps)
- [ ] Consecutive chunks play smoothly without clicks
- [ ] End-of-stream sentinel causes the stage to exit cleanly
- [ ] Browser disconnection during playback is handled gracefully
- [ ] All files pass `ruff check` and `mypy --strict`

## Dependencies

- 008 — TTS Providers (produces AudioChunk for playback)
- 011 — Google Meet Adapter (adapter must be connected and capturing)

## Files to Create/Modify

- `src/call_operator/audio/playback.py`
- `src/call_operator/adapters/google_meet.py` (implement `play_audio()`)
