# syntax=docker/dockerfile:1

FROM python:3.10.19-slim-bookworm

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY tests ./tests
COPY docs ./docs
COPY failure_taxonomy ./failure_taxonomy
COPY scripts ./scripts

RUN python -m pip install --no-cache-dir -e ".[dev]"

CMD ["python", "-m", "unittest", "discover", "-s", "tests"]
