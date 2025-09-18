"""Render resolved documents into DOCX bytes."""

import base64
from io import BytesIO

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Mm, Pt

from app.core.exceptions import ValidationError
from app.services.generation.models import ResolvedDocument


class DocumentComposerService:
    """Compose DOCX files from normalized constructor blocks."""

    def compose(self, document: ResolvedDocument) -> bytes:
        """Return a DOCX document for the resolved constructor payload."""
        doc = Document()
        self._apply_document_defaults(doc, document)

        first_block = True
        for block in document.blocks:
            if block.type == "page_break":
                doc.add_page_break()
                first_block = True
                continue

            if not first_block:
                paragraph = doc.add_paragraph()
                paragraph.paragraph_format.space_before = Pt(0)
                paragraph.paragraph_format.space_after = Pt(0)
            first_block = False

            if block.type == "header":
                self._add_header(doc, block.content)
            elif block.type == "text":
                self._add_text(doc, block.content)
            elif block.type == "table":
                self._add_table(doc, block.content)
            elif block.type == "image":
                self._add_image(doc, block.content)
            elif block.type == "signature":
                self._add_signature(doc, block.content)
            elif block.type == "spacer":
                self._add_spacer(doc, block.content)

        output = BytesIO()
        doc.save(output)
        return output.getvalue()

    def _apply_document_defaults(self, doc: Document, document: ResolvedDocument) -> None:
        """Apply page margins and typography defaults."""
        section = doc.sections[0]
        page = document.formatting.page
        typography = document.formatting.typography

        section.left_margin = Mm(page.margin_left_mm)
        section.right_margin = Mm(page.margin_right_mm)
        section.top_margin = Mm(page.margin_top_mm)
        section.bottom_margin = Mm(page.margin_bottom_mm)
        section.header_distance = Mm(page.header_distance_mm)
        section.footer_distance = Mm(page.footer_distance_mm)

        normal_style = doc.styles["Normal"]
        normal_style.font.name = typography.font_family
        normal_style.font.size = Pt(typography.font_size_pt)

    def _add_header(self, doc: Document, content: dict) -> None:
        """Add a heading paragraph."""
        paragraph = doc.add_paragraph()
        run = paragraph.add_run(str(content["text"]))
        run.bold = True
        self._apply_text_style(paragraph, content["style"])

    def _add_text(self, doc: Document, content: dict) -> None:
        """Add a text paragraph."""
        paragraph = doc.add_paragraph()
        run = paragraph.add_run("" if content["text"] is None else str(content["text"]))
        style = content["style"]
        run.bold = style.get("bold", False)
        run.italic = style.get("italic", False)
        run.underline = style.get("underline", False)
        self._apply_text_style(paragraph, style)

    def _add_table(self, doc: Document, content: dict) -> None:
        """Add a table block."""
        columns = content["columns"]
        rows = content["rows"]
        if content.get("caption"):
            caption = doc.add_paragraph()
            caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
            caption.add_run(str(content["caption"])).bold = True

        table = doc.add_table(rows=1, cols=len(columns))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = "Table Grid"

        header_cells = table.rows[0].cells
        for index, column in enumerate(columns):
            header_cells[index].text = str(column["header"])

        for row in rows:
            cells = table.add_row().cells
            for index, column in enumerate(columns):
                value = row.get(column["key"], "")
                cells[index].text = "" if value is None else str(value)

    def _add_image(self, doc: Document, content: dict) -> None:
        """Add an image block from a local path or base64 payload."""
        image_source = content["image"]
        if not image_source:
            raise ValidationError("Image block requires image data.")

        paragraph = doc.add_paragraph()
        paragraph.alignment = self._map_alignment(content["alignment"])

        if not isinstance(image_source, str) or not image_source.startswith("data:image"):
            raise ValidationError("Image block requires a validated image data URL.")

        _, encoded = image_source.split(",", 1)
        image_bytes = BytesIO(base64.b64decode(encoded))
        paragraph.add_run().add_picture(image_bytes, width=Mm(content["width_mm"]))

        if content.get("caption"):
            caption = doc.add_paragraph()
            caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
            caption.add_run(str(content["caption"]))

    def _add_signature(self, doc: Document, content: dict) -> None:
        """Add a signature block."""
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        paragraph.add_run(f"{content['line_label']}: ____________________")

        name_paragraph = doc.add_paragraph()
        name_paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        name_paragraph.add_run(str(content["signer_name"]))

        if content.get("signer_role"):
            role_paragraph = doc.add_paragraph()
            role_paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            role_paragraph.add_run(str(content["signer_role"]))

        if content.get("include_date") and content.get("date"):
            date_paragraph = doc.add_paragraph()
            date_paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            date_paragraph.add_run(str(content["date"]))

    def _add_spacer(self, doc: Document, content: dict) -> None:
        """Add vertical space using paragraph spacing."""
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(content["height_mm"] * 2.83465)

    def _apply_text_style(self, paragraph, style: dict) -> None:
        """Apply paragraph-level style overrides."""
        alignment = style.get("alignment")
        if alignment:
            paragraph.alignment = self._map_alignment(alignment)

        if style.get("font_size_pt") is not None:
            for run in paragraph.runs:
                run.font.size = Pt(style["font_size_pt"])

        if style.get("first_line_indent_mm") is not None:
            paragraph.paragraph_format.first_line_indent = Mm(style["first_line_indent_mm"])

        if style.get("uppercase"):
            for run in paragraph.runs:
                run.text = run.text.upper()

        paragraph.paragraph_format.keep_with_next = bool(style.get("keep_with_next", False))

    def _map_alignment(self, alignment: str) -> WD_ALIGN_PARAGRAPH:
        """Map alignment strings to python-docx constants."""
        mapping = {
            "left": WD_ALIGN_PARAGRAPH.LEFT,
            "center": WD_ALIGN_PARAGRAPH.CENTER,
            "right": WD_ALIGN_PARAGRAPH.RIGHT,
            "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
        }
        return mapping.get(alignment, WD_ALIGN_PARAGRAPH.LEFT)
