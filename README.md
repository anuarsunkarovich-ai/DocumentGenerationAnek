# Lean Generator Backend

Professional backend foundation for a template-driven document generation system.

## Documentation

Project documentation lives under [docs/README.md](/C:/Users/Anek/DocumentGenerationAnek/docs/README.md).

- [Architecture Overview](/C:/Users/Anek/DocumentGenerationAnek/docs/architecture.md)
- [Environment Variables](/C:/Users/Anek/DocumentGenerationAnek/docs/environment.md)
- [Setup](/C:/Users/Anek/DocumentGenerationAnek/docs/setup.md)
- [API Contract For Frontend](/C:/Users/Anek/DocumentGenerationAnek/docs/api-contract.md)
- [Template Format Rules](/C:/Users/Anek/DocumentGenerationAnek/docs/templates.md)
- [Constructor Block Schema](/C:/Users/Anek/DocumentGenerationAnek/docs/constructor-schema.md)
- [Authorization And Tenancy](/C:/Users/Anek/DocumentGenerationAnek/docs/authorization.md)
- [Generation Lifecycle](/C:/Users/Anek/DocumentGenerationAnek/docs/generation-lifecycle.md)
- [Changelog](/C:/Users/Anek/DocumentGenerationAnek/CHANGELOG.md)

## Quick Start

For a full local backend stack with PostgreSQL, Redis, MinIO, and a Celery worker:

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`, MinIO at `http://localhost:9001`, PostgreSQL at `localhost:5432`, and Redis at `localhost:6379`.

For local development without Docker:

1. Copy `.env.example` to `.env`
2. Start PostgreSQL, Redis, and MinIO locally
3. Run `uv sync --dev`
4. Run `uv run alembic upgrade head`
5. Run `uv run uvicorn app.main:app --reload`
6. Run `uv run celery -A app.workers.celery_app:celery_app worker --loglevel=info --pool=solo`

## UV Commands

The backend is UV-first. These are the supported day-to-day commands:

