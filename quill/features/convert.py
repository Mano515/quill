"""Phase 7 — Conversions: PDF↔images, PDF→Markdown, PDF→JSON, images→PDF."""

from pathlib import Path


def pdf_to_png(input: Path, output_dir: Path, dpi: int = 150) -> list[Path]:
    """Convert each page of a PDF to a PNG image."""
    import fitz

    output_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(input))
    saved: list[Path] = []
    mat = fitz.Matrix(dpi / 72, dpi / 72)

    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=mat)
        out = output_dir / f"page_{i + 1:04d}.png"
        pix.save(str(out))
        saved.append(out)

    doc.close()
    return saved


def pdf_to_jpg(input: Path, output_dir: Path, dpi: int = 150, quality: int = 85) -> list[Path]:
    """Convert each page of a PDF to a JPEG image."""
    import fitz

    output_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(input))
    saved: list[Path] = []
    mat = fitz.Matrix(dpi / 72, dpi / 72)

    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=mat)
        out = output_dir / f"page_{i + 1:04d}.jpg"
        # pymupdf can save jpg directly
        pix.save(str(out), jpg_quality=quality)
        saved.append(out)

    doc.close()
    return saved


def images_to_pdf(images: list[Path], output: Path) -> None:
    """Combine a list of images into a single PDF, one image per page."""
    import fitz
    from PIL import Image

    doc = fitz.open()
    for img_path in images:
        # Open with PIL to get dimensions
        with Image.open(img_path) as im:
            w, h = im.size
        # Points: 1px = 0.75pt at 96 dpi — use actual pixel size
        page = doc.new_page(width=w, height=h)
        page.insert_image(page.rect, filename=str(img_path))

    doc.save(str(output))
    doc.close()


def pdf_to_markdown(input: Path, output: Path | None = None) -> str:
    """
    Convert a PDF to Markdown, preserving headings and structure where possible.
    Uses pymupdf4llm if available, falls back to pdfplumber plain text.
    """
    try:
        import pymupdf4llm
        md = pymupdf4llm.to_markdown(str(input))
    except ImportError:
        import pdfplumber
        lines = []
        with pdfplumber.open(input) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                lines.append(f"## Page {i}\n")
                text = page.extract_text() or ""
                lines.append(text)
                lines.append("")
        md = "\n".join(lines)

    if output:
        output.write_text(md, encoding="utf-8")
    return md


def pdf_to_json(input: Path, output: Path | None = None, pages: list[int] | None = None) -> list[dict]:
    """
    Convert PDF text content to structured JSON.
    Returns list of {page, words: [{text, x0, y0, x1, y1, size, font}]}.
    """
    import json
    import pdfplumber

    result = []
    with pdfplumber.open(input) as pdf:
        target = set(pages) if pages else set(range(1, len(pdf.pages) + 1))
        for page_num in target:
            page = pdf.pages[page_num - 1]
            words = page.extract_words(extra_attrs=["size", "fontname"])
            result.append({
                "page": page_num,
                "width": page.width,
                "height": page.height,
                "words": [
                    {
                        "text": w["text"],
                        "x0": round(w["x0"], 2),
                        "y0": round(w["top"], 2),
                        "x1": round(w["x1"], 2),
                        "y1": round(w["bottom"], 2),
                        "size": round(w.get("size") or 0, 2),
                        "font": w.get("fontname"),
                    }
                    for w in words
                ],
            })

    if output:
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def word_to_pdf(input: Path, output: Path) -> None:
    """Convert a .docx file to PDF using LibreOffice headless."""
    import subprocess

    result = subprocess.run(
        ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(output.parent), str(input)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"LibreOffice conversion failed: {result.stderr}")

    # LibreOffice names the output <stem>.pdf
    generated = output.parent / f"{input.stem}.pdf"
    if generated != output:
        generated.rename(output)


def pdf_to_word(input: Path, output: Path) -> None:
    """Convert a PDF to .docx using LibreOffice headless."""
    import subprocess

    result = subprocess.run(
        ["soffice", "--headless", "--convert-to", "docx", "--outdir", str(output.parent), str(input)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"LibreOffice conversion failed: {result.stderr}")

    generated = output.parent / f"{input.stem}.docx"
    if generated != output:
        generated.rename(output)
