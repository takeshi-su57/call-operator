# [Feature]: Text-to-speech providers — OpenAI, ElevenLabs, Google Cloud

## Description

Implement three TTS providers behind a common `TTSProvider` abstract interface. Each provider converts text to an `AudioChunk` containing synthesized PCM audio. The providers are: OpenAI TTS (simple, good quality), ElevenLabs (best voice quality, streaming), and Google Cloud TTS (cost-effective, many languages). The active provider is selected via the `TTS_PROVIDER` config variable.

## Motivation

The agent needs to speak in meetings. Different TTS providers offer different trade-offs: OpenAI is simple to integrate, ElevenLabs has the most natural voices, and Google Cloud TTS supports the most languages at the lowest cost. Supporting all three lets users choose based on their needs.

## Tasks

- [x] Create `src/call_operator/tts/__init__.py`
- [x] Create `src/call_operator/tts/base.py` with abstract `TTSProvider` class
- [x] Define abstract methods: `async synthesize(text: str) -> AudioChunk`, `async start()`, `async stop()`
- [x] Define `tts_stage(input_queue: asyncio.Queue[str], output_queue: asyncio.Queue[AudioChunk], provider: TTSProvider) -> None`
- [x] Create `src/call_operator/tts/openai_tts.py` with `OpenAITTS(TTSProvider)`
- [x] Use the OpenAI API `client.audio.speech.create()` with model "tts-1" (or "tts-1-hd")
- [x] Support voice selection via `TTS_VOICE` (default "alloy")
- [x] Support speed control via `TTS_SPEED`
- [x] Convert response bytes to PCM AudioChunk at configured sample rate
- [x] Create `src/call_operator/tts/elevenlabs_tts.py` with `ElevenLabsTTS(TTSProvider)`
- [x] Use ElevenLabs SDK for streaming synthesis
- [x] Configure with `ELEVENLABS_API_KEY` and `TTS_VOICE` (ElevenLabs voice ID)
- [x] Support streaming: yield audio chunks as they arrive for lower latency
- [x] Configure voice settings: stability, similarity_boost, style
- [x] Create `src/call_operator/tts/google_tts.py` with `GoogleTTS(TTSProvider)`
- [x] Use `google-cloud-texttospeech` SDK
- [x] Configure with `GOOGLE_API_KEY` and `TTS_VOICE` (e.g., "en-US-Neural2-D")
- [x] Support SSML input for better prosody control
- [x] Request LINEAR16 audio output at configured sample rate
- [x] Implement `get_tts_provider() -> TTSProvider` factory function that reads `TTS_PROVIDER` from config

## Acceptance Criteria

- [x] All three providers implement the `TTSProvider` interface
- [x] `OpenAITTS.synthesize("Hello")` returns a valid `AudioChunk` with PCM audio
- [x] `ElevenLabsTTS.synthesize("Hello")` returns a valid `AudioChunk` with PCM audio
- [x] `GoogleTTS.synthesize("Hello")` returns a valid `AudioChunk` with PCM audio
- [x] `get_tts_provider()` returns the correct provider based on `TTS_PROVIDER` config
- [x] Missing API keys raise clear errors
- [x] `tts_stage()` reads text from input queue and writes AudioChunks to output queue
- [x] End-of-stream sentinel is propagated
- [x] All files pass `ruff check` and `mypy --strict`

## Implementation Notes

### Audio format strategy — no extra decode dependencies needed

| Provider | Request Format | Raw Output | Conversion |
|----------|---------------|------------|------------|
| OpenAI | `response_format="pcm"` | 24 kHz 16-bit PCM | Downsample to 16 kHz via numpy `np.linspace` index resampling |
| ElevenLabs | `output_format="pcm_16000"` | 16 kHz 16-bit PCM | None — already in target format |
| Google Cloud | `AudioEncoding.LINEAR16`, `sample_rate_hertz=16000` | WAV with 16 kHz 16-bit PCM | Strip 44-byte WAV header |

### Key design decisions

- All providers request PCM natively — no ffmpeg/pydub/soundfile dependency
- `tts_stage()` catches and skips individual synthesis errors (pipeline continues)
- API key validation happens at construction time (fail-fast)
- Google Cloud TTS uses Application Default Credentials (no explicit API key parameter)
- ElevenLabs `voice` parameter expects a voice ID, not a display name
- OpenAI PCM is 24 kHz; downsampled to 16 kHz to match project audio standard

### Testing

- **Unit tests** (`tests/test_tts.py`): factory, API key validation, `tts_stage` with `FakeTTS` — 11 tests
- **Live smoke tests** (`tests/test_tts_live.py`): real API calls per provider, `tts_stage` end-to-end — 7 tests (skipped without keys)

## Dependencies

- 001 — Project Setup (package structure)

## Files Created/Modified

- `src/call_operator/tts/__init__.py` — `tts_stage()` pipeline function + exports
- `src/call_operator/tts/base.py` — added `start()` / `stop()` abstract methods
- `src/call_operator/tts/openai_tts.py` — full implementation
- `src/call_operator/tts/elevenlabs_tts.py` — full implementation
- `src/call_operator/tts/google_tts.py` — full implementation
- `pyproject.toml` — added `google.cloud.*` to mypy overrides
- `tests/test_tts.py` — expanded with validation + stage tests
- `tests/test_tts_live.py` — live smoke tests for all three providers
