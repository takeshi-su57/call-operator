# [Feature]: Google Meet adapter with Playwright browser automation

## Description

Implement `GoogleMeetAdapter(MeetingAdapter)` — a concrete meeting adapter that uses Playwright to join a Google Meet call, handle the meeting UI (dismiss dialogs, click join, manage permissions), and capture audio from the meeting via the Web Audio API. The adapter exposes `read_audio()` to stream meeting audio as PCM bytes to the pipeline.

## Motivation

Google Meet is the target platform. The adapter must handle the full lifecycle: navigate to the meeting URL, handle browser permission prompts, dismiss pre-join UI elements, join the call, capture incoming audio from other participants, and eventually play back synthesized audio. This is the most complex adapter due to Google Meet's dynamic UI.

## Tasks

- [x] Create `src/call_operator/adapters/google_meet.py` with `GoogleMeetAdapter(MeetingAdapter)`
- [x] Implement `connect(url: str)`:
  - Launch Playwright Chromium browser (headless or headed based on config)
  - Set browser args for audio: `--use-fake-ui-for-media-stream`, `--use-fake-device-for-media-stream`, `--autoplay-policy=no-user-gesture-required`, `--disable-features=WebRtcHideLocalIpsWithMdns`
  - Navigate to the Google Meet URL
  - Wait for the pre-join page to load (`wait_until="networkidle"`)
- [x] Handle pre-join UI (`_handle_prejoin_ui`):
  - Dismiss info dialogs ("Got it", "Dismiss" buttons)
  - Set display name to `BOT_NAME` from config
  - Turn off camera (click camera toggle button)
  - Turn off microphone (click mic toggle button)
  - Click "Ask to join" or "Join now" button
  - Wait for admission to the meeting (leave button becomes visible)
- [x] Implement audio capture via Web Audio API:
  - Inject JavaScript that creates an `AudioContext` at configured sample rate
  - Use `ScriptProcessorNode` (4096 buffer) to extract PCM samples as Int16
  - Connect all existing `<audio>` and `<video>` elements via `createMediaElementSource`
  - Watch for new media elements via `MutationObserver` and auto-connect them
  - Store samples in `window.__audioBuffer` array for Python to read
  - Bridge audio data from browser to Python via `page.evaluate()`
- [x] Implement `read_audio() -> bytes | None`:
  - Poll browser-side buffer via `page.evaluate(_AUDIO_READ_JS)`
  - Merge accumulated Int16 chunks into single array
  - Convert to raw PCM bytes via `struct.pack`
  - Return `None` when disconnected or meeting ended
  - 50ms poll interval between reads
- [x] Implement `play_audio(chunk: AudioChunk)`:
  - Stub for now — logs debug message, full implementation in issue 012
- [x] Implement `disconnect()`:
  - Click "Leave call" button (if visible)
  - Close browser context, browser, and Playwright instance
  - Each cleanup step wrapped in try/except for robustness
  - Set `_connected = False`, clear all references
- [x] Implement `is_connected() -> bool`:
  - Returns `self._connected` state flag
  - Updated by `connect()`, `disconnect()`, `read_audio()` (on error/meeting end)
- [x] Handle meeting events (`_check_meeting_ended`):
  - Detect `div[data-call-ended]`
  - Detect "You've been removed" text
  - Detect "The meeting has ended" text
  - Detect "You left the meeting" text
  - Detect "Return to home screen" text
  - Any exception during check → treat as ended
- [x] Add retry logic for flaky selectors:
  - `_try_click(selector, timeout)` — returns True/False, never raises
  - `_try_fill(selector, value, timeout)` — returns True/False, never raises
  - All non-critical UI interactions use these helpers
- [x] Support configurable selectors via constants:
  - `_SEL_NAME_INPUT`, `_SEL_MIC_BUTTON`, `_SEL_CAM_BUTTON`, `_SEL_JOIN_BUTTON`, `_SEL_LEAVE_BUTTON`, `_SEL_DISMISS_BUTTON`, `_SEL_ENDED_INDICATORS`

## Acceptance Criteria

- [x] `GoogleMeetAdapter` can launch a browser and navigate to a Meet URL
- [x] Pre-join UI is handled: camera off, mic off, name set, join clicked
- [x] Audio is captured from the meeting as PCM bytes
- [x] `read_audio()` returns audio chunks at the configured sample rate
- [x] `disconnect()` leaves the meeting and closes the browser
- [x] `is_connected()` accurately reflects meeting state
- [x] Meeting end and removal are detected
- [x] Headless mode works (configurable via `BROWSER_HEADLESS`)
- [x] Selectors are defined as constants for easy maintenance
- [x] All files pass `ruff check` and `mypy --strict`

## Implementation Notes

### Audio capture strategy

Uses Web Audio API with `ScriptProcessorNode` (deprecated but universally supported in Chromium). The injected JS:
1. Creates `AudioContext` at 16kHz (configurable via `audio_sample_rate`)
2. Creates `ScriptProcessorNode` with 4096-sample buffer
3. Connects all `<audio>` and `<video>` elements via `createMediaElementSource`
4. A `MutationObserver` watches for dynamically added media elements
5. PCM float32 samples are converted to Int16 and stored in `window.__audioBuffer`
6. Python reads via `page.evaluate()` which splices and merges the buffer

### Known limitations

- **Selectors may need updating** — Google Meet's HTML changes frequently. All selectors are module-level constants for easy maintenance.
- **Audio capture approach** — `createMediaElementSource` works for `<audio>`/`<video>` elements. If Meet uses raw WebRTC `MediaStream` objects without elements, a different approach (e.g., `RTCPeerConnection.getReceivers()`) may be needed.
- **Polling latency** — 50ms poll interval via `page.evaluate()` adds ~50-100ms latency. CDP-based streaming could reduce this in the future.
- **`play_audio`** — Stub only. Full audio injection is issue 012.

### Testing

- **Unit tests** (`tests/test_google_meet.py`): 9 tests with fully mocked Playwright
  - Init state, browser launch, URL navigation, PCM audio read, disconnect/cleanup, meeting ended detection
- **Live testing** requires: `uv run playwright install chromium`, a real Meet URL, and headed mode (`BROWSER_HEADLESS=false`)

## Dependencies

- 004 — Audio Capture (`MeetingAdapter` base class and `AudioChunk`)
- 010 — Async Pipeline (pipeline must be ready to consume audio)

## Files Created/Modified

- `src/call_operator/adapters/google_meet.py` — full implementation replacing stub
- `tests/test_google_meet.py` — 9 tests with mocked Playwright
