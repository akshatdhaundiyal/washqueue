# Use python slim image
FROM python:3.11-slim

# Install uv binary from official astral image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy pyproject config and lock file
COPY pyproject.toml uv.lock /app/

# Install python dependencies natively using uv sync
RUN uv sync --frozen --no-cache

# Copy application code
COPY app/ /app/app/

# Configure execution environment
ENV PYTHONUNBUFFERED=1
ENV WATCHFILES_FORCE_POLLING=true
EXPOSE 8000

# Execute uvicorn via uv run with reload enabled for development
CMD ["uv", "run", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
