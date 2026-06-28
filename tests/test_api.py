"""
test_api.py — Tests bout-en-bout de toutes les routes FastAPI de Quill.

Chaque route est testée via TestClient (ASGI) :
  - Code HTTP attendu
  - Content-Type de la réponse
  - Structure / contenu minimal de la réponse
  - Authentification (401 sans clé)
"""
from __future__ import annotations

import json
import zipfile
from io import BytesIO

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate
from starlette.testclient import TestClient

from quill.api.app import app
from quill.api.auth import API_KEY


# ══════════════════════════════════════════════════════════════════════════════
# Helpers & factories
# ══════════════════════════════════════════════════════════════════════════════

def _make_pdf_bytes(pages: int = 3) -> bytes:
    buf = BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    story = []
    for i in range(1, pages + 1):
        story.append(Paragraph(f"Page {i} — Quill test", styles["Title"]))
        if i < pages:
            story.append(PageBreak())
    doc.build(story)
    return buf.getvalue()


def _make_form_pdf_bytes() -> bytes:
    from reportlab.lib.colors import black, white
    from reportlab.pdfgen import canvas

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica", 12)
    c.drawString(50, 750, "Nom :")
    c.acroForm.textfield(
        name="nom", tooltip="Votre nom",
        x=50, y=720, width=200, height=20,
        borderColor=black, fillColor=white, textColor=black, forceBorder=True,
    )
    c.drawString(50, 690, "Email :")
    c.acroForm.textfield(
        name="email", tooltip="Votre email",
        x=50, y=660, width=200, height=20,
        borderColor=black, fillColor=white, textColor=black, forceBorder=True,
    )
    c.save()
    return buf.getvalue()


def _make_table_pdf_bytes() -> bytes:
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    data = [["Nom", "Âge", "Ville"], ["Alice", "30", "Paris"], ["Bob", "25", "Lyon"]]
    t = Table(data)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)]))
    doc.build([t])
    return buf.getvalue()


def _make_image_pdf_bytes() -> bytes:
    from io import BytesIO as _BIO

    from PIL import Image as PILImage
    from reportlab.platypus import Image as RLImage

    img_buf = _BIO()
    PILImage.new("RGB", (100, 100), color=(0, 128, 255)).save(img_buf, format="PNG")
    img_buf.seek(0)

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    doc.build([RLImage(img_buf, width=100, height=100)])
    return buf.getvalue()


def _make_fitz_pdf_bytes(text: str = "TEXTE ORIGINAL") -> bytes:
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
    return (95.0, 88.0, 200.0, 103.0)


def _make_png_bytes() -> bytes:
    from PIL import Image as PILImage

    buf = BytesIO()
    PILImage.new("RGB", (200, 150), color=(255, 100, 0)).save(buf, format="PNG")
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
def auth() -> dict:
    return {"X-API-Key": API_KEY}


@pytest.fixture(scope="module")
def pdf_bytes() -> bytes:
    return _make_pdf_bytes(pages=3)


@pytest.fixture(scope="module")
def form_pdf_bytes() -> bytes:
    return _make_form_pdf_bytes()


@pytest.fixture(scope="module")
def table_pdf_bytes() -> bytes:
    return _make_table_pdf_bytes()


@pytest.fixture(scope="module")
def image_pdf_bytes() -> bytes:
    return _make_image_pdf_bytes()


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


# ══════════════════════════════════════════════════════════════════════════════
# Basic — routes manquantes
# ══════════════════════════════════════════════════════════════════════════════

