# API Backend - Riot DevOps
# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Ensure installed tools can be executed out of the box
ENV UV_TOOL_BIN_DIR=/usr/local/bin

# Copy dependency files first (for better layer caching)
COPY pyproject.toml uv.lock ./

# Install the project's dependencies
# Note: Using --no-install-project to install only dependencies first
RUN uv sync --locked --no-install-project --no-dev

# Copy the rest of the project source code
COPY . /app

# Install the project itself
RUN uv sync --locked --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Expose API port
EXPOSE 8000

# Health check using Python (curl not available in slim image)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the FastAPI application
CMD ["fastapi", "run", "api/main.py", "--host", "0.0.0.0", "--port", "8000"]
