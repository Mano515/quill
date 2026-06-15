"""Phase 3 — Annotations, watermarks, stamps, images, page numbers."""

from pathlib import Path


def add_text(
    input: Path,
    output: Path,
    text: str,
    x: float,
    y: float,
    pages: list[int] | None = None,
    font_size: int = 12,
    color: tuple[float, float, float] = (0, 0, 0),
    font: str = "helv",
) -> None:
    """Overlay free text at (x, y) on specified pages (1-indexed, None = all)."""
    import fitz

    doc = fitz.open(str(input))
    target = set(pages) if pages else set(range(1, len(doc) + 1))

    for page_num in target:
        page = doc[page_num - 1]
        page.insert_text(
            fitz.Point(x, y),
            text,
            fontname=font,
            fontsize=font_size,
            color=color,
        )

    doc.save(str(output))
    doc.close()


def add_watermark_text(
    input: Path,
    output: Path,
    text: str,
    opacity: float = 0.15,
    font_size: int = 60,
    color: tuple[float, float, float] = (0.5, 0.5, 0.5),
    angle: float = 45.0,
) -> None:
    """Add a diagonal text watermark to every page."""
    import fitz

    doc = fitz.open(str(input))
    for page in doc:
        rect = page.rect
        pivot = fitz.Point(rect.width / 2, rect.height / 2)
        mat = fitz.Matrix(angle)  # rotation matrix from degrees
        page.insert_text(
            pivot,
            text,
            fontsize=font_size,
            color=color,
            morph=(pivot, mat),
            overlay=True,
        )
    doc.save(str(output))
    doc.close()


def add_watermark_image(
    input: Path,
    output: Path,
    image: Path,
    opacity: float = 0.2,
    pages: list[int] | None = None,
) -> None:
    """Overlay a semi-transparent image watermark on pages."""
    import fitz

    doc = fitz.open(str(input))
    target = set(pages) if pages else set(range(1, len(doc) + 1))

    for page_num in target:
        page = doc[page_num - 1]
        rect = page.rect
        img_rect = fitz.Rect(
            rect.width * 0.1,
            rect.height * 0.3,
            rect.width * 0.9,
            rect.height * 0.7,
        )
        page.insert_image(img_rect, filename=str(image))

    doc.save(str(output))
    doc.close()


def add_stamp(
    input: Path,
    output: Path,
    label: str = "CONFIDENTIEL",
    pages: list[int] | None = None,
    color: tuple[float, float, float] = (0.8, 0, 0),
    font_size: int = 48,
) -> None:
    """Add a bold stamp (CONFIDENTIEL, APPROUVÉ, BROUILLON…) to pages."""
    import fitz

    doc = fitz.open(str(input))
    target = set(pages) if pages else set(range(1, len(doc) + 1))

    for page_num in target:
        page = doc[page_num - 1]
        rect = page.rect
        tw = fitz.TextWriter(rect)
        font = fitz.Font("helv")
        # Measure text width to center it
        text_width = font.text_length(label, fontsize=font_size)
        x = (rect.width - text_width) / 2
        y = rect.height / 2
        tw.append(fitz.Point(x, y), label, font=font, fontsize=font_size)
        tw.write_text(page, color=color, opacity=0.6)

    doc.save(str(output))
    doc.close()


def add_image(
    input: Path,
    output: Path,
    image: Path,
    x: float,
    y: float,
    width: float,
    height: float,
    pages: list[int] | None = None,
) -> None:
    """Insert an image (logo, scanned signature…) at a given position."""
    import fitz

    doc = fitz.open(str(input))
    target = set(pages) if pages else set(range(1, len(doc) + 1))

    for page_num in target:
        page = doc[page_num - 1]
        page.insert_image(fitz.Rect(x, y, x + width, y + height), filename=str(image))

    doc.save(str(output))
    doc.close()


def add_page_numbers(
    input: Path,
    output: Path,
    position: str = "bottom-center",
    font_size: int = 10,
    prefix: str = "",
    suffix: str = "",
    start: int = 1,
    color: tuple[float, float, float] = (0, 0, 0),
) -> None:
    """
    Add page numbers to every page.
    position: 'bottom-center' | 'bottom-right' | 'bottom-left' | 'top-center' | 'top-right' | 'top-left'
    """
    import fitz

    doc = fitz.open(str(input))
    margin = 30

    for i, page in enumerate(doc):
        rect = page.rect
        label = f"{prefix}{i + start}{suffix}"
        font = fitz.Font("helv")
        text_width = font.text_length(label, fontsize=font_size)

        if "bottom" in position:
            y = rect.height - margin
        else:
            y = margin + font_size

        if "center" in position:
            x = (rect.width - text_width) / 2
        elif "right" in position:
            x = rect.width - margin - text_width
        else:
            x = margin

        page.insert_text(fitz.Point(x, y), label, fontsize=font_size, color=color)

    doc.save(str(output))
    doc.close()


def add_comment(
    input: Path,
    output: Path,
    text: str,
    x: float,
    y: float,
    page: int = 1,
    author: str = "Quill",
    color: tuple[float, float, float] = (1, 1, 0),
) -> None:
    """Add a sticky-note annotation on a page."""
    import fitz

    doc = fitz.open(str(input))
    p = doc[page - 1]
    annot = p.add_text_annot(fitz.Point(x, y), text, icon="Note")
    annot.set_info(title=author)
    annot.set_colors(stroke=color)
    annot.update()
    doc.save(str(output))
    doc.close()
