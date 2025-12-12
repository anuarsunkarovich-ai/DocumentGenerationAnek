# Changelog

Release notes for API, authentication, and operational changes.

## [Unreleased]

- Document and template routes now require bearer authentication via access tokens issued by `/api/v1/auth/login`.
- `POST /api/v1/documents/generate` and `POST /api/v1/documents/jobs` no longer accept `requested_by_user_id`; the backend derives it from the authenticated user.
- `POST /api/v1/templates/upload` and `POST /api/v1/templates/register` no longer accept `created_by_user_id`; the backend derives it from the authenticated user.
- Organization access is now validated through active memberships instead of trusting a matching `users.organization_id` alone.
- Auth responses now expose organization memberships so clients can present valid tenant choices.
