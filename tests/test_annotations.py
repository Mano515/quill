"""Tests for Phase 3 — annotations."""

from pathlib import Path

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate


def make_pdf(path: Path, pages: int = 3) -> Path:
    from reportlab.platypus import PageBreak

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    story = []
    for i in range(1, pages + 1):
        story.append(Paragraph(f"Page {i}", styles["Normal"]))
        if i < pages:
            story.append(PageBreak())
    doc.build(story)
    return path


@pytest.fixture()
def sample_pdf(tmp_path):
    return make_pdf(tmp_path / "sample.pdf")


def page_count(path: Path) -> int:
    from pypdf import PdfReader
    return len(PdfReader(path).pages)


def test_add_text(sample_pdf, tmp_path):
    from quill.features.annotations import add_text

    out = tmp_path / "text.pdf"
    add_text(sample_pdf, out, "Hello Quill", x=50, y=100, pages=[1])
    assert out.exists()
    assert page_count(out) == 3


def test_add_text_all_pages(sample_pdf, tmp_path):
    from quill.features.annotations import add_text

    out = tmp_path / "text_all.pdf"
    add_text(sample_pdf, out, "Draft", x=50, y=50)
    assert out.exists()
    assert page_count(out) == 3


def test_watermark_text(sample_pdf, tmp_path):
    from quill.features.annotations import add_watermark_text

    out = tmp_path / "wm.pdf"
    add_watermark_text(sample_pdf, out, "CONFIDENTIEL")
    assert out.exists()
    assert page_count(out) == 3


def test_watermark_image(sample_pdf, tmp_path):
    from quill.features.annotations import add_watermark_image
    from PIL import Image as PILImage

    img_path = tmp_path / "logo.png"
    img = PILImage.new("RGBA", (200, 100), color=(255, 0, 0, 128))
    img.save(img_path)

    out = tmp_path / "wm_img.pdf"
    add_watermark_image(sample_pdf, out, img_path)
    assert out.exists()
    assert page_count(out) == 3


def test_stamp(sample_pdf, tmp_path):
    from quill.features.annotations import add_stamp

    out = tmp_path / "stamp.pdf"
    add_stamp(sample_pdf, out, label="APPROUVÉ")
    assert out.exists()
    assert page_count(out) == 3


def test_add_image(sample_pdf, tmp_path):
    from quill.features.annotations import add_image
    from PIL import Image as PILImage

    img_path = tmp_path / "sig.png"
    PILImage.new("RGB", (100, 50), color=(0, 0, 255)).save(img_path)

    out = tmp_path / "with_img.pdf"
    add_image(sample_pdf, out, img_path, x=50, y=50, width=100, height=50, pages=[1])
    assert out.exists()


def test_page_numbers(sample_pdf, tmp_path):
    from quill.features.annotations import add_page_numbers

    out = tmp_path / "numbered.pdf"
    add_page_numbers(sample_pdf, out, position="bottom-center", prefix="Page ", start=1)
    assert out.exists()
    assert page_count(out) == 3


def test_comment(sample_pdf, tmp_path):
    from quill.features.annotations import add_comment

    out = tmp_path / "comment.pdf"
    add_comment(sample_pdf, out, text="À revoir", x=100, y=200, page=1, author="Alice")
    assert out.exists()
