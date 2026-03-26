# [Feature]: Project setup — pyproject.toml, editable install, CLI skeleton

## Description

Bootstrap the call-operator project with a proper Python package structure. Create `pyproject.toml` with all runtime and dev dependencies, configure ruff and mypy, and implement a minimal CLI entry point using Typer so that `python -m call_operator --help` works.

## Motivation

Every subsequent issue depends on a working project skeleton. The editable install ensures developers can iterate quickly, and the linting/type-checking configuration enforces code quality from day one.

## Tasks

- [ ] Create/verify `pyproject.toml` with project metadata (name: `call-operator`, Python 3.12+)
- [ ] Add runtime dependencies: `langchain`, `langchain-openai`, `langchain-anthropic`, `langchain-google-genai`, `playwright`, `pydantic`, `pydantic-settings`, `python-dotenv`, `typer`, `rich`, `faster-whisper`, `deepgram-sdk`, `openai`, `elevenlabs`, `google-cloud-texttospeech`, `silero-vad`, `torch`, `torchaudio`, `numpy`
- [ ] Add dev dependencies: `ruff`, `mypy`, `pytest`, `pytest-asyncio`, `pytest-cov`
- [ ] Configure `[tool.ruff]` — line-length 100, target Python 3.12
- [ ] Configure `[tool.mypy]` — strict mode
- [ ] Create `src/call_operator/__init__.py` with `__version__`
- [ ] Create `src/call_operator/__main__.py` that calls the Typer app
- [ ] Create `src/call_operator/main.py` with Typer CLI app and a `run` command stub
- [ ] Create empty `tests/__init__.py` and `tests/conftest.py`
- [ ] Verify `pip install -e ".[dev]"` succeeds
- [ ] Verify `python -m call_operator --help` prints usage
- [ ] Verify `ruff check src/ tests/` passes with no errors
- [ ] Verify `mypy src/` passes

## Acceptance Criteria

- [ ] `pip install -e ".[dev]"` completes without errors
- [ ] `python -m call_operator --help` displays CLI help with the `run` command listed
- [ ] `ruff check src/ tests/` exits 0
- [ ] `ruff format --check src/ tests/` exits 0
- [ ] `mypy src/` exits 0 with strict mode
- [ ] Project structure matches the layout defined in CLAUDE.md

## Dependencies

None — this is the first issue.

## Files to Create/Modify

- `pyproject.toml`
- `src/call_operator/__init__.py`
- `src/call_operator/__main__.py`
- `src/call_operator/main.py`
- `tests/__init__.py`
- `tests/conftest.py`