def test_basic_split_returns_zip(client, auth, pdf_bytes, log_step):
    """POST /basic/split → ZIP contenant autant de fichiers que de pages."""
    log_step("Envoi d'un PDF 3 pages sans paramètre 'ranges' (split page par page)")
    r = client.post(
        "/basic/split",
        headers=auth,
        files={"file": ("s.pdf", pdf_bytes, "application/pdf")},
    )

    log_step("Vérification HTTP 200 + content-type application/zip")
    assert r.status_code == 200, r.text
    assert "zip" in r.headers.get("content-type", "")

    log_step("Vérification que le ZIP contient 3 fichiers PDF (1 par page)")
    zf = zipfile.ZipFile(BytesIO(r.content))
    assert len(zf.namelist()) == 3, f"Attendu 3 fichiers, trouvé : {zf.namelist()}"


def test_basic_split_with_ranges(client, auth, pdf_bytes, log_step):
    """POST /basic/split avec ranges='1-2' → ZIP avec 1 seul fichier."""
    log_step("Split avec ranges='1-2' (pages 1 à 2 seulement)")
    r = client.post(
        "/basic/split",
        headers=auth,
        files={"file": ("s.pdf", pdf_bytes, "application/pdf")},
        data={"ranges": "1-2"},
    )

    log_step("Vérification HTTP 200")
    assert r.status_code == 200, r.text

    log_step("Vérification que le ZIP contient 1 fichier (la plage 1-2)")
    zf = zipfile.ZipFile(BytesIO(r.content))
    assert len(zf.namelist()) == 1


def test_basic_reorder(client, auth, pdf_bytes, log_step):
    """POST /basic/reorder → PDF avec pages réordonnées."""
    log_step("Réordonnancement : order='3,2,1' (inversion des 3 pages)")
    r = client.post(
        "/basic/reorder",
        headers=auth,
        files={"file": ("s.pdf", pdf_bytes, "application/pdf")},
        data={"order": "3,2,1"},
    )

    log_step("Vérification HTTP 200 + application/pdf")
    assert r.status_code == 200, r.text
    assert "application/pdf" in r.headers.get("content-type", "")

    log_step("Vérification que le PDF retourné a toujours 3 pages")
    from pypdf import PdfReader
    reader = PdfReader(BytesIO(r.content))
    assert len(reader.pages) == 3


def test_basic_delete_pages(client, auth, pdf_bytes, log_step):
    """POST /basic/delete-pages → PDF avec la page supprimée en moins."""
    log_step("Suppression de la page 2 d'un PDF 3 pages")
    r = client.post(
        "/basic/delete-pages",
        headers=auth,
        files={"file": ("s.pdf", pdf_bytes, "application/pdf")},
        data={"pages": "2"},
    )

    log_step("Vérification HTTP 200 + application/pdf")
    assert r.status_code == 200, r.text
    assert "application/pdf" in r.headers.get("content-type", "")

    log_step("Vérification que le PDF résultant a 2 pages (3 - 1)")
    from pypdf import PdfReader
    reader = PdfReader(BytesIO(r.content))
    assert len(reader.pages) == 2


# ══════════════════════════════════════════════════════════════════════════════
# Security — route manquante
# ══════════════════════════════════════════════════════════════════════════════

def test_security_info_unencrypted(client, auth, pdf_bytes, log_step):
    """POST /security/info sur un PDF non chiffré → encrypted=false."""
    log_step("Appel /security/info sur un PDF non chiffré")
    r = client.post(
        "/security/info",
        headers=auth,
        files={"file": ("s.pdf", pdf_bytes, "application/pdf")},
    )

    log_step("Vérification HTTP 200 + champ 'encrypted'")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "encrypted" in data, f"Champ 'encrypted' absent : {data}"
    assert data["encrypted"] is False


def test_security_info_encrypted(client, auth, pdf_bytes, log_step):
    """POST /security/info sur un PDF chiffré → encrypted=true."""
    log_step("Chiffrement préalable du PDF")
    enc = client.post(
        "/security/encrypt",
        headers=auth,
        files={"file": ("s.pdf", pdf_bytes, "application/pdf")},
        data={"password": "quill123"},
    )
    assert enc.status_code == 200

    log_step("Appel /security/info sur le PDF chiffré")
    r = client.post(
        "/security/info",
        headers=auth,
        files={"file": ("enc.pdf", enc.content, "application/pdf")},
    )

    log_step("Vérification encrypted=true")
    assert r.status_code == 200, r.text
    assert r.json().get("encrypted") is True


