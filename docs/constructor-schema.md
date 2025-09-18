# Constructor Block Schema

## Overview

The generation request contains a `constructor` object. This is the component-driven description of the final document layout.

Top-level shape:

```json
{
  "locale": "ru-RU",
  "formatting": {},
  "metadata": {},
  "blocks": []
}
```

## Top-Level Fields

| Field | Type | Notes |
| --- | --- | --- |
| `locale` | string | current default is `ru-RU` |
| `formatting` | object | optional GOST-aware overrides |
| `metadata` | object | freeform string map for client-side context |
| `blocks` | array | required, at least one block |

## Global Validation Rules

- block ids must be unique
- total block count must not exceed configured limits
- unknown fields are rejected
- all block variants are discriminated by `type`

## Shared Binding Shape

```json
{
  "key": "student_name",
  "required": true,
  "fallback": null
}
```

Fields:

- `key`: data payload key to resolve
- `required`: whether missing data is an error
- `fallback`: optional default string

## Block Types

### `text`

```json
{
  "type": "text",
  "id": "text-1",
  "text": "Static text",
  "binding": { "key": "student_name" },
  "multiline": true,
  "style": {
    "bold": false,
    "italic": false,
    "underline": false,
    "uppercase": false,
    "font_size_pt": 14,
    "alignment": "justify",
    "first_line_indent_mm": 12.5,
    "keep_with_next": false
  }
}
```

Rules:

- requires either `text` or `binding`

### `header`

```json
{
  "type": "header",
  "id": "header-1",
  "text": "Certificate",
  "level": 1,
  "numbering": false
}
```

Rules:

- requires either `text` or `binding`
- default style is bold, centered, and `keep_with_next=true`

### `table`

```json
{
  "type": "table",
  "id": "table-1",
  "columns": [
    { "key": "subject", "header": "Subject", "width_percent": 60, "alignment": "left" },
    { "key": "score", "header": "Score", "width_percent": 40, "alignment": "center" }
  ],
  "rows_binding": { "key": "table_scores" },
  "caption": "Results",
  "header_bold": true,
  "compact": false
}
```

Rules:

- requires either `rows` or `rows_binding`
- max column count is 20
- total explicit `width_percent` cannot exceed 100
- row count cannot exceed configured limit

### `image`

```json
{
  "type": "image",
  "id": "image-1",
  "binding": { "key": "image_signature" },
  "width_mm": 50,
  "height_mm": 20,
  "keep_aspect_ratio": true,
  "caption": "Signature",
  "alignment": "right"
}
```

Rules:

- `binding` is required
- image values must be inline `data:image/...;base64,...` strings
- local filesystem paths and arbitrary URLs are rejected

### `signature`

```json
{
  "type": "signature",
  "id": "signature-1",
  "signer_name": { "key": "signer_name" },
  "signer_role": { "key": "signer_role" },
  "date_binding": { "key": "sign_date" },
  "line_label": "Signature",
  "include_date": true,
  "include_stamp_area": false
}
```

### `page_break`

```json
{
  "type": "page_break",
  "id": "page-break-1",
  "reason": "manual"
}
```

Allowed `reason` values:

- `section`
- `appendix`
- `manual`

### `spacer`

```json
{
  "type": "spacer",
  "id": "spacer-1",
  "height_mm": 8
}
```

## Formatting Defaults

Default profile:

- paper: `A4`
- orientation: `portrait`
- margins: `30 / 10 / 20 / 20 mm`
- font: `Times New Roman`
- font size: `14pt`
- line spacing: `1.5`
- first-line indent: `12.5mm`
- alignment: `justify`

## Frontend Guidance

1. Use `GET /api/v1/documents/constructor-schema` to initialize defaults.
2. Use extracted template schema to suggest bindings.
3. Keep block ids stable so users can edit and resubmit constructor payloads predictably.
4. Prefer storing constructor state as JSON in the frontend app, not as hand-built form fragments.
