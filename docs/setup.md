# Setup

## Local Setup With UV

### Prerequisites

- Python 3.12
- UV
- PostgreSQL
- Redis
- MinIO or another S3-compatible storage service

### First Run

1. Copy `.env.example` to `.env`
2. Start PostgreSQL, Redis, and MinIO locally
3. Install dependencies:

```bash
uv sync --dev
```

4. Apply migrations:

```bash
uv run alembic upgrade head
```

5. Start the API:

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

6. Start the worker:

```bash
uv run celery -A app.workers.celery_app:celery_app worker --loglevel=info --pool=solo
```

### Daily Commands

```bash
uv run ruff check .
uv run ruff format .
uv run mypy app tests
uv run pytest
uv run python scripts/quality_gate.py
```

### Smoke-Test Admin

For a local Docker stack you can seed an admin user with:

```bash
uv run python scripts/seed_stack_admin.py
```

The script writes JSON with the seeded organization and login credentials so you can start testing the live API immediately.

## Docker Setup

### Files

- `Dockerfile`: multi-stage image with `dev` and `prod` targets
- `docker-compose.yml`: local stack for API, Celery worker, Redis, PostgreSQL, MinIO, and bucket bootstrap
- `docker/entrypoint.sh`: applies Alembic before app start

### Development Stack

```bash
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- Prometheus metrics: `http://localhost:8000/metrics`
- Liveness: `http://localhost:8000/health/live`
- Readiness: `http://localhost:8000/health/ready`
- Redis: `localhost:6379`
- PostgreSQL: `localhost:5432`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`

### Production-Like Stack

1. Copy `.env.prod.example` to `.env.prod`
2. Replace all example secrets and hostnames
3. Run:

```bash
docker compose --profile prod up --build api-prod worker-prod db redis minio minio-init
```

### Migration Behavior

The container entrypoint runs:

```bash
uv run alembic upgrade head
```

before launching the server when `RUN_MIGRATIONS=true`.

## Troubleshooting

### Backend starts but template operations fail

Check:

- PostgreSQL connectivity
- Redis connectivity
- MinIO connectivity
- bucket name and credentials

### Download URLs do not open

Check:

- `STORAGE__ENDPOINT`
- `STORAGE__PUBLIC_ENDPOINT`
- `STORAGE__SECURE`
- `STORAGE__PUBLIC_SECURE`
- whether the frontend can reach the storage endpoint used for presigned URLs

### Migrations fail in Docker

Check:

- `DATABASE__HOST`
- whether the `db` service is healthy
- whether the app is using the correct env file