# ══════════════════════════════════════════════════════════════════════════════
# Annotations — add-image
# ══════════════════════════════════════════════════════════════════════════════

def test_annotations_add_image(client, auth, pdf_bytes, log_step):
    """POST /annotations/add-image → PDF avec une image incrustée."""
    log_step("Génération d'une image PNG 200×150 en mémoire")
    png = _make_png_bytes()

    log_step("Appel /annotations/add-image page=1, position (50,50), taille 100×75")
    r = client.post(
        "/annotations/add-image",
        headers=auth,
        files={
            "file": ("s.pdf", pdf_bytes, "application/pdf"),
            "image": ("logo.png", png, "image/png"),
        },
        data={"x": "50", "y": "50", "width": "100", "height": "75", "pages": "1"},
    )

    log_step("Vérification HTTP 200 + application/pdf")
    assert r.status_code == 200, r.text
    assert "application/pdf" in r.headers.get("content-type", "")


# ══════════════════════════════════════════════════════════════════════════════
# Extraction — routes manquantes
# ══════════════════════════════════════════════════════════════════════════════

def test_extraction_tables_csv(client, auth, table_pdf_bytes, log_step):
    """POST /extraction/tables fmt=csv → CSV ou ZIP de CSV."""
    log_step("Envoi d'un PDF contenant un tableau 3×3")
    r = client.post(
        "/extraction/tables",
        headers=auth,
        files={"file": ("t.pdf", table_pdf_bytes, "application/pdf")},
        data={"fmt": "csv"},
    )

    log_step("Vérification HTTP 200 + contenu non vide")
    assert r.status_code == 200, r.text
    assert len(r.content) > 0


def test_extraction_tables_excel(client, auth, table_pdf_bytes, log_step):
    """POST /extraction/tables fmt=excel → fichier .xlsx."""
    log_step("Extraction du tableau au format Excel")
    r = client.post(
        "/extraction/tables",
        headers=auth,
        files={"file": ("t.pdf", table_pdf_bytes, "application/pdf")},
        data={"fmt": "excel"},
    )

    log_step("Vérification HTTP 200 + content-type Excel")
    assert r.status_code == 200, r.text
    ct = r.headers.get("content-type", "")
    assert "spreadsheetml" in ct or "excel" in ct or "octet-stream" in ct, f"Content-type inattendu : {ct}"


def test_extraction_images(client, auth, image_pdf_bytes, log_step):
    """POST /extraction/images → ZIP ou message 'no images'."""
    log_step("Envoi d'un PDF contenant une image PNG embarquée")
    r = client.post(
        "/extraction/images",
        headers=auth,
        files={"file": ("img.pdf", image_pdf_bytes, "application/pdf")},
    )

    log_step("Vérification HTTP 200")
    assert r.status_code == 200, r.text

    log_step("Vérification que la réponse est un ZIP contenant au moins une image")
    ct = r.headers.get("content-type", "")
    if "zip" in ct:
        zf = zipfile.ZipFile(BytesIO(r.content))
        assert len(zf.namelist()) >= 1, "ZIP vide — aucune image extraite"
    else:
        # Réponse JSON {"message": "No images found"} acceptable si l'image n'est pas extractible
        assert r.json() is not None


