# [Feature]: MILESTONE — Async pipeline assembly wiring all stages end-to-end

## Description

This is the integration milestone. Wire all pipeline stages together in `pipeline.py` using `asyncio.Queue` as the connective tissue. The pipeline flows: audio capture -> VAD -> STT -> conversation engine -> TTS -> audio playback. Each stage runs as an independent `asyncio.Task`, communicating via bounded queues. Implement graceful startup, shutdown, and error propagation.

## Motivation

Individual stages are useless in isolation. The pipeline is where the agent comes alive — audio enters from one end, and synthesized speech exits the other. This is the most critical integration point in the entire system. Once this works, the agent can listen and respond in real-time.

## Tasks

- [ ] Create `src/call_operator/pipeline.py`
- [ ] Define `Pipeline` class with methods: `async start()`, `async stop()`, `async run()`, `is_running() -> bool`
- [ ] In `__init__()`, accept configuration and create all queues:
  - `audio_queue: asyncio.Queue[AudioChunk]` — capture -> VAD
  - `speech_queue: asyncio.Queue[AudioChunk]` — VAD -> STT
  - `transcript_queue: asyncio.Queue[Transcript]` — STT -> conversation
  - `response_queue: asyncio.Queue[str]` — conversation -> TTS
  - `playback_queue: asyncio.Queue[AudioChunk]` — TTS -> playback
- [ ] All queues are bounded (configurable max size, default 100) to provide backpressure
- [ ] In `start()`, initialize all providers based on config:
  - Create `MeetingAdapter` (Google Meet)
  - Create `VoiceActivityDetector`
  - Create `STTProvider` (whisper_local or deepgram)
  - Create `ConversationEngine`
  - Create `TTSProvider` (openai, elevenlabs, or google)
- [ ] In `run()`, launch all stages as concurrent `asyncio.Task` instances:
  - `capture_task = asyncio.create_task(capture_stage(adapter, audio_queue))`
  - `vad_task = asyncio.create_task(vad_stage(audio_queue, speech_queue, threshold))`
  - `stt_task = asyncio.create_task(stt_stage(speech_queue, transcript_queue, stt_provider))`
  - `conversation_task = asyncio.create_task(conversation_stage(transcript_queue, response_queue, engine))`
  - `tts_task = asyncio.create_task(tts_stage(response_queue, playback_queue, tts_provider))`
  - `playback_task = asyncio.create_task(playback_stage(playback_queue, adapter))`
- [ ] Use `asyncio.gather()` or `TaskGroup` to run all tasks and propagate exceptions
- [ ] Implement `stop()`:
  - Signal all stages to stop (via event or sentinel)
  - Cancel running tasks
  - Wait for tasks to complete (with timeout)
  - Clean up resources (close adapter, stop providers)
- [ ] Handle task failures: if any stage crashes, log the error and initiate graceful shutdown
- [ ] Handle `KeyboardInterrupt` and `SIGTERM` for clean shutdown
- [ ] Wire `Pipeline` into the CLI `run` command in `main.py`:
  - Parse meeting URL from CLI argument
  - Create and start the pipeline
  - Wait until pipeline stops or user interrupts
- [ ] Add logging for pipeline lifecycle: stage started, stage stopped, errors

## Acceptance Criteria

- [ ] `Pipeline` can be instantiated with settings
- [ ] `start()` initializes all providers without error
- [ ] `run()` launches all 6 stages as concurrent tasks
- [ ] Data flows through all queues: AudioChunk -> AudioChunk -> Transcript -> str -> AudioChunk
- [ ] `stop()` cleanly shuts down all tasks within 5 seconds
- [ ] Task failures are caught and trigger pipeline shutdown
- [ ] `KeyboardInterrupt` triggers graceful shutdown
- [ ] CLI `run` command creates and runs the pipeline
- [ ] Queue backpressure prevents unbounded memory growth
- [ ] All files pass `ruff check` and `mypy --strict`

## Dependencies

- 004 — Audio Capture (capture_stage, AudioChunk, MeetingAdapter)
- 005 — VAD Integration (vad_stage, VoiceActivityDetector)
- 006 — STT Local (stt_stage, STTProvider, Transcript)
- 007 — STT Cloud (DeepgramSTT as alternative STTProvider)
- 008 — TTS Providers (tts_stage, TTSProvider)
- 009 — Conversation Engine (conversation_stage, ConversationEngine)

## Files to Create/Modify

- `src/call_operator/pipeline.py`
- `src/call_operator/main.py` (wire Pipeline into CLI)
