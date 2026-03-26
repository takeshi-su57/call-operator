# [Feature]: Project setup — pyproject.toml, editable install, CLI skeleton

## Description

Bootstrap the call-operator project with a proper Python package structure. Create `pyproject.toml` with all runtime and dev dependencies, configure ruff and mypy, and implement a minimal CLI entry point using Typer so that `python -m call_operator --help` works.

## Motivation

Every subsequent issue depends on a working project skeleton. The editable install ensures developers can iterate quickly, and the linting/type-checking configuration enforces code quality from day one.

## Tasks

- [x] Create/verify `pyproject.toml` with project metadata (name: `call-operator`, Python 3.12+)
- [x] Add runtime dependencies: `langchain`, `langchain-openai`, `langchain-anthropic`, `langchain-google-genai`, `playwright`, `pydantic`, `pydantic-settings`, `python-dotenv`, `typer`, `rich`, `faster-whisper`, `deepgram-sdk`, `openai`, `elevenlabs`, `google-cloud-texttospeech`, `silero-vad`, `torch`, `torchaudio`, `numpy`
- [x] Add dev dependencies: `ruff`, `mypy`, `pytest`, `pytest-asyncio`, `pytest-cov`
- [x] Configure `[tool.ruff]` — line-length 100, target Python 3.12
- [x] Configure `[tool.mypy]` — strict mode
- [x] Create `src/call_operator/__init__.py` with `__version__`
- [x] Create `src/call_operator/__main__.py` that calls the Typer app
- [x] Create `src/call_operator/main.py` with Typer CLI app and a `join` command stub
- [x] Create empty `tests/__init__.py` and `tests/conftest.py`
- [x] Verify `uv sync --all-extras` succeeds
- [x] Verify `uv run python -m call_operator --help` prints usage
- [x] Verify `uv run ruff check src/ tests/` passes with no errors
- [x] Verify `uv run mypy src/` passes
- [x] Add OpenRouter as configurable LLM provider
- [x] Fix type-only imports (ruff TC001/TC003) across all stub modules
- [x] Fix async iterator abstract method signatures (mypy strict)
- [x] Update docs (README, architecture, developer guide, CLAUDE.md) with OpenRouter
- [x] Untrack `.claude/settings.local.json` and fix `.gitignore`

## Acceptance Criteria

- [x] `uv sync --all-extras` completes without errors
- [x] `uv run python -m call_operator --help` displays CLI help with the `join` command listed
- [x] `uv run ruff check src/ tests/` exits 0
- [x] `uv run ruff format --check src/ tests/` exits 0
- [x] `uv run mypy src/` exits 0 with strict mode
- [x] Project structure matches the layout defined in CLAUDE.md
- [x] 17 tests pass (`uv run pytest`)

## Dependencies

None — this is the first issue.

## Files Created/Modified

- `pyproject.toml`
- `src/call_operator/__init__.py`
- `src/call_operator/__main__.py`
- `src/call_operator/main.py`
- `src/call_operator/config.py`
- `src/call_operator/llm/provider.py`
- `src/call_operator/adapters/base.py`
- `src/call_operator/adapters/google_meet.py`
- `src/call_operator/audio/capture.py`
- `src/call_operator/audio/playback.py`
- `src/call_operator/audio/vad.py`
- `src/call_operator/llm/conversation.py`
- `src/call_operator/stt/base.py`
- `src/call_operator/stt/deepgram_cloud.py`
- `src/call_operator/stt/whisper_local.py`
- `src/call_operator/tts/base.py`
- `tests/__init__.py`
- `tests/conftest.py`
- `tests/test_llm.py`
- `.env.example`
- `.gitignore`
- `.claude/CLAUDE.md`
- `README.md`
- `docs/architecture/architecture.md`
- `docs/guide/developer.md`
