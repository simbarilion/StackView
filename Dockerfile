FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=2.4.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "poetry==${POETRY_VERSION}"

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

RUN poetry install --only main

COPY scripts/start.sh ./scripts/start.sh
RUN chmod +x ./scripts/start.sh

EXPOSE 8000

CMD ["./scripts/start.sh"]
