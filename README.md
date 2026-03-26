# call-operator

Real-time AI meeting agent that joins video calls, listens to participants, and responds with generated voice. An automated conversational participant powered by STT, LLM, and TTS.

## How It Works

```
Google Meet ──► Audio Capture ──► VAD ──► STT ──► LLM ──► TTS ──► Audio Playback
                (Playwright)     (Silero)  (Whisper/   (OpenAI/    (OpenAI/
                                           Deepgram)   Anthropic/  ElevenLabs/
                                                       Google)     Google)
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
- At least one LLM API key (OpenAI, Anthropic, or Google)

### Setup

```bash
git clone <repo-url>
cd call-operator

python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# source .venv/Scripts/activate  # Windows (Git Bash)

pip install -e ".[dev]"
playwright install chromium

cp .env.example .env
# Edit .env with your API keys
```

### Run

```bash
python -m call_operator join --url "https://meet.google.com/xxx-yyyy-zzz"
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_PROVIDER` | Yes | `openai` | LLM provider: `openai`, `anthropic`, `google` |
| `LLM_MODEL` | Yes | `gpt-4o` | Model name |
| `OPENAI_API_KEY` | If provider=openai | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | If provider=anthropic | — | Anthropic API key |
| `GOOGLE_API_KEY` | If provider=google | — | Google AI API key |
| `STT_PROVIDER` | No | `whisper_local` | STT: `whisper_local`, `deepgram` |
| `STT_MODEL` | No | `tiny` | Whisper model size or Deepgram model |
| `DEEPGRAM_API_KEY` | If stt=deepgram | — | Deepgram API key |
| `TTS_PROVIDER` | No | `openai` | TTS: `openai`, `elevenlabs`, `google` |
| `TTS_VOICE` | No | `alloy` | Voice name (provider-specific) |
| `ELEVENLABS_API_KEY` | If tts=elevenlabs | — | ElevenLabs API key |
| `BROWSER_HEADLESS` | No | `true` | `false` to see the browser |
| `LOG_LEVEL` | No | `INFO` | `DEBUG` for verbose output |

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
| `python -m call_operator join --url <url>` | Join a meeting |
| `python -m call_operator --help` | Show CLI help |
| `pytest` | Run tests |
| `ruff check src/ tests/` | Lint |
| `ruff format src/ tests/` | Format |
| `mypy src/` | Type check |

## Docker

```bash
docker compose up --build
```

See [Deployment Guide](docs/guide/deployment.md) for production setup.

## Documentation

- [Architecture Overview](docs/architecture/architecture.md)
- [Developer Guide](docs/guide/developer.md)
- [Deployment Guide](docs/guide/deployment.md)
