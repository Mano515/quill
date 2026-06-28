"""
test_edit.py — Tests pour la fonctionnalité d'édition de texte PDF.

Couvre :
  • replace_text()  : remplacement de texte dans une bounding box
  • Validation des erreurs (page < 1, page hors limites)
  • Route API  POST /edit/replace-text
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _make_fitz_pdf(path: Path, text: str = "TEXTE ORIGINAL") -> Path:
    """Crée un PDF d'une page avec du texte inséré à coordonnées exactes."""
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(fitz.Point(100, 100), text, fontsize=14)
    doc.save(str(path))
    doc.close()
    return path


def _detect_bbox(path: Path, page: int = 1) -> tuple[float, float, float, float]:
    """Retourne la bounding box du premier span de texte trouvé sur la page."""
    import fitz

    doc = fitz.open(str(path))
    try:
        pg = doc[page - 1]
        for block in pg.get_text("dict")["blocks"]:
            if block.get("type") == 0:
                for line in block["lines"]:
                    for span in line["spans"]:
                        return tuple(span["bbox"])  # type: ignore[return-value]
    finally:
        doc.close()
    pytest.fail("Aucun texte détecté dans le PDF source.")


def _read_text(path: Path, page: int = 1) -> str:
    import fitz

    doc = fitz.open(str(path))
    try:
        return doc[page - 1].get_text()
    finally:
        doc.close()


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def source_pdf(tmp_path: Path) -> Path:
    return _make_fitz_pdf(tmp_path / "source.pdf", text="TEXTE ORIGINAL")


# ══════════════════════════════════════════════════════════════════════════════
# Tests fonctionnels — quill.features.edit
# ══════════════════════════════════════════════════════════════════════════════

def test_replace_text_creates_output(source_pdf: Path, tmp_path: Path, log_step) -> None:
    """Le fichier de sortie doit exister et ne pas être vide."""
    from quill.features.edit import replace_text

    log_step("Détection automatique de la bounding box du texte source")
    x0, y0, x1, y1 = _detect_bbox(source_pdf)

    log_step(f"Remplacement du texte  bbox=({x0:.0f},{y0:.0f},{x1:.0f},{y1:.0f})")
    out = tmp_path / "edited.pdf"
    replace_text(source_pdf, out, page=1, x0=x0 - 2, y0=y0 - 2, x1=x1 + 20, y1=y1 + 2, new_text="TEXTE REMPLACÉ")

    log_step("Vérification : fichier créé et non vide")
    assert out.exists(), "Le fichier de sortie n'a pas été créé"
    assert out.stat().st_size > 0, "Le fichier de sortie est vide"


def test_replace_text_new_content_present(source_pdf: Path, tmp_path: Path, log_step) -> None:
    """Le nouveau texte doit apparaître dans le document modifié."""
    from quill.features.edit import replace_text

    log_step("Localisation de la bbox du texte 'TEXTE ORIGINAL'")
    x0, y0, x1, y1 = _detect_bbox(source_pdf)

    log_step("Application du remplacement → 'REMPLACÉ'")
    out = tmp_path / "out.pdf"
    replace_text(source_pdf, out, page=1, x0=x0 - 2, y0=y0 - 2, x1=x1 + 40, y1=y1 + 2, new_text="REMPLACÉ")

    log_step("Lecture du texte du PDF résultant")
    result_text = _read_text(out)

    log_step("Vérification que 'REMPLACÉ' est bien dans le document")
    assert "REMPLACÉ" in result_text, f"Nouveau texte absent du document. Texte trouvé : {result_text!r}"


def test_replace_text_page_count_unchanged(source_pdf: Path, tmp_path: Path, log_step) -> None:
    """Le nombre de pages ne doit pas changer après remplacement."""
    import fitz
    from quill.features.edit import replace_text

    x0, y0, x1, y1 = _detect_bbox(source_pdf)

    log_step("Remplacement sur document 1 page")
    out = tmp_path / "out.pdf"
    replace_text(source_pdf, out, page=1, x0=x0, y0=y0, x1=x1 + 20, y1=y1, new_text="OK")

    log_step("Vérification que le nombre de pages = 1 (inchangé)")
    doc = fitz.open(str(out))
    n = len(doc)
    doc.close()
    assert n == 1, f"Nombre de pages attendu : 1, obtenu : {n}"


