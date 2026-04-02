# Document Constructor Model

The backend now exposes a strict component-driven document model for generation requests.

## Supported Blocks

- `text`: paragraph-like content with optional direct text or data binding
- `table`: structured rows plus column definitions for GOST-friendly tables
- `image`: bound image content such as signatures, photos, or seals
- `header`: headings and titles with formal alignment defaults
- `signature`: signer area with name, role, and optional date
- `page_break`: explicit page transition between sections
- `spacer`: bounded vertical spacing block

## Default Formatting

- Profile: `gost_r_7_0_97_2016`
- Paper size: `A4`
- Margins: left `30mm`, right `10mm`, top `20mm`, bottom `20mm`
- Font: `Times New Roman`, `14pt`
- Line spacing: `1.5`
- First-line indent: `12.5mm`
- Paragraph alignment: `justify`

## Backend Contract

The contract is defined in [app/dtos/constructor.py](/C:/Users/Anek/DocumentGenerationAnek/app/dtos/constructor.py).

- `DocumentConstructor` is the top-level payload
- `blocks` uses a discriminated union keyed by `type`
- Validation rejects unknown fields, duplicate block ids, oversized tables, and empty content blocks

## Discovery Endpoint

The frontend can fetch `GET /api/v1/documents/constructor-schema` to discover the active schema descriptor and default formatting profile.
