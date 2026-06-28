"""
conftest.py — Configuration globale de la suite de tests Quill.

Fournit :
  • Factories PDF partagées (reportlab, fitz)
  • Fixture log_step  : journalisation étape par étape dans chaque test
  • Plugin QuillReporter : synthèse structurée par module en fin de session
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import datetime
from io import BytesIO

import pytest


# ══════════════════════════════════════════════════════════════════════════════
# Factories PDF
# ══════════════════════════════════════════════════════════════════════════════

def make_pdf_bytes(pages: int = 3, text_prefix: str = "Page") -> bytes:
    """PDF multi-pages généré avec ReportLab (texte pur)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate

    buf = BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    story: list = []
    for i in range(1, pages + 1):
        story.append(Paragraph(f"{text_prefix} {i} — Quill test", styles["Title"]))
        if i < pages:
            story.append(PageBreak())
    doc.build(story)
    return buf.getvalue()


def make_form_pdf_bytes() -> bytes:
    """PDF avec deux champs de formulaire texte (nom, email)."""
    from reportlab.lib.colors import black, white
    from reportlab.lib.pagesizes import A4
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


def make_table_pdf_bytes() -> bytes:
    """PDF contenant un tableau ReportLab (3 colonnes × 3 lignes)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    data = [["Nom", "Âge", "Ville"], ["Alice", "30", "Paris"], ["Bob", "25", "Lyon"]]
    t = Table(data)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)]))
    doc.build([t])
    return buf.getvalue()


def make_image_pdf_bytes() -> bytes:
    """PDF contenant une image PNG embarquée."""
    from io import BytesIO as _BIO

    from PIL import Image as PILImage
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import Image as RLImage, SimpleDocTemplate

    img_buf = _BIO()
    PILImage.new("RGB", (100, 100), color=(0, 128, 255)).save(img_buf, format="PNG")
    img_buf.seek(0)

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    doc.build([RLImage(img_buf, width=100, height=100)])
    return buf.getvalue()


def make_fitz_pdf_bytes(text: str = "TEXTE ORIGINAL") -> bytes:
    """PDF avec un bloc de texte à coordonnées exactes (PyMuPDF)."""
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(fitz.Point(100, 100), text, fontsize=14)
    buf = BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures de session partagées
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def shared_pdf_bytes() -> bytes:
    """PDF simple 3 pages, recalculé une seule fois par session."""
    return make_pdf_bytes(pages=3)


@pytest.fixture(scope="session")
def shared_form_pdf_bytes() -> bytes:
    return make_form_pdf_bytes()


@pytest.fixture(scope="session")
def shared_table_pdf_bytes() -> bytes:
    return make_table_pdf_bytes()


@pytest.fixture(scope="session")
def shared_image_pdf_bytes() -> bytes:
    return make_image_pdf_bytes()


# ══════════════════════════════════════════════════════════════════════════════
# Fixture log_step — journalisation étape par étape
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def log_step(request: pytest.FixtureRequest):
    """
    Journalise les étapes intermédiaires d'un test.

    Exemple d'utilisation ::

        def test_merge(log_step):
            log_step("Fusion de deux PDFs (2p + 3p)")
            result = merge(...)
            log_step("Vérification du nombre de pages résultant")
            assert page_count(result) == 5
    """
    logger = logging.getLogger(f"quill.step")

    def _step(msg: str) -> None:
        logger.info("    ↳ %s", msg)

    return _step


# ══════════════════════════════════════════════════════════════════════════════
# Plugin QuillReporter — synthèse terminal structurée
# ══════════════════════════════════════════════════════════════════════════════

class _QuillReporter:
    """
    Plugin pytest qui ajoute, après le résumé natif, un tableau de synthèse
    organisé par module avec durée par test et compteurs pass/fail/skip.
    """

    def pytest_terminal_summary(
        self,
        terminalreporter,  # noqa: ANN001
        exitstatus: int,
        config: pytest.Config,
    ) -> None:
        stats = terminalreporter.stats

        # Collecter uniquement les rapports de la phase "call"
        call_reports: list = []
        for outcome in ("passed", "failed", "skipped"):
            for rep in stats.get(outcome, []):
                if getattr(rep, "when", None) == "call":
                    call_reports.append(rep)
        for rep in stats.get("error", []):
            if getattr(rep, "when", None) in ("call", "setup"):
                call_reports.append(rep)

        if not call_reports:
            return

        # Regroupement par module
        by_module: dict[str, list] = defaultdict(list)
        for rep in sorted(call_reports, key=lambda r: r.nodeid):
            parts = rep.nodeid.replace("\\", "/").split("::")
            module = parts[0].split("/")[-1].removesuffix(".py")
            name = parts[-1]
            outcome = getattr(rep, "outcome", "error")
            duration = getattr(rep, "duration", 0.0)
            by_module[module].append((name, outcome, duration))

        # ── Écriture ──────────────────────────────────────────────────────────
        tw = terminalreporter._tw  # TerminalWriter

        tw.sep("═", "QUILL — SYNTHÈSE PAR MODULE")

        for module, entries in sorted(by_module.items()):
            n_pass = sum(1 for _, o, _ in entries if o == "passed")
            n_fail = sum(1 for _, o, _ in entries if o in ("failed", "error"))
            n_skip = sum(1 for _, o, _ in entries if o == "skipped")
            total_dur = sum(d for _, _, d in entries)

            module_icon = "✓" if n_fail == 0 else "✗"
            tw.write(f"\n  {module_icon} ", bold=True)
            tw.write(f"{module}", bold=True)
            tw.write(
                f"   {n_pass} passés · {n_fail} échoués · {n_skip} ignorés"
                f"   ({total_dur:.2f}s)\n",
                bold=False,
            )

            for name, outcome, duration in entries:
                icon = {"passed": "✓", "failed": "✗", "error": "✗", "skipped": "○"}.get(outcome, "?")
                color = {"passed": {"green": True}, "failed": {"red": True}, "error": {"red": True}, "skipped": {"yellow": True}}.get(outcome, {})
                label = name.replace("test_", "", 1).replace("_", " ")
                tw.write(f"      {icon}  ", **color)
                tw.write(f"{label:<50}")
                tw.write(f"  {duration:.3f}s\n", bold=False)

        tw.sep("═", "")


def pytest_configure(config: pytest.Config) -> None:
    config.pluginmanager.register(_QuillReporter(), "quill_reporter")
