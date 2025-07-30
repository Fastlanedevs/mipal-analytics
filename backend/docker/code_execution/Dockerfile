FROM ghcr.io/astral-sh/uv:latest AS uv

FROM python:3.11-slim-bookworm

# Copy uv from the first stage
COPY --from=uv /uv /usr/local/bin/uv

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    UV_NO_CACHE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app
# Copy dependency specifications first for layer caching
COPY pyproject.toml uv.lock* ./
# Install system dependencies, project dependencies, then clean up
RUN --mount=type=cache,target=/root/.cache/uv \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        python3-dev && \
    uv sync --frozen --no-install-project && \
    apt-get remove -y gcc python3-dev && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .

# Install project with uv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# Make port 80 available to the world outside this container
EXPOSE 80

ENTRYPOINT ["uvicorn", "cmd_server.code_execution_server.main:app", "--host", "0.0.0.0", "--port", "80"]