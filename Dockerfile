FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS runtime-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./


FROM runtime-base AS dev

RUN uv sync --frozen --dev

COPY app ./app
COPY migrations ./migrations
COPY docker ./docker
COPY alembic.ini ./alembic.ini
COPY main.py ./main.py
COPY README.md ./README.md

RUN chmod +x /app/docker/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/bin/sh", "/app/docker/entrypoint.sh"]
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


FROM runtime-base AS prod

RUN uv sync --frozen --no-dev

COPY app ./app
COPY migrations ./migrations
COPY docker ./docker
COPY alembic.ini ./alembic.ini
COPY main.py ./main.py
COPY README.md ./README.md

RUN chmod +x /app/docker/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/bin/sh", "/app/docker/entrypoint.sh"]
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
