FROM python:3.12-slim

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY scripts ./scripts

# Install dependencies and create venv
RUN uv sync --frozen --no-dev

# Set PATH to use venv
ENV PATH="/app/.venv/bin:$PATH"

# Expose port for web UI
EXPOSE 8000

# Default command
ENTRYPOINT ["uptimer"]
CMD ["serve", "--host", "0.0.0.0"]
