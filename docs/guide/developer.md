# Developer Guide

How to set up, develop, and test call-operator locally.

## Prerequisites

| Requirement | Version | Check |
|-------------|---------|-------|
| Python | 3.12+ | `python --version` |
| pip | latest | `pip --version` |
| Git | any | `git --version` |
| LLM API key | — | At least one: OpenAI, Anthropic, or Google |

## Initial Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd call-operator
```

### 2. Create a virtual environment

```bash
python -m venv .venv

# Activate it:
# Linux/macOS
source .venv/bin/activate

# Windows (Git Bash)
source .venv/Scripts/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
# Install package with all providers + dev dependencies
pip install -e ".[dev]"

# Or install with specific providers only
pip install -e ".[openai]"        # OpenAI LLM + TTS
pip install -e ".[deepgram]"      # Deepgram STT

# Install Playwright browser binaries
playwright install chromium
```

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and configure your providers:

```bash
# Minimum required: LLM provider
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-...

# STT (default: local Whisper, no API key needed)
STT_PROVIDER=whisper_local
STT_MODEL=tiny

# TTS (default: OpenAI, uses same API key)
TTS_PROVIDER=openai
TTS_VOICE=alloy
```

### 5. Verify the setup

```bash
# Check CLI loads
python -m call_operator --help

# Run tests
pytest

# Lint + type check
ruff check src/ tests/
mypy src/
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_PROVIDER` | Yes | `openai` | LLM provider: `openai`, `anthropic`, `google` |
| `LLM_MODEL` | Yes | `gpt-4o` | Model name (provider-specific) |
| `OPENAI_API_KEY` | If provider=openai | — | OpenAI API key (also used for OpenAI TTS) |
| `ANTHROPIC_API_KEY` | If provider=anthropic | — | Anthropic API key |
| `GOOGLE_API_KEY` | If provider=google | — | Google AI API key |
| `STT_PROVIDER` | No | `whisper_local` | STT: `whisper_local`, `deepgram` |
| `STT_MODEL` | No | `tiny` | Whisper model size or Deepgram model name |
| `DEEPGRAM_API_KEY` | If stt=deepgram | — | Deepgram API key |
| `TTS_PROVIDER` | No | `openai` | TTS: `openai`, `elevenlabs`, `google` |
| `TTS_VOICE` | No | `alloy` | Voice name (provider-specific) |
| `ELEVENLABS_API_KEY` | If tts=elevenlabs | — | ElevenLabs API key |
| `BROWSER_HEADLESS` | No | `true` | `false` to see the browser during dev |
| `LOG_LEVEL` | No | `INFO` | `DEBUG` for verbose output |
| `AUDIO_SAMPLE_RATE` | No | `16000` | Audio sample rate in Hz |
| `VAD_THRESHOLD` | No | `0.5` | VAD speech probability threshold (0.0-1.0) |
| `RECORD_AUDIO` | No | `false` | `true` to save audio recordings to data/ |

## Project Structure

```
src/call_operator/
├── main.py              # CLI entry point (Typer + Rich)
├── config.py            # Pydantic Settings — reads .env
├── pipeline.py          # Async pipeline orchestration
├── adapters/            # Meeting platform adapters
│   ├── base.py          # Abstract MeetingAdapter interface
│   └── google_meet.py   # Google Meet via Playwright
├── audio/               # Audio processing
│   ├── capture.py       # Audio stream capture
│   ├── vad.py           # Silero Voice Activity Detection
│   └── playback.py      # Audio output to meeting
├── stt/                 # Speech-to-Text providers
│   ├── base.py          # Abstract STTProvider + factory
│   ├── whisper_local.py # faster-whisper (CPU, local)
│   └── deepgram_cloud.py # Deepgram streaming API
├── llm/                 # LLM conversation engine
│   ├── provider.py      # LangChain model factory
│   └── conversation.py  # Conversation history + response
├── tts/                 # Text-to-Speech providers
│   ├── base.py          # Abstract TTSProvider + factory
│   ├── openai_tts.py    # OpenAI TTS
│   ├── elevenlabs_tts.py # ElevenLabs
│   └── google_tts.py    # Google Cloud TTS
└── prompts/             # LLM prompt templates
    └── conversation.py  # System prompt, response template
