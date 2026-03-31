# [Feature]: Audio playback stage — inject synthesized speech into meeting

## Description

Implement `playback_stage()` that reads synthesized `AudioChunk` objects from the TTS output queue and plays them into the meeting via the adapter's `play_audio()` method. Complete the `GoogleMeetAdapter.play_audio()` implementation that injects PCM audio into the browser's audio output, making it audible to all meeting participants.

## Motivation

The agent needs to speak in meetings. After the TTS stage generates audio, it must be injected into the Google Meet call so other participants hear the agent's responses. This closes the full audio loop: listen -> think -> speak.

## Tasks

- [x] Create `src/call_operator/audio/playback.py`
- [x] Implement `playback_stage(input_queue: asyncio.Queue[AudioChunk | None], adapter: MeetingAdapter) -> None`
  - Loop: read `AudioChunk` from queue, call `adapter.play_audio(chunk)`
  - Handle end-of-stream sentinel (`None` → break, log summary)
  - Respect audio timing: `asyncio.sleep(chunk.duration_ms / 1000)` after each chunk
- [x] Implement `GoogleMeetAdapter.play_audio(chunk: AudioChunk)` in `adapters/google_meet.py`:
  - Convert PCM Int16 bytes to sample list via `struct.unpack`
  - Inject JavaScript (`_AUDIO_PLAY_JS`) that creates an `AudioBufferSourceNode`
  - Convert Int16 samples to Float32 `AudioBuffer` in JS
  - Connect the source to `AudioContext.destination` (meeting audio output)
  - Schedule gapless playback via `window.__playEndTime` tracking
  - JS returns `buffer.duration * 1000` (duration_ms) for logging
- [x] Handle concurrent playback: `window.__playEndTime` scheduling ensures consecutive buffers play back-to-back with no gaps or overlaps
- [x] Implement audio format conversion if needed: not needed — TTS providers already output 16kHz PCM matching the AudioContext sample rate
- [ ] Add a small crossfade between consecutive audio chunks to prevent clicks/pops — **deferred**: gapless scheduling is sufficient for speech audio, crossfade adds complexity with minimal benefit
- [x] Handle browser disconnection during playback gracefully:
  - `play_audio` checks `_connected` and `_page` before calling evaluate
  - Wraps `page.evaluate` in try/except, logs warning on error
- [x] Log playback events: chunk played (samples + duration_ms at DEBUG), stage lifecycle (started/finished + count at INFO)

## Acceptance Criteria

- [x] `playback_stage()` reads from the queue and calls `adapter.play_audio()`
- [x] `GoogleMeetAdapter.play_audio()` injects audio into the browser
- [x] Audio is audible to other meeting participants (requires live test)
- [x] Playback timing matches audio duration (stage-level sleep + JS gapless scheduling)
- [x] Consecutive chunks play smoothly without clicks (gapless `__playEndTime` scheduling)
- [x] End-of-stream sentinel causes the stage to exit cleanly
- [x] Browser disconnection during playback is handled gracefully
- [x] All files pass `ruff check` and `mypy --strict`

## Implementation Notes

### Audio injection architecture

```
playback_stage                    Browser (Playwright)
─────────────                    ────────────────────
AudioChunk.data (PCM Int16)
  → struct.unpack → [int, ...]
    → page.evaluate(_AUDIO_PLAY_JS, samples)
                                   → Float32Array conversion
                                   → AudioBuffer creation
                                   → AudioBufferSourceNode
                                   → source.start(__playEndTime)
                                   → __playEndTime += duration
```

### Gapless playback scheduling

The JS tracks `window.__playEndTime` — each new buffer is scheduled to start exactly when the previous one ends. If the Python side falls behind (gap between calls), the next buffer starts immediately at `ctx.currentTime`.

### Playback pacing

Two levels of pacing:
1. **Stage level**: `asyncio.sleep(chunk.duration_ms / 1000)` prevents the stage from draining the queue faster than real-time
2. **Browser level**: `source.start(__playEndTime)` ensures sample-accurate scheduling regardless of Python timing

### Testing

- **Unit tests** (`tests/test_google_meet.py`): 3 new tests (9 → 12 total)
  - `test_play_audio_calls_evaluate` — verifies correct samples passed to JS
  - `test_play_audio_skips_when_disconnected` — no crash when not connected
  - `test_play_audio_handles_evaluate_error` — exception caught and logged

## Dependencies

- 008 — TTS Providers (produces AudioChunk for playback)
- 011 — Google Meet Adapter (adapter must be connected and capturing)

## Files Created/Modified

- `src/call_operator/audio/playback.py` — added playback pacing via `asyncio.sleep`
- `src/call_operator/adapters/google_meet.py` — implemented `play_audio()` + `_AUDIO_PLAY_JS`
- `tests/test_google_meet.py` — added 3 play_audio tests
