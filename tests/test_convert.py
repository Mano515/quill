"""Tests for Phase 7 — conversions."""

from pathlib import Path

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate


def make_pdf(path: Path, pages: int = 2) -> Path:
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    story = []
    for i in range(1, pages + 1):
        story.append(Paragraph(f"Page {i} — Hello Quill", styles["Normal"]))
        if i < pages:
            story.append(PageBreak())
    doc.build(story)
    return path


@pytest.fixture()
def sample_pdf(tmp_path):
    return make_pdf(tmp_path / "sample.pdf", pages=3)


# ── PDF → images ───────────────────────────────────────────────────────────


def test_pdf_to_png(sample_pdf, tmp_path):
    from quill.features.convert import pdf_to_png

    out_dir = tmp_path / "pngs"
    saved = pdf_to_png(sample_pdf, out_dir, dpi=72)
    assert len(saved) == 3
    assert all(p.exists() and p.suffix == ".png" for p in saved)


def test_pdf_to_jpg(sample_pdf, tmp_path):
    from quill.features.convert import pdf_to_jpg

    out_dir = tmp_path / "jpgs"
    saved = pdf_to_jpg(sample_pdf, out_dir, dpi=72)
    assert len(saved) == 3
    assert all(p.exists() and p.suffix == ".jpg" for p in saved)


# ── images → PDF ───────────────────────────────────────────────────────────


def test_images_to_pdf(tmp_path):
    from quill.features.convert import images_to_pdf, pdf_to_png
    from pypdf import PdfReader

    src = make_pdf(tmp_path / "src.pdf", pages=2)
    images = pdf_to_png(src, tmp_path / "imgs", dpi=72)

    out = tmp_path / "from_images.pdf"
    images_to_pdf(images, out)
    assert out.exists()
    assert len(PdfReader(out).pages) == 2


# ── PDF → Markdown ─────────────────────────────────────────────────────────


def test_pdf_to_markdown_returns_string(sample_pdf):
    from quill.features.convert import pdf_to_markdown

    md = pdf_to_markdown(sample_pdf)
    assert isinstance(md, str)
    assert len(md) > 0


def test_pdf_to_markdown_saves_file(sample_pdf, tmp_path):
    from quill.features.convert import pdf_to_markdown

    out = tmp_path / "doc.md"
    pdf_to_markdown(sample_pdf, out)
    assert out.exists()
    assert out.read_text(encoding="utf-8").strip() != ""


# ── PDF → JSON ─────────────────────────────────────────────────────────────


def test_pdf_to_json_structure(sample_pdf):
    from quill.features.convert import pdf_to_json

    result = pdf_to_json(sample_pdf)
    assert len(result) == 3
    assert result[0]["page"] == 1
    assert "words" in result[0]
    assert isinstance(result[0]["words"], list)


def test_pdf_to_json_saves_file(sample_pdf, tmp_path):
    import json
    from quill.features.convert import pdf_to_json

    out = tmp_path / "doc.json"
    pdf_to_json(sample_pdf, out)
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, list)


def test_pdf_to_json_specific_pages(sample_pdf):
    from quill.features.convert import pdf_to_json

    result = pdf_to_json(sample_pdf, pages=[1, 3])
    assert len(result) == 2
    assert {r["page"] for r in result} == {1, 3}


# ── LibreOffice conversions (skipped if not installed) ─────────────────────


def libreoffice_available() -> bool:
    import shutil
    return shutil.which("soffice") is not None


requires_lo = pytest.mark.skipif(not libreoffice_available(), reason="LibreOffice not installed")


@requires_lo
def test_word_to_pdf(tmp_path):
    from quill.features.convert import word_to_pdf
    from docx import Document

    docx_path = tmp_path / "test.docx"
    doc = Document()
    doc.add_paragraph("Hello from Quill")
    doc.save(docx_path)

    out = tmp_path / "output.pdf"
    word_to_pdf(docx_path, out)
    assert out.exists()
