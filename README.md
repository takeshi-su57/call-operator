# call-operator

Real-time AI meeting agent that joins video calls, listens to participants, and responds with generated voice. An automated conversational participant powered by STT, LLM, and TTS.

## How It Works

```
Google Meet ──► Audio Capture ──► VAD ──► STT ──► LLM ──► TTS ──► Audio Playback
                (Playwright)     (Silero)  (Whisper/   (OpenAI/    (OpenAI/
                                           Deepgram)   Anthropic/  ElevenLabs/
                                                       Google/     Google)
                                                       OpenRouter)
```

1. **Joins the meeting** — Playwright bot joins Google Meet as a participant
2. **Captures audio** — Streams participant audio from the browser
3. **Detects speech** — Silero VAD filters silence, passes speech segments
4. **Transcribes** — STT converts speech to text (local Whisper or cloud Deepgram)
5. **Generates response** — LLM processes the conversation and generates a reply
6. **Speaks back** — TTS converts the reply to audio and plays it in the meeting

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (install: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- At least one LLM API key (OpenAI, Anthropic, Google, or OpenRouter)

### Setup

```bash
git clone <repo-url>
cd call-operator

uv sync --all-extras             # Install all deps + create .venv
uv run playwright install chromium

cp .env.example .env
# Edit .env with your API keys
```

### Run

```bash
uv run python -m call_operator join --url "https://meet.google.com/xxx-yyyy-zzz"
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_PROVIDER` | Yes | `openai` | LLM provider: `openai`, `anthropic`, `google`, `openrouter` |
| `LLM_MODEL` | Yes | `gpt-4o` | Model name |
| `LLM_TEMPERATURE` | No | `0.7` | LLM response temperature |
| `OPENAI_API_KEY` | If provider=openai | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | If provider=anthropic | — | Anthropic API key |
| `GOOGLE_API_KEY` | If provider=google | — | Google AI API key |
| `OPENROUTER_API_KEY` | If provider=openrouter | — | OpenRouter API key |
| `STT_PROVIDER` | No | `whisper_local` | STT: `whisper_local`, `deepgram` |
| `STT_MODEL` | No | `tiny` | Whisper model size or Deepgram model |
| `STT_LANGUAGE` | No | `en` | Language code for transcription |
| `DEEPGRAM_API_KEY` | If stt=deepgram | — | Deepgram API key |
| `TTS_PROVIDER` | No | `openai` | TTS: `openai`, `elevenlabs`, `google` |
| `TTS_VOICE` | No | `alloy` | Voice name (provider-specific) |
| `TTS_SPEED` | No | `1.0` | TTS playback speed |
| `ELEVENLABS_API_KEY` | If tts=elevenlabs | — | ElevenLabs API key |
| `BROWSER_HEADLESS` | No | `true` | `false` to see the browser |
| `BROWSER_TIMEOUT` | No | `30000` | Browser action timeout (ms) |
| `LOG_LEVEL` | No | `INFO` | `DEBUG` for verbose output |
| `AUDIO_SAMPLE_RATE` | No | `16000` | Audio sample rate in Hz |
| `VAD_THRESHOLD` | No | `0.5` | VAD speech probability threshold |
| `RECORD_AUDIO` | No | `false` | Save audio recordings to data/ |
| `AUDIO_CHUNK_MS` | No | `30` | Audio chunk size in ms |
| `BOT_NAME` | No | `AI Assistant` | Display name in meetings |

## Project Structure

```
src/call_operator/
├── main.py              # CLI entry point (Typer)
├── config.py            # Pydantic Settings
├── pipeline.py          # Async pipeline orchestration
├── adapters/            # Meeting platform adapters (Google Meet)
├── audio/               # Audio capture, VAD, playback
├── stt/                 # Speech-to-Text providers (Whisper, Deepgram)
├── llm/                 # LLM conversation engine
├── tts/                 # Text-to-Speech providers (OpenAI, ElevenLabs, Google)
└── prompts/             # LLM prompt templates
tests/                   # pytest test suite
docs/                    # Architecture docs + guides
```

## Commands

| Command | Description |
|---------|-------------|
| `uv sync --all-extras` | Install all dependencies |
| `uv run python -m call_operator join --url <url>` | Join a meeting |
| `uv run python -m call_operator --help` | Show CLI help |
| `uv run pytest` | Run tests |
| `uv run ruff check src/ tests/` | Lint |
| `uv run ruff format src/ tests/` | Format |
| `uv run mypy src/` | Type check |

## Docker

```bash
docker compose up --build
```

See [Deployment Guide](docs/guide/deployment.md) for production setup.

## Documentation

- [Architecture Overview](docs/architecture/architecture.md)
- [Developer Guide](docs/guide/developer.md)
- [Deployment Guide](docs/guide/deployment.md)