- install dependencies: `uv sync --dev`
- run API: `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- lint: `uv run ruff check .`
- format: `uv run ruff format .`
- type-check: `uv run mypy app tests`
- test: `uv run pytest`
- quality gate: `uv run python scripts/quality_gate.py`
- create migration: `uv run alembic revision --autogenerate -m "message"`
- apply migrations: `uv run alembic upgrade head`
- roll back one migration: `uv run alembic downgrade -1`

## Quality Gates

The repository now includes a layered quality gate stack:

- `ruff` for linting and import/order hygiene
- `pytest` for unit, migration, and API integration tests
- `mypy` for static type checks on the typed backend surface
- Alembic migration validation through offline upgrade tests, single-head checks, and destructive-change guards
- GitHub Actions jobs for fast checks, service-backed integration tests, and a full Docker stack smoke test
- one-command verification through [scripts/quality_gate.py](/C:/Users/Anek/DocumentGenerationAnek/scripts/quality_gate.py)

The CI pipeline boots real PostgreSQL, MinIO, and Redis infrastructure, runs migration round-trips on an empty database, and brings the full Docker stack up from zero to verify template upload, schema extraction, Celery generation, cache reuse, audit persistence, and download endpoints.

Public API and operational changes are summarized in [CHANGELOG.md](/C:/Users/Anek/DocumentGenerationAnek/CHANGELOG.md).

## Environment Files

- [.env.example](/C:/Users/Anek/DocumentGenerationAnek/.env.example): local development defaults for running the app on the host machine
- [.env.prod.example](/C:/Users/Anek/DocumentGenerationAnek/.env.prod.example): production-oriented template for containerized deployment

The Docker development stack reads `.env.example` directly, so `docker compose up --build` works without creating a local `.env` first. For host-based development, copy `.env.example` to `.env`.

## Docker

The container setup is split into:

- [Dockerfile](/C:/Users/Anek/DocumentGenerationAnek/Dockerfile): multi-stage image with `dev` and `prod` targets
- [docker-compose.yml](/C:/Users/Anek/DocumentGenerationAnek/docker-compose.yml): local orchestration for API, Celery worker, Redis, PostgreSQL, MinIO, and bucket bootstrap
- [docker/entrypoint.sh](/C:/Users/Anek/DocumentGenerationAnek/docker/entrypoint.sh): startup wrapper that applies Alembic migrations before launching the app

Default development stack:

```bash
docker compose up --build
```

Production profile:

1. Copy `.env.prod.example` to `.env.prod`
2. Set real credentials and hostnames
3. Run `docker compose --profile prod up --build api-prod worker-prod db redis minio minio-init`

## Current Scope

- Fixed FastAPI package structure under `app/`
- Clear separation between routers, controllers, services, DTOs, models, and repositories
- Minimal starter endpoints for health, templates, and document jobs
- Internal JWT auth with hashed passwords and revocable refresh sessions
- Membership-based tenancy with role-driven authorization
- Public machine-to-machine API routes secured by scoped API keys
- Structured request/job logging, Prometheus metrics, and optional Sentry integration

## Configuration

The backend reads environment configuration through nested Pydantic settings in [app/core/config.py](/C:/Users/Anek/DocumentGenerationAnek/app/core/config.py).

- `app`: HTTP server metadata and API paths
- `database`: PostgreSQL connectivity and pool settings
- `storage`: MinIO or S3-compatible storage settings
  - `public_endpoint` and `public_secure` let the API generate client-reachable presigned URLs even when the storage service uses an internal container hostname
- `redis`: Celery broker/result connectivity
- `generation`: upload, rendering, cache, and block-size limits
- `worker`: queue name, retries, backoff, and stale-job recovery windows
- `api_keys`: public API header name and per-key/per-org rate limits
- `observability`: request IDs, correlation headers, and Sentry options
- `paths`: local fallback directories for templates, artifacts, and temp files

Use [.env.example](/C:/Users/Anek/DocumentGenerationAnek/.env.example) for host-based development and [.env.prod.example](/C:/Users/Anek/DocumentGenerationAnek/.env.prod.example) as the starting point for production configuration.

## Database

SQLAlchemy 2.x async session management lives in [app/core/database.py](/C:/Users/Anek/DocumentGenerationAnek/app/core/database.py), and Alembic is configured under [migrations](/C:/Users/Anek/DocumentGenerationAnek/migrations).

## Storage

Object storage is abstracted behind [app/services/storage/base.py](/C:/Users/Anek/DocumentGenerationAnek/app/services/storage/base.py) and currently implemented with MinIO in [app/services/storage/minio.py](/C:/Users/Anek/DocumentGenerationAnek/app/services/storage/minio.py).

- Template uploads are stored under the `templates/` prefix
- Generated files are stored under the `artifacts/` prefix
- Preview files are stored under the `previews/` prefix
- Cached reusable files are stored under the `cache/` prefix

Use [app/services/storage/factory.py](/C:/Users/Anek/DocumentGenerationAnek/app/services/storage/factory.py) to inject the storage service instead of calling MinIO directly from business logic.

## Template Ingestion

The DOCX ingestion pipeline is implemented in [app/services/template_service.py](/C:/Users/Anek/DocumentGenerationAnek/app/services/template_service.py) and [app/services/template_schema_service.py](/C:/Users/Anek/DocumentGenerationAnek/app/services/template_schema_service.py).

- `GET /api/v1/templates?organization_id=...`: list templates for one organization
- `GET /api/v1/templates/{id}?organization_id=...`: fetch template details and current version schema inside one organization
- `POST /api/v1/templates/upload`: upload a `.docx`, store it, extract `{{variables}}`, and persist template metadata plus version schema
- `POST /api/v1/templates/register`: register a `.docx` that already exists in object storage using its `storage_key`
- `POST /api/v1/templates/extract-schema`: extract the normalized schema without persisting anything
- `POST /api/v1/templates/{id}/extract-schema?organization_id=...`: re-extract and persist schema from the stored current template version

The normalized schema includes a flat list of variables plus default frontend component hints such as `text`, `table`, and `image`.

## Constructor Model

The component-driven constructor contract is defined in [app/dtos/constructor.py](/C:/Users/Anek/DocumentGenerationAnek/app/dtos/constructor.py) and documented in [CONSTRUCTOR_MODEL.md](/C:/Users/Anek/DocumentGenerationAnek/CONSTRUCTOR_MODEL.md).

- `GET /api/v1/documents/constructor-schema`: returns the supported block types and default GOST formatting profile
- `POST /api/v1/documents/jobs`: accepts validated constructor blocks instead of an unstructured payload

The constructor supports `text`, `table`, `image`, `header`, `signature`, `page_break`, and `spacer` blocks with strict validation and default GOST page and typography rules.

## Generation Engine

The generation pipeline is split into focused services under [app/services/generation](/C:/Users/Anek/DocumentGenerationAnek/app/services/generation):

- `TemplateResolverService`: resolves the template and active version for a job
- `VariableMapperService`: applies constructor bindings to the supplied data payload
- `DocumentComposerService`: renders `.docx` output first
- `PdfRenderService`: renders a `.pdf` as the second stage
- `ArtifactService`: stores generated artifacts and persists their metadata

## Async Jobs

Document jobs now follow a real lifecycle and are executed through Celery workers backed by Redis:

- `GET /health`: root health endpoint for infrastructure checks
- `GET /api/v1/documents/jobs/{task_id}?organization_id=...`: returns `queued`, `processing`, `completed`, or `failed` plus generated artifact URLs when available
- `POST /api/v1/documents/generate`: creates a job and returns `task_id` immediately
- `POST /api/v1/documents/jobs`: alias for the same generation contract
- `GET /api/v1/documents/jobs/{task_id}/download?organization_id=...`: returns the preferred artifact plus a presigned download URL
- `GET /api/v1/documents/jobs/{task_id}/preview?organization_id=...`: returns the preferred preview artifact plus a presigned URL

The API contract stays the same, but generation now leaves the API process immediately after enqueue. Workers claim queued jobs in the database, retry transient failures with backoff, and recover stale `processing` jobs after worker restarts. When the template version and normalized payload hash match a recent completed job, the backend reuses cached artifacts instead of regenerating the document.

Internal template and document routes are protected by bearer auth. Public SaaS routes under `/api/v1/public` use `X-API-Key` machine auth with per-key scopes and rate limits. The backend derives actor fields such as `requested_by_user_id` and `created_by_user_id` from the authenticated user or API key context instead of trusting client input.

Observability is available through structured logs, `/metrics`, `/health/live`, `/health/ready`, and admin diagnostics routes under `/api/v1/admin/diagnostics`.

## Multi-Tenancy

Templates, template versions, document jobs, artifacts, audit logs, and API keys are modeled with `organization_id`. Browser routes still accept explicit `organization_id` selection and validate it against the authenticated user's active memberships. Public API-key routes derive tenant context from the API key and do not trust client-supplied organization identifiers.

## Validation and Security

Request validation is enforced with Pydantic v2 DTOs under [app/dtos](/C:/Users/Anek/DocumentGenerationAnek/app/dtos), and defensive input checks live in [app/services/security_service.py](/C:/Users/Anek/DocumentGenerationAnek/app/services/security_service.py).

- query and JSON request payloads are parsed through strict DTOs with `extra="forbid"`
- multipart template metadata is validated through `TemplateUploadRequest` before it reaches service logic
- template uploads are limited by configured size caps, must end in `.docx`, and must contain a valid DOCX-style zip payload
- user-supplied file names are sanitized before storage keys are built
- registered `storage_key` values are revalidated against the tenant template prefix instead of being trusted as-is
- constructor image blocks accept only base64 `data:image/...` URLs, not local file paths or arbitrary remote URLs

## Audit Logging

Document generation now writes immutable audit events through [app/services/audit_service.py](/C:/Users/Anek/DocumentGenerationAnek/app/services/audit_service.py).

- job creation logs who requested the document and which template version was targeted
- job completion logs whether the result was generated fresh or reused from cache
- job failure logs the error message for operational debugging
- artifact creation logs each produced file with kind and cache origin

The job status response also exposes `requested_by_user_id`, `template_version_id`, timestamps, and `from_cache` so the frontend can show basic traceability without querying audit tables directly.

## Run Target

The runtime application object is exposed from `app.main:app`.

## Architecture Guide

See `ARCHITECTURE.md` for the package ownership rules that freeze the backend structure.
