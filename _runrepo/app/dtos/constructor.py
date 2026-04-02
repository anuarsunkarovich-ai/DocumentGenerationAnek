"""DTOs for the component-driven document constructor."""

from typing import Annotated, Any, Literal

from pydantic import Field, model_validator

from app.core.config import get_settings
from app.dtos.common import BaseDTO


class GOSTPageSettings(BaseDTO):
    """GOST-oriented page geometry defaults for generated documents."""

    profile: Literal["gost_r_7_0_97_2016"] = "gost_r_7_0_97_2016"
    paper_size: Literal["A4"] = "A4"
    orientation: Literal["portrait"] = "portrait"
    margin_left_mm: float = Field(default=30.0, ge=20.0, le=40.0)
    margin_right_mm: float = Field(default=10.0, ge=10.0, le=25.0)
    margin_top_mm: float = Field(default=20.0, ge=10.0, le=30.0)
    margin_bottom_mm: float = Field(default=20.0, ge=10.0, le=30.0)
    header_distance_mm: float = Field(default=12.5, ge=5.0, le=20.0)
    footer_distance_mm: float = Field(default=12.5, ge=5.0, le=20.0)


class GOSTTypographySettings(BaseDTO):
    """GOST-oriented typography defaults for paragraphs and headings."""

    font_family: Literal["Times New Roman"] = "Times New Roman"
    font_size_pt: float = Field(default=14.0, ge=10.0, le=16.0)
    line_spacing: float = Field(default=1.5, ge=1.0, le=2.0)
    first_line_indent_mm: float = Field(default=12.5, ge=0.0, le=20.0)
    paragraph_spacing_before_pt: float = Field(default=0.0, ge=0.0, le=24.0)
    paragraph_spacing_after_pt: float = Field(default=0.0, ge=0.0, le=24.0)
    alignment: Literal["justify"] = "justify"


class GOSTFormattingRules(BaseDTO):
    """GOST-aware formatting rules applied by default to the constructor output."""

    page: GOSTPageSettings = Field(default_factory=GOSTPageSettings)
    typography: GOSTTypographySettings = Field(default_factory=GOSTTypographySettings)
    allow_orphan_headings: bool = False
    repeat_table_header_on_each_page: bool = True
    force_table_borders: bool = True
    signatures_align_right: bool = True


class ConstructorBindingReference(BaseDTO):
    """Reference to dynamic data supplied by the user or database layer."""

    key: str = Field(min_length=1, max_length=120)
    required: bool = True
    fallback: str | None = Field(default=None, max_length=500)


class ConstructorTextStyle(BaseDTO):
    """Shared text styling overrides for text-like blocks."""

    bold: bool = False
    italic: bool = False
    underline: bool = False
    uppercase: bool = False
    font_size_pt: float | None = Field(default=None, ge=10.0, le=18.0)
    alignment: Literal["left", "center", "right", "justify"] | None = None
    first_line_indent_mm: float | None = Field(default=None, ge=0.0, le=20.0)
    keep_with_next: bool = False


class BaseBlock(BaseDTO):
    """Shared fields for constructor blocks."""

    id: str = Field(min_length=1, max_length=100)
    required: bool = True


class TextBlock(BaseBlock):
    """Paragraph-like block for prose and free text sections."""

    type: Literal["text"] = "text"
    text: str | None = Field(default=None, max_length=20000)
    binding: ConstructorBindingReference | None = None
    multiline: bool = True
    style: ConstructorTextStyle = Field(default_factory=ConstructorTextStyle)

    @model_validator(mode="after")
    def validate_content_source(self) -> "TextBlock":
        """Require either direct text or a data binding."""
        if not self.text and self.binding is None:
            raise ValueError("Text block requires either 'text' or 'binding'.")
        return self


class HeaderBlock(BaseBlock):
    """Block for document headings, titles, and official captions."""

    type: Literal["header"] = "header"
    text: str | None = Field(default=None, max_length=1000)
    binding: ConstructorBindingReference | None = None
    level: Literal[1, 2, 3] = 1
    numbering: bool = False
    style: ConstructorTextStyle = Field(
        default_factory=lambda: ConstructorTextStyle(
            bold=True,
            alignment="center",
            keep_with_next=True,
        )
    )

    @model_validator(mode="after")
    def validate_content_source(self) -> "HeaderBlock":
        """Require either direct header text or a data binding."""
        if not self.text and self.binding is None:
            raise ValueError("Header block requires either 'text' or 'binding'.")
        return self


