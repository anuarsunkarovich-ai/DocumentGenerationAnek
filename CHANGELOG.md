# Changelog

This file records backend-breaking changes from the `v0.1` release baseline onward.

- Add an entry when a backend change breaks an existing frontend or client integration.
- Do not use this file for internal refactors, bug fixes, or additive changes that keep the shipped contract compatible.
- When a breaking change is necessary, update this file in the same change as the code and contract docs.

## [Unreleased]

- Document and template routes now require bearer authentication via access tokens issued by `/api/v1/auth/login`.
- `POST /api/v1/documents/generate` and `POST /api/v1/documents/jobs` no longer accept `requested_by_user_id`; the backend derives it from the authenticated user.
- `POST /api/v1/templates/upload` and `POST /api/v1/templates/register` no longer accept `created_by_user_id`; the backend derives it from the authenticated user.
- Organization access is now validated through active memberships instead of trusting a matching `users.organization_id` alone.
- Auth responses now expose organization memberships so clients can present valid tenant choices.

## [v0.1] - 2026-03-20

Release baseline established from [docs/release-checklist.md](/C:/Users/Anek/DocumentGenerationAnek/docs/release-checklist.md).

Locked frontend-facing backend contracts:

- document generation job creation: `POST /api/v1/documents/generate`
- document generation job creation alias: `POST /api/v1/documents/jobs`
- template schema extraction format: `POST /api/v1/templates/extract-schema`
- constructor schema discovery: `GET /api/v1/documents/constructor-schema`
- document job polling format: `GET /api/v1/documents/jobs/{task_id}`

Breaking changes after this point must extend these contracts intentionally or version them explicitly before rollout.
