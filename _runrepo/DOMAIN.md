# Domain Vocabulary

This backend is organized around a small set of stable entities.

## Core Entities

- `Organization`: tenant boundary for departments, faculties, or student organizations.
- `User`: actor inside an organization who manages templates or runs document generation.
- `Template`: logical document definition identified by a business code.
- `TemplateVersion`: immutable versioned source file plus extracted variable and component schemas.
- `DocumentJob`: asynchronous generation request created from one template version and one payload.
- `DocumentArtifact`: generated file stored in object storage for download, preview, or cache reuse.
- `AuditLog`: immutable event entry for traceability and compliance.

## Relationship Rules

1. Every business entity is scoped to an `Organization`.
2. A `Template` can have many `TemplateVersion` records.
3. A `DocumentJob` always points to one exact `TemplateVersion`.
4. A `DocumentJob` can produce multiple `DocumentArtifact` files.
5. `AuditLog` records capture important state changes across templates, jobs, and artifacts.

## Lifecycle Notes

- `Template` controls the business identity of a document type.
- `TemplateVersion` stores the exact source file and extracted schemas used for generation.
- `DocumentJob` tracks generation state from `queued` to `completed` or `failed`.
- `DocumentArtifact` is the durable output that can be cached and downloaded later.
