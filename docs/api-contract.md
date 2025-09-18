# API Contract For Frontend

## Base Rules

- Base prefix: `/api/v1`
- JSON requests and responses use Pydantic DTOs with strict validation
- tenant-sensitive routes require `organization_id`
- document generation is asynchronous

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
- `created_by_user_id` optional
- `publish` optional
- `file`

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
  "created_by_user_id": "uuid",
  "publish": true
}
```

### `POST /api/v1/templates/{template_id}/extract-schema?organization_id=<uuid>`

Re-extract schema from the currently stored template version and persist the updated schema payload.

## Constructor Discovery

### `GET /api/v1/documents/constructor-schema`

Returns:

- `schema_version`
- `default_formatting`
- supported block type names

Use this route to initialize frontend defaults instead of hardcoding them in UI code.

## Document Generation

### `POST /api/v1/documents/generate`

Alias of `POST /api/v1/documents/jobs`.

Request body:

```json
{
  "organization_id": "uuid",
  "template_id": "uuid",
  "template_version_id": "uuid",
  "requested_by_user_id": "uuid",
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
  "created_at": "2026-03-20T10:00:00Z",
  "started_at": "2026-03-20T10:00:01Z",
  "completed_at": "2026-03-20T10:00:03Z",
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

## Frontend Integration Notes

1. Always preserve `organization_id` in list, detail, polling, download, and preview calls.
2. Treat `task_id` as the stable polling identifier.
3. Do not build storage URLs yourself; use the returned artifact URLs.
4. Expect `from_cache=true` on very fast repeated generation runs.
