"""End-to-end tests for the FastAPI routes using TestClient."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate
from starlette.testclient import TestClient

from quill.api.app import app
from quill.api.auth import API_KEY


# ── Helpers ────────────────────────────────────────────────────────────────


def _make_pdf_bytes(pages: int = 3) -> bytes:
    buf = BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    story = []
    for i in range(1, pages + 1):
        story.append(Paragraph(f"Page {i}", styles["Title"]))
        if i < pages:
            story.append(PageBreak())
    doc.build(story)
    return buf.getvalue()


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
def auth() -> dict:
    return {"X-API-Key": API_KEY}


@pytest.fixture(scope="module")
def pdf_bytes() -> bytes:
    return _make_pdf_bytes(pages=3)


# ── Auth ───────────────────────────────────────────────────────────────────


def test_auth_missing_key(client):
    r = client.post("/basic/info", files={"file": ("x.pdf", b"", "application/pdf")})
    assert r.status_code == 401


def test_auth_wrong_key(client):
    r = client.post(
        "/basic/info",
        headers={"X-API-Key": "wrong"},
        files={"file": ("x.pdf", b"", "application/pdf")},
    )
    assert r.status_code == 401


def test_auth_login_ok(client):
    r = client.post("/auth/login", json={"key": API_KEY})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_auth_login_bad(client):
    r = client.post("/auth/login", json={"key": "bad"})
    assert r.status_code == 401


# ── Basic ──────────────────────────────────────────────────────────────────


def test_basic_info(client, auth, pdf_bytes):
    r = client.post("/basic/info", headers=auth, files={"file": ("s.pdf", pdf_bytes, "application/pdf")})
    assert r.status_code == 200
    data = r.json()
    assert data["page_count"] == 3
    assert data["encrypted"] is False


def test_basic_merge(client, auth, pdf_bytes):
    r = client.post(
        "/basic/merge",
        headers=auth,
        files=[
            ("files", ("a.pdf", pdf_bytes, "application/pdf")),
            ("files", ("b.pdf", _make_pdf_bytes(2), "application/pdf")),
        ],
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"


def test_basic_rotate(client, auth, pdf_bytes):
    r = client.post(
        "/basic/rotate",
        headers=auth,
        files={"file": ("s.pdf", pdf_bytes, "application/pdf")},
        data={"degrees": "90"},
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"


def test_basic_extract_text(client, auth, pdf_bytes):
    r = client.post(
        "/basic/extract-text",
        headers=auth,
        files={"file": ("s.pdf", pdf_bytes, "application/pdf")},
    )
    assert r.status_code == 200
    data = r.json()
    pages = data.get("pages", data)
    assert "1" in pages or 1 in pages


# ── Security ───────────────────────────────────────────────────────────────


def test_security_encrypt_decrypt(client, auth, pdf_bytes):
    # Encrypt
    r = client.post(
        "/security/encrypt",
        headers=auth,
        files={"file": ("s.pdf", pdf_bytes, "application/pdf")},
        data={"password": "secret"},
    )
    assert r.status_code == 200
    enc = r.content

    # Decrypt
    r2 = client.post(
        "/security/decrypt",
        headers=auth,
        files={"file": ("enc.pdf", enc, "application/pdf")},
        data={"password": "secret"},
    )
    assert r2.status_code == 200
    assert r2.headers["content-type"] == "application/pdf"


# ── Annotations ────────────────────────────────────────────────────────────


def test_annotations_watermark(client, auth, pdf_bytes):
    r = client.post(
        "/annotations/watermark",
        headers=auth,
        files={"file": ("s.pdf", pdf_bytes, "application/pdf")},
        data={"text": "TEST", "opacity": "0.1"},
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"


def test_annotations_stamp(client, auth, pdf_bytes):
    r = client.post(
        "/annotations/stamp",
        headers=auth,
        files={"file": ("s.pdf", pdf_bytes, "application/pdf")},
        data={"label": "DRAFT"},
    )
    assert r.status_code == 200


def test_annotations_add_text(client, auth, pdf_bytes):
    r = client.post(
        "/annotations/add-text",
        headers=auth,
        files={"file": ("s.pdf", pdf_bytes, "application/pdf")},
        data={"text": "Hello", "x": "50", "y": "100"},
    )
    assert r.status_code == 200


def test_annotations_page_numbers(client, auth, pdf_bytes):
    r = client.post(
        "/annotations/page-numbers",
        headers=auth,
        files={"file": ("s.pdf", pdf_bytes, "application/pdf")},
        data={"position": "bottom-center", "prefix": "Page "},
    )
    assert r.status_code == 200


def test_annotations_comment(client, auth, pdf_bytes):
    r = client.post(
        "/annotations/comment",
        headers=auth,
        files={"file": ("s.pdf", pdf_bytes, "application/pdf")},
        data={"text": "A note", "x": "50", "y": "50", "page": "1"},
    )
    assert r.status_code == 200


# ── Extraction ─────────────────────────────────────────────────────────────


def test_extraction_links(client, auth, pdf_bytes):
    r = client.post(
        "/extraction/links",
        headers=auth,
        files={"file": ("s.pdf", pdf_bytes, "application/pdf")},
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_extraction_language(client, auth, pdf_bytes):
    r = client.post(
        "/extraction/language",
        headers=auth,
        files={"file": ("s.pdf", pdf_bytes, "application/pdf")},
    )
    assert r.status_code == 200
    data = r.json()
    assert "language" in data


# ── Forms ──────────────────────────────────────────────────────────────────


def test_forms_create(client, auth):
    fields_json = '[{"name":"nom","type":"text","label":"Nom","x":50,"y":100},{"name":"email","type":"text","label":"Email","x":50,"y":140}]'
    r = client.post("/forms/create", headers=auth, data={"fields": fields_json})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"


def test_forms_list(client, auth, pdf_bytes):
    r = client.post("/forms/list", headers=auth, files={"file": ("s.pdf", pdf_bytes, "application/pdf")})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ── Convert ────────────────────────────────────────────────────────────────


def test_convert_to_json(client, auth, pdf_bytes):
    r = client.post(
        "/convert/to-json",
        headers=auth,
        files={"file": ("s.pdf", pdf_bytes, "application/pdf")},
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_convert_to_markdown(client, auth, pdf_bytes):
    r = client.post(
        "/convert/to-markdown",
        headers=auth,
        files={"file": ("s.pdf", pdf_bytes, "application/pdf")},
    )
    assert r.status_code == 200


# ── Signatures ─────────────────────────────────────────────────────────────


def test_sign_pdf(client, auth, pdf_bytes):
    r = client.post(
        "/sign/sign",
        headers=auth,
        files={"file": ("s.pdf", pdf_bytes, "application/pdf")},
        data={"name": "Alice Martin", "reason": "Approbation", "location": "Paris", "page": "1"},
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"


def test_sign_list(client, auth, pdf_bytes):
    r = client.post("/sign/list", headers=auth, files={"file": ("s.pdf", pdf_bytes, "application/pdf")})
    assert r.status_code == 200
    assert isinstance(r.json(), list)
