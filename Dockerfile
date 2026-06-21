# syntax=docker/dockerfile:1

# ---- builder: install dependencies into a venv with uv ----
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Install deps first (cached layer) using only the lockfiles.
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Now install the project itself.
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---- runtime: slim image, non-root user ----
FROM python:3.12-slim AS runtime

RUN useradd --create-home --uid 10001 appuser
WORKDIR /app

COPY --from=builder --chown=appuser:appuser /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

USER appuser

# Default transport is stdio (for MCP clients that spawn the process).
ENTRYPOINT ["latamfx-mcp"]
