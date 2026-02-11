# API Contract For Frontend

## Base Rules

- Base prefix: `/api/v1`
- JSON requests and responses use Pydantic DTOs with strict validation
- internal tenant-sensitive routes require `organization_id`
- document generation is asynchronous
- queued jobs are executed by Celery workers using Redis as the broker and result backend
- internal template and document routes require `Authorization: Bearer <access_token>`
- public machine routes live under `/api/v1/public/*` and require `X-API-Key: <plaintext-key>`
- actor identifiers on protected routes are derived from the authenticated user, not trusted from client input
- `organization_id` selections on protected routes are validated against active organization memberships
- public API-key routes derive `organization_id` from the authenticated key and do not accept tenant selection from clients

## Health

### `GET /health`

Infrastructure-friendly health route without the API prefix.

Response:

```json
{
  "status": "ok",
  "service": "lean-generator-backend"
}
```

### `GET /api/v1/health`

Versioned health route for application clients.

### `GET /health/live` and `GET /api/v1/health/live`

Process liveness only. Useful for container liveness probes.

### `GET /health/ready` and `GET /api/v1/health/ready`

Dependency readiness for database, storage, and Redis. Returns `503` when dependencies are unavailable.

## Authentication

### `POST /api/v1/auth/login`

Authenticate with internal email/password credentials.

Request body:

```json
{
  "email": "anek@example.com",
  "password": "correct-password"
}
```

Response:

```json
{
  "access_token": "jwt",
  "refresh_token": "opaque-token",
  "token_type": "bearer",
  "access_token_expires_in": 900,
  "refresh_token_expires_in": 2592000,
  "user": {
    "id": "uuid",
    "organization_id": "uuid",
    "email": "anek@example.com",
    "full_name": "Anek",
    "role": "admin",
    "is_active": true,
    "organization": {
      "id": "uuid",
      "name": "Math Department",
      "code": "math-dept"
    },
    "memberships": [
      {
        "id": "uuid",
        "organization_id": "uuid",
        "role": "admin",
        "is_active": true,
        "is_default": true,
        "organization": {
          "id": "uuid",
          "name": "Math Department",
          "code": "math-dept"
        }
      }
    ]
  }
}
```

### `POST /api/v1/auth/refresh`

Rotate a refresh token and return a fresh access/refresh pair.

### `POST /api/v1/auth/logout`

Protected route. Revokes the supplied refresh token for the authenticated user.

### `GET /api/v1/auth/me`

Protected route. Returns the authenticated user profile and organization summary.

## API Keys

### `POST /api/v1/admin/api-keys`

Admin-only route for creating one machine key.

Request body:

```json
{
  "organization_id": "uuid",
  "name": "Production integration",
  "scopes": ["templates:read", "documents:generate", "documents:read"]
}
```

Response:

```json
{
  "api_key": "lgk_...",
  "metadata": {
    "id": "uuid",
    "organization_id": "uuid",
    "name": "Production integration",
    "key_prefix": "lgk_abcd1234",
    "scopes": ["documents:generate", "documents:read", "templates:read"],
    "status": "active",
    "rotated_at": null,
    "last_used_at": null,
    "revoked_at": null,
    "created_at": "2026-02-01T09:00:00Z"
  }
}
```

The plaintext key is returned only on create and rotate.

### `GET /api/v1/admin/api-keys?organization_id=<uuid>`

Admin-only route. Lists API keys for one organization.

### `POST /api/v1/admin/api-keys/{api_key_id}/rotate?organization_id=<uuid>`

Admin-only route. Rotates a key and returns a fresh plaintext secret once.

### `POST /api/v1/admin/api-keys/{api_key_id}/revoke?organization_id=<uuid>`

Admin-only route. Revokes a key.

### `GET /api/v1/admin/api-keys/usage?organization_id=<uuid>&limit=25`

Admin-only route. Returns recent API-key request logs for one organization.

Supported scopes:

- `templates:read`
- `documents:generate`
- `documents:read`
- `audit:read`

## Templates

### `GET /api/v1/templates?organization_id=<uuid>`

List templates visible to one organization.

Response shape:

```json
{
  "items": [
    {
      "id": "uuid",
      "organization_id": "uuid",
      "name": "Certificate",
      "code": "certificate",
      "status": "active",
      "description": "Optional text",
      "current_version": {
        "id": "uuid",
        "version": "1.0.0",
        "is_current": true,
        "is_published": true
      }
    }
  ]
}
```

