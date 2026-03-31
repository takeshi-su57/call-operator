# [Feature]: MILESTONE — Async pipeline assembly wiring all stages end-to-end

## Description

This is the integration milestone. Wire all pipeline stages together in `pipeline.py` using `asyncio.Queue` as the connective tissue. The pipeline flows: audio capture -> VAD -> STT -> conversation engine -> TTS -> audio playback. Each stage runs as an independent `asyncio.Task`, communicating via bounded queues. Implement graceful startup, shutdown, and error propagation.

## Motivation

Individual stages are useless in isolation. The pipeline is where the agent comes alive — audio enters from one end, and synthesized speech exits the other. This is the most critical integration point in the entire system. Once this works, the agent can listen and respond in real-time.

## Tasks

- [x] Create `src/call_operator/pipeline.py`
- [x] Define `Pipeline` class with methods: `async start()`, `async stop()`, `async run()`, `is_running -> bool`
- [x] In `__init__()`, accept configuration and create all queues:
  - `_audio_q: asyncio.Queue[AudioChunk | None]` — capture -> VAD
  - `_speech_q: asyncio.Queue[AudioChunk | None]` — VAD -> STT
  - `_transcript_q: asyncio.Queue[Transcript | None]` — STT -> conversation
  - `_response_q: asyncio.Queue[str | None]` — conversation -> TTS
  - `_playback_q: asyncio.Queue[AudioChunk | None]` — TTS -> playback
- [x] All queues are bounded (configurable via `PIPELINE_QUEUE_SIZE`, default 100) to provide backpressure
- [x] In `start()`, initialize all providers based on config:
  - Create `GoogleMeetAdapter` and connect to meeting URL
  - Create `STTProvider` via `get_stt()` factory (whisper_local or deepgram)
  - Create `TTSProvider` via `get_tts()` factory (openai, elevenlabs, or google)
  - VAD and ConversationEngine are created internally by their respective stages
- [x] In `run()`, launch all stages as concurrent `asyncio.Task` instances:
  - `capture_stage(adapter, _audio_q)` named "capture"
  - `vad_stage(_audio_q, _speech_q, threshold)` named "vad"
  - `stt_stage(_speech_q, _transcript_q, stt_provider)` named "stt"
  - `conversation_stage(_transcript_q, _response_q, settings)` named "conversation"
  - `tts_stage(_response_q, _playback_q, tts_provider)` named "tts"
  - `playback_stage(_playback_q, adapter)` named "playback"
- [x] Use `asyncio.gather(*tasks, return_exceptions=True)` to run all tasks and propagate exceptions
- [x] Implement `stop()`:
  - Inject `None` sentinel on `_audio_q` to trigger cascade through all stages
  - Wait for tasks to complete with 5-second timeout
  - Cancel remaining tasks that didn't stop in time
  - Disconnect adapter and clean up resources
- [x] Handle task failures: if any stage crashes, log the error via `return_exceptions=True` check
- [x] Handle `KeyboardInterrupt` and `SIGTERM` for clean shutdown (Unix signal handlers + try/except)
- [x] Wire `Pipeline` into the CLI `join` command in `main.py`:
  - Create Pipeline with settings
  - Call `start(url)` then `run()`
  - Signal handlers trigger `pipeline.stop()` on SIGINT/SIGTERM (Unix only)
  - KeyboardInterrupt caught at outer level for Windows
- [x] Add logging for pipeline lifecycle: initialized, running, shutting down, stopped, stage errors
- [x] Implement `playback_stage()` — was a stub, now reads AudioChunks with sentinel support

## Acceptance Criteria

- [x] `Pipeline` can be instantiated with settings
- [x] `start()` initializes all providers without error
- [x] `run()` launches all 6 stages as concurrent tasks
- [x] Data flows through all queues: AudioChunk -> AudioChunk -> Transcript -> str -> AudioChunk
- [x] `stop()` cleanly shuts down all tasks within 5 seconds
- [x] Task failures are caught and trigger pipeline shutdown
- [x] `KeyboardInterrupt` triggers graceful shutdown
- [x] CLI `join` command creates and runs the pipeline
- [x] Queue backpressure prevents unbounded memory growth
- [x] All files pass `ruff check` and `mypy --strict`

## Implementation Notes

### Pipeline architecture

```
┌──────────┐    ┌─────┐    ┌─────┐    ┌──────────────┐    ┌─────┐    ┌──────────┐
│  Capture  │───►│ VAD │───►│ STT │───►│ Conversation │───►│ TTS │───►│ Playback │
└──────────┘    └─────┘    └─────┘    └──────────────┘    └─────┘    └──────────┘
   AudioQ       SpeechQ   TranscriptQ    ResponseQ      PlaybackQ
```

All queues are `asyncio.Queue` with `maxsize=PIPELINE_QUEUE_SIZE` (default 100).

### Shutdown cascade

`stop()` injects a `None` sentinel on `_audio_q`. Each stage forwards `None` to its output queue in its `finally` block, creating a cascade: capture → VAD → STT → conversation → TTS → playback. If stages don't finish within 5 seconds, they are cancelled.

### Provider initialization

STT and TTS providers are created via their factory functions (`get_stt()`, `get_tts()`) with kwargs built from settings. VAD threshold is passed as a parameter to `vad_stage()`. ConversationEngine is created internally by `conversation_stage()` from settings.

### Signal handling

- **Unix**: `SIGINT` and `SIGTERM` registered via `loop.add_signal_handler()` to call `pipeline.stop()`
- **Windows**: Falls back to `KeyboardInterrupt` caught at the `asyncio.run()` level

### Testing

- **Unit tests** (`tests/test_pipeline.py`): 8 tests using fake adapter/STT/TTS
  - Pipeline init (queues created, not running)
  - Start (adapter connected, providers created)
  - Stop (adapter disconnected, idempotent)
  - Run raises if not started
  - Full end-to-end with fakes (data flows through all 6 stages)
  - Sentinel cascade (None propagates through all queues)

### Known limitations

- Google Meet adapter is still a stub — full E2E with a real meeting requires adapter implementation
- No reconnection logic yet — if the adapter disconnects, capture_stage ends the pipeline

## Dependencies

- 004 — Audio Capture (capture_stage, AudioChunk, MeetingAdapter)
- 005 — VAD Integration (vad_stage, VoiceActivityDetector)
- 006 — STT Local (stt_stage, STTProvider, Transcript)
- 007 — STT Cloud (DeepgramSTT as alternative STTProvider)
- 008 — TTS Providers (tts_stage, TTSProvider)
- 009 — Conversation Engine (conversation_stage, ConversationEngine)

## Files Created/Modified

- `src/call_operator/pipeline.py` — full `Pipeline` class replacing stub
- `src/call_operator/audio/playback.py` — implemented `playback_stage` with sentinel support
- `src/call_operator/main.py` — wired Pipeline into CLI with signal handling
- `src/call_operator/config.py` — added `pipeline_queue_size` setting
- `.env.example` — added `PIPELINE_QUEUE_SIZE`
- `tests/test_pipeline.py` — rewritten with 8 tests using fakes