def test_replace_text_raises_on_page_zero(source_pdf: Path, tmp_path: Path, log_step) -> None:
    """page=0 doit lever ValueError (pages indexées à partir de 1)."""
    from quill.features.edit import replace_text

    log_step("Appel avec page=0 → doit lever ValueError")
    with pytest.raises(ValueError, match="page must be >= 1"):
        replace_text(source_pdf, tmp_path / "out.pdf", page=0, x0=0, y0=0, x1=100, y1=20, new_text="X")


def test_replace_text_raises_on_page_out_of_bounds(source_pdf: Path, tmp_path: Path, log_step) -> None:
    """page > nombre de pages doit lever ValueError."""
    from quill.features.edit import replace_text

    log_step("Appel avec page=99 sur un PDF d'1 page → doit lever ValueError")
    with pytest.raises(ValueError, match="exceeds document length"):
        replace_text(source_pdf, tmp_path / "out.pdf", page=99, x0=0, y0=0, x1=100, y1=20, new_text="X")


# ══════════════════════════════════════════════════════════════════════════════
# Tests API — POST /edit/replace-text
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def api_client():
    from starlette.testclient import TestClient
    from quill.api.app import app
    return TestClient(app)


@pytest.fixture(scope="module")
def api_auth():
    from quill.api.auth import API_KEY
    return {"X-API-Key": API_KEY}


def _make_fitz_pdf_bytes(text: str = "TEXTE API") -> bytes:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(fitz.Point(100, 100), text, fontsize=14)
    buf = BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def _detect_bbox_from_bytes(pdf_bytes: bytes) -> tuple[float, float, float, float]:
    import fitz

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        pg = doc[0]
        for block in pg.get_text("dict")["blocks"]:
            if block.get("type") == 0:
                for line in block["lines"]:
                    for span in line["spans"]:
                        return tuple(span["bbox"])  # type: ignore[return-value]
    finally:
        doc.close()
    return (95.0, 88.0, 200.0, 103.0)  # fallback


def test_api_edit_replace_text_ok(api_client, api_auth, log_step) -> None:
    """POST /edit/replace-text doit retourner 200 et un PDF valide."""
    log_step("Génération d'un PDF avec texte 'TEXTE API'")
    pdf = _make_fitz_pdf_bytes("TEXTE API")

    log_step("Détection de la bounding box du texte source")
    x0, y0, x1, y1 = _detect_bbox_from_bytes(pdf)

    log_step("Appel POST /edit/replace-text")
    r = api_client.post(
        "/edit/replace-text",
        headers=api_auth,
        files={"file": ("test.pdf", pdf, "application/pdf")},
        data={
            "page": "1",
            "x0": str(x0 - 2), "y0": str(y0 - 2),
            "x1": str(x1 + 40), "y1": str(y1 + 2),
            "new_text": "NOUVEAU TEXTE API",
        },
    )

    log_step("Vérification HTTP 200 + content-type application/pdf")
    assert r.status_code == 200, f"Statut inattendu : {r.status_code} — {r.text[:200]}"
    assert "application/pdf" in r.headers.get("content-type", "")

    log_step("Vérification que le PDF retourné contient 'NOUVEAU TEXTE API'")
    import fitz
    doc = fitz.open(stream=r.content, filetype="pdf")
    text = doc[0].get_text()
    doc.close()
    assert "NOUVEAU TEXTE API" in text, f"Texte absent du PDF retourné. Contenu : {text!r}"


def test_api_edit_replace_text_no_auth(api_client, log_step) -> None:
    """Sans clé API, /edit/replace-text doit retourner 401."""
    log_step("Appel sans header X-API-Key")
    r = api_client.post(
        "/edit/replace-text",
        files={"file": ("t.pdf", b"", "application/pdf")},
        data={"page": "1", "x0": "0", "y0": "0", "x1": "100", "y1": "20", "new_text": "X"},
    )

    log_step("Vérification du statut 401")
    assert r.status_code == 401, f"Statut attendu : 401, reçu : {r.status_code}"
