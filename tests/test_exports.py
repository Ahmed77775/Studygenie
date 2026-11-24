"""Files StudyGenie makes: PDFs, the sketch PNG, and read-aloud text."""

import io
import unittest

from app import pdf, speech
from app.deps import FPDF, Image
from tests.helpers import AppTestCase


@unittest.skipIf(FPDF is None, "fpdf2 not installed")
class PdfTests(unittest.TestCase):
    def test_document_is_a_pdf_with_a_page_each(self):
        data = pdf.document("Biology revision", [{"heading": "Cells", "body": "The basic unit of life."},
                                                 {"heading": "", "body": "Only text."}])
        self.assertTrue(data.startswith(b"%PDF-"))
        self.assertIn(b"/Count 3", data)  # the title page plus the two pages

    def test_unicode_text_does_not_crash(self):
        data = pdf.document("“Quotes” — dashes", [{"heading": "हिंदी", "body": "తెలుగు · اردو · ∑ π √"}])
        self.assertTrue(data.startswith(b"%PDF-"))

    def test_notes_and_progress_report(self):
        notes = [{"title": "One", "content": "First", "created": "2026-11-08T09:30:00"},
                 {"title": "", "content": "Untitled", "created": None}]
        self.assertTrue(pdf.notes(notes, lambda value: str(value)).startswith(b"%PDF-"))
        self.assertTrue(pdf.progress_report([("Level", "3"), ("XP", "40 / 220")]).startswith(b"%PDF-"))


class ProgressRowsTests(AppTestCase, unittest.TestCase):
    def test_report_rows_use_real_figures(self):
        from app.core import StudyCore
        core = StudyCore(self.tmp / "core.db", self.tmp / "none.json")
        try:
            core.data["quiz_scores"] = [60, 80]
            rows = dict(core.progress_rows())
            self.assertEqual(rows["Average quiz score"], "70%")
            self.assertEqual(rows["Student"], "Student")  # no profile yet
            core.made_pdf(6)
            self.assertEqual(core.data["pdfs_created"], 1)
        finally:
            core.conn.close()


@unittest.skipIf(Image is None, "Pillow not installed")
class SketchTests(unittest.TestCase):
    def test_png_is_board_sized_and_has_the_ink(self):
        from app.views.sketchpad import BOARD_H, BOARD_W, EXPORT_SCALE, render_png
        strokes = [{"color": "#DC2626", "width": 6, "points": [(10, 10), (100, 10)]},
                   {"color": "#2563EB", "width": 8, "points": [(400, 200)]}]
        image = Image.open(io.BytesIO(render_png(strokes))).convert("RGB")
        self.assertEqual(image.size, (BOARD_W * EXPORT_SCALE, BOARD_H * EXPORT_SCALE))
        self.assertEqual(image.getpixel((50 * EXPORT_SCALE, 10 * EXPORT_SCALE)), (0xDC, 0x26, 0x26))  # on the line
        self.assertEqual(image.getpixel((400 * EXPORT_SCALE, 200 * EXPORT_SCALE)), (0x25, 0x63, 0xEB))  # the dot
        self.assertEqual(image.getpixel((5, 400)), (255, 255, 255))  # untouched paper

    def test_empty_board_is_white(self):
        from app.views.sketchpad import render_png
        image = Image.open(io.BytesIO(render_png([]))).convert("RGB")
        self.assertEqual(image.getextrema(), ((255, 255), (255, 255), (255, 255)))


class ReadAloudTextTests(unittest.TestCase):
    def test_markdown_symbols_are_not_read_out(self):
        text = "## Photosynthesis\n**Plants** make *food*.\n- uses `light`\n[more](http://x.y)"
        self.assertEqual(speech.plain_text(text), "Photosynthesis Plants make food . - uses light more")

    def test_code_blocks_are_skipped(self):
        self.assertEqual(speech.plain_text("Try this:\n```python\nprint(1)\n```\nDone."), "Try this: Done.")


if __name__ == "__main__":
    unittest.main()
