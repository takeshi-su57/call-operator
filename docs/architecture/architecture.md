# Architecture Overview

## System Design

call-operator is a real-time AI meeting agent built as an async pipeline in Python.

```
                         ┌──────────────────────────────────┐
                         │          CLI (Typer + Rich)       │
                         └───────────────┬──────────────────┘
                                         │
                         ┌───────────────▼──────────────────┐
                         │        Async Pipeline             │
                         │                                   │
                         │  ┌─────────┐    ┌─────┐          │
                         │  │ Capture  │───►│ VAD │          │
                         │  └─────────┘    └──┬──┘          │
                         │                    │              │
                         │               ┌────▼────┐        │
                         │               │   STT   │        │
                         │               └────┬────┘        │
                         │                    │              │
                         │               ┌────▼────┐        │
                         │               │   LLM   │        │
                         │               └────┬────┘        │
                         │                    │              │
                         │               ┌────▼────┐        │
                         │               │   TTS   │        │
                         │               └────┬────┘        │
                         │                    │              │
                         │              ┌─────▼─────┐       │
                         │              │ Playback   │       │
                         │              └────────────┘       │
                         └───────────────┬──────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                     │
             ┌──────▼──────┐    ┌───────▼──────┐    ┌───────▼───────┐
             │  Playwright  │    │  STT/TTS APIs │    │   LLM APIs    │
             │  (browser)   │    │  (Whisper/    │    │   (OpenAI/    │
             │              │    │   Deepgram/   │    │   Anthropic/  │
             │              │    │   ElevenLabs) │    │   Google)     │
             └──────────────┘    └──────────────┘    └──────────────┘
```

## Pipeline Flow

1. **Audio Capture** — Meeting adapter (Playwright) captures audio from participants
2. **VAD** — Silero Voice Activity Detection filters silence, passes speech segments
3. **STT** — Speech-to-Text converts audio to text (local Whisper or cloud Deepgram)
4. **LLM** — Conversation engine generates a response using the configured LLM
5. **TTS** — Text-to-Speech converts the response to audio (OpenAI, ElevenLabs, or Google)
6. **Playback** — Synthesized audio is played back into the meeting

## Component Architecture

### Meeting Adapters (`adapters/`)
Abstract interface for meeting platforms. Currently supports Google Meet via Playwright.
Each adapter handles: joining, audio capture, audio playback, leaving.

### Audio Processing (`audio/`)
- **capture.py** — Reads audio from the adapter and pushes to VAD queue
- **vad.py** — Silero VAD filters silence, forwards speech to STT queue
- **playback.py** — Reads synthesized audio and sends to adapter

### STT Providers (`stt/`)
Pluggable speech-to-text. Factory function `get_stt()` returns the configured provider.
- **whisper_local.py** — faster-whisper on CPU (default, free, ~1-2s latency)
- **deepgram_cloud.py** — Deepgram streaming API (~200ms latency)

### LLM Engine (`llm/`)
- **provider.py** — LangChain factory returning `BaseChatModel` (OpenAI/Anthropic/Google)
- **conversation.py** — Manages conversation history, system prompt, response generation

### TTS Providers (`tts/`)
Pluggable text-to-speech. Factory function `get_tts()` returns the configured provider.
- **openai_tts.py** — OpenAI TTS API
- **elevenlabs_tts.py** — ElevenLabs API
- **google_tts.py** — Google Cloud TTS API

## Data Flow

```
Meeting Audio (PCM 16kHz mono)
    │
    ▼
AudioChunk ──► VAD ──► AudioChunk (speech only)
                           │
                           ▼
                    STT ──► Transcript (text + metadata)
                                │
                                ▼
                         LLM ──► Response (text)
                                      │
                                      ▼
                               TTS ──► AudioChunk (synthesized speech)
                                            │
                                            ▼
                                     Meeting Playback
```

## Current Limitations

- All implementations are stubs (TODO placeholders)
- Google Meet audio capture via Playwright not proven yet
- No reconnection logic on meeting disconnect
- No conversation memory persistence across sessions
- Single-meeting support only (no concurrent meetings)
- No speaker diarization (cannot identify who is speaking)
