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
    --env-file .env \
    call-operator join --url "https://meet.google.com/xxx-yyyy-zzz"
```

### Docker Compose

```bash
# Start the service
docker compose up --build

# Run with a specific meeting URL
docker compose run --rm agent join --url "https://meet.google.com/xxx-yyyy-zzz"
```

## Environment Variables (Production)

Same variables as development. See the [Developer Guide](developer.md) for the full table.

For production use, ensure:
- `BROWSER_HEADLESS=true` (no display server available in containers)
- `LOG_LEVEL=INFO` (not DEBUG — avoids logging transcript data)
- `RECORD_AUDIO=false` (unless you need audio recordings)
- API keys set via environment variables, not `.env` file
- Use secrets management (Docker secrets, Vault, AWS SSM, etc.) for API keys

## Container Architecture

The Docker image includes:
- Python 3.12
- Playwright + Chromium browser
- System dependencies for audio processing
- All Python dependencies

The container runs as a single process that joins one meeting at a time.

## Resource Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 cores | 4 cores |
| RAM | 2 GB | 4 GB |
| Disk | 2 GB (image) | 5 GB (with audio recording) |
| Network | Stable internet | Low-latency connection |

**Note:** GPU is NOT required. faster-whisper runs on CPU. For lower latency, use Deepgram cloud STT instead.

## Health Monitoring

Currently no built-in health check endpoint. For production:
- Monitor container exit codes
- Monitor log output for error patterns
- Consider adding a `/health` endpoint if wrapping with a web API

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
