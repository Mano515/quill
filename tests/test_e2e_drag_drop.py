"""
E2E — Drag & Drop via Playwright.

Lance le serveur Quill en sous-processus, ouvre Chromium, simule un dépôt
de fichier par drag & drop sur la page d'accueil et dans un panneau opération,
et vérifie le comportement attendu.

Nécessite :  pip install pytest-playwright playwright
             python -m playwright install chromium
"""
from __future__ import annotations

import subprocess
import sys
import time
import tempfile
from io import BytesIO
from pathlib import Path

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

BASE_URL = "http://127.0.0.1:8080"
SERVER_STARTUP_TIMEOUT = 10  # secondes


def _make_simple_pdf() -> bytes:
    """PDF minimal d'une page pour les tests."""
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    doc.build([Paragraph("Fichier de test Quill — drag & drop", styles["Normal"])])
    return buf.getvalue()


def _wait_for_server(url: str, timeout: int) -> bool:
    """Attend que le serveur réponde (polling)."""
    import urllib.request, urllib.error
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.4)
    return False


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def quill_server():
    """Démarre le serveur Quill en sous-processus pour toute la durée du module."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "quill.server"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if not _wait_for_server(BASE_URL, SERVER_STARTUP_TIMEOUT):
        proc.terminate()
        pytest.skip("Serveur Quill non disponible — test ignoré")
    yield proc
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="module")
def sample_pdf(tmp_path_factory) -> Path:
    """PDF temporaire réutilisé dans tous les tests du module."""
    p = tmp_path_factory.mktemp("e2e") / "test_drag.pdf"
    p.write_bytes(_make_simple_pdf())
    return p


# ── Helpers Playwright ────────────────────────────────────────────────────────

def _login(page, api_key: str):
    """Injecte la clé API dans le localStorage, recharge et attend l'accueil."""
    page.evaluate(f"localStorage.setItem('quill_api_key', '{api_key}')")
    page.reload()
    # boot() fait un fetch async vers /auth/login avant d'appeler showApp() ;
    # on attend que #app reçoive la classe "visible".
    page.wait_for_selector("#app.visible", timeout=10000)
    # dbGet('inputFile') peut charger un fichier et changer de panel ;
    # on force le retour à l'accueil pour que les tests partent d'un état stable.
    page.evaluate("if (typeof activate === 'function') activate('__home')")
    # state="attached" : on vérifie que le panel est dans le DOM avec la classe
    # active, sans exiger la visibilité CSS (l'ancêtre #app peut avoir un
    # display calculé non visible selon le contexte de test Playwright).
    page.wait_for_selector("#panel-__home.active", state="attached", timeout=5000)


