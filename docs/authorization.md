# Authorization And Tenancy

## Tenancy Model

The backend now supports organization memberships.

- A user can belong to one or more organizations.
- One membership may be marked as the default membership.
- Existing routes that already carry `organization_id` still use explicit org selection.
- The backend validates that selection against the authenticated user's active memberships before serving the request.

This keeps the current frontend contract workable while allowing multi-organization support to grow later.

## Role Matrix

| Role | Allowed actions |
| --- | --- |
| `viewer` | read templates, read document jobs, read downloads/previews |
| `operator` | viewer permissions plus generate documents |
| `manager` | operator permissions plus upload/register/re-extract templates |
| `admin` | manager permissions plus user-management and audit-log access |

## Policy Helpers

Reusable authorization checks live in `app/api/dependencies/authorization.py`.

- `require_template_read_access`
- `require_job_read_access`
- `require_template_write_access`
- `require_generation_access`
- `require_audit_access`

Each helper:

1. resolves the active membership for the requested organization
2. rejects cross-tenant access attempts
3. enforces the role rule for that action

## Route Behavior

- Template list/detail routes require template read access.
- Template upload/register/schema-refresh routes require template write access.
- Document generation routes require generation access.
- Job status/download/preview routes require read access.
- Routes without explicit org selection use the authenticated user's default membership.
