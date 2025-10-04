# Release Checklist

## Baseline Reference

This checklist is the reference point for backend release baseline `v0.1` established on March 20, 2026.

After this baseline:

- keep the frontend-facing contract additions backward compatible where possible
- document intentional contract changes in `docs/api-contract.md` and `docs/constructor-schema.md`
- record every backend-breaking change in `CHANGELOG.md`

Use this checklist before calling the backend "usable" for the first release.

## Current Status

Verified on March 20, 2026:

- [x] migrations run cleanly
- [x] MinIO bucket creation is automated
- [x] healthcheck covers DB and storage
- [x] generation works end to end for one constructor-driven document flow
- [x] cached downloads work
- [x] audit logs are written
- [x] Docker stack boots from zero

## Verification Evidence

### Migrations run cleanly

Verified by:

- `tests/test_migrations.py`
- live Alembic execution during `docker-compose.exe up --build -d`

What is checked:

- single migration head
- offline SQL renders successfully
- PostgreSQL enum types are emitted once
- container startup can apply migrations on a fresh database

### MinIO bucket creation is automated

Verified by:

- application lifespan startup in `app/main.py`
- `tests/integration/test_release_readiness.py`
- live Docker startup logs showing successful MinIO bucket checks

What is checked:

- bucket is ensured on app startup
- health checks can confirm storage readiness

### Healthcheck covers DB and storage

Verified by:

- `app/services/health_service.py`
- `tests/test_health.py`
- live `/health` response after Docker boot

Expected response shape:

```json
{
  "status": "ok",
  "service": "lean-generator-backend",
  "checks": {
    "database": { "status": "ok", "detail": null },
    "storage": { "status": "ok", "detail": null }
  }
}
```

Rule:

- return `200` only when checks are healthy
- return `503` when one or more infrastructure checks fail

### Generation works end to end for one real template flow

Verified by:

- `tests/integration/test_template_routes.py`
- `tests/integration/test_release_readiness.py`

What is checked:

- a real DOCX fixture is parsed for template variables
- constructor-driven generation produces DOCX and PDF artifacts
- the job moves from `queued` to `completed`

Important note:

The current MVP generation path is constructor-driven. Real DOCX template extraction is verified and feeds schema/binding behavior, while the final rendered document is composed from the constructor model.

### Cached downloads work

Verified by:

- `tests/integration/test_release_readiness.py`

What is checked:

- repeated generation requests can reuse cached artifacts
- `from_cache` is reported on the job response
- the download endpoint returns a usable artifact response and URL

### Audit logs are written

Verified by:

- `tests/integration/test_release_readiness.py`

What is checked:

- job creation audit events
- job completion audit events
- artifact creation audit events
- cache-origin information on reused flows

### Docker stack boots from zero

Verified by live commands on March 20, 2026:

```bash
docker-compose.exe down -v
docker-compose.exe up --build -d
docker-compose.exe ps
```

Live result:

- `api` healthy
- `db` healthy
- `minio` running
- `/health` returned `status=ok` with both dependency checks healthy

## Recommended Final Pre-Release Command

Run:

```bash
uv run python scripts/quality_gate.py
docker-compose.exe down -v
docker-compose.exe up --build -d
```

Then confirm:

1. `docker-compose.exe ps` shows healthy API and database containers
2. `GET http://localhost:8000/health` returns healthy database and storage checks
3. one known-good template flow still generates successfully