def _drag_drop_file(page, selector: str, file_path: Path):
    """
    Simule un drag & drop de fichier sur un élément DOM.

    Playwright n'expose pas nativement le drag & drop depuis le système de
    fichiers ; on utilise l'API DataTransfer injectée en JS pour reproduire
    fidèlement ce que fait le navigateur.
    """
    mime = "application/pdf"
    data_b64 = __import__("base64").b64encode(file_path.read_bytes()).decode()

    js = f"""
    async (selector) => {{
        const el = document.querySelector(selector);
        if (!el) throw new Error('Élément introuvable : ' + selector);

        // Reconstruit un File depuis les octets base64
        const b64 = '{data_b64}';
        const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
        const file = new File([bytes], '{file_path.name}', {{type: '{mime}'}});

        const dt = new DataTransfer();
        dt.items.add(file);

        const opts = {{ bubbles: true, cancelable: true, dataTransfer: dt }};
        el.dispatchEvent(new DragEvent('dragenter', opts));
        el.dispatchEvent(new DragEvent('dragover',  opts));
        el.dispatchEvent(new DragEvent('drop',      opts));
        window.dispatchEvent(new DragEvent('drop',  opts));
    }}
    """
    page.evaluate(js, selector)


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.e2e
class TestDragDrop:
    """Suite E2E — drag & drop de fichiers PDF."""

    def test_server_reachable(self, quill_server):
        """Le serveur Quill démarre et répond sur le port 8080."""
        import urllib.request
        with urllib.request.urlopen(BASE_URL, timeout=3) as r:
            assert r.status == 200, f"Statut inattendu : {r.status}"

    def test_homepage_loads(self, quill_server, page):
        """La page d'accueil se charge sans erreur JS."""
        from quill.api.auth import API_KEY
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(BASE_URL)
        _login(page, API_KEY)
        page.wait_for_selector("#panel-__home.active", state="attached", timeout=5000)
        assert not errors, f"Erreurs JS au chargement : {errors}"

    def test_overlay_shows_on_dragenter(self, quill_server, page):
        """L'overlay global apparaît quand un fichier entre dans la fenêtre."""
        from quill.api.auth import API_KEY
        page.goto(BASE_URL)
        _login(page, API_KEY)
        page.wait_for_selector("#panel-__home.active", state="attached")

        page.evaluate("""
            const dt = new DataTransfer();
            dt.items.add(new File([''], 'test.pdf', {type:'application/pdf'}));
            const opts = {bubbles:true, cancelable:true, dataTransfer:dt};
            window.dispatchEvent(new DragEvent('dragenter', opts));
        """)

        overlay = page.locator("#drag-overlay")
        overlay.wait_for(state="visible", timeout=2000)
        assert overlay.is_visible(), "L'overlay drag & drop devrait être visible"

    def test_overlay_hides_on_drop(self, quill_server, page, sample_pdf):
        """L'overlay disparaît après un drop."""
        from quill.api.auth import API_KEY
        page.goto(BASE_URL)
        _login(page, API_KEY)
        page.wait_for_selector("#panel-__home.active", state="attached")

        _drag_drop_file(page, "#home-hero", sample_pdf)
        page.wait_for_timeout(300)

        overlay = page.locator("#drag-overlay")
        assert not overlay.is_visible(), "L'overlay devrait se fermer après le drop"

    def test_drop_on_home_loads_file(self, quill_server, page, sample_pdf):
        """Déposer un PDF sur l'accueil charge le fichier dans l'aperçu."""
        from quill.api.auth import API_KEY
        page.goto(BASE_URL)
        _login(page, API_KEY)
        page.wait_for_selector("#panel-__home.active", state="attached")

        _drag_drop_file(page, "#home-hero", sample_pdf)
        # Le nom du fichier doit apparaître dans le header de prévisualisation
        page.wait_for_selector(f"#preview-filename:has-text('{sample_pdf.name}')", timeout=5000)
        filename = page.locator("#preview-filename").inner_text()
        assert sample_pdf.name in filename, f"Nom attendu '{sample_pdf.name}', obtenu '{filename}'"

    def test_drop_on_home_renders_pdf(self, quill_server, page, sample_pdf):
        """Après le drop, le canvas PDF est dessiné dans l'aperçu."""
        from quill.api.auth import API_KEY
        page.goto(BASE_URL)
        _login(page, API_KEY)
        page.wait_for_selector("#panel-__home.active", state="attached")

        _drag_drop_file(page, "#home-hero", sample_pdf)
        # Un <canvas> doit apparaître dans le corps de l'aperçu
        page.wait_for_selector("#preview-body canvas", timeout=6000)
        canvas = page.locator("#preview-body canvas")
        assert canvas.count() > 0, "Aucun canvas rendu dans l'aperçu"

    def test_drop_on_panel_loads_file(self, quill_server, page, sample_pdf):
        """Déposer un PDF dans la zone d'une opération charge le fichier."""
        from quill.api.auth import API_KEY
        page.goto(BASE_URL)
        _login(page, API_KEY)

        # En home-mode la colonne nav est masquée (grid 1fr sans sidebar nav).
        # On active le panel merge directement via JS pour contourner ce comportement.
        # activate() est dans un module ES — pas accessible via window.
        # On reproduit son effet directement : retirer home-mode, activer le panel.
        page.evaluate("""() => {
            document.querySelector('.panel.active')?.classList.remove('active');
            document.querySelector('.layout')?.classList.remove('home-mode');
            document.getElementById('panel-merge')?.classList.add('active');
        }""")
        page.wait_for_selector("#panel-merge.active", state="attached", timeout=4000)

        # Dépose sur la première drop-zone du panneau actif
        _drag_drop_file(page, "#panel-merge .drop-zone", sample_pdf)

        # Le nom du fichier doit apparaître dans un item de la liste
        page.wait_for_selector(
            f"#panel-merge .dz-file-item",
            timeout=5000,
        )
        items_text = page.locator("#panel-merge .dz-file-item").all_inner_texts()
        names = " ".join(items_text)
        assert sample_pdf.name in names, (
            f"Le fichier '{sample_pdf.name}' devrait apparaître dans la drop zone, "
            f"obtenu : {names!r}"
        )
