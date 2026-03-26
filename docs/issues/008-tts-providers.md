# [Feature]: Text-to-speech providers — OpenAI, ElevenLabs, Google Cloud

## Description

Implement three TTS providers behind a common `TTSProvider` abstract interface. Each provider converts text to an `AudioChunk` containing synthesized PCM audio. The providers are: OpenAI TTS (simple, good quality), ElevenLabs (best voice quality, streaming), and Google Cloud TTS (cost-effective, many languages). The active provider is selected via the `TTS_PROVIDER` config variable.

## Motivation

The agent needs to speak in meetings. Different TTS providers offer different trade-offs: OpenAI is simple to integrate, ElevenLabs has the most natural voices, and Google Cloud TTS supports the most languages at the lowest cost. Supporting all three lets users choose based on their needs.

## Tasks

- [ ] Create `src/call_operator/tts/__init__.py`
- [ ] Create `src/call_operator/tts/base.py` with abstract `TTSProvider` class
- [ ] Define abstract methods: `async synthesize(text: str) -> AudioChunk`, `async start()`, `async stop()`
- [ ] Define `tts_stage(input_queue: asyncio.Queue[str], output_queue: asyncio.Queue[AudioChunk], provider: TTSProvider) -> None`
- [ ] Create `src/call_operator/tts/openai_tts.py` with `OpenAITTS(TTSProvider)`
- [ ] Use the OpenAI API `client.audio.speech.create()` with model "tts-1" (or "tts-1-hd")
- [ ] Support voice selection via `TTS_VOICE` (default "alloy")
- [ ] Support speed control via `TTS_SPEED`
- [ ] Convert response bytes to PCM AudioChunk at configured sample rate
- [ ] Create `src/call_operator/tts/elevenlabs_tts.py` with `ElevenLabsTTS(TTSProvider)`
- [ ] Use ElevenLabs SDK for streaming synthesis
- [ ] Configure with `ELEVENLABS_API_KEY` and `TTS_VOICE` (ElevenLabs voice ID)
- [ ] Support streaming: yield audio chunks as they arrive for lower latency
- [ ] Configure voice settings: stability, similarity_boost, style
- [ ] Create `src/call_operator/tts/google_tts.py` with `GoogleTTS(TTSProvider)`
- [ ] Use `google-cloud-texttospeech` SDK
- [ ] Configure with `GOOGLE_API_KEY` and `TTS_VOICE` (e.g., "en-US-Neural2-D")
- [ ] Support SSML input for better prosody control
- [ ] Request LINEAR16 audio output at configured sample rate
- [ ] Implement `get_tts_provider() -> TTSProvider` factory function that reads `TTS_PROVIDER` from config

## Acceptance Criteria

- [ ] All three providers implement the `TTSProvider` interface
- [ ] `OpenAITTS.synthesize("Hello")` returns a valid `AudioChunk` with PCM audio
- [ ] `ElevenLabsTTS.synthesize("Hello")` returns a valid `AudioChunk` with PCM audio
- [ ] `GoogleTTS.synthesize("Hello")` returns a valid `AudioChunk` with PCM audio
- [ ] `get_tts_provider()` returns the correct provider based on `TTS_PROVIDER` config
- [ ] Missing API keys raise clear errors
- [ ] `tts_stage()` reads text from input queue and writes AudioChunks to output queue
- [ ] End-of-stream sentinel is propagated
- [ ] All files pass `ruff check` and `mypy --strict`

## Dependencies

- 001 — Project Setup (package structure)

## Files to Create/Modify

- `src/call_operator/tts/__init__.py`
- `src/call_operator/tts/base.py`
- `src/call_operator/tts/openai_tts.py`
- `src/call_operator/tts/elevenlabs_tts.py`
- `src/call_operator/tts/google_tts.py`
