"""Tests for Phase 8: PDF signatures."""

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
        story.append(Paragraph(f"Page {i}", styles["Title"]))
        if i < pages:
            story.append(PageBreak())
    doc.build(story)
    return path


@pytest.fixture()
def sample_pdf(tmp_path: Path) -> Path:
    return make_pdf(tmp_path / "sample.pdf", pages=2)


def test_sign_creates_output(sample_pdf, tmp_path):
    from quill.features.sign import sign_pdf

    out = tmp_path / "signed.pdf"
    sign_pdf(sample_pdf, out, name="Alice Martin", reason="Approbation", location="Paris")
    assert out.exists()
    assert out.stat().st_size > 0


def test_sign_page_count_unchanged(sample_pdf, tmp_path):
    from pypdf import PdfReader

    from quill.features.sign import sign_pdf

    out = tmp_path / "signed.pdf"
    sign_pdf(sample_pdf, out, name="Bob")
    assert len(PdfReader(out).pages) == 2


def test_sign_target_page(sample_pdf, tmp_path):
    from quill.features.sign import sign_pdf

    out = tmp_path / "signed_p2.pdf"
    sign_pdf(sample_pdf, out, name="Carol", page=2)
    assert out.exists()


def test_list_signatures_empty(sample_pdf):
    from quill.features.sign import list_signatures

    result = list_signatures(sample_pdf)
    assert isinstance(result, list)
