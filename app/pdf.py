"""PDF files, built in memory: a PDF Maker document, all notes, and the
progress report. Each function returns the file as bytes, so the screen
can save it on a computer or download it in a browser the same way."""

import logging
from datetime import datetime
from pathlib import Path

from .deps import FPDF

FONT_DIR = Path("C:/Windows/Fonts")


def available():
    return FPDF is not None


class _Doc:
    """An FPDF document plus the font family it ended up with."""

    def __init__(self):
        self.pdf, self.family, self.unicode = _new_pdf()

    def safe(self, text):
        """With Unicode fonts, text passes through. The built-in Helvetica
        only covers Latin-1, so anything else becomes '?' instead of crashing."""
        text = str(text)
        return text if self.unicode else text.encode("latin-1", "replace").decode("latin-1")

    def line(self, text, size, bold=False, height=7, grey=False):
        self.pdf.set_font(self.family, "B" if bold else "", size)
        self.pdf.set_text_color(*((130, 130, 130) if grey else (20, 20, 20)))
        self.pdf.multi_cell(0, height, self.safe(text), new_x="LMARGIN", new_y="NEXT")

    def bytes(self):
        return bytes(self.pdf.output())


def _new_pdf():
    """Uses Windows' Unicode fonts when present, so quotes, symbols and
    Indian-language text print properly: Segoe UI for Latin/Urdu, Nirmala UI
    as a fallback for Hindi, Telugu, Tamil, Kannada, Malayalam, Bengali and
    Marathi. Elsewhere (Linux, the Dev Container) it falls back to Helvetica."""
    pdf = FPDF()
    logging.getLogger("fontTools").setLevel(logging.ERROR)  # harmless "MERG NOT subset" notes
    regular, bold = FONT_DIR / "segoeui.ttf", FONT_DIR / "segoeuib.ttf"
    if not (regular.exists() and bold.exists()):
        return pdf, "Helvetica", False
    try:
        pdf.add_font("SegoeUI", "", str(regular))
        pdf.add_font("SegoeUI", "B", str(bold))
        fallbacks = []
        if (FONT_DIR / "Nirmala.ttc").exists():
            pdf.add_font("Nirmala", "", str(FONT_DIR / "Nirmala.ttc"), collection_font_number=0)
            fallbacks.append("Nirmala")
        if (FONT_DIR / "seguisym.ttf").exists():
            pdf.add_font("SegoeSymbol", "", str(FONT_DIR / "seguisym.ttf"))
            fallbacks.append("SegoeSymbol")
        if fallbacks:
            pdf.set_fallback_fonts(fallbacks, exact_match=False)
        try:
            import uharfbuzz  # noqa: F401  (optional: correct Indic letter shaping)
            pdf.set_text_shaping(True)
        except ImportError:
            pass
    except Exception:
        return FPDF(), "Helvetica", False  # any font problem: plain Helvetica still works
    return pdf, "SegoeUI", True


def document(title, pages):
    """A title page, then one page per {"heading", "body"}."""
    doc = _Doc()
    doc.pdf.set_auto_page_break(auto=True, margin=18)
    doc.pdf.add_page()
    doc.line(title or "Untitled document", 24, bold=True, height=14)
    doc.line(f"Made with StudyGenie · {datetime.now():%d %b %Y}", 9, grey=True, height=6)
    for page in pages:
        doc.pdf.add_page()
        if page.get("heading"):
            doc.line(page["heading"], 17, bold=True, height=10)
            doc.pdf.ln(2)
        if page.get("body"):
            doc.line(page["body"], 12)
    return doc.bytes()


def notes(notes, time_label):
    """One page per note. `time_label` turns a stored time into display text."""
    doc = _Doc()
    doc.pdf.set_auto_page_break(auto=True, margin=15)
    for note in notes:
        doc.pdf.add_page()
        doc.line(note.get("title") or "Untitled note", 16, bold=True, height=10)
        doc.line(time_label(note.get("updated") or note.get("created")), 9, grey=True, height=6)
        doc.pdf.ln(4)
        doc.line(note.get("content", ""), 12)
    return doc.bytes()


def progress_report(rows):
    """A one-page report of (label, value) rows."""
    doc = _Doc()
    doc.pdf.add_page()
    doc.line("StudyGenie Progress Report", 18, bold=True, height=12)
    doc.line(f"{datetime.now():%d %b %Y}", 9, grey=True, height=6)
    doc.pdf.ln(6)
    for label, value in rows:
        doc.pdf.set_text_color(20, 20, 20)
        doc.pdf.set_font(doc.family, "B", 11)
        doc.pdf.cell(70, 8, doc.safe(label))
        doc.pdf.set_font(doc.family, "", 11)
        doc.pdf.cell(0, 8, doc.safe(value), new_x="LMARGIN", new_y="NEXT")
    return doc.bytes()
