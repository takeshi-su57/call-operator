# [Feature]: Docker deployment with Dockerfile and docker-compose

## Description

Create a production-ready Docker setup for call-operator. The container must include Playwright with Chromium, all Python dependencies, and audio support. Provide a `docker-compose.yml` for easy deployment with environment variable configuration. Verify the full pipeline works inside the container. Document the production deployment workflow.

## Motivation

Docker is the primary deployment target. The agent needs Playwright with Chromium, which has complex system dependencies (fonts, codecs, audio libraries). A well-built Docker image ensures consistent deployment across environments and avoids "works on my machine" issues. docker-compose simplifies configuration and running.

## Tasks

- [ ] Create `Dockerfile`:
  - Base image: `python:3.12-slim` (or `mcr.microsoft.com/playwright/python:v1.40.0-jammy` for pre-installed Playwright)
  - Install system dependencies: audio libraries (pulseaudio, alsa), fonts, codecs
  - Install Python package: `pip install .`
  - Install Playwright browsers: `playwright install chromium --with-deps`
  - Set up virtual audio device (PulseAudio) for audio I/O in headless mode
  - Non-root user for security
  - Health check endpoint or command
  - Optimize layer caching: copy `pyproject.toml` first, then source
- [ ] Create `docker-compose.yml`:
  - Service: `call-operator`
  - Environment variables via `env_file: .env`
  - Volume mount for `data/` directory (persist results and logs)
  - SHM size increase (`shm_size: 2gb`) for Chromium
  - Network configuration
  - Restart policy: `unless-stopped`
- [ ] Create PulseAudio configuration for container:
  - Virtual sink and source for audio capture/playback
  - No-hardware mode for headless operation
- [ ] Test inside container:
  - Verify `python -m call_operator --help` works
  - Verify Playwright can launch Chromium
  - Verify audio capture works with virtual audio device
  - Verify LLM/STT/TTS API calls work (with real keys in .env)
- [ ] Add `.dockerignore`:
  - Exclude `.env`, `data/`, `__pycache__/`, `.git/`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`
- [ ] Update `docs/guide/deployment.md` with:
  - Build instructions: `docker build -t call-operator .`
  - Run instructions: `docker-compose up -d`
  - Configuration via `.env`
  - Troubleshooting: audio issues, Chromium crashes, permissions
  - Resource requirements: CPU, memory, disk
  - Monitoring: logs, health check

## Acceptance Criteria

- [ ] `docker build -t call-operator .` succeeds
- [ ] `docker-compose up` starts the container
- [ ] Container runs the CLI successfully: `docker run call-operator --help`
- [ ] Playwright launches Chromium inside the container
- [ ] Virtual audio device works for capture and playback
- [ ] `.env` variables are passed to the container
- [ ] `data/` volume persists across container restarts
- [ ] Container runs as non-root user
- [ ] Image size is reasonable (under 3GB)
- [ ] `docs/guide/deployment.md` covers build, run, configure, troubleshoot

## Dependencies

- 010 — Async Pipeline (full pipeline must work to verify in Docker)

## Files to Create/Modify

- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`
- `docs/guide/deployment.md`
