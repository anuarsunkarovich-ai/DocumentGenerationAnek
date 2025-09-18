"""Render resolved documents into PDF bytes."""

import base64
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.exceptions import ValidationError
from app.services.generation.models import ResolvedDocument


class PdfRenderService:
    """Render PDFs from normalized constructor blocks."""

    def render(self, document: ResolvedDocument) -> bytes:
        """Return a PDF representation of the resolved document."""
        buffer = BytesIO()
        page = document.formatting.page
        typography = document.formatting.typography

        pdf = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=page.margin_left_mm * mm,
            rightMargin=page.margin_right_mm * mm,
            topMargin=page.margin_top_mm * mm,
            bottomMargin=page.margin_bottom_mm * mm,
        )
        styles = getSampleStyleSheet()
        normal = ParagraphStyle(
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
        header = ParagraphStyle(
            "GOSTHeader",
            parent=normal,
            alignment=TA_CENTER,
            fontSize=typography.font_size_pt,
        )

        story = []
        for block in document.blocks:
            if block.type == "header":
                story.append(Paragraph(self._escape(block.content["text"]), header))
            elif block.type == "text":
                story.append(Paragraph(self._escape(str(block.content["text"] or "")), normal))
            elif block.type == "table":
                story.extend(self._build_table(block.content, normal))
            elif block.type == "image":
                story.append(self._build_image(block.content))
            elif block.type == "signature":
                story.extend(self._build_signature(block.content, normal))
            elif block.type == "spacer":
                story.append(Spacer(1, block.content["height_mm"] * mm))
            elif block.type == "page_break":
                from reportlab.platypus import PageBreak

                story.append(PageBreak())

        pdf.build(story)
        return buffer.getvalue()

    def _build_table(self, content: dict, normal: ParagraphStyle) -> list:
        """Build a ReportLab table block."""
        flowables = []
        if content.get("caption"):
            flowables.append(Paragraph(self._escape(str(content["caption"])), normal))
            flowables.append(Spacer(1, 3 * mm))

        headers = [self._escape(str(column["header"])) for column in content["columns"]]
        rows = [
            [self._escape(str(row.get(column["key"], ""))) for column in content["columns"]]
            for row in content["rows"]
        ]
        table = Table([headers, *rows], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAEAEA")),
                    ("FONTNAME", (0, 0), (-1, -1), normal.fontName),
                    ("FONTSIZE", (0, 0), (-1, -1), normal.fontSize),
                    ("LEADING", (0, 0), (-1, -1), normal.leading),
                ]
            )
        )
        flowables.append(table)
        return flowables

    def _build_image(self, content: dict) -> Image:
        """Build a ReportLab image flowable."""
        image_source = content["image"]
        if not image_source:
            raise ValidationError("Image block requires image data.")
        if not isinstance(image_source, str) or not image_source.startswith("data:image"):
            raise ValidationError("Image block requires a validated image data URL.")
        _, encoded = image_source.split(",", 1)
        return Image(BytesIO(base64.b64decode(encoded)), width=content["width_mm"] * mm)

    def _build_signature(self, content: dict, normal: ParagraphStyle) -> list:
        """Build signature paragraphs."""
        parts = [
            Paragraph(self._escape(f"{content['line_label']}: ____________________"), normal),
            Paragraph(self._escape(str(content["signer_name"])), normal),
        ]
        if content.get("signer_role"):
            parts.append(Paragraph(self._escape(str(content["signer_role"])), normal))
        if content.get("include_date") and content.get("date"):
            parts.append(Paragraph(self._escape(str(content["date"])), normal))
        return parts

    def _map_alignment(self, alignment: str) -> int:
        """Map alignment labels to ReportLab constants."""
        mapping = {
            "left": TA_LEFT,
            "center": TA_CENTER,
            "right": TA_RIGHT,
            "justify": TA_JUSTIFY,
        }
        return mapping.get(alignment, TA_LEFT)

    def _map_font_name(self, font_family: str) -> str:
        """Map requested fonts to built-in ReportLab fonts."""
        if font_family == "Times New Roman":
            return "Times-Roman"
        return font_family

    def _escape(self, value: str) -> str:
        """Escape minimal XML entities for ReportLab paragraphs."""
        return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