### `GET /api/v1/templates/{template_id}?organization_id=<uuid>`

Get one template plus current version details.

Response adds:

- `versions`
- `current_version_details`
- extracted schema under `current_version_details.schema`

### `POST /api/v1/templates/extract-schema`

Multipart upload route for schema extraction without persistence.

Form fields:

- `file`: `.docx`

Response:

```json
{
  "variable_count": 2,
  "variables": [
    {
      "key": "student_name",
      "label": "Student Name",
      "placeholder": "{{student_name}}",
      "value_type": "string",
      "component_type": "text",
      "required": true,
      "occurrences": 1,
      "sources": ["word/document.xml"]
    }
  ],
  "components": [
    {
      "id": "student_name",
      "component": "text",
      "binding": "student_name",
      "label": "Student Name",
      "value_type": "string",
      "required": true
    }
  ]
}
```

### `POST /api/v1/templates/upload`

Persist a new template version from multipart form-data.

Form fields:

- `organization_id`
- `name`
- `code`
- `version`
- `description` optional
- `notes` optional
- `publish` optional
- `file`

The backend derives `created_by_user_id` from the access token.

### `POST /api/v1/templates/register`

Persist a template version that already exists in object storage.

JSON body:

```json
{
  "organization_id": "uuid",
  "name": "Certificate",
  "code": "certificate",
  "version": "1.0.0",
  "storage_key": "templates/math-dept/certificate/1.0.0/certificate.docx",
  "original_filename": "certificate.docx",
  "description": "Optional text",
  "notes": "Optional text",
  "publish": true
}
```

The backend derives `created_by_user_id` from the access token.

### `POST /api/v1/templates/{template_id}/extract-schema?organization_id=<uuid>`

Re-extract schema from the currently stored template version and persist the updated schema payload.

## Constructor Discovery

### `GET /api/v1/documents/constructor-schema`

Returns:

```json
{
  "descriptor": {
    "schema_version": "1.0",
    "default_formatting": {
      "page": {
        "profile": "gost_r_7_0_97_2016",
        "paper_size": "A4",
        "orientation": "portrait",
        "margin_left_mm": 30.0,
        "margin_right_mm": 10.0,
        "margin_top_mm": 20.0,
        "margin_bottom_mm": 20.0,
        "header_distance_mm": 12.5,
        "footer_distance_mm": 12.5
      },
      "typography": {
        "font_family": "Times New Roman",
        "font_size_pt": 14.0,
        "line_spacing": 1.5,
        "first_line_indent_mm": 12.5,
        "paragraph_spacing_before_pt": 0.0,
        "paragraph_spacing_after_pt": 0.0,
        "alignment": "justify"
      },
      "allow_orphan_headings": false,
      "repeat_table_header_on_each_page": true,
      "force_table_borders": true,
      "signatures_align_right": true
    },
    "supported_blocks": [
      "text",
      "table",
      "image",
      "header",
      "signature",
      "page_break",
      "spacer"
    ]
  }
}
```

Use `descriptor.schema_version` as the constructor model version and use this route to initialize frontend defaults instead of hardcoding them in UI code.

## Document Generation

### `POST /api/v1/documents/generate`

Alias of `POST /api/v1/documents/jobs`.

Request body:

```json
{
  "organization_id": "uuid",
  "template_id": "uuid",
  "template_version_id": "uuid",
  "data": {
    "student_name": "Anek"
  },
  "constructor": {
    "locale": "ru-RU",
    "metadata": {
      "document_type": "certificate"
    },
    "blocks": [
      {
        "type": "text",
        "id": "text-1",
        "binding": {
          "key": "student_name"
        }
      }
    ]
  }
}
```

The backend derives `requested_by_user_id` from the access token and returns it in job responses.

Immediate response:

```json
{
  "task_id": "uuid",
  "organization_id": "uuid",
  "status": "queued",
  "template_id": "uuid",
  "template_version_id": "uuid",
  "requested_by_user_id": "uuid",
  "from_cache": false
}
```

Backend execution note:

- the HTTP contract is unchanged by the worker move
- API nodes now enqueue a Celery task and return immediately
- workers recover stale `processing` jobs after restarts and retry transient failures with backoff

