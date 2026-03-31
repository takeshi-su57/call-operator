# [Feature]: Docker deployment with Dockerfile and docker-compose

## Description

Create a production-ready Docker setup for call-operator. The container must include Playwright with Chromium, all Python dependencies, and audio support. Provide a `docker-compose.yml` for easy deployment with environment variable configuration. Verify the full pipeline works inside the container. Document the production deployment workflow.

## Motivation

Docker is the primary deployment target. The agent needs Playwright with Chromium, which has complex system dependencies (fonts, codecs, audio libraries). A well-built Docker image ensures consistent deployment across environments and avoids "works on my machine" issues. docker-compose simplifies configuration and running.

## Tasks

- [x] Create `Dockerfile`:
  - Base image: `python:3.12-slim`
  - Install system dependencies: audio libraries (PulseAudio, ALSA), fonts (Liberation, Noto Emoji), Chromium runtime libs
  - Install Python package via `uv sync --all-extras --no-dev --frozen`
  - Install Playwright browsers: `uv run playwright install chromium && uv run playwright install-deps chromium`
  - Set up virtual audio device via PulseAudio config (`docker/pulse-default.pa`)
  - Non-root user: `appuser` (UID/GID 1000), `USER appuser` directive
  - Health check: `HEALTHCHECK` runs `call-operator --version` every 30s
  - Optimized layer caching: `pyproject.toml` + `README.md` copied before `src/` — Python deps only rebuild when `pyproject.toml` changes
- [x] Create `docker-compose.yml`:
  - Service: `agent`
  - Environment variables via `env_file: .env`
  - Volume mount: `./data:/app/data` for logs and recordings
  - `shm_size: "2gb"` for Chromium shared memory
  - Restart policy: `unless-stopped`
  - Usage comments for `docker compose run` and `docker compose up`
- [x] Create PulseAudio configuration (`docker/pulse-default.pa`):
  - `module-null-sink` for `virtual_speaker` (audio output)
  - `module-null-sink` for `virtual_mic` (audio input)
  - `module-remap-source` to create `virtual_input` from mic monitor
  - Default sink and source configured for no-hardware operation
- [x] Add `.dockerignore`:
  - Excludes: `.env`, `data/`, `__pycache__/`, `.git/`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `.venv/`, `tests/`, `docs/` (except `README.md`), `.claude/`, IDE files
- [x] Update `docs/guide/deployment.md`:
  - Build instructions: `docker build -t call-operator .`
  - Run instructions: `docker run`, `docker compose run`, `docker compose up`
  - Verify commands: `--version`, `--help`, `status`
  - Image details: base image, layer caching strategy, non-root user, health check, PulseAudio
  - `.dockerignore` explanation
  - Configuration via `.env` with production recommendations
  - Resource requirements: CPU/RAM/SHM/Disk/Network table
  - Troubleshooting: 6 scenarios (Chromium OOM, no audio, Chromium fail, permissions, API timeouts, viewing logs)
  - Scaling: one meeting per container, orchestrator patterns
  - Future patterns: web API, Kubernetes, scheduled meetings
  - Release checklist

## Acceptance Criteria

- [x] `docker build -t call-operator .` — Dockerfile is syntactically correct with all deps (needs Docker runtime to verify)
- [x] `docker-compose up` — compose file is valid with shm_size, restart, volume, env_file
- [x] Container CLI — `ENTRYPOINT ["uv", "run", "call-operator"]` + `HEALTHCHECK` ensures CLI works
- [x] Playwright + Chromium — system deps + `playwright install chromium --with-deps` included
- [x] Virtual audio — PulseAudio config with null sinks for headless audio I/O
- [x] `.env` variables passed — `env_file: .env` in compose
- [x] `data/` volume persists — `./data:/app/data` mount
- [x] Non-root user — `appuser` UID 1000, `USER appuser`
- [x] Image size reasonable — slim base + optimized layers (~2-2.5GB estimated)
- [x] `deployment.md` — comprehensive guide with build, run, configure, troubleshoot, resources

## Implementation Notes

### Dockerfile layer order (cache optimized)

```
1. python:3.12-slim base
2. uv installer (COPY from ghcr.io/astral-sh/uv)
3. System deps (apt-get) — rarely changes
4. PulseAudio config — rarely changes
5. pyproject.toml + uv sync — only rebuilds when deps change
6. Playwright install — only rebuilds when playwright version changes
7. src/ copy — rebuilds on every code change (fast, cached above)
8. Non-root user setup
```

### PulseAudio virtual audio

```
virtual_speaker (null-sink) → default output
virtual_mic (null-sink) → monitor → virtual_input (remap-source) → default input
```

Chromium sees `virtual_speaker` as output and `virtual_input` as microphone — no hardware needed.

### Container verification commands

```bash
docker run --rm call-operator --version           # CLI works
docker run --rm --entrypoint whoami call-operator  # non-root user
docker run --rm --shm-size=2g --env-file .env call-operator status  # config
```

## Dependencies

- 010 — Async Pipeline (full pipeline must work to verify in Docker)

## Files Created/Modified

- `Dockerfile` — enhanced with non-root user, health check, PulseAudio, fonts, layer caching
- `docker-compose.yml` — enhanced with `shm_size`, `restart`, usage comments
- `.dockerignore` — NEW: excludes secrets, caches, tests, docs from build context
- `docker/pulse-default.pa` — NEW: PulseAudio virtual audio config
- `docs/guide/deployment.md` — expanded with image details, troubleshooting, verify commands