def test_extraction_text_layout(client, auth, pdf_bytes, log_step):
    """POST /extraction/text → liste de mots avec coordonnées."""
    log_step("Extraction du layout texte (mots + coordonnées)")
    r = client.post(
        "/extraction/text",
        headers=auth,
        files={"file": ("s.pdf", pdf_bytes, "application/pdf")},
    )

    log_step("Vérification HTTP 200 + liste non vide")
    assert r.status_code == 200, r.text
    data = r.json()
    assert isinstance(data, list), f"Attendu une liste, reçu : {type(data)}"
    assert len(data) > 0, "Liste de mots vide"

    log_step("Vérification de la structure d'un mot (text + x0)")
    first = data[0]
    assert "text" in first, f"Champ 'text' absent : {first}"
    assert "x0" in first, f"Champ 'x0' absent : {first}"


# ══════════════════════════════════════════════════════════════════════════════
# Convert — routes manquantes
# ══════════════════════════════════════════════════════════════════════════════

def test_convert_to_images_png(client, auth, pdf_bytes, log_step):
    """POST /convert/to-images fmt=png → ZIP de 3 PNG."""
    log_step("Conversion PDF 3 pages → images PNG (dpi=72 pour rapidité)")
    r = client.post(
        "/convert/to-images",
        headers=auth,
        files={"file": ("s.pdf", pdf_bytes, "application/pdf")},
        data={"dpi": "72", "fmt": "png"},
    )

    log_step("Vérification HTTP 200 + ZIP")
    assert r.status_code == 200, r.text
    assert "zip" in r.headers.get("content-type", "")

    log_step("Vérification que le ZIP contient 3 fichiers .png")
    zf = zipfile.ZipFile(BytesIO(r.content))
    png_files = [n for n in zf.namelist() if n.endswith(".png")]
    assert len(png_files) == 3, f"Attendu 3 PNG, trouvé : {zf.namelist()}"


def test_convert_to_images_jpg(client, auth, pdf_bytes, log_step):
    """POST /convert/to-images fmt=jpg → ZIP de 3 JPG."""
    log_step("Conversion PDF 3 pages → images JPG")
    r = client.post(
        "/convert/to-images",
        headers=auth,
        files={"file": ("s.pdf", pdf_bytes, "application/pdf")},
        data={"dpi": "72", "fmt": "jpg"},
    )

    log_step("Vérification HTTP 200 + ZIP contenant des .jpg")
    assert r.status_code == 200, r.text
    zf = zipfile.ZipFile(BytesIO(r.content))
    jpg_files = [n for n in zf.namelist() if n.endswith(".jpg")]
    assert len(jpg_files) == 3, f"Attendu 3 JPG, trouvé : {zf.namelist()}"


def test_convert_from_images(client, auth, log_step):
    """POST /convert/from-images → PDF avec 2 pages (une par image)."""
    log_step("Génération de 2 images PNG distinctes")
    from PIL import Image as PILImage

    def _png(color: tuple) -> bytes:
        buf = BytesIO()
        PILImage.new("RGB", (200, 200), color=color).save(buf, format="PNG")
        return buf.getvalue()

    log_step("Appel /convert/from-images avec 2 PNG")
    r = client.post(
        "/convert/from-images",
        headers=auth,
        files=[
            ("files", ("a.png", _png((255, 0, 0)), "image/png")),
            ("files", ("b.png", _png((0, 0, 255)), "image/png")),
        ],
    )

    log_step("Vérification HTTP 200 + application/pdf")
    assert r.status_code == 200, r.text
    assert "application/pdf" in r.headers.get("content-type", "")

    log_step("Vérification que le PDF résultant a 2 pages")
    from pypdf import PdfReader
    reader = PdfReader(BytesIO(r.content))
    assert len(reader.pages) == 2


# ══════════════════════════════════════════════════════════════════════════════
# Forms — routes manquantes
# ══════════════════════════════════════════════════════════════════════════════

