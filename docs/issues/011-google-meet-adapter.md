# [Feature]: Google Meet adapter with Playwright browser automation

## Description

Implement `GoogleMeetAdapter(MeetingAdapter)` — a concrete meeting adapter that uses Playwright to join a Google Meet call, handle the meeting UI (dismiss dialogs, click join, manage permissions), and capture audio from the meeting via the Web Audio API. The adapter exposes `read_audio()` to stream meeting audio as PCM bytes to the pipeline.

## Motivation

Google Meet is the target platform. The adapter must handle the full lifecycle: navigate to the meeting URL, handle browser permission prompts, dismiss pre-join UI elements, join the call, capture incoming audio from other participants, and eventually play back synthesized audio. This is the most complex adapter due to Google Meet's dynamic UI.

## Tasks

- [ ] Create `src/call_operator/adapters/google_meet.py` with `GoogleMeetAdapter(MeetingAdapter)`
- [ ] Implement `connect(url: str)`:
  - Launch Playwright Chromium browser (headless or headed based on config)
  - Set browser args for audio: `--use-fake-ui-for-media-stream`, `--use-fake-device-for-media-stream`, `--autoplay-policy=no-user-gesture-required`
  - Navigate to the Google Meet URL
  - Wait for the pre-join page to load
- [ ] Handle pre-join UI:
  - Turn off camera (click camera toggle button)
  - Turn off microphone (click mic toggle button)
  - Set display name to `BOT_NAME` from config
  - Click "Ask to join" or "Join now" button
  - Wait for admission to the meeting
- [ ] Implement audio capture via Web Audio API:
  - Inject JavaScript that creates an `AudioContext` and `MediaStreamDestination`
  - Capture all audio output from the meeting using `createMediaElementSource` or `getDisplayMedia`
  - Use `ScriptProcessorNode` or `AudioWorklet` to extract PCM samples
  - Bridge audio data from browser to Python via `page.evaluate()` or CDP (Chrome DevTools Protocol)
- [ ] Implement `read_audio() -> bytes | None`:
  - Return the next chunk of PCM audio bytes from the browser
  - Return `None` when disconnected or meeting ended
- [ ] Implement `play_audio(chunk: AudioChunk)`:
  - Stub for now — full implementation in issue 012
- [ ] Implement `disconnect()`:
  - Click "Leave call" button
  - Close the browser context
- [ ] Implement `is_connected() -> bool`:
  - Check if still in the meeting (presence of leave button, no "removed" dialog)
- [ ] Handle meeting events:
  - Detect when removed from meeting
  - Detect when meeting ends
  - Detect waiting room / admission pending state
- [ ] Add retry logic for flaky selectors (Google Meet UI changes frequently)
- [ ] Support configurable selectors via constants (easy to update when Meet UI changes)

## Acceptance Criteria

- [ ] `GoogleMeetAdapter` can launch a browser and navigate to a Meet URL
- [ ] Pre-join UI is handled: camera off, mic off, name set, join clicked
- [ ] Audio is captured from the meeting as PCM bytes
- [ ] `read_audio()` returns audio chunks at the configured sample rate
- [ ] `disconnect()` leaves the meeting and closes the browser
- [ ] `is_connected()` accurately reflects meeting state
- [ ] Meeting end and removal are detected
- [ ] Headless mode works (configurable via `BROWSER_HEADLESS`)
- [ ] Selectors are defined as constants for easy maintenance
- [ ] All files pass `ruff check` and `mypy --strict`

## Dependencies

- 004 — Audio Capture (`MeetingAdapter` base class and `AudioChunk`)
- 010 — Async Pipeline (pipeline must be ready to consume audio)

## Files to Create/Modify

- `src/call_operator/adapters/google_meet.py`
