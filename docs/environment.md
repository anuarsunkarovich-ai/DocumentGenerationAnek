# Environment Variables

## Overview

Settings are loaded by nested Pydantic settings in `app/core/config.py` using the `SECTION__FIELD=value` format.

Example:

```env
APP__PORT=8000
DATABASE__HOST=localhost
STORAGE__ENDPOINT=localhost:9000
```

## App Settings

| Variable | Meaning | Default |
| --- | --- | --- |
| `APP__NAME` | API display name | `Lean Generator Backend` |
| `APP__VERSION` | API version string | `0.1.0` |
| `APP__DESCRIPTION` | OpenAPI description | `Template-driven backend for document generation.` |
| `APP__ENVIRONMENT` | runtime mode | `development` |
| `APP__DEBUG` | FastAPI debug flag | `false` |
| `APP__HOST` | bind host | `0.0.0.0` |
| `APP__PORT` | bind port | `8000` |
| `APP__API_PREFIX` | versioned API prefix | `/api/v1` |
| `APP__DOCS_URL` | Swagger path | `/docs` |
| `APP__REDOC_URL` | ReDoc path | `/redoc` |
| `APP__OPENAPI_URL` | OpenAPI JSON path | `/openapi.json` |
| `APP__CORS_ORIGINS` | allowed frontend origins | `["http://localhost:5173"]` |

## Database Settings

| Variable | Meaning | Default |
| --- | --- | --- |
| `DATABASE__HOST` | PostgreSQL host | `db` |
| `DATABASE__PORT` | PostgreSQL port | `5432` |
| `DATABASE__NAME` | database name | `lean_generator` |
| `DATABASE__USER` | database user | `postgres` |
| `DATABASE__PASSWORD` | database password | `postgres` |
| `DATABASE__PASSWORD_FILE` | mounted secret file for the database password | empty |
| `DATABASE__ECHO` | SQLAlchemy SQL echo | `false` |
| `DATABASE__POOL_SIZE` | async engine pool size | `10` |
| `DATABASE__MAX_OVERFLOW` | extra pooled connections | `20` |

Derived value:

- SQLAlchemy URL is built internally as `postgresql+asyncpg://...`

## Storage Settings

| Variable | Meaning | Default |
| --- | --- | --- |
| `STORAGE__ENDPOINT` | MinIO or S3-compatible endpoint | `minio:9000` |
| `STORAGE__PUBLIC_ENDPOINT` | external host used when building presigned download URLs | empty |
| `STORAGE__ACCESS_KEY` | storage access key | `minioadmin` |
| `STORAGE__ACCESS_KEY_FILE` | mounted secret file for the storage access key | empty |
| `STORAGE__SECRET_KEY` | storage secret key | `minioadmin` |
| `STORAGE__SECRET_KEY_FILE` | mounted secret file for the storage secret key | empty |
| `STORAGE__BUCKET` | main object bucket | `documents` |
| `STORAGE__SECURE` | use HTTPS | `false` |
| `STORAGE__PUBLIC_SECURE` | override HTTPS for presigned public URLs | empty |
| `STORAGE__REGION` | optional storage region | empty |
| `STORAGE__TEMPLATES_PREFIX` | template source prefix | `templates` |
| `STORAGE__ARTIFACTS_PREFIX` | generated artifact prefix | `artifacts` |
| `STORAGE__CACHE_PREFIX` | reusable artifact cache prefix | `cache` |
| `STORAGE__PREVIEWS_PREFIX` | preview prefix | `previews` |
| `STORAGE__PRESIGNED_URL_EXPIRY_SECONDS` | download URL TTL | `3600` |
| `STORAGE__AUTO_CREATE_BUCKET` | auto-create bucket on startup | `true` |

Notes:

- `STORAGE__ENDPOINT` is the backend-to-storage address.
- `STORAGE__PUBLIC_ENDPOINT` is optional and should be set when clients must download through a different host than the API container uses internally.

## Redis Settings

| Variable | Meaning | Default |
| --- | --- | --- |
| `REDIS__HOST` | Redis host for Celery | `redis` |
| `REDIS__PORT` | Redis port | `6379` |
| `REDIS__BROKER_DB` | Redis logical DB for Celery broker traffic | `0` |
| `REDIS__RESULT_DB` | Redis logical DB for Celery result metadata | `1` |
| `REDIS__PASSWORD` | optional Redis password | empty |
| `REDIS__PASSWORD_FILE` | mounted secret file for the Redis password | empty |

## Generation Settings

| Variable | Meaning | Default |
| --- | --- | --- |
| `GENERATION__CACHE_TTL_HOURS` | artifact cache reuse window | `24` |
| `GENERATION__JOB_TIMEOUT_SECONDS` | logical generation timeout budget | `180` |
| `GENERATION__MAX_UPLOAD_SIZE_MB` | max DOCX upload size | `25` |
| `GENERATION__MAX_TEMPLATE_VARIABLES` | max variable bindings per request | `250` |
| `GENERATION__MAX_DOCUMENT_BLOCKS` | max constructor blocks | `150` |
| `GENERATION__MAX_TABLE_ROWS` | max rows in one constructor table | `500` |
| `GENERATION__MAX_IMAGE_SIZE_MB` | max inline image size | `10` |
| `GENERATION__MAX_ARTIFACTS_PER_JOB` | max stored files per job | `4` |
| `GENERATION__PREVIEW_ENABLED` | preview artifact support toggle | `true` |

