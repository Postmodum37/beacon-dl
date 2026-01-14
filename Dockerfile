# Dockerfile for beacon-dl
# BeaconTV downloader with subtitle support

FROM python:3.14-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Build the wheel
RUN uv build --wheel

# Create virtual environment and install the wheel
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python dist/*.whl

# Install Playwright Chromium browser
ENV PLAYWRIGHT_BROWSERS_PATH=/app/.playwright
RUN /app/.venv/bin/playwright install chromium

# Final stage
FROM python:3.14-slim

# Install system dependencies
# - ffmpeg: Required for muxing video and subtitle streams
# - Playwright dependencies: Required for browser automation
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    # Playwright Chromium dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    # Fonts for proper page rendering
    fonts-liberation \
    fonts-noto-color-emoji \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --system beacon && useradd --system --gid beacon beacon

# Copy virtual environment from builder
COPY --from=builder --chown=beacon:beacon /app/.venv /app/.venv

# Copy Playwright browser cache from builder
COPY --from=builder --chown=beacon:beacon /app/.playwright /app/.playwright

# Create directories for downloads and data, set ownership
RUN mkdir -p /downloads /data && chown -R beacon:beacon /downloads /data

# Switch to non-root user
USER beacon

WORKDIR /app

# Set environment variables
ENV PLAYWRIGHT_BROWSERS_PATH=/app/.playwright
ENV DOWNLOAD_PATH=/downloads
ENV COOKIE_PATH=/data/beacon_cookies.txt
ENV HISTORY_DB_PATH=/data/.beacon-dl-history.db

# Default command shows help
ENTRYPOINT ["/app/.venv/bin/beacon-dl"]
CMD ["--help"]
