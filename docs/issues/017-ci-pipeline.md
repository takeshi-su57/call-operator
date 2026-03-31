# [Feature]: GitHub Actions CI pipeline

## Description

Set up a GitHub Actions CI workflow that runs on every push and pull request. The pipeline runs linting (ruff), type checking (mypy), and tests (pytest) to catch regressions before merge. Optionally cache dependencies for faster runs.

## Motivation

Without CI, broken code can be merged into main. Automated checks enforce code quality standards (linting, typing) and verify functionality (tests) on every change. This is especially important as the project grows and multiple issues are worked on in parallel.

## Tasks

- [x] Create `.github/workflows/ci.yml`
- [x] Configure triggers: `push` to `main`, `pull_request` to `main`
- [x] Set up Python 3.12 environment using `actions/setup-python@v5`
- [x] Install and cache uv using `astral-sh/setup-uv@v4` with `enable-cache: true`
- [x] Install the project: `uv sync --all-extras --frozen`
- [x] Run linting step: `uv run ruff check src/ tests/`
- [x] Run format check step: `uv run ruff format --check src/ tests/`
- [x] Run type checking step: `uv run mypy src/`
- [x] Run tests step: `uv run pytest --cov=call_operator --cov-report=xml --cov-report=term -q`
- [x] Upload coverage report as artifact via `actions/upload-artifact@v4`
- [x] Set job timeout: 10 minutes
- [x] Add status badge to README.md
- [ ] Consider matrix strategy for Python 3.12 and 3.13 — **deferred**: single version sufficient for now
- [x] Do NOT install Playwright browsers in CI — tests mock the browser

## Acceptance Criteria

- [x] CI workflow runs on push to main
- [x] CI workflow runs on pull requests targeting main
- [x] Lint failures cause the CI to fail
- [x] Type check failures cause the CI to fail
- [x] Test failures cause the CI to fail
- [x] CI completes in under 5 minutes for a clean run (uv caching)
- [x] Dependencies are cached between runs (`astral-sh/setup-uv` with `enable-cache: true`)
- [x] Coverage report is generated (XML artifact + terminal output)
- [x] All steps are clearly named in the Actions UI

## Implementation Notes

### Workflow steps

```
1. Checkout code (actions/checkout@v4)
2. Set up Python 3.12 (actions/setup-python@v5)
3. Install uv (astral-sh/setup-uv@v4, cache enabled)
4. Install dependencies (uv sync --all-extras --frozen)
5. Lint — ruff check src/ tests/
6. Format check — ruff format --check src/ tests/
7. Type check — mypy src/
8. Tests — pytest --cov + coverage XML + terminal
9. Upload coverage artifact (always, even on failure)
```

### Key decisions

- **uv instead of pip**: matches the project's package manager, faster installs, built-in caching
- **`--all-extras --frozen`**: installs all optional providers so mypy resolves all imports
- **No Playwright install**: all browser tests use mocked Playwright — saves ~1 minute
- **Coverage uploaded with `if: always()`**: preserved even if tests fail
- **Single job**: lint + type check + test in one job (simpler for this project size)

## Dependencies

- 015 — Testing (tests must exist for CI to run them)

## Files Created/Modified

- `.github/workflows/ci.yml` — NEW: CI workflow
- `README.md` — added CI status badge
