FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install system deps for Playwright + audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libatspi2.0-0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
    libasound2 libpulse0 \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ src/

# Install dependencies with uv
RUN uv sync --all-extras --no-dev --frozen

# Install Playwright browser
RUN uv run playwright install chromium && uv run playwright install-deps chromium

# Create data directory
RUN mkdir -p /app/data

# Default env
ENV BROWSER_HEADLESS=true
ENV LOG_LEVEL=INFO

ENTRYPOINT ["uv", "run", "call-operator"]