Response headers:

- `X-Request-ID`: request identifier generated or echoed by the API
- `X-Correlation-ID`: correlation identifier propagated into worker execution

### `GET /api/v1/documents/jobs/{task_id}?organization_id=<uuid>`

Polling route for job status.

Response:

```json
{
  "task_id": "uuid",
  "organization_id": "uuid",
  "status": "completed",
  "template_id": "uuid",
  "template_version_id": "uuid",
  "requested_by_user_id": "uuid",
  "from_cache": false,
  "error_message": null,
  "created_at": "2025-01-10T10:00:00Z",
  "started_at": "2025-01-10T10:00:01Z",
  "completed_at": "2025-01-10T10:00:03Z",
  "artifacts": [
    {
      "id": "uuid",
      "kind": "pdf",
      "file_name": "certificate-1.0.0.pdf",
      "content_type": "application/pdf",
      "size_bytes": 12034,
      "download_url": "https://..."
    }
  ]
}
```

Possible statuses:

- `queued`
- `processing`
- `completed`
- `failed`

### `GET /api/v1/documents/jobs/{task_id}/download?organization_id=<uuid>`

Returns the preferred download artifact, currently PDF first and DOCX second.

### `GET /api/v1/documents/jobs/{task_id}/preview?organization_id=<uuid>`

Returns the preferred preview artifact, currently PDF first and DOCX second.

## Public API

Public SaaS routes are machine-authenticated and tenant-scoped by API key.

### `GET /api/v1/public/templates`

List published templates visible to the API key's organization.

### `GET /api/v1/public/templates/{template_id}`

Return one published template for the API key's organization.

### `GET /api/v1/public/documents/constructor-schema`

Return the constructor schema for machine clients with `documents:generate`.

### `POST /api/v1/public/documents/generate`

Alias of `POST /api/v1/public/documents/jobs`.

Request body:

```json
{
  "template_id": "uuid",
  "template_version_id": "uuid",
  "data": {
    "student_name": "Anek"
  },
  "constructor": {
    "blocks": [
      {
        "type": "text",
        "id": "text-1",
        "binding": {
          "key": "student_name"
        }
      }
    ]
  }
}
```

Differences from internal browser routes:

- `organization_id` is omitted and derived from the API key
- only published templates and published template versions are allowed
- `requested_by_user_id` is `null` because the request is machine-authenticated

### `GET /api/v1/public/documents/jobs/{task_id}`

Return job status for the API key's organization. Requires `documents:read`.

### `GET /api/v1/public/documents/jobs/{task_id}/download`

Return the preferred artifact plus a presigned download URL. Requires `documents:read`.

### `GET /api/v1/public/documents/jobs/{task_id}/preview`

Return the preferred preview artifact. Requires `documents:read`.

### `GET /api/v1/public/audit/events`

Return recent audit events for the API key's organization. Requires `audit:read`.

Public-route responses also honor:

- `X-Request-ID`
- `X-Correlation-ID`

Rate limits and quotas are applied per API key and per organization. Exceeded limits return `429`.

## Error Shape

Domain-level failures return:

```json
{
  "detail": "Readable error message"
}
```

Typical statuses:

- `404` not found
- `409` conflict
- `422` validation failure

## Admin Diagnostics

These routes require an admin membership for the target organization.

### `GET /api/v1/admin/diagnostics/failed-jobs?organization_id=<uuid>&limit=25`

Returns recent failed document jobs for one organization.

### `GET /api/v1/admin/diagnostics/audit-events?organization_id=<uuid>&limit=25`

Returns recent audit events for one organization.

### `GET /api/v1/admin/diagnostics/cache-stats?organization_id=<uuid>`

Returns aggregate cache usage stats for one organization.

### `GET /api/v1/admin/diagnostics/worker-status?organization_id=<uuid>`

Returns worker availability and current queue depth.

## Frontend Integration Notes

1. Always preserve `organization_id` in list, detail, polling, download, and preview calls.
2. Treat the authenticated user's memberships as the source of truth for which organizations can be selected.
3. Treat `task_id` as the stable polling identifier.
4. Do not build storage URLs yourself; use the returned artifact URLs.
5. Expect `from_cache=true` on very fast repeated generation runs.
6. For server-to-server integrations, use `/api/v1/public/*` routes with `X-API-Key` instead of browser bearer tokens.
