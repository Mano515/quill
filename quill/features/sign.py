"""Phase 8 — PDF signatures: visual signature stamps."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def sign_pdf(
    input: Path,
    output: Path,
    name: str,
    reason: str = "",
    location: str = "",
    page: int = 1,
    x: float = 50,
    y: float = 50,
    width: float = 220,
    height: float = 70,
) -> None:
    """Stamp a visible signature block onto a PDF page."""
    import fitz

    doc = fitz.open(str(input))
    pg = doc[page - 1]
    rect = fitz.Rect(x, y, x + width, y + height)

    shape = pg.new_shape()
    shape.draw_rect(rect)
    shape.finish(color=(0.18, 0.22, 0.55), fill=(0.94, 0.95, 1.0), width=1.5)

    # Divider under name
    shape.draw_line(fitz.Point(x + 4, y + 24), fitz.Point(x + width - 4, y + 24))
    shape.finish(color=(0.18, 0.22, 0.55), width=0.5)

    # Signature glyph (stylised "S")
    shape.insert_text(fitz.Point(x + 5, y + 18), "✍", fontsize=14, color=(0.18, 0.22, 0.55))
    shape.insert_text(fitz.Point(x + 22, y + 18), name, fontsize=12, color=(0.1, 0.1, 0.45))

    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    row2_y = y + 36
    if reason:
        shape.insert_text(fitz.Point(x + 6, row2_y), f"Motif : {reason}", fontsize=8, color=(0.3, 0.3, 0.4))
        row2_y += 14
    loc_date = (f"{location} · " if location else "") + date_str
    shape.insert_text(fitz.Point(x + 6, row2_y), loc_date, fontsize=7, color=(0.5, 0.5, 0.55))

    shape.commit()
    doc.save(str(output))
    doc.close()


def list_signatures(input: Path) -> list[dict]:
    """Return visible signature annotations found in the PDF."""
    import fitz

    doc = fitz.open(str(input))
    results = []
    for i, page in enumerate(doc, start=1):
        for annot in page.annots():
            if annot.type[1] in ("Stamp", "Widget", "FreeText"):
                info = annot.info
                results.append(
                    {
                        "page": i,
                        "type": annot.type[1],
                        "content": info.get("content", ""),
                        "author": info.get("title", ""),
                        "rect": list(annot.rect),
                    }
                )
    doc.close()
    return results
