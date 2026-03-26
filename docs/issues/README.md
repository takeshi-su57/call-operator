# Implementation Roadmap

This document tracks the implementation plan for **call-operator** — a real-time AI meeting agent that joins Google Meet via Playwright, captures audio, and responds using an STT -> LLM -> TTS pipeline.

## Phase Overview

### Phase 1: Foundation (Issues 001-003)

Establish the project skeleton, configuration system, and LLM provider abstraction.

- [001 - Project Setup](001-project-setup.md)
- [002 - Config and Environment](002-config-and-env.md)
- [003 - LLM Provider Setup](003-llm-provider-setup.md)

```
001 Project Setup
 └──> 002 Config and Environment
       └──> 003 LLM Provider Setup
```

### Phase 2: Audio Pipeline Core (Issues 004-008)

Build the audio capture, voice activity detection, speech-to-text, and text-to-speech components.

- [004 - Audio Capture](004-audio-capture.md)
- [005 - VAD Integration](005-vad-integration.md)
- [006 - STT Local (Whisper)](006-stt-local.md)
- [007 - STT Cloud (Deepgram)](007-stt-cloud.md)
- [008 - TTS Providers](008-tts-providers.md)

```
001 ──> 004 Audio Capture
         ├──> 005 VAD Integration
         │     └──> 006 STT Local (Whisper)
         └──> 007 STT Cloud (Deepgram)

001 ──> 008 TTS Providers
```

### Phase 3: Conversation Engine (Issues 009-010)

Wire the LLM conversation logic and assemble the full async pipeline.

- [009 - Conversation Engine](009-conversation-engine.md)
- [010 - Async Pipeline (MILESTONE)](010-async-pipeline.md)

```
003 + 006 ──> 009 Conversation Engine
004-009   ──> 010 Async Pipeline  <<<  MILESTONE: end-to-end audio flow
```

### Phase 4: Meeting Integration (Issues 011-012)

Connect to Google Meet and enable two-way audio in a live meeting.

- [011 - Google Meet Adapter](011-google-meet-adapter.md)
- [012 - Audio Playback](012-audio-playback.md)

```
004 + 010 ──> 011 Google Meet Adapter
008 + 011 ──> 012 Audio Playback
```

### Phase 5: Hardening and Polish (Issues 013-017)

Add resilience, monitoring, tests, Docker deployment, and CI.

- [013 - Error Handling](013-error-handling.md)
- [014 - CLI and Monitoring](014-cli-and-monitoring.md)
- [015 - Testing](015-testing.md)
- [016 - Docker Deployment](016-docker-deployment.md)
- [017 - CI Pipeline](017-ci-pipeline.md)

```
010 ──> 013 Error Handling
010 ──> 014 CLI and Monitoring
010 ──> 015 Testing
010 ──> 016 Docker Deployment
015 ──> 017 CI Pipeline
```

## Dependency Graph (Full)

```
001 Project Setup
 ├──> 002 Config and Env
 │     └──> 003 LLM Provider
 │           └──> 009 Conversation Engine (+ 006)
 ├──> 004 Audio Capture
 │     ├──> 005 VAD
 │     │     └──> 006 STT Local
 │     └──> 007 STT Cloud
 ├──> 008 TTS Providers
 │
 ├── 004-009 all feed into:
 │     └──> 010 Async Pipeline  <<< MILESTONE
 │           ├──> 011 Google Meet Adapter (+ 004)
 │           │     └──> 012 Audio Playback (+ 008)
 │           ├──> 013 Error Handling
 │           ├──> 014 CLI and Monitoring
 │           ├──> 015 Testing
 │           │     └──> 017 CI Pipeline
 │           └──> 016 Docker Deployment
```

## Milestone

**Issue 010 — Async Pipeline** is the integration milestone. Once complete, audio flows end-to-end: capture -> VAD -> STT -> LLM -> TTS -> playback. All subsequent work builds on this foundation.
