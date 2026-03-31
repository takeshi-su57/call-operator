FROM python:3.12-slim AS base

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# ---------------------------------------------------------------------------
# System dependencies for Playwright + audio processing
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Chromium runtime deps
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libatspi2.0-0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
    # Audio libraries
    libasound2 libpulse0 pulseaudio \
    # Fonts (needed for Chromium rendering)
    fonts-liberation fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# PulseAudio virtual audio device for headless audio I/O
# ---------------------------------------------------------------------------
RUN mkdir -p /etc/pulse
COPY docker/pulse-default.pa /etc/pulse/default.pa

# ---------------------------------------------------------------------------
# Python dependencies (cached layer — only rebuilds when pyproject.toml changes)
# ---------------------------------------------------------------------------
COPY pyproject.toml README.md ./
RUN uv sync --all-extras --no-dev --frozen

# ---------------------------------------------------------------------------
# Install Playwright browser
# ---------------------------------------------------------------------------
RUN uv run playwright install chromium && uv run playwright install-deps chromium

# ---------------------------------------------------------------------------
# Application source
# ---------------------------------------------------------------------------
COPY src/ src/

# ---------------------------------------------------------------------------
# Data directory + non-root user
# ---------------------------------------------------------------------------
RUN mkdir -p /app/data \
    && groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 --home-dir /app appuser \
    && chown -R appuser:appuser /app

USER appuser

# ---------------------------------------------------------------------------
# Default environment
# ---------------------------------------------------------------------------
ENV BROWSER_HEADLESS=true
ENV LOG_LEVEL=INFO

# ---------------------------------------------------------------------------
# Health check — verify CLI responds
# ---------------------------------------------------------------------------
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["uv", "run", "python", "-m", "call_operator", "--version"]

ENTRYPOINT ["uv", "run", "call-operator"]