class TableColumn(BaseDTO):
    """Column definition for constructor tables."""

    key: str = Field(min_length=1, max_length=100)
    header: str = Field(min_length=1, max_length=200)
    width_percent: float | None = Field(default=None, gt=0.0, le=100.0)
    alignment: Literal["left", "center", "right", "justify"] = "left"


class TableBlock(BaseBlock):
    """Block for structured tabular data rendered to GOST-friendly tables."""

    type: Literal["table"] = "table"
    columns: list[TableColumn] = Field(min_length=1, max_length=20)
    rows: list[dict[str, Any]] | None = None
    rows_binding: ConstructorBindingReference | None = None
    caption: str | None = Field(default=None, max_length=300)
    header_bold: bool = True
    compact: bool = False

    @model_validator(mode="after")
    def validate_rows_source(self) -> "TableBlock":
        """Require either inline rows or a bound row source."""
        settings = get_settings()
        if self.rows is None and self.rows_binding is None:
            raise ValueError("Table block requires either 'rows' or 'rows_binding'.")
        if self.rows is not None and len(self.rows) > settings.generation.max_table_rows:
            raise ValueError("Table block exceeds the configured row limit.")
        width_total = sum(column.width_percent or 0.0 for column in self.columns)
        if width_total and width_total > 100.0:
            raise ValueError("Table column widths cannot exceed 100 percent in total.")
        return self


class ImageBlock(BaseBlock):
    """Block for stamps, logos, signatures, and inline images."""

    type: Literal["image"] = "image"
    binding: ConstructorBindingReference
    width_mm: float = Field(default=50.0, gt=5.0, le=180.0)
    height_mm: float | None = Field(default=None, gt=5.0, le=250.0)
    keep_aspect_ratio: bool = True
    caption: str | None = Field(default=None, max_length=300)
    alignment: Literal["left", "center", "right"] = "center"


class SignatureBlock(BaseBlock):
    """Block for official signature areas compliant with formal documents."""

    type: Literal["signature"] = "signature"
    signer_name: ConstructorBindingReference
    signer_role: ConstructorBindingReference | None = None
    date_binding: ConstructorBindingReference | None = None
    line_label: str = Field(default="Signature", max_length=100)
    include_date: bool = True
    include_stamp_area: bool = False


class PageBreakBlock(BaseBlock):
    """Explicit page break block between document sections."""

    type: Literal["page_break"] = "page_break"
    reason: Literal["section", "appendix", "manual"] = "manual"


class SpacerBlock(BaseBlock):
    """Vertical spacing block with tightly bounded GOST-safe size."""

    type: Literal["spacer"] = "spacer"
    height_mm: float = Field(default=5.0, ge=1.0, le=30.0)


DocumentBlock = Annotated[
    TextBlock
    | TableBlock
    | ImageBlock
    | HeaderBlock
    | SignatureBlock
    | PageBreakBlock
    | SpacerBlock,
    Field(discriminator="type"),
]


class DocumentConstructor(BaseDTO):
    """Component-driven document payload consumed by the generation engine."""

    locale: str = "ru-RU"
    formatting: GOSTFormattingRules = Field(default_factory=GOSTFormattingRules)
    metadata: dict[str, str] = Field(default_factory=dict)
    blocks: list[DocumentBlock] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_constructor_limits(self) -> "DocumentConstructor":
        """Apply global constructor constraints from settings."""
        settings = get_settings()
        if len(self.blocks) > settings.generation.max_document_blocks:
            raise ValueError("Document constructor exceeds the configured block limit.")

        block_ids = [block.id for block in self.blocks]
        if len(block_ids) != len(set(block_ids)):
            raise ValueError("Document block identifiers must be unique.")
        return self


class ConstructorSchemaDescriptor(BaseDTO):
    """Small descriptor that documents the active constructor contract."""

    schema_version: Literal["1.0"] = "1.0"
    default_formatting: GOSTFormattingRules = Field(default_factory=GOSTFormattingRules)
    supported_blocks: list[str] = Field(
        default_factory=lambda: [
            "text",
            "table",
            "image",
            "header",
            "signature",
            "page_break",
            "spacer",
        ]
    )
