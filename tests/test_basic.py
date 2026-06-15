"""Tests for Phase 1 basic operations."""

from pathlib import Path

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet


# ── Fixtures ───────────────────────────────────────────────────────────────


def make_pdf(path: Path, pages: int = 3, prefix: str = "Page") -> Path:
    """Helper: create a minimal PDF with N pages."""
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    story = []
    for i in range(1, pages + 1):
        story.append(Paragraph(f"{prefix} {i}", styles["Title"]))
        if i < pages:
            from reportlab.platypus import PageBreak
            story.append(PageBreak())
    doc.build(story)
    return path


@pytest.fixture()
def sample_pdf(tmp_path: Path) -> Path:
    return make_pdf(tmp_path / "sample.pdf", pages=5)


@pytest.fixture()
def two_pdfs(tmp_path: Path) -> tuple[Path, Path]:
    a = make_pdf(tmp_path / "a.pdf", pages=2, prefix="A")
    b = make_pdf(tmp_path / "b.pdf", pages=3, prefix="B")
    return a, b


# ── Tests ──────────────────────────────────────────────────────────────────


def test_merge(two_pdfs, tmp_path):
    from quill.features.basic import merge
    from pypdf import PdfReader

    a, b = two_pdfs
    out = tmp_path / "merged.pdf"
    merge([a, b], out)

    assert out.exists()
    assert len(PdfReader(out).pages) == 5


def test_split_all_pages(sample_pdf, tmp_path):
    from quill.features.basic import split
    from pypdf import PdfReader

    out_dir = tmp_path / "split"
    results = split(sample_pdf, out_dir)

    assert len(results) == 5
    for r in results:
        assert r.exists()
        assert len(PdfReader(r).pages) == 1


def test_split_ranges(sample_pdf, tmp_path):
    from quill.features.basic import split
    from pypdf import PdfReader

    out_dir = tmp_path / "split_ranges"
    results = split(sample_pdf, out_dir, ranges=[(1, 2), (4, 5)])

    assert len(results) == 2
    assert len(PdfReader(results[0]).pages) == 2
    assert len(PdfReader(results[1]).pages) == 2


def test_rotate(sample_pdf, tmp_path):
    from quill.features.basic import rotate
    from pypdf import PdfReader

    out = tmp_path / "rotated.pdf"
    rotate(sample_pdf, out, degrees=90, pages=[1, 3])

    assert out.exists()
    reader = PdfReader(out)
    assert len(reader.pages) == 5


def test_reorder(sample_pdf, tmp_path):
    from quill.features.basic import reorder
    from pypdf import PdfReader

    out = tmp_path / "reordered.pdf"
    reorder(sample_pdf, out, order=[5, 4, 3, 2, 1])

    assert out.exists()
    assert len(PdfReader(out).pages) == 5


def test_delete_pages(sample_pdf, tmp_path):
    from quill.features.basic import delete_pages
    from pypdf import PdfReader

    out = tmp_path / "deleted.pdf"
    delete_pages(sample_pdf, out, pages=[2, 4])

    assert out.exists()
    assert len(PdfReader(out).pages) == 3


def test_extract_text(sample_pdf):
    from quill.features.basic import extract_text

    result = extract_text(sample_pdf)
    assert len(result) == 5
    for page_num, text in result.items():
        assert isinstance(text, str)


def test_extract_text_specific_pages(sample_pdf):
    from quill.features.basic import extract_text

    result = extract_text(sample_pdf, pages=[1, 3])
    assert set(result.keys()) == {1, 3}


def test_get_metadata(sample_pdf):
    from quill.features.basic import get_metadata

    meta = get_metadata(sample_pdf)
    assert meta["page_count"] == 5
    assert meta["encrypted"] is False


def test_create_from_text(tmp_path):
    from quill.features.basic import create_from_text
    from pypdf import PdfReader

    out = tmp_path / "created.pdf"
    create_from_text("Hello\nWorld\nLine 3", out, title="Test Doc")

    assert out.exists()
    reader = PdfReader(out)
    assert len(reader.pages) >= 1
