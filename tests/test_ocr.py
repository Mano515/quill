"""Tests for Phase 5 — OCR.

These tests require: tesseract, poppler (for pdf2image), Pillow.
Skipped automatically if tesseract is not installed.
"""

from pathlib import Path

import pytest


def tesseract_available() -> bool:
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def poppler_available() -> bool:
    try:
        from pdf2image import convert_from_path
        return True
    except ImportError:
        return False


requires_ocr = pytest.mark.skipif(
    not tesseract_available() or not poppler_available(),
    reason="tesseract or poppler not installed",
)


def make_image_pdf(path: Path, text: str = "Hello OCR") -> Path:
    """Create a PDF that looks like a scanned image (rendered text as image)."""
    from PIL import Image, ImageDraw, ImageFont
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate
    from reportlab.platypus import Image as RLImage
    import tempfile

    # Draw text onto an image
    img = Image.new("RGB", (800, 1000), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((50, 100), text, fill=(0, 0, 0))

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img_path = Path(f.name)
    img.save(img_path)

    doc = SimpleDocTemplate(str(path), pagesize=A4)
    doc.build([RLImage(str(img_path), width=400, height=500)])
    img_path.unlink(missing_ok=True)
    return path


@pytest.fixture()
def image_pdf(tmp_path):
    return make_image_pdf(tmp_path / "scan.pdf", text="Hello OCR test")


@requires_ocr
def test_pdf_to_images(image_pdf, tmp_path):
    from quill.features.ocr import pdf_to_images

    out_dir = tmp_path / "pages"
    saved = pdf_to_images(image_pdf, out_dir, dpi=72)
    assert len(saved) >= 1
    assert all(p.exists() for p in saved)


@requires_ocr
def test_ocr_pdf_produces_output(image_pdf, tmp_path):
    from quill.features.ocr import ocr_pdf

    out = tmp_path / "searchable.pdf"
    text = ocr_pdf(image_pdf, out, lang="eng", dpi=72)
    assert out.exists()
    assert isinstance(text, str)


@requires_ocr
def test_ocr_pdf_extracts_text(image_pdf, tmp_path):
    from quill.features.ocr import ocr_pdf

    out = tmp_path / "searchable.pdf"
    text = ocr_pdf(image_pdf, out, lang="eng", dpi=150)
    # Tesseract should find at least some of "Hello OCR test"
    assert any(word in text.lower() for word in ["hello", "ocr", "test"])
