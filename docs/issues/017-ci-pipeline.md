# [Feature]: GitHub Actions CI pipeline

## Description

Set up a GitHub Actions CI workflow that runs on every push and pull request. The pipeline runs linting (ruff), type checking (mypy), and tests (pytest) to catch regressions before merge. Optionally cache dependencies for faster runs.

## Motivation

Without CI, broken code can be merged into main. Automated checks enforce code quality standards (linting, typing) and verify functionality (tests) on every change. This is especially important as the project grows and multiple issues are worked on in parallel.

## Tasks

- [ ] Create `.github/workflows/ci.yml`
- [ ] Configure triggers: `push` to `main`, `pull_request` to `main`
- [ ] Set up Python 3.12 environment using `actions/setup-python@v5`
- [ ] Cache pip dependencies using `actions/cache@v4` with `hashFiles('pyproject.toml')` key
- [ ] Install the project: `pip install -e ".[dev]"`
- [ ] Run linting step: `ruff check src/ tests/`
- [ ] Run format check step: `ruff format --check src/ tests/`
- [ ] Run type checking step: `mypy src/`
- [ ] Run tests step: `pytest --cov=call_operator --cov-report=xml`
- [ ] Upload coverage report as artifact (or integrate with Codecov)
- [ ] Set job timeout: 10 minutes
- [ ] Configure job to fail fast on first error
- [ ] Add status badge to README.md
- [ ] Consider matrix strategy for Python 3.12 and 3.13 (optional)
- [ ] Do NOT install Playwright browsers in CI (tests mock the browser) — skip `playwright install`

## Acceptance Criteria

- [ ] CI workflow runs on push to main
- [ ] CI workflow runs on pull requests targeting main
- [ ] Lint failures cause the CI to fail
- [ ] Type check failures cause the CI to fail
- [ ] Test failures cause the CI to fail
- [ ] CI completes in under 5 minutes for a clean run
- [ ] Pip dependencies are cached between runs
- [ ] Coverage report is generated
- [ ] All steps are clearly named in the Actions UI

## Dependencies

- 015 — Testing (tests must exist for CI to run them)

## Files to Create/Modify

- `.github/workflows/ci.yml`
- `README.md` (add CI badge)
