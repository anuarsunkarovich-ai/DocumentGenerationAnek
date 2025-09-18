# Template Format Rules

## Supported Input

- file type: `.docx`
- storage format: DOCX archive in object storage
- extraction source: XML parts under the `word/` folder inside the DOCX package

The backend currently does not support `.doc`, `.odt`, `.pdf`, or raw HTML as template sources.

## Variable Syntax

Use double curly braces:

```text
{{student_name}}
{{table_scores}}
{{image_signature}}
```

## Allowed Variable Key Pattern

- must start with an alphanumeric character
- may contain letters, numbers, underscores, dots, and dashes
- examples:
  - `student_name`
  - `student.group`
  - `signature_dean`
  - `table_scores`

## Extraction Behavior

When a template is parsed, the backend extracts:

- `key`
- human-friendly `label`
- `placeholder`
- inferred `value_type`
- inferred `component_type`
- `occurrences`
- XML `sources`

## Inference Rules

### Component Type

- keys starting with `image_`, `photo_`, `logo_`, or `signature_` become `image`
- keys starting with `table_`, `rows_`, `items_`, or `list_` become `table`
- all others become `text`

### Value Type

- `image` component => `image`
- `table` component => `array`
- all others => `string`

## Template Authoring Rules

1. Keep one stable business meaning per variable key.
2. Reuse the same key if the same value appears in multiple places.
3. Use `table_*` prefixes for row collections.
4. Use `image_*` or `signature_*` prefixes for image placeholders.
5. Avoid spaces and non-Latin punctuation in variable keys.
6. Keep template codes and versions file-safe.

## Upload Rules

Template uploads are rejected when:

- the file is not a `.docx`
- the file is empty
- the file exceeds the configured upload size limit
- the file content is not a valid DOCX-style ZIP package

## Registration Rules

When registering an already uploaded file, the client-provided `storage_key` is accepted only if it belongs to the organization template prefix.

Expected shape:

```text
templates/<organization_code>/<template_code>/<version>/<file_name>.docx
```

## Frontend Usage

Frontend should treat extracted template schema as the source of truth for:

- which fields to render
- which blocks can be prefilled
- which values are table-like or image-like

Do not duplicate template parsing logic in the frontend.
