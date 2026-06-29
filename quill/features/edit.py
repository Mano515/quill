"""Text editing: cover original text with white, insert replacement at same position."""

from pathlib import Path

_JS_MARGIN = 3

# Mots-clés dans les noms de police → niveau de graisse (0=normal, 1=medium, 2=bold, 3=heavy)
_WEIGHT_KEYWORDS = {
    3: ["black", "heavy", "extrabold", "ultrabold", "ultra", "extrablack"],
    2: ["bold", "demibold", "semibold"],
    1: ["medium"],
}


def _normalize(name: str) -> str:
    return name.split("+")[-1].lower().replace("-", "").replace("_", "").replace(" ", "")


def _font_weight(flags: int, font_name: str) -> int:
    """Retourne le niveau de graisse : 0=normal, 1=medium, 2=bold, 3=heavy."""
    fn = _normalize(font_name)
    for level in (3, 2, 1):
        if any(kw in fn for kw in _WEIGHT_KEYWORDS[level]):
            return level
    if flags & 16:
        return 2
    return 0


def replace_text(
    input: Path,
    output: Path,
    page: int,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    new_text: str,
    tracking_extra: float = 0.0,
    weight_extra: float = 0.0,
) -> None:
    import fitz

    if page < 1:
        raise ValueError(f"page must be >= 1, got {page}")

    doc = fitz.open(str(input))
    try:
        if page > len(doc):
            raise ValueError(f"page {page} exceeds document length ({len(doc)})")

        pg         = doc[page - 1]
        tight_rect = fitz.Rect(x0 + _JS_MARGIN, y0 + _JS_MARGIN,
                               x1 - _JS_MARGIN, y1 - _JS_MARGIN)

        # ── 1. Propriétés de police + positions de glyphes (rawdict) ──────────
        # On collecte les positions de TOUS les spans intersectants pour avoir
        # un tracking représentatif (ex. "Manuel" et "HERNANDEZ" peuvent avoir
        # des trackings différents — on prend la moyenne globale).
        font_size    = 12.0
        color        = (0.0, 0.0, 0.0)
        weight_level = 0          # 0=normal, 1=medium, 2=bold, 3=heavy
        is_italic    = False
        baseline_y   = None
        span_fname   = ""
        char_origins = []         # (char, x_origin) de TOUS les spans

        _got_font = False
        for block in pg.get_text("rawdict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    if not fitz.Rect(span["bbox"]).intersects(tight_rect):
                        continue
                    # Propriétés de police : premier span seulement
                    if not _got_font:
                        font_size    = span["size"]
                        flags        = span.get("flags", 0)
                        span_fname   = span.get("font", "")
                        weight_level = _font_weight(flags, span_fname)
                        fn_low       = span_fname.lower()
                        is_italic    = bool(flags & 2) or "italic" in fn_low or "oblique" in fn_low
                        c = span.get("color", 0)
                        if isinstance(c, int):
                            color = (((c >> 16) & 0xFF) / 255,
                                     ((c >>  8) & 0xFF) / 255,
                                     ( c        & 0xFF) / 255)
                        origin = span.get("origin")
                        if origin:
                            baseline_y = origin[1]
                        _got_font = True

                    # Positions de glyphes : TOUS les spans
                    for ch in span.get("chars", []):
                        if ch.get("c") and ch.get("origin"):
                            char_origins.append((ch["c"], ch["origin"][0]))

        is_bold = weight_level >= 2

        # ── 2. Extraction du font embarqué ─────────────────────────────────────
        fontbuffer = None
        try:
            all_fonts = pg.get_fonts()
        except Exception:
            all_fonts = []

        if span_fname:
            norm_span = _normalize(span_fname)
            for fi in all_fonts:
                norm_base = _normalize(fi[3] or "")
                if norm_base and (norm_base == norm_span
                                  or norm_span in norm_base
                                  or norm_base in norm_span):
                    data = doc.extract_font(fi[0])
                    if data and len(data) >= 4 and data[3]:
                        fontbuffer = data[3]
                        break

        # ── 3. Police Helvetica de fallback ───────────────────────────────────
        fontname_fb = ("hebi" if (is_bold and is_italic) else
                       "hebo" if is_bold else
                       "heit" if is_italic else "helv")

        # ── 4. Enregistrement du font extrait (si disponible) ─────────────────
        # INVARIANT : font_obj doit toujours correspondre au font réellement inséré.
        active_fontname = fontname_fb
        if fontbuffer:
            try:
                pg.insert_font(fontname="_qf0", fontbuffer=fontbuffer)
                active_fontname = "_qf0"
            except Exception:
                fontbuffer = None

        try:
            font_obj = (fitz.Font(fontbuffer=fontbuffer) if fontbuffer
                        else fitz.Font(fontname=fontname_fb))
        except Exception:
            font_obj = None

        # ── 5. Simulation de graisse par contour (render_mode=2) ───────────────
        # stroke_width est en points PDF fixes (pas proportionnel au corps).
        # Pas de simulation automatique — les PDFs Figma (Type3) ne permettent
        # pas de détecter la graisse de façon fiable.
        # weight_extra est en points PDF : 0.1 ≈ 1 px écran à 96 dpi.
        stroke_width = max(0.0, min(weight_extra, 2.0))
        render_mode  = 2 if stroke_width > 0 else 0

        # ── 6. Alignement ─────────────────────────────────────────────────────
        text_x0   = x0 + _JS_MARGIN
        text_x1   = x1 - _JS_MARGIN
        page_w    = pg.rect.width
        left_gap  = text_x0
        right_gap = page_w - text_x1

        if (abs(left_gap - right_gap) < font_size
                and abs((text_x0 + text_x1) / 2 - page_w / 2) < font_size):
            align = fitz.TEXT_ALIGN_CENTER
        elif right_gap < left_gap * 0.4:
            align = fitz.TEXT_ALIGN_RIGHT
        else:
            align = fitz.TEXT_ALIGN_LEFT

        # ── 7. Redaction ───────────────────────────────────────────────────────
        pg.add_redact_annot(tight_rect, fill=(1, 1, 1))
        pg.apply_redactions(images=0)

        # ── 8. Charspacing depuis les positions réelles de TOUS les glyphes ───
        # gap(i→i+1) − avance_naturelle(char_i, font_réel) = tracking pur.
        charspacing = 0.0
        if font_obj and len(char_origins) > 1:
            deltas = []
            for i in range(len(char_origins) - 1):
                gap = char_origins[i + 1][1] - char_origins[i][1]
                try:
                    nat = font_obj.text_length(char_origins[i][0], fontsize=font_size)
                except Exception:
                    nat = 0.0
                if gap > 0:   # ignorer les paires avec gap négatif (ligatures, RTL)
                    deltas.append(gap - nat)
            if deltas:
                raw_cs = sum(deltas) / len(deltas)
                charspacing = max(-font_size * 0.1, min(raw_cs, font_size * 0.4))

        charspacing += tracking_extra

        # ── 9. Insertion caractère par caractère ───────────────────────────────
        if baseline_y is None:
            baseline_y = tight_rect.y0 + (tight_rect.y1 - tight_rect.y0) * 0.80

        try:
            nat_new    = (font_obj.text_length(new_text, fontsize=font_size) if font_obj
                          else fitz.Font(fontname=fontname_fb).text_length(new_text, fontsize=font_size))
            text_width = nat_new + charspacing * max(len(new_text) - 1, 0)
        except Exception:
            text_width = text_x1 - text_x0

        if align == fitz.TEXT_ALIGN_RIGHT:
            insert_x = text_x1 - text_width
        elif align == fitz.TEXT_ALIGN_CENTER:
            insert_x = (text_x0 + text_x1) / 2 - text_width / 2
        else:
            insert_x = text_x0

        x = insert_x
        for ch in new_text:
            pg.insert_text(
                fitz.Point(x, baseline_y),
                ch,
                fontname=active_fontname,
                fontsize=font_size,
                color=color,
                fill=color,
                render_mode=render_mode,
                border_width=stroke_width,
            )
            try:
                ch_w = (font_obj.text_length(ch, fontsize=font_size) if font_obj
                        else fitz.Font(fontname=fontname_fb).text_length(ch, fontsize=font_size))
            except Exception:
                ch_w = font_size * 0.5
            x += ch_w + charspacing

        doc.save(str(output), garbage=4, deflate=True)
    finally:
        doc.close()
