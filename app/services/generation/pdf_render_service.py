"""Render resolved documents into PDF bytes."""

import base64
from io import BytesIO
from typing import cast

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.exceptions import ValidationError
from app.services.generation.models import ResolvedDocument

USE_DOCUMENT_DEFAULT = object()


class PdfRenderService:
    """Render PDFs from normalized constructor blocks."""

    def render(self, document: ResolvedDocument) -> bytes:
        """Return a PDF representation of the resolved document."""
        buffer = BytesIO()
        page = document.formatting.page

        pdf = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=page.margin_left_mm * mm,
            rightMargin=page.margin_right_mm * mm,
            topMargin=page.margin_top_mm * mm,
            bottomMargin=page.margin_bottom_mm * mm,
        )
        base_style = self._build_base_style(document)

        story = []
        for block in document.blocks:
            if block.type == "header":
                style = self._build_block_style(
                    document,
                    base_style,
                    name=f"Header-{block.id}",
                    overrides=block.content["style"],
                    default_alignment="center",
                    default_first_line_indent_mm=0.0,
                    bold=True,
                )
                story.append(Paragraph(self._render_text(str(block.content["text"]), block.content["style"]), style))
            elif block.type == "text":
                style = self._build_block_style(
                    document,
                    base_style,
                    name=f"Text-{block.id}",
                    overrides=block.content["style"],
                    default_alignment=document.formatting.typography.alignment,
                    default_first_line_indent_mm=USE_DOCUMENT_DEFAULT,
                )
                story.append(Paragraph(self._render_text(str(block.content["text"] or ""), block.content["style"]), style))
            elif block.type == "table":
                story.extend(self._build_table(document, block.content, base_style))
            elif block.type == "image":
                story.extend(self._build_image(document, block.content, base_style))
            elif block.type == "signature":
                story.extend(self._build_signature(document, block.content, base_style))
            elif block.type == "spacer":
                story.append(Spacer(1, block.content["height_mm"] * mm))
            elif block.type == "page_break":
                story.append(PageBreak())

        pdf.build(story)
        return buffer.getvalue()

    def _build_base_style(self, document: ResolvedDocument) -> ParagraphStyle:
        """Return the base paragraph style for the configured GOST profile."""
        typography = document.formatting.typography
        styles = getSampleStyleSheet()
        return ParagraphStyle(
            "GOSTNormal",
            parent=styles["Normal"],
            fontName=self._map_font_name(typography.font_family),
            fontSize=typography.font_size_pt,
            leading=typography.font_size_pt * typography.line_spacing,
            firstLineIndent=typography.first_line_indent_mm * mm,
            alignment=self._map_alignment(typography.alignment),
            spaceBefore=typography.paragraph_spacing_before_pt,
            spaceAfter=typography.paragraph_spacing_after_pt,
        )

    def _build_block_style(
        self,
        document: ResolvedDocument,
        parent: ParagraphStyle,
        *,
        name: str,
        overrides: dict,
        default_alignment: str,
        default_first_line_indent_mm: float | object,
        bold: bool = False,
    ) -> ParagraphStyle:
        """Return one paragraph style layered on top of the base document style."""
        typography = document.formatting.typography
        font_size = float(overrides.get("font_size_pt") or typography.font_size_pt)
        alignment = overrides.get("alignment") or default_alignment
        first_line_indent_mm = (
            overrides["first_line_indent_mm"]
            if overrides.get("first_line_indent_mm") is not None
            else default_first_line_indent_mm
        )
        if first_line_indent_mm is USE_DOCUMENT_DEFAULT:
            first_line_indent = typography.first_line_indent_mm * mm
        else:
            first_line_indent = float(cast(float, first_line_indent_mm)) * mm

        return ParagraphStyle(
            name,
            parent=parent,
            fontName=self._map_font_name(
                typography.font_family,
                bold=bold or bool(overrides.get("bold", False)),
                italic=bool(overrides.get("italic", False)),
            ),
            fontSize=font_size,
            leading=font_size * typography.line_spacing,
            firstLineIndent=first_line_indent,
            alignment=self._map_alignment(alignment),
            spaceBefore=typography.paragraph_spacing_before_pt,
            spaceAfter=typography.paragraph_spacing_after_pt,
            keepWithNext=1 if overrides.get("keep_with_next", False) else 0,
        )

    def _build_table(
        self,
        document: ResolvedDocument,
        content: dict,
        base_style: ParagraphStyle,
    ) -> list:
        """Build a ReportLab table block."""
        flowables = []
        if content.get("caption"):
            caption_style = self._build_block_style(
                document,
                base_style,
                name="TableCaption",
                overrides={"bold": True},
                default_alignment="center",
                default_first_line_indent_mm=0.0,
                bold=True,
            )
            flowables.append(Paragraph(self._escape(str(content["caption"])), caption_style))
            flowables.append(Spacer(1, 3 * mm))

        header_style = self._build_block_style(
            document,
            base_style,
            name="TableHeader",
            overrides={"bold": True},
            default_alignment="center",
            default_first_line_indent_mm=0.0,
            bold=True,
        )
        headers = [
            Paragraph(self._escape(str(column["header"])), header_style) for column in content["columns"]
        ]
        rows = []
        for row in content["rows"]:
            rendered_row = []
            for index, column in enumerate(content["columns"]):
                cell_style = self._build_block_style(
                    document,
                    base_style,
                    name=f"TableCell-{index}",
                    overrides={},
                    default_alignment=column.get("alignment") or "left",
                    default_first_line_indent_mm=0.0,
                )
                rendered_row.append(
                    Paragraph(self._escape(str(row.get(column["key"], ""))), cell_style)
                )
            rows.append(rendered_row)

        table = Table([headers, *rows], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAEAEA")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        flowables.append(table)
        return flowables

    def _build_image(
        self,
        document: ResolvedDocument,
        content: dict,
        base_style: ParagraphStyle,
    ) -> list:
        """Build ReportLab flowables for an image block."""
        image_source = content["image"]
        if not image_source:
            raise ValidationError("Image block requires image data.")
        if not isinstance(image_source, str) or not image_source.startswith("data:image"):
            raise ValidationError("Image block requires a validated image data URL.")
        _, encoded = image_source.split(",", 1)
        image = Image(BytesIO(base64.b64decode(encoded)), width=content["width_mm"] * mm)
        image.hAlign = content["alignment"].upper()
        flowables: list = [image]
        if content.get("caption"):
            caption_style = self._build_block_style(
                document,
                base_style,
                name="ImageCaption",
                overrides={},
                default_alignment="center",
                default_first_line_indent_mm=0.0,
            )
            flowables.append(Paragraph(self._escape(str(content["caption"])), caption_style))
        return flowables

    def _build_signature(
        self,
        document: ResolvedDocument,
        content: dict,
        base_style: ParagraphStyle,
    ) -> list:
        """Build signature paragraphs."""
        alignment = (
            "right" if document.formatting.signatures_align_right else document.formatting.typography.alignment
        )
        signature_style = self._build_block_style(
            document,
            base_style,
            name="Signature",
            overrides={},
            default_alignment=alignment,
            default_first_line_indent_mm=0.0,
        )
        parts = [
            Paragraph(self._escape(f"{content['line_label']}: ____________________"), signature_style),
            Paragraph(self._escape(str(content["signer_name"])), signature_style),
        ]
        if content.get("signer_role"):
            parts.append(Paragraph(self._escape(str(content["signer_role"])), signature_style))
        if content.get("include_date") and content.get("date"):
            parts.append(Paragraph(self._escape(str(content["date"])), signature_style))
        return parts

    def _render_text(self, value: str, style: dict) -> str:
        """Render inline style-safe paragraph text."""
        rendered = self._escape(value).replace("\n", "<br/>")
        if style.get("uppercase"):
            rendered = rendered.upper()
        if style.get("underline"):
            rendered = f"<u>{rendered}</u>"
        return rendered

    def _map_alignment(self, alignment: str) -> int:
        """Map alignment labels to ReportLab constants."""
        mapping = {
            "left": TA_LEFT,
            "center": TA_CENTER,
            "right": TA_RIGHT,
            "justify": TA_JUSTIFY,
        }
        return mapping.get(alignment, TA_LEFT)

    def _map_font_name(self, font_family: str, *, bold: bool = False, italic: bool = False) -> str:
        """Map requested fonts to built-in ReportLab fonts."""
        if font_family == "Times New Roman":
            if bold and italic:
                return "Times-BoldItalic"
            if bold:
                return "Times-Bold"
            if italic:
                return "Times-Italic"
            return "Times-Roman"
        return font_family

    def _escape(self, value: str) -> str:
        """Escape minimal XML entities for ReportLab paragraphs."""
        return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