tests/                   # pytest test suite
data/                    # Runtime output (git-ignored)
docs/                    # Architecture docs + guides
```

## Development Workflow

### Running the agent

```bash
# Join a Google Meet
python -m call_operator join --url "https://meet.google.com/xxx-yyyy-zzz"
```

### Debugging with visible browser

Set `BROWSER_HEADLESS=false` in `.env` to watch Playwright interact with Google Meet:

```bash
BROWSER_HEADLESS=false python -m call_operator join --url "https://meet.google.com/xxx-yyyy-zzz"
```

### Adding a new meeting adapter

1. Create `src/call_operator/adapters/<platform>.py`
2. Implement the `MeetingAdapter` interface from `adapters/base.py`
3. Register in the pipeline factory
4. Update `docs/architecture/architecture.md`

### Adding a new STT/TTS provider

1. Create `src/call_operator/stt/<provider>.py` or `tts/<provider>.py`
2. Implement the abstract base class (`STTProvider` or `TTSProvider`)
3. Register in the factory function (`get_stt()` or `get_tts()` in `base.py`)
4. Add provider-specific env vars to `.env.example` and `config.py`

### Adding a new prompt template

1. Add constants to existing file in `prompts/` or create a new file
2. Use `{placeholder}` syntax for variable parts
3. Keep prompts conversational (the agent speaks, not writes)

## All Commands

| Command | Description |
|---------|-------------|
| `python -m call_operator join --url <url>` | Join a meeting |
| `python -m call_operator --help` | Show CLI help |
| `pytest` | Run all tests |
| `pytest -v` | Run tests (verbose) |
| `pytest -k test_name` | Run specific test |
| `pytest --cov=call_operator` | Run with coverage |
| `ruff check src/ tests/` | Lint code |
| `ruff check --fix src/ tests/` | Auto-fix lint issues |
| `ruff format src/ tests/` | Format code |
| `mypy src/` | Type check |
| `playwright install chromium` | Install/update browser |

## Testing

Tests live in `tests/`. Shared fixtures are in `tests/conftest.py`.

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=call_operator

# Run specific test file
pytest tests/test_config.py
```

Key principle: **always mock external I/O** (LLM calls, browser, STT/TTS APIs). See `.claude/rules/testing.md` for mocking patterns.

## Code Quality

All code must pass before committing:

```bash
ruff check src/ tests/     # No lint errors
ruff format src/ tests/    # Consistent formatting
mypy src/                  # No type errors
pytest                     # All tests pass
```

## Commit Conventions

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
feat(stt): add Deepgram streaming provider
fix(vad): handle empty audio chunks
docs: update developer guide
test: add tests for TTS factory
chore: update langchain dependency
```

See `.claude/rules/git-commit.md` for full details.

## Troubleshooting

### `playwright install` fails

Make sure you have system dependencies. On Linux:
```bash
playwright install-deps chromium
```

### Import errors after install

Make sure you installed in editable mode:
```bash
pip install -e ".[dev]"
```

### LLM calls fail

1. Check your API key is set in `.env`
2. Check `LLM_PROVIDER` matches the key you provided
3. Try `LOG_LEVEL=DEBUG` for detailed error output

### faster-whisper is slow

The `tiny` model is fastest on CPU. If still too slow:
- Try `STT_PROVIDER=deepgram` for cloud-based low-latency STT
- Ensure no other heavy processes are running on the same CPU

### Audio not captured from meeting

1. Set `BROWSER_HEADLESS=false` to debug visually
2. Check that Playwright joined the meeting successfully
3. Check browser permissions for microphone/audio
