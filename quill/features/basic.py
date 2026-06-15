"""Phase 1 — Basic PDF operations."""

from pathlib import Path

from pypdf import PdfReader, PdfWriter


def merge(inputs: list[Path], output: Path) -> None:
    """Merge multiple PDFs into one."""
    writer = PdfWriter()
    for path in inputs:
        reader = PdfReader(path)
        for page in reader.pages:
            writer.add_page(page)
    with open(output, "wb") as f:
        writer.write(f)


def split(input: Path, output_dir: Path, ranges: list[tuple[int, int]] | None = None) -> list[Path]:
    """
    Split a PDF into multiple files.
    If ranges is None, each page becomes its own file.
    ranges: list of (start, end) tuples, 1-indexed inclusive.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(input)
    total = len(reader.pages)
    outputs = []

    if ranges is None:
        ranges = [(i + 1, i + 1) for i in range(total)]

    for start, end in ranges:
        writer = PdfWriter()
        for i in range(start - 1, min(end, total)):
            writer.add_page(reader.pages[i])
        out = output_dir / f"{input.stem}_{start}-{end}.pdf"
        with open(out, "wb") as f:
            writer.write(f)
        outputs.append(out)

    return outputs


def rotate(input: Path, output: Path, degrees: int, pages: list[int] | None = None) -> None:
    """
    Rotate pages by degrees (90, 180, 270).
    pages: 1-indexed list of pages to rotate. None = all pages.
    """
    reader = PdfReader(input)
    writer = PdfWriter()
    target = set(pages) if pages else None

    for i, page in enumerate(reader.pages):
        if target is None or (i + 1) in target:
            page.rotate(degrees)
        writer.add_page(page)

    with open(output, "wb") as f:
        writer.write(f)


def reorder(input: Path, output: Path, order: list[int]) -> None:
    """
    Reorder pages. order: 1-indexed list of page numbers in desired order.
    Example: [3, 1, 2] puts page 3 first.
    """
    reader = PdfReader(input)
    writer = PdfWriter()
    for i in order:
        writer.add_page(reader.pages[i - 1])
    with open(output, "wb") as f:
        writer.write(f)


def delete_pages(input: Path, output: Path, pages: list[int]) -> None:
    """Delete specific pages (1-indexed)."""
    reader = PdfReader(input)
    writer = PdfWriter()
    to_delete = set(pages)
    for i, page in enumerate(reader.pages):
        if (i + 1) not in to_delete:
            writer.add_page(page)
    with open(output, "wb") as f:
        writer.write(f)


def extract_text(input: Path, pages: list[int] | None = None) -> dict[int, str]:
    """
    Extract plain text from pages.
    Returns a dict mapping page number (1-indexed) to text.
    """
    import pdfplumber

    result: dict[int, str] = {}
    with pdfplumber.open(input) as pdf:
        target = set(pages) if pages else None
        for i, page in enumerate(pdf.pages):
            if target is None or (i + 1) in target:
                result[i + 1] = page.extract_text() or ""
    return result


def get_metadata(input: Path) -> dict:
    """Extract PDF metadata."""
    reader = PdfReader(input)
    meta = reader.metadata or {}
    return {
        "page_count": len(reader.pages),
        "title": meta.get("/Title"),
        "author": meta.get("/Author"),
        "subject": meta.get("/Subject"),
        "creator": meta.get("/Creator"),
        "producer": meta.get("/Producer"),
        "creation_date": meta.get("/CreationDate"),
        "modification_date": meta.get("/ModDate"),
        "encrypted": reader.is_encrypted,
    }


def create_from_text(text: str, output: Path, title: str = "", font_size: int = 12) -> None:
    """Create a simple PDF from plain text using reportlab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    doc = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
    )
    styles = getSampleStyleSheet()
    story = []

    if title:
        story.append(Paragraph(title, styles["Title"]))
        story.append(Spacer(1, 0.5 * cm))

    for line in text.split("\n"):
        story.append(Paragraph(line or "&nbsp;", styles["Normal"]))

    doc.build(story)
