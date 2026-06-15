"""Tests for Phase 2 — security."""

from pathlib import Path

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate


def make_pdf(path: Path, pages: int = 2) -> Path:
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


def test_encrypt_decrypt(sample_pdf, tmp_path):
    from quill.features.security import encrypt, decrypt
    from pypdf import PdfReader

    enc = tmp_path / "enc.pdf"
    dec = tmp_path / "dec.pdf"

    encrypt(sample_pdf, enc, user_password="secret")
    assert PdfReader(enc).is_encrypted

    decrypt(enc, dec, password="secret")
    reader = PdfReader(dec)
    assert not reader.is_encrypted
    assert len(reader.pages) == 2


def test_decrypt_wrong_password(sample_pdf, tmp_path):
    from quill.features.security import encrypt, decrypt

    enc = tmp_path / "enc.pdf"
    encrypt(sample_pdf, enc, user_password="correct")

    with pytest.raises(ValueError, match="Wrong password"):
        decrypt(enc, tmp_path / "dec.pdf", password="wrong")


def test_check_security_unencrypted(sample_pdf):
    from quill.features.security import check_security

    info = check_security(sample_pdf)
    assert info["encrypted"] is False


def test_check_security_encrypted(sample_pdf, tmp_path):
    from quill.features.security import encrypt, check_security

    enc = tmp_path / "enc.pdf"
    encrypt(sample_pdf, enc, user_password="pass")

    info = check_security(enc, password="pass")
    assert info["encrypted"] is True
    assert info["password_valid"] is True

    info_bad = check_security(enc, password="bad")
    assert info_bad["password_valid"] is False
