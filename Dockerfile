# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.13

FROM python:${PYTHON_VERSION}-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1
WORKDIR /app

# usuário não-root
RUN useradd -m -u 10001 appuser

FROM base AS builder
# deps para compilar wheels e falar com postgres
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential curl git libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# instala Poetry (fixa versão para builds reproduzíveis)
ARG POETRY_VERSION=2.1.1
RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

# cache melhor: primeiro só manifests
COPY pyproject.toml poetry.lock /app/
RUN poetry check --lock --no-ansi
RUN poetry install --no-ansi --no-root

# agora copia o projeto
COPY . /app/

FROM base AS runtime
# runtime lib do postgres
RUN apt-get update \
 && apt-get install -y --no-install-recommends libpq5 \
 && rm -rf /var/lib/apt/lists/*

# copia python deps + app já instalados no builder
COPY --from=builder /usr/local /usr/local
COPY --from=builder /app /app

USER appuser
EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]