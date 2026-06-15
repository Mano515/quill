"""Tests for Phase 4 — advanced extraction."""

from pathlib import Path

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Table, TableStyle


def make_pdf_with_table(path: Path) -> Path:
    from reportlab.lib import colors

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    data = [["Name", "Age", "City"], ["Alice", "30", "Paris"], ["Bob", "25", "Lyon"]]
    t = Table(data)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)]))
    doc.build([t])
    return path


def make_pdf_with_text(path: Path, text: str, pages: int = 2) -> Path:
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=A4)
    story = []
    for i in range(pages):
        story.append(Paragraph(text, styles["Normal"]))
        if i < pages - 1:
            story.append(PageBreak())
    doc.build(story)
    return path


def make_pdf_with_image(path: Path, img_path: Path) -> Path:
    from reportlab.platypus import Image as RLImage

    doc = SimpleDocTemplate(str(path), pagesize=A4)
    doc.build([RLImage(str(img_path), width=100, height=100)])
    return path


@pytest.fixture()
def table_pdf(tmp_path):
    return make_pdf_with_table(tmp_path / "tables.pdf")


@pytest.fixture()
def text_pdf(tmp_path):
    return make_pdf_with_text(tmp_path / "text.pdf", "Bonjour le monde, ceci est un test en français.")


@pytest.fixture()
def image_pdf(tmp_path):
    from PIL import Image as PILImage

    img = tmp_path / "logo.png"
    PILImage.new("RGB", (100, 100), color=(0, 128, 255)).save(img)
    return make_pdf_with_image(tmp_path / "images.pdf", img)


# ── Tests ──────────────────────────────────────────────────────────────────


def test_extract_tables_returns_data(table_pdf):
    from quill.features.extraction import extract_tables

    results = extract_tables(table_pdf)
    assert len(results) >= 1
    assert results[0]["page"] == 1
    assert len(results[0]["data"]) >= 2


def test_extract_tables_to_csv(table_pdf, tmp_path):
    from quill.features.extraction import extract_tables

    out = tmp_path / "table.csv"
    results = extract_tables(table_pdf, output=out, fmt="csv")
    assert len(results) >= 1
    # CSV files are created with suffix
    csv_files = list(tmp_path.glob("*.csv"))
    assert len(csv_files) >= 1


def test_extract_tables_to_excel(table_pdf, tmp_path):
    from quill.features.extraction import extract_tables

    out = tmp_path / "table.xlsx"
    results = extract_tables(table_pdf, output=out, fmt="excel")
    assert out.exists()


def test_extract_images(image_pdf, tmp_path):
    from quill.features.extraction import extract_images

    out_dir = tmp_path / "imgs"
    saved = extract_images(image_pdf, out_dir)
    assert len(saved) >= 1
    assert all(p.exists() for p in saved)


def test_extract_links_no_links(text_pdf):
    from quill.features.extraction import extract_links

    links = extract_links(text_pdf)
    assert isinstance(links, list)


def test_extract_form_fields_no_fields(text_pdf):
    from quill.features.extraction import extract_form_fields

    fields = extract_form_fields(text_pdf)
    assert fields == []


def test_extract_layout(text_pdf):
    from quill.features.extraction import extract_layout

    words = extract_layout(text_pdf)
    assert len(words) > 0
    assert "text" in words[0]
    assert "x0" in words[0]
    assert "font" in words[0]


def test_detect_language(text_pdf):
    from quill.features.extraction import detect_language

    result = detect_language(text_pdf)
    assert "language" in result
    assert "confidence" in result
    assert isinstance(result["per_page"], dict)
    assert result["language"] in ("fr", "en", "unknown")
