# Changelog

Release notes for API, authentication, and operational changes.

## [Unreleased]

- Document and template routes now require bearer authentication via access tokens issued by `/api/v1/auth/login`.
- `POST /api/v1/documents/generate` and `POST /api/v1/documents/jobs` no longer accept `requested_by_user_id`; the backend derives it from the authenticated user.
- `POST /api/v1/templates/upload` and `POST /api/v1/templates/register` no longer accept `created_by_user_id`; the backend derives it from the authenticated user.
- Organization access is now validated through active memberships instead of trusting a matching `users.organization_id` alone.
- Auth responses now expose organization memberships so clients can present valid tenant choices.
- Public SaaS routes are now available under `/api/v1/public/*` and are authenticated with scoped API keys via `X-API-Key`.
- API-key management and usage diagnostics are now available under `/api/v1/admin/api-keys`.
- Public API requests now enforce per-key and per-organization rate limits and persist usage records with request and correlation identifiers.
- Organizations now default onto a seeded per-organization plan model with monthly usage meters.
- Document generation, template creation, storage growth, signature-block usage, and audit retention are now constrained by plan enforcement at the service boundary.
- Generated artifacts now use the stored SHA-256 checksum as their authenticity fingerprint, and verification endpoints are available at `POST /api/v1/documents/verify` and `POST /api/v1/public/documents/verify`.
- DOCX and PDF generation now enforce the project GOST paragraph defaults consistently, including 1.5 line spacing, 12.5 mm first-line indent for body text, zero paragraph spacing, and right-aligned signature blocks.
