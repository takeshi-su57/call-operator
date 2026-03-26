# Architecture Rules

## Project Structure

call-operator is a single Python package. All source code lives in `src/call_operator/`.

```
src/call_operator/
├── main.py              # CLI entry point (Typer)
├── config.py            # Pydantic Settings
├── pipeline.py          # Async pipeline orchestration
├── adapters/            # Meeting platform adapters
├── audio/               # Audio capture, VAD, playback
├── stt/                 # Speech-to-Text providers
├── llm/                 # LLM conversation engine
├── tts/                 # Text-to-Speech providers
└── prompts/             # LLM prompt templates
```

## Async Pipeline Architecture

The agent is an async pipeline where each stage runs as a concurrent `asyncio.Task`, connected by `asyncio.Queue` instances.

```
┌──────────┐    ┌─────┐    ┌─────┐    ┌─────┐    ┌─────┐    ┌──────────┐
│  Capture  │───►│ VAD │───►│ STT │───►│ LLM │───►│ TTS │───►│ Playback │
└──────────┘    └─────┘    └─────┘    └─────┘    └─────┘    └──────────┘
     Queue         Queue       Queue       Queue       Queue
```

### Pipeline Design Rules

- Each stage is an async function: `async def stage(in_queue, out_queue, config)`
- Stages communicate ONLY through queues — no shared mutable state
- Each stage handles its own errors and logs them — pipeline continues
- Stages can be started/stopped independently for graceful shutdown
- Use `asyncio.Queue` with bounded size to apply backpressure
- Pipeline is assembled and run in `pipeline.py`

### Data flowing through the pipeline

| Queue | Data Type | Description |
|-------|-----------|-------------|
| capture → VAD | `AudioChunk` | Raw PCM audio frames (16kHz, mono) |
| VAD → STT | `AudioChunk` | Speech segments (non-silent audio) |
| STT → LLM | `Transcript` | Transcribed text with speaker info |
| LLM → TTS | `str` | Generated response text |
| TTS → playback | `AudioChunk` | Synthesized speech audio |

## Adapter Pattern (Meeting Platforms)

Each meeting platform is an adapter that implements the abstract interface:

```python
# adapters/base.py
from abc import ABC, abstractmethod

class MeetingAdapter(ABC):
    @abstractmethod
    async def join(self, url: str) -> None: ...

    @abstractmethod
    async def capture_audio(self) -> AsyncIterator[AudioChunk]: ...

    @abstractmethod
    async def play_audio(self, audio: AudioChunk) -> None: ...

    @abstractmethod
    async def leave(self) -> None: ...
```

Rules:
- **One adapter per platform** — `google_meet.py`, future `zoom.py`, etc.
- **Adapters handle platform specifics** — joining, auth, UI interaction
- **Pipeline is adapter-agnostic** — it receives audio and sends audio, doesn't know the platform
- **Google Meet adapter uses Playwright** — browser automation to join as a participant

## Provider Pattern (STT / TTS)

STT and TTS are pluggable via abstract base classes:

```python
# stt/base.py
class STTProvider(ABC):
    @abstractmethod
    async def transcribe_stream(
        self, audio_stream: AsyncIterator[AudioChunk]
    ) -> AsyncIterator[Transcript]: ...

# tts/base.py
class TTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str) -> AudioChunk: ...
```

Rules:
- **Config selects the provider** — `STT_PROVIDER` and `TTS_PROVIDER` env vars
- **Lazy imports** — provider-specific packages imported only when that provider is selected
- **Same interface** — all providers implement the same abstract methods
- **Factory functions** — `get_stt()` and `get_tts()` return the configured provider instance

## LLM Layer

`llm/provider.py` returns a LangChain `BaseChatModel` based on `LLM_PROVIDER` env var. Supports `openai`, `anthropic`, `google`.

`llm/conversation.py` manages:
- Conversation history (message buffer)
- System prompt from `prompts/conversation.py`
- Response generation via the LLM
- Context window management (truncation)

Rules:
- Use `llm/provider.py` for all LLM calls — never import provider SDKs directly
- Use prompt templates from `prompts/` — never inline prompts
- Conversation state lives in `conversation.py`, not scattered across stages

## Audio Processing

### Audio Format Standard
- **Sample rate:** 16000 Hz
- **Channels:** 1 (mono)
- **Format:** PCM 16-bit signed integers
- **Chunk size:** configurable (default ~30ms frames for VAD)

### Voice Activity Detection (VAD)
- Silero VAD model — runs locally on CPU, no GPU needed
- Detects speech vs. silence in audio chunks
- Only passes speech segments to STT (saves compute and reduces noise)

## Prompts

LLM prompt templates live in `prompts/` as Python string constants:

```python
# prompts/conversation.py
SYSTEM_PROMPT = """You are an AI meeting participant...
{context}
"""
```

Rules:
- One file per concern
- Templates are constants, not functions
- Use `str.format()` to fill placeholders
- Always include clear instructions for the LLM's role in the meeting

## Configuration

`config.py` uses Pydantic Settings with `.env` file support:

```python
from call_operator.config import get_settings
settings = get_settings()
```

All configuration comes from environment variables. Never hardcode values.

## Storage

Local files in `data/` (git-ignored):
- Conversation logs
- Audio recordings (if enabled)
- Session metadata

## Error Handling

- Pipeline stages catch exceptions and log them — the pipeline continues
- Meeting disconnection triggers reconnection logic (adapter responsibility)
- STT/TTS provider failures fall back to logging the error and skipping
- All errors are collected and reported at session end
- CLI displays errors via Rich

## Anti-Patterns (Do NOT)

- Put business logic in `main.py` — CLI is thin, delegates to pipeline
- Use synchronous I/O — everything is async
- Share mutable state between pipeline stages — use queues
- Make LLM calls directly — use `llm/provider.py`
- Hardcode prompts in pipeline stages — use `prompts/` templates
- Use synchronous Playwright calls — always use async API
- Store API keys in code — use env vars via `config.py`
- Import from one adapter into another — adapters are independent
- Import provider-specific SDKs at module level — use lazy imports
- Block the event loop with CPU-bound work — use `asyncio.to_thread()`
