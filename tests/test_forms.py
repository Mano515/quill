"""Tests for Phase 6 — forms."""

from pathlib import Path

import pytest


def make_form_pdf(path: Path) -> Path:
    """Create a PDF with two text form fields using reportlab."""
    from reportlab.lib.colors import black, white
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Helvetica", 12)
    c.drawString(50, 750, "Name:")
    c.acroForm.textfield(
        name="name",
        tooltip="Your name",
        x=50, y=720, width=200, height=20,
        borderColor=black,
        fillColor=white,
        textColor=black,
        forceBorder=True,
    )
    c.drawString(50, 690, "Email:")
    c.acroForm.textfield(
        name="email",
        tooltip="Your email",
        x=50, y=660, width=200, height=20,
        borderColor=black,
        fillColor=white,
        textColor=black,
        forceBorder=True,
    )
    c.save()
    return path


@pytest.fixture()
def form_pdf(tmp_path):
    return make_form_pdf(tmp_path / "form.pdf")


def test_list_fields(form_pdf):
    from quill.features.forms import list_fields

    fields = list_fields(form_pdf)
    assert len(fields) == 2
    names = {f["name"] for f in fields}
    assert "name" in names
    assert "email" in names


def test_fill_form(form_pdf, tmp_path):
    from quill.features.forms import fill_form, list_fields

    out = tmp_path / "filled.pdf"
    fill_form(form_pdf, out, {"name": "Alice", "email": "alice@example.com"})
    assert out.exists()

    fields = list_fields(out)
    values = {f["name"]: f["value"] for f in fields}
    assert values.get("name") == "Alice"
    assert values.get("email") == "alice@example.com"


def test_flatten_form(form_pdf, tmp_path):
    from quill.features.forms import flatten_form, list_fields

    out = tmp_path / "flat.pdf"
    flatten_form(form_pdf, out)
    assert out.exists()

    # After flattening, no editable fields remain
    fields = list_fields(out)
    assert fields == []


def test_create_form(tmp_path):
    from quill.features.forms import create_form, list_fields

    fields = [
        {"name": "first_name", "type": "text", "label": "First Name", "x": 50, "y": 100, "width": 200, "height": 24},
        {"name": "subscribe", "type": "checkbox", "label": "Subscribe", "x": 50, "y": 150, "width": 20, "height": 20},
    ]
    out = tmp_path / "new_form.pdf"
    create_form(out, fields)
    assert out.exists()

    listed = list_fields(out)
    names = {f["name"] for f in listed}
    assert "first_name" in names
    assert "subscribe" in names
