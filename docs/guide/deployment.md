# Deployment Guide

How to package and deploy call-operator using Docker.

## Deployment Model

call-operator is a **Dockerized service** that runs a headless browser to join meetings. It requires:
- A container runtime (Docker)
- Network access to meeting platforms (Google Meet)
- Network access to API providers (LLM, STT, TTS)
- No GPU required (CPU-only by default)

## Docker Deployment

### Build

```bash
docker build -t call-operator .
```

### Run

```bash
docker run --rm \
    --shm-size=2g \
    --env-file .env \
    call-operator join --url "https://meet.google.com/xxx-yyyy-zzz"
```

### Docker Compose

```bash
# Build and run with a specific meeting URL
docker compose run --rm agent join --url "https://meet.google.com/xxx-yyyy-zzz"

# Start detached
docker compose up -d --build

# View logs
docker compose logs -f agent

# Stop
docker compose down
```

### Verify the image

```bash
# Check CLI works
docker run --rm call-operator --version

# Check help
docker run --rm call-operator --help

# Check config
docker run --rm --env-file .env call-operator status
```

## Docker Image Details

### Base image

`python:3.12-slim` with system dependencies added:
- Chromium runtime libraries (NSS, ATK, GBM, etc.)
- Audio libraries (ALSA, PulseAudio)
- Fonts (Liberation, Noto Emoji)
- Playwright + Chromium browser

### Layer caching

The Dockerfile is optimized for cache efficiency:
1. System dependencies (rarely changes)
2. `pyproject.toml` + `uv sync` (only rebuilds when deps change)
3. Playwright install (only rebuilds when playwright version changes)
4. Application source (rebuilds on every code change — fast)

### Non-root user

The container runs as `appuser` (UID 1000) for security. The `/app/data` directory is writable.

### Health check

Built-in Docker health check runs `call-operator --version` every 30 seconds:
```
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3
```

### Virtual audio (PulseAudio)

The container includes PulseAudio configured with virtual audio devices (`docker/pulse-default.pa`):
- `virtual_speaker` — null sink for audio output
- `virtual_mic` — null sink with monitor for audio input

This allows Chromium to capture and play audio without real hardware.

## Environment Variables (Production)

Same variables as development. See the [Developer Guide](developer.md) for the full table.

For production use, ensure:
- `BROWSER_HEADLESS=true` (no display server available in containers)
- `LOG_LEVEL=INFO` (not DEBUG — avoids logging transcript data)
- `RECORD_AUDIO=false` (unless you need audio recordings)
- API keys set via environment variables, not `.env` file
- Use secrets management (Docker secrets, Vault, AWS SSM, etc.) for API keys

## .dockerignore

The `.dockerignore` excludes:
- `.env` files (secrets)
- `data/`, `tests/`, `docs/` (not needed in image)
- `__pycache__/`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`
- `.git/`, `.venv/`, IDE files

## Container Architecture

The Docker image includes:
- Python 3.12
- Playwright + Chromium browser
- PulseAudio with virtual audio devices
- All Python dependencies (including optional providers)

The container runs as a single process that joins one meeting at a time.

## Resource Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 cores | 4 cores |
| RAM | 2 GB | 4 GB |
| SHM | 2 GB | 2 GB |
| Disk | 2 GB (image) | 5 GB (with audio recording) |
| Network | Stable internet | Low-latency connection |

**Note:** GPU is NOT required. faster-whisper runs on CPU. For lower latency, use Deepgram cloud STT instead.

**Important:** Chromium requires at least 2 GB of shared memory (`--shm-size=2g`). Without this, Chromium will crash with "out of memory" errors. The `docker-compose.yml` sets this automatically.

## Troubleshooting

### Chromium crashes with "out of memory"

Increase shared memory size:
```bash
docker run --rm --shm-size=2g --env-file .env call-operator join --url "..."
```

Or in `docker-compose.yml`:
```yaml
shm_size: "2gb"
```

### No audio capture / silence only

Verify PulseAudio is running inside the container:
```bash
docker exec -it <container> pulseaudio --check
```

If not running, start it:
```bash
docker exec -it <container> pulseaudio --start --daemonize
```

### Chromium fails to launch

Check that system dependencies are installed:
```bash
docker exec -it <container> uv run playwright install-deps chromium
```

### Permission denied on /app/data

The container runs as UID 1000. Ensure the host `data/` directory is writable:
```bash
chmod 777 data/
# Or match the UID:
chown 1000:1000 data/
```

### API timeouts

Ensure the container has network access to:
- `meet.google.com` (Google Meet)
- `api.openai.com` (OpenAI LLM/TTS)
- `api.deepgram.com` (Deepgram STT)
- `api.elevenlabs.io` (ElevenLabs TTS)

### Container logs

```bash
# Real-time logs
docker compose logs -f agent

# Session log file (persisted in data volume)
cat data/session.log
```

## Scaling

Current architecture supports **one meeting per container**. For multiple concurrent meetings:
- Run multiple containers, each joining a different meeting
- Use an orchestrator (Docker Compose, Kubernetes) to manage containers
- Each container is independent — no shared state

## Future Deployment Patterns

These are **not implemented** — documented here for planning purposes.

### Web API wrapper

If a web interface is added later, the agent could be wrapped with FastAPI:
- `POST /join` — start a session for a meeting URL
- `GET /status` — check session status
- `POST /leave` — leave the meeting
- `GET /transcript` — get conversation transcript

### Kubernetes deployment

For multi-tenant production use:
- Helm chart with configurable replicas
- One pod per active meeting
- Horizontal Pod Autoscaler based on meeting count
- Persistent volumes for audio recordings

### Scheduled meetings

```bash
# Join a meeting at a specific time (via cron or scheduler)
0 14 * * 1 docker run --rm --env-file .env call-operator join --url "https://meet.google.com/xxx"
```

## Release Checklist

Before releasing a new version:

1. Update version in `pyproject.toml`
2. Ensure all tests pass: `uv run pytest`
3. Ensure lint + type check pass: `uv run ruff check src/ tests/ && uv run mypy src/`
4. Build Docker image: `docker build -t call-operator .`
5. Test the Docker image with a real meeting
6. Tag the release: `git tag v0.1.0`
7. Push tag: `git push origin v0.1.0`