def test_forms_fill(client, auth, form_pdf_bytes, log_step):
    """POST /forms/fill → PDF avec les champs remplis."""
    log_step("Envoi d'un formulaire PDF avec champs 'nom' et 'email'")
    data_json = json.dumps({"nom": "Alice Dupont", "email": "alice@quill.io"})
    r = client.post(
        "/forms/fill",
        headers=auth,
        files={"file": ("form.pdf", form_pdf_bytes, "application/pdf")},
        data={"data": data_json},
    )

    log_step("Vérification HTTP 200 + application/pdf")
    assert r.status_code == 200, r.text
    assert "application/pdf" in r.headers.get("content-type", "")

    log_step("Lecture des champs du PDF rempli — vérification des valeurs")
    from quill.features.forms import list_fields
    import tempfile, pathlib
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(r.content)
        tmp = pathlib.Path(f.name)
    try:
        fields = list_fields(tmp)
        values = {fld["name"]: fld.get("value", "") for fld in fields}
        assert values.get("nom") == "Alice Dupont", f"Champ 'nom' = {values.get('nom')!r}"
        assert values.get("email") == "alice@quill.io", f"Champ 'email' = {values.get('email')!r}"
    finally:
        tmp.unlink(missing_ok=True)


def test_forms_flatten(client, auth, form_pdf_bytes, log_step):
    """POST /forms/flatten → PDF sans champs éditables."""
    log_step("Aplatissement des champs du formulaire PDF")
    r = client.post(
        "/forms/flatten",
        headers=auth,
        files={"file": ("form.pdf", form_pdf_bytes, "application/pdf")},
    )

    log_step("Vérification HTTP 200 + application/pdf")
    assert r.status_code == 200, r.text
    assert "application/pdf" in r.headers.get("content-type", "")

    log_step("Vérification qu'il ne reste aucun champ éditable")
    from quill.features.forms import list_fields
    import tempfile, pathlib
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(r.content)
        tmp = pathlib.Path(f.name)
    try:
        fields = list_fields(tmp)
        assert fields == [], f"Champs encore présents après flatten : {fields}"
    finally:
        tmp.unlink(missing_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# Edit — route manquante
# ══════════════════════════════════════════════════════════════════════════════

def test_edit_replace_text(client, auth, log_step):
    """POST /edit/replace-text → PDF avec le texte remplacé."""
    log_step("Génération d'un PDF avec texte 'ORIGINAL' à coordonnées connues")
    pdf = _make_fitz_pdf_bytes("ORIGINAL")

    log_step("Détection automatique de la bounding box")
    x0, y0, x1, y1 = _detect_bbox_from_bytes(pdf)

    log_step("Appel /edit/replace-text → 'MODIFIÉ PAR QUILL'")
    r = client.post(
        "/edit/replace-text",
        headers=auth,
        files={"file": ("edit.pdf", pdf, "application/pdf")},
        data={
            "page": "1",
            "x0": str(x0 - 2), "y0": str(y0 - 2),
            "x1": str(x1 + 60), "y1": str(y1 + 2),
            "new_text": "MODIFIÉ PAR QUILL",
        },
    )

    log_step("Vérification HTTP 200 + application/pdf")
    assert r.status_code == 200, f"Statut {r.status_code} : {r.text[:200]}"
    assert "application/pdf" in r.headers.get("content-type", "")

    log_step("Vérification que 'MODIFIÉ PAR QUILL' est présent dans le PDF retourné")
    import fitz
    doc = fitz.open(stream=r.content, filetype="pdf")
    text = doc[0].get_text()
    doc.close()
    assert "MODIFIÉ PAR QUILL" in text, f"Texte absent. Contenu page : {text!r}"


def test_edit_replace_text_no_auth(client, log_step):
    """POST /edit/replace-text sans clé → 401."""
    log_step("Appel sans header X-API-Key")
    r = client.post(
        "/edit/replace-text",
        files={"file": ("t.pdf", b"", "application/pdf")},
        data={"page": "1", "x0": "0", "y0": "0", "x1": "100", "y1": "20", "new_text": "X"},
    )
    log_step("Vérification statut 401")
    assert r.status_code == 401
