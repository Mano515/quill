"""Text editing: cover original text with white, insert replacement at same position."""

from pathlib import Path


def replace_text(
    input: Path,
    output: Path,
    page: int,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    new_text: str,
) -> None:
    """
    Replace text inside a bounding box on a PDF page.

    Strategy: draw a white rectangle over the original text, then write
    the new text at the same position. Font is auto-detected from the
    content inside the rect; falls back to 12pt Helvetica if not found.
    """
    import fitz

    if page < 1:
        raise ValueError(f"page must be >= 1, got {page}")

    doc = fitz.open(str(input))
    try:
        if page > len(doc):
            raise ValueError(f"page {page} exceeds document length ({len(doc)})")

        pg = doc[page - 1]
        rect = fitz.Rect(x0, y0, x1, y1)

        # Detect font properties from the span(s) that overlap the target rect
        font_size = 12.0
        color = (0.0, 0.0, 0.0)
        is_bold = False
        is_italic = False
        for block in pg.get_text("dict")["blocks"]:
            if block.get("type") != 0:  # 0 = text block
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    if fitz.Rect(span["bbox"]).intersects(rect):
                        font_size = span["size"]
                        # flags: bit 1 = italic, bit 4 = bold
                        flags = span.get("flags", 0)
                        is_bold   = bool(flags & 16)
                        is_italic = bool(flags & 2)
                        # Normalise color from 0-255 int to 0-1 float if needed
                        c = span.get("color", 0)
                        if isinstance(c, int):
                            r = ((c >> 16) & 0xFF) / 255
                            g = ((c >> 8) & 0xFF) / 255
                            b = (c & 0xFF) / 255
                            color = (r, g, b)
                        break

        # Choose the closest built-in Helvetica variant
        if is_bold and is_italic:
            fontname = "hebi"   # Helvetica-BoldOblique
        elif is_bold:
            fontname = "hebo"   # Helvetica-Bold
        elif is_italic:
            fontname = "heit"   # Helvetica-Oblique
        else:
            fontname = "helv"   # Helvetica

        # Extend the cover rect downward to include descenders (p, g, y…)
        # Descenders reach approx 25 % of the font size below the baseline.
        descender = font_size * 0.30
        cover_rect = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y1 + descender)

        # Cover the original text with a white rectangle
        shape = pg.new_shape()
        shape.draw_rect(cover_rect)
        shape.finish(color=(1, 1, 1), fill=(1, 1, 1), width=0)
        shape.commit()

        # Insert new text at the baseline (y1 = bottom of the original rect)
        pg.insert_text(
            fitz.Point(x0, y1),
            new_text,
            fontsize=font_size,
            fontname=fontname,
            color=color,
        )

        doc.save(str(output), garbage=4, deflate=True)
    finally:
        doc.close()
