# Backend Docs

This folder is the working contract for the Lean Generator backend.

## Start Here

- [Architecture Overview](architecture.md)
- [Environment Variables](environment.md)
- [Local Setup With UV](setup.md#local-setup-with-uv)
- [Docker Setup](setup.md#docker-setup)
- [API Contract For Frontend](api-contract.md)
- [Template Format Rules](templates.md)
- [Constructor Block Schema](constructor-schema.md)
- [Generation Lifecycle And Polling Flow](generation-lifecycle.md)
- [Release Checklist](release-checklist.md)

## Who This Is For

- Backend developers: package ownership, setup, persistence, and runtime behavior
- Frontend developers: stable API routes, request payloads, response payloads, and polling flow
- DevOps and deployment work: environment variables, Docker stack, and migration startup behavior

## Documentation Rules

1. Update docs in this folder in the same PR or commit as backend behavior changes.
2. Treat `api-contract.md`, `templates.md`, and `constructor-schema.md` as frontend-facing contracts.
3. Treat `environment.md` and `setup.md` as onboarding sources of truth.
4. Record every backend-breaking change after the `v0.1` baseline in `CHANGELOG.md`.
5. Do not leave route or payload changes documented only in chat or commit history.