## Auth Settings

| Variable | Meaning | Default |
| --- | --- | --- |
| `AUTH__JWT_SECRET_KEY` | HMAC secret for JWT signing | `change-this-in-production-32-byte-key` |
| `AUTH__JWT_SECRET_KEY_FILE` | mounted secret file for the JWT signing key | empty |
| `AUTH__JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `AUTH__ISSUER` | expected JWT issuer | `lean-generator-backend` |
| `AUTH__AUDIENCE` | expected JWT audience | `lean-generator-clients` |
| `AUTH__ACCESS_TOKEN_TTL_MINUTES` | access token lifetime | `15` |
| `AUTH__REFRESH_TOKEN_TTL_DAYS` | refresh token lifetime | `30` |
| `AUTH__PASSWORD_MIN_LENGTH` | minimum password length for internal auth flows | `8` |

## Worker Settings

| Variable | Meaning | Default |
| --- | --- | --- |
| `WORKER__QUEUE_NAME` | Celery queue used for generation tasks | `document-generation` |
| `WORKER__MAX_RETRIES` | max retries for transient generation failures | `4` |
| `WORKER__RETRY_BACKOFF_SECONDS` | base delay for exponential backoff | `15` |
| `WORKER__STALE_JOB_TIMEOUT_SECONDS` | age after which a `processing` job is considered stale | `300` |
| `WORKER__STALE_JOB_RECOVERY_BATCH_SIZE` | max stale jobs recovered per scan | `100` |
| `WORKER__RESULT_EXPIRES_SECONDS` | retention period for Celery result metadata | `3600` |
| `WORKER__MAINTENANCE_CLEANUP_INTERVAL_MINUTES` | scheduler cadence for retention cleanup | `60` |

## Retention Settings

| Variable | Meaning | Default |
| --- | --- | --- |
| `RETENTION__GENERATED_ARTIFACT_RETENTION_DAYS` | retention window for generated artifacts | `30` |
| `RETENTION__FAILED_JOB_RETENTION_DAYS` | retention window for failed jobs | `14` |
| `RETENTION__AUDIT_LOG_RETENTION_DAYS` | hard-prune window for audit logs | `90` |
| `RETENTION__TEMP_DATA_RETENTION_HOURS` | retention window for files under `data/tmp` | `24` |
| `RETENTION__CLEANUP_BATCH_SIZE` | max rows processed per cleanup batch | `250` |

## API Key Settings

| Variable | Meaning | Default |
| --- | --- | --- |
| `API_KEYS__HEADER_NAME` | header used for public machine auth | `X-API-Key` |
| `API_KEYS__PUBLIC_PREFIX` | public machine-route prefix | `/public` |
| `API_KEYS__REQUESTS_PER_MINUTE_PER_KEY` | minute-level limit for one API key | `120` |
| `API_KEYS__REQUESTS_PER_MINUTE_PER_ORG` | minute-level shared limit for one organization | `600` |
| `API_KEYS__REQUESTS_PER_DAY_PER_KEY` | daily quota for one API key | `5000` |
| `API_KEYS__REQUESTS_PER_DAY_PER_ORG` | daily shared quota for one organization | `50000` |

## Observability Settings

| Variable | Meaning | Default |
| --- | --- | --- |
| `OBSERVABILITY__SENTRY_DSN` | optional Sentry DSN for API and worker exceptions | empty |
| `OBSERVABILITY__SENTRY_DSN_FILE` | mounted secret file for the Sentry DSN | empty |
| `OBSERVABILITY__SENTRY_TRACES_SAMPLE_RATE` | Sentry tracing sample rate | `0.0` |
| `OBSERVABILITY__REQUEST_ID_HEADER` | response and request header used for request IDs | `X-Request-ID` |
| `OBSERVABILITY__CORRELATION_ID_HEADER` | response and request header used for distributed correlation | `X-Correlation-ID` |

## Recommended Files

- `.env.example`: host-based local development
- `.env.prod.example`: production-oriented example
- `.env`: your local override file
- `.env.prod`: your real production or prod-like Docker file

## Production Secret Management

Production mode requires mounted secret files for:

- `DATABASE__PASSWORD_FILE`
- `STORAGE__ACCESS_KEY_FILE`
- `STORAGE__SECRET_KEY_FILE`
- `AUTH__JWT_SECRET_KEY_FILE`

If Redis auth or Sentry are enabled in production, use:

- `REDIS__PASSWORD_FILE`
- `OBSERVABILITY__SENTRY_DSN_FILE`

The application rejects production startup when required secrets are still configured only as plaintext values.

## Frontend-Relevant Settings

Frontend work usually only needs these values:

- `APP__API_PREFIX`
- `APP__CORS_ORIGINS`
- auth token storage and refresh behavior derived from `AUTH__ACCESS_TOKEN_TTL_MINUTES` and `AUTH__REFRESH_TOKEN_TTL_DAYS`
- the Celery/Redis worker topology driven by `REDIS__*` and `WORKER__*`
- request/correlation headers controlled by `OBSERVABILITY__REQUEST_ID_HEADER` and `OBSERVABILITY__CORRELATION_ID_HEADER`
- public API-key authentication and quotas controlled by `API_KEYS__*`
- the host/port where the backend is running
- the MinIO-presigned URL behavior indirectly used by download endpoints
