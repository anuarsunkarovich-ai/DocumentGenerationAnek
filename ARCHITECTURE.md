# Backend Skeleton

This repository now uses a fixed backend package structure under `app/`.

## Packages

- `app/core`: shared configuration, logging, database, and base exceptions.
- `app/api/routers`: FastAPI route declarations only.
- `app/api/controllers`: request orchestration between routers and services.
- `app/services`: domain/application logic.
- `app/dtos`: Pydantic request and response schemas.
- `app/models`: ORM models and persistence primitives.
- `app/repositories`: database access boundaries.
- `app/utils`: small reusable helpers without business logic.
- `tests`: automated tests and fixtures.

## Rules

1. Routers should stay thin and delegate immediately to controllers.
2. Controllers should coordinate services and DTO translation only.
3. Services should own business rules and generation workflows.
4. Repositories should encapsulate persistence access.
5. DTOs should validate all external input and output shapes.
6. Utilities should not contain domain decisions.
