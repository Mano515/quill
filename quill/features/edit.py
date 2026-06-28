"""Text editing: cover original text with white, insert replacement at same position."""

from pathlib import Path

# Doit correspondre à la constante MARGIN dans le JS de showInlineEditor.
# Le JS ajoute cette marge autour du span pour agrandir la zone de couverture ;
# on la soustrait ici pour retrouver la position exacte du texte original.
_JS_MARGIN = 3


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

    Strategy:
      1. Detect font properties (size, bold, italic, color) from overlapping spans.
      2. Detect text alignment (left / center / right) from span position on page.
      3. Draw a white rectangle that covers the original text including descenders.
      4. Insert the replacement text with matching style and alignment.
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

        # ── 1. Detect font properties ──────────────────────────────────────
        font_size = 12.0
        color     = (0.0, 0.0, 0.0)
        is_bold   = False
        is_italic = False

        for block in pg.get_text("dict")["blocks"]:
            if block.get("type") != 0:   # 0 = text block
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    if fitz.Rect(span["bbox"]).intersects(rect):
                        font_size = span["size"]
                        # flags: bit 1 = italic, bit 4 = bold
                        flags     = span.get("flags", 0)
                        is_bold   = bool(flags & 16)
                        is_italic = bool(flags & 2)
                        c = span.get("color", 0)
                        if isinstance(c, int):
                            color = (
                                ((c >> 16) & 0xFF) / 255,
                                ((c >>  8) & 0xFF) / 255,
                                ( c        & 0xFF) / 255,
                            )
                        break

        # Closest built-in Helvetica variant (bold / italic combinations)
        if is_bold and is_italic:
            fontname = "hebi"   # Helvetica-BoldOblique
        elif is_bold:
            fontname = "hebo"   # Helvetica-Bold
        elif is_italic:
            fontname = "heit"   # Helvetica-Oblique
        else:
            fontname = "helv"   # Helvetica

        # ── 2. Detect alignment ────────────────────────────────────────────
        # The JS MARGIN was subtracted from x0 and added to x1, so the real
        # text boundaries are x0+MARGIN and x1-MARGIN.
        text_x0   = x0 + _JS_MARGIN   # actual left edge of original text
        text_x1   = x1 - _JS_MARGIN   # actual right edge
        text_y1   = y1 - _JS_MARGIN   # actual baseline

        page_w    = pg.rect.width
        left_gap  = text_x0
        right_gap = page_w - text_x1
        mid_text  = (text_x0 + text_x1) / 2
        mid_page  = page_w / 2

        if abs(left_gap - right_gap) < font_size and abs(mid_text - mid_page) < font_size:
            # Roughly symmetric margins → centered
            align      = fitz.TEXT_ALIGN_CENTER
            box_x0     = 0
            box_x1     = page_w
        elif right_gap < left_gap * 0.4:
            # Much smaller right gap → right-aligned
            align      = fitz.TEXT_ALIGN_RIGHT
            box_x0     = 0
            box_x1     = text_x1
        else:
            # Default: left-aligned
            align      = fitz.TEXT_ALIGN_LEFT
            box_x0     = text_x0
            box_x1     = page_w - right_gap

        # ── 3. Cover original text ─────────────────────────────────────────
        # Extend the rect downward to hide descenders (p, g, y… ≈ 30 % of font).
        descender   = font_size * 0.30
        cover_rect  = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y1 + descender)

        shape = pg.new_shape()
        shape.draw_rect(cover_rect)
        shape.finish(color=(1, 1, 1), fill=(1, 1, 1), width=0)
        shape.commit()

        # ── 4. Insert replacement text ─────────────────────────────────────
        # insert_text(Point, text) place le texte à partir de la baseline —
        # beaucoup plus fiable qu'insert_textbox qui échoue silencieusement
        # si le rect est trop petit (retourne < 0 sans rien insérer).
        # On calcule la largeur du texte de remplacement pour positionner
        # correctement selon l'alignement détecté.
        try:
            text_width = fitz.Font(fontname=fontname).text_length(new_text, fontsize=font_size)
        except Exception:
            text_width = text_x1 - text_x0   # fallback : largeur du span original

        if align == fitz.TEXT_ALIGN_RIGHT:
            insert_x = text_x1 - text_width
        elif align == fitz.TEXT_ALIGN_CENTER:
            center = (text_x0 + text_x1) / 2
            insert_x = center - text_width / 2
        else:  # gauche
            insert_x = text_x0

        pg.insert_text(
            fitz.Point(insert_x, text_y1),
            new_text,
            fontsize=font_size,
            fontname=fontname,
            color=color,
        )

        doc.save(str(output), garbage=4, deflate=True)
    finally:
        doc.close()
