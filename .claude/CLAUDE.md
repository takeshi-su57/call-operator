# call-operator — Project Context

**Project name:** call-operator

Real-time AI meeting agent. Joins video calls (Google Meet), listens to participants via STT, processes with an LLM, and responds with generated voice via TTS. Fully automated conversational participant.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12+ |
| Audio Capture | Playwright (browser bot joins meeting) |
| VAD | Silero VAD (local, no GPU) |
| STT (local) | faster-whisper (tiny/base, CPU) |
| STT (cloud) | Deepgram (streaming WebSocket) |
| LLM | LangChain (OpenAI / Anthropic / Google — configurable) |
| TTS | OpenAI TTS / ElevenLabs / Google Cloud TTS (configurable) |
| Pipeline | asyncio queues (streaming stages) |
| CLI | Typer + Rich |
| Config | Pydantic Settings + python-dotenv |
| Linting | Ruff |
| Type Checking | mypy (strict) |
| Testing | pytest + pytest-asyncio |
| Containerization | Docker |

## Repository Layout

```
src/call_operator/           → Main Python package
  main.py                    → CLI entry point (Typer app)
  config.py                  → Pydantic Settings (env var bindings)
  pipeline.py                → Async pipeline orchestration
  adapters/                  → Meeting platform adapters
    base.py                  → Abstract adapter interface
    google_meet.py           → Playwright-based Google Meet bot
  audio/                     → Audio processing modules
    capture.py               → Audio stream capture from browser
    vad.py                   → Voice Activity Detection (Silero)
    playback.py              → Audio output back to meeting
  stt/                       → Speech-to-Text providers
    base.py                  → Abstract STT interface
    whisper_local.py         → faster-whisper (CPU, local)
    deepgram_cloud.py        → Deepgram streaming API
  llm/                       → LLM conversation engine
    provider.py              → LangChain model factory
    conversation.py          → Conversation memory + response generation
  tts/                       → Text-to-Speech providers
    base.py                  → Abstract TTS interface
    openai_tts.py            → OpenAI TTS
    elevenlabs_tts.py        → ElevenLabs
    google_tts.py            → Google Cloud TTS
  prompts/                   → LLM prompt templates
    conversation.py          → System prompts, response templates
tests/                       → pytest test suite
data/                        → Runtime data (git-ignored)
docs/                        → Architecture docs, guides
  architecture/              → System design + ADRs
  guide/                     → Developer and deployment guides
```

## Architecture Patterns

**Async Pipeline** — The agent is an asyncio pipeline with stages connected by `asyncio.Queue`. Audio flows: `capture → VAD → STT → LLM → TTS → playback`. Each stage runs as an async task. See `.claude/rules/architecture.md`.

**Adapter Pattern** — Meeting platforms (Google Meet, Zoom, etc.) are abstracted behind `adapters/base.py`. Each adapter handles joining, audio capture, and audio playback for its platform.

**Provider Pattern** — STT, LLM, and TTS are pluggable. Abstract base classes in `stt/base.py`, `tts/base.py`. Config selects the active provider via env vars.

**Pipeline Flow** — `audio capture → VAD (speech detection) → STT (speech→text) → LLM (generate response) → TTS (text→speech) → audio playback`

## Key Commands

```bash
pip install -e ".[dev]"                          # Install with dev deps
python -m call_operator join --url <meet-url>    # Join a meeting
python -m call_operator --help                   # CLI help
pytest                                           # Run tests
ruff check src/ tests/                           # Lint
ruff format src/ tests/                          # Format
mypy src/                                        # Type check
playwright install chromium                      # Install browser
```

## Conventions

- **Commits:** Conventional commits — `type(scope): description`
- **File naming:** snake_case for files, PascalCase for classes
- **Typing:** strict mypy, all functions typed
- **Linting:** Ruff (line-length 100, Python 3.12 target)
- **Config:** Never hardcode API keys — use env vars via `config.py`

## Rules (Detailed Guidance)

- `.claude/rules/architecture.md` — Pipeline design, adapter/provider patterns, async patterns, anti-patterns
- `.claude/rules/testing.md` — pytest strategy, mocking patterns, fixtures, coverage targets
- `.claude/rules/security.md` — API key management, audio data handling, browser safety
- `.claude/rules/git-commit.md` — Conventional commit format, types, examples
- `.claude/rules/pull-request.md` — PR title format, description template, size guidelines
- `.claude/rules/gh-issue.md` — Issue title format, templates for bugs/features/chores
- `.claude/rules/ai-framework.md` — Sync protocol, skill/rule design, maintenance
- `.claude/rules/documentation.md` — Docs structure, ADR conventions

## Known Gaps

- All module implementations are stubs (TODO placeholders)
- No CI pipeline yet
- Google Meet adapter strategy not fully designed (Playwright audio capture approach TBD)
- No reconnection/resilience logic yet
- No conversation memory persistence
- VAD + streaming STT integration not tested end-to-end
- Audio playback back into meeting not implemented
