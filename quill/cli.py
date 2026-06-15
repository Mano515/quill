"""Quill CLI — entry point."""

from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.table import Table

app = typer.Typer(
    name="quill",
    help="Quill — PDF editor and processor.",
    no_args_is_help=True,
)

# ── Phase 1 ────────────────────────────────────────────────────────────────


@app.command()
def merge(
    inputs: list[Path] = typer.Argument(..., help="PDF files to merge"),
    output: Path = typer.Option(..., "-o", "--output", help="Output file"),
) -> None:
    """Merge multiple PDFs into one."""
    from quill.features.basic import merge as _merge

    _merge(inputs, output)
    rprint(f"[green]✓[/green] Merged {len(inputs)} files → {output}")


@app.command()
def split(
    input: Path = typer.Argument(..., help="PDF to split"),
    output_dir: Path = typer.Option(Path("."), "-o", "--output-dir", help="Output directory"),
    pages: Optional[str] = typer.Option(
        None, "-p", "--pages", help="Page ranges e.g. '1-3,5-7' (default: one file per page)"
    ),
) -> None:
    """Split a PDF into multiple files."""
    from quill.features.basic import split as _split

    ranges = None
    if pages:
        ranges = []
        for part in pages.split(","):
            part = part.strip()
            if "-" in part:
                s, e = part.split("-")
                ranges.append((int(s), int(e)))
            else:
                ranges.append((int(part), int(part)))

    results = _split(input, output_dir, ranges)
    for r in results:
        rprint(f"[green]✓[/green] {r}")


@app.command()
def rotate(
    input: Path = typer.Argument(..., help="PDF to rotate"),
    output: Path = typer.Option(..., "-o", "--output", help="Output file"),
    degrees: int = typer.Option(90, "-d", "--degrees", help="Rotation degrees (90, 180, 270)"),
    pages: Optional[str] = typer.Option(None, "-p", "--pages", help="Pages to rotate e.g. '1,3,5'"),
) -> None:
    """Rotate pages in a PDF."""
    from quill.features.basic import rotate as _rotate

    page_list = [int(p) for p in pages.split(",")] if pages else None
    _rotate(input, output, degrees, page_list)
    rprint(f"[green]✓[/green] Rotated → {output}")


@app.command()
def reorder(
    input: Path = typer.Argument(..., help="PDF to reorder"),
    output: Path = typer.Option(..., "-o", "--output", help="Output file"),
    order: str = typer.Option(..., "--order", help="New page order e.g. '3,1,2'"),
) -> None:
    """Reorder pages in a PDF."""
    from quill.features.basic import reorder as _reorder

    page_list = [int(p) for p in order.split(",")]
    _reorder(input, output, page_list)
    rprint(f"[green]✓[/green] Reordered → {output}")


@app.command(name="delete-pages")
def delete_pages(
    input: Path = typer.Argument(..., help="PDF to edit"),
    output: Path = typer.Option(..., "-o", "--output", help="Output file"),
    pages: str = typer.Option(..., "-p", "--pages", help="Pages to delete e.g. '2,4,6'"),
) -> None:
    """Delete specific pages from a PDF."""
    from quill.features.basic import delete_pages as _delete

    page_list = [int(p) for p in pages.split(",")]
    _delete(input, output, page_list)
    rprint(f"[green]✓[/green] Deleted pages {pages} → {output}")


@app.command(name="extract-text")
def extract_text(
    input: Path = typer.Argument(..., help="PDF to extract text from"),
    pages: Optional[str] = typer.Option(None, "-p", "--pages", help="Pages e.g. '1,2,3'"),
    output: Optional[Path] = typer.Option(None, "-o", "--output", help="Save to file"),
) -> None:
    """Extract plain text from a PDF."""
    from quill.features.basic import extract_text as _extract

    page_list = [int(p) for p in pages.split(",")] if pages else None
    result = _extract(input, page_list)

    full_text = "\n\n".join(f"--- Page {n} ---\n{t}" for n, t in sorted(result.items()))

    if output:
        output.write_text(full_text, encoding="utf-8")
        rprint(f"[green]✓[/green] Text saved → {output}")
    else:
        print(full_text)


@app.command()
def info(
    input: Path = typer.Argument(..., help="PDF to inspect"),
) -> None:
    """Show metadata and info about a PDF."""
    from quill.features.basic import get_metadata

    meta = get_metadata(input)

    table = Table(title=str(input), show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold cyan")
    table.add_column("Value")

    for key, value in meta.items():
        table.add_row(key.replace("_", " ").title(), str(value) if value is not None else "[dim]—[/dim]")

    rprint(table)


@app.command(name="create")
def create_pdf(
    text: Optional[str] = typer.Option(None, "--text", help="Text content"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Text file to import"),
    output: Path = typer.Option(..., "-o", "--output", help="Output PDF"),
    title: str = typer.Option("", "--title", help="Document title"),
) -> None:
    """Create a PDF from text."""
    from quill.features.basic import create_from_text

    if file:
        content = file.read_text(encoding="utf-8")
    elif text:
        content = text
    else:
        raise typer.BadParameter("Provide --text or --file")

    create_from_text(content, output, title=title)
    rprint(f"[green]✓[/green] Created → {output}")


# ── Phase 2 — Security ─────────────────────────────────────────────────────


@app.command()
def encrypt(
    input: Path = typer.Argument(..., help="PDF to encrypt"),
    output: Path = typer.Option(..., "-o", "--output", help="Output file"),
    password: str = typer.Option(..., "--password", "-p", help="User password", prompt=True, hide_input=True),
    owner_password: Optional[str] = typer.Option(None, "--owner-password", help="Owner password (defaults to user password)"),
    no_print: bool = typer.Option(False, "--no-print", help="Disallow printing"),
    no_copy: bool = typer.Option(False, "--no-copy", help="Disallow copying"),
    no_modify: bool = typer.Option(False, "--no-modify", help="Disallow modifying"),
) -> None:
    """Encrypt a PDF with a password."""
    from quill.features.security import encrypt as _encrypt

    _encrypt(input, output, password, owner_password,
             allow_printing=not no_print,
             allow_copying=not no_copy,
             allow_modifying=not no_modify)
    rprint(f"[green]✓[/green] Encrypted → {output}")


@app.command()
def decrypt(
    input: Path = typer.Argument(..., help="Encrypted PDF"),
    output: Path = typer.Option(..., "-o", "--output", help="Output file"),
    password: str = typer.Option(..., "--password", "-p", help="Password", prompt=True, hide_input=True),
) -> None:
    """Remove password protection from a PDF."""
    from quill.features.security import decrypt as _decrypt

    try:
        _decrypt(input, output, password)
        rprint(f"[green]✓[/green] Decrypted → {output}")
    except ValueError as e:
        rprint(f"[red]✗[/red] {e}")
        raise typer.Exit(1)


@app.command(name="security-info")
def security_info(
    input: Path = typer.Argument(..., help="PDF to inspect"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Password to test"),
) -> None:
    """Show security/encryption status of a PDF."""
    from quill.features.security import check_security

    info = check_security(input, password)
    for key, value in info.items():
        rprint(f"  [bold cyan]{key.replace('_', ' ').title()}:[/bold cyan] {value}")


# ── Phase 3 — Annotations ──────────────────────────────────────────────────


@app.command(name="add-text")
def add_text(
    input: Path = typer.Argument(..., help="PDF to annotate"),
    output: Path = typer.Option(..., "-o", "--output", help="Output file"),
    text: str = typer.Option(..., "--text", "-t", help="Text to add"),
    x: float = typer.Option(..., "--x", help="X position in points"),
    y: float = typer.Option(..., "--y", help="Y position in points"),
    pages: Optional[str] = typer.Option(None, "-p", "--pages", help="Pages e.g. '1,3'"),
    font_size: int = typer.Option(12, "--font-size"),
) -> None:
    """Overlay free text on pages at a given position."""
    from quill.features.annotations import add_text as _add_text

    page_list = [int(p) for p in pages.split(",")] if pages else None
    _add_text(input, output, text, x, y, page_list, font_size)
    rprint(f"[green]✓[/green] Text added → {output}")


@app.command(name="watermark")
def watermark(
    input: Path = typer.Argument(..., help="PDF to watermark"),
    output: Path = typer.Option(..., "-o", "--output", help="Output file"),
    text: Optional[str] = typer.Option(None, "--text", "-t", help="Watermark text"),
    image: Optional[Path] = typer.Option(None, "--image", "-i", help="Watermark image"),
    opacity: float = typer.Option(0.15, "--opacity", help="Opacity 0.0–1.0"),
    font_size: int = typer.Option(60, "--font-size"),
    angle: float = typer.Option(45.0, "--angle"),
) -> None:
    """Add a text or image watermark to every page."""
    from quill.features.annotations import add_watermark_text, add_watermark_image

    if image:
        add_watermark_image(input, output, image, opacity)
    elif text:
        add_watermark_text(input, output, text, opacity, font_size, angle=angle)
    else:
        rprint("[red]✗[/red] Provide --text or --image")
        raise typer.Exit(1)
    rprint(f"[green]✓[/green] Watermark added → {output}")


@app.command()
def stamp(
    input: Path = typer.Argument(..., help="PDF to stamp"),
    output: Path = typer.Option(..., "-o", "--output", help="Output file"),
    label: str = typer.Option("CONFIDENTIEL", "--label", "-l", help="Stamp text"),
    pages: Optional[str] = typer.Option(None, "-p", "--pages", help="Pages e.g. '1,2'"),
    font_size: int = typer.Option(48, "--font-size"),
) -> None:
    """Add a bold stamp (CONFIDENTIEL, APPROUVÉ…) to pages."""
    from quill.features.annotations import add_stamp

    page_list = [int(p) for p in pages.split(",")] if pages else None
    add_stamp(input, output, label, page_list, font_size=font_size)
    rprint(f"[green]✓[/green] Stamp '{label}' added → {output}")


@app.command(name="add-image")
def add_image_cmd(
    input: Path = typer.Argument(..., help="PDF"),
    output: Path = typer.Option(..., "-o", "--output", help="Output file"),
    image: Path = typer.Option(..., "--image", "-i", help="Image to insert"),
    x: float = typer.Option(..., "--x", help="X position"),
    y: float = typer.Option(..., "--y", help="Y position"),
    width: float = typer.Option(100.0, "--width", "-w"),
    height: float = typer.Option(100.0, "--height", "-h"),
    pages: Optional[str] = typer.Option(None, "-p", "--pages"),
) -> None:
    """Insert an image (logo, signature…) into pages."""
    from quill.features.annotations import add_image

    page_list = [int(p) for p in pages.split(",")] if pages else None
    add_image(input, output, image, x, y, width, height, page_list)
    rprint(f"[green]✓[/green] Image inserted → {output}")


@app.command(name="page-numbers")
def page_numbers(
    input: Path = typer.Argument(..., help="PDF"),
    output: Path = typer.Option(..., "-o", "--output", help="Output file"),
    position: str = typer.Option("bottom-center", "--position", help="bottom-center | bottom-right | top-center …"),
    prefix: str = typer.Option("", "--prefix", help="Text before number e.g. 'Page '"),
    suffix: str = typer.Option("", "--suffix", help="Text after number e.g. ' / 10'"),
    start: int = typer.Option(1, "--start", help="Starting page number"),
    font_size: int = typer.Option(10, "--font-size"),
) -> None:
    """Add page numbers to every page."""
    from quill.features.annotations import add_page_numbers

    add_page_numbers(input, output, position, font_size, prefix, suffix, start)
    rprint(f"[green]✓[/green] Page numbers added → {output}")


@app.command(name="comment")
def comment(
    input: Path = typer.Argument(..., help="PDF"),
    output: Path = typer.Option(..., "-o", "--output", help="Output file"),
    text: str = typer.Option(..., "--text", "-t", help="Comment content"),
    x: float = typer.Option(50.0, "--x"),
    y: float = typer.Option(50.0, "--y"),
    page: int = typer.Option(1, "--page", "-p"),
    author: str = typer.Option("Quill", "--author"),
) -> None:
    """Add a sticky-note comment annotation."""
    from quill.features.annotations import add_comment

    add_comment(input, output, text, x, y, page, author)
    rprint(f"[green]✓[/green] Comment added → {output}")


# ── Phase 4 — Extraction avancée ───────────────────────────────────────────


@app.command(name="extract-tables")
def extract_tables(
    input: Path = typer.Argument(..., help="PDF to extract tables from"),
    output: Optional[Path] = typer.Option(None, "-o", "--output", help="Output file (.csv or .xlsx)"),
    pages: Optional[str] = typer.Option(None, "-p", "--pages", help="Pages e.g. '1,3'"),
    fmt: str = typer.Option("csv", "--format", "-f", help="csv | excel"),
) -> None:
    """Extract tables from a PDF to CSV or Excel."""
    from quill.features.extraction import extract_tables as _extract

    page_list = [int(p) for p in pages.split(",")] if pages else None
    results = _extract(input, output, page_list, fmt)

    if not results:
        rprint("[yellow]No tables found.[/yellow]")
        return

    rprint(f"[green]✓[/green] Found {len(results)} table(s)")
    for r in results:
        rows = len(r["data"])
        cols = len(r["data"][0]) if r["data"] else 0
        rprint(f"  Page {r['page']} · Table {r['table_index']} · {rows}×{cols}")


@app.command(name="extract-images")
def extract_images(
    input: Path = typer.Argument(..., help="PDF to extract images from"),
    output_dir: Path = typer.Option(Path("."), "-o", "--output-dir"),
) -> None:
    """Extract all embedded images from a PDF."""
    from quill.features.extraction import extract_images as _extract

    saved = _extract(input, output_dir)
    rprint(f"[green]✓[/green] Extracted {len(saved)} image(s) → {output_dir}")
    for p in saved:
        rprint(f"  {p.name}")


@app.command(name="extract-links")
def extract_links(
    input: Path = typer.Argument(..., help="PDF to extract links from"),
    pages: Optional[str] = typer.Option(None, "-p", "--pages"),
) -> None:
    """Extract all hyperlinks from a PDF."""
    from quill.features.extraction import extract_links as _extract
    from rich.table import Table

    page_list = [int(p) for p in pages.split(",")] if pages else None
    links = _extract(input, page_list)

    if not links:
        rprint("[yellow]No links found.[/yellow]")
        return

    table = Table(show_header=True)
    table.add_column("Page", style="cyan")
    table.add_column("URL")
    for link in links:
        table.add_row(str(link["page"]), link["uri"])
    rprint(table)


@app.command(name="extract-fields")
def extract_fields(
    input: Path = typer.Argument(..., help="PDF with form fields"),
) -> None:
    """List all form fields and their values."""
    from quill.features.extraction import extract_form_fields
    from rich.table import Table

    fields = extract_form_fields(input)
    if not fields:
        rprint("[yellow]No form fields found.[/yellow]")
        return

    table = Table(show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Type")
    table.add_column("Value")
    for f in fields:
        table.add_row(f["name"], f["type"], str(f["value"] or ""))
    rprint(table)


@app.command(name="detect-lang")
def detect_lang(
    input: Path = typer.Argument(..., help="PDF to analyse"),
    pages: Optional[str] = typer.Option(None, "-p", "--pages"),
) -> None:
    """Detect the language of a PDF."""
    from quill.features.extraction import detect_language

    page_list = [int(p) for p in pages.split(",")] if pages else None
    result = detect_language(input, page_list)
    rprint(f"  [bold cyan]Language:[/bold cyan] {result['language']}")
    rprint(f"  [bold cyan]Confidence:[/bold cyan] {result['confidence']:.1%}")
    for page_num, lang in result["per_page"].items():
        rprint(f"  Page {page_num}: {lang}")


# ── Phase 5 — OCR ──────────────────────────────────────────────────────────


@app.command(name="ocr")
def ocr(
    input: Path = typer.Argument(..., help="Scanned PDF to process"),
    output: Path = typer.Option(..., "-o", "--output", help="Output searchable PDF"),
    lang: str = typer.Option("fra+eng", "--lang", "-l", help="Tesseract language(s) e.g. 'fra+eng'"),
    dpi: int = typer.Option(300, "--dpi"),
    deskew: bool = typer.Option(False, "--deskew", help="Auto-straighten tilted pages"),
    denoise: bool = typer.Option(False, "--denoise", help="Reduce image noise before OCR"),
    pages: Optional[str] = typer.Option(None, "-p", "--pages"),
    text_output: Optional[Path] = typer.Option(None, "--text", help="Also save extracted text"),
) -> None:
    """Run OCR on a scanned PDF and produce a searchable PDF."""
    from quill.features.ocr import ocr_pdf

    page_list = [int(p) for p in pages.split(",")] if pages else None
    text = ocr_pdf(input, output, lang=lang, dpi=dpi, deskew=deskew, denoise=denoise, pages=page_list)

    rprint(f"[green]✓[/green] Searchable PDF → {output}")
    if text_output:
        text_output.write_text(text, encoding="utf-8")
        rprint(f"[green]✓[/green] Text → {text_output}")


@app.command(name="pdf-to-images")
def pdf_to_images(
    input: Path = typer.Argument(..., help="PDF to convert"),
    output_dir: Path = typer.Option(Path("."), "-o", "--output-dir"),
    dpi: int = typer.Option(300, "--dpi"),
    fmt: str = typer.Option("png", "--format", "-f", help="png | jpg"),
    pages: Optional[str] = typer.Option(None, "-p", "--pages"),
) -> None:
    """Convert PDF pages to images."""
    from quill.features.ocr import pdf_to_images as _convert

    page_list = [int(p) for p in pages.split(",")] if pages else None
    saved = _convert(input, output_dir, dpi=dpi, fmt=fmt, pages=page_list)
    rprint(f"[green]✓[/green] {len(saved)} image(s) → {output_dir}")


# ── Phase 6 — Forms ────────────────────────────────────────────────────────


@app.command(name="list-fields")
def list_fields(
    input: Path = typer.Argument(..., help="PDF with form fields"),
) -> None:
    """List all interactive form fields in a PDF."""
    from quill.features.forms import list_fields as _list
    from rich.table import Table

    fields = _list(input)
    if not fields:
        rprint("[yellow]No form fields found.[/yellow]")
        return

    table = Table(show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Type")
    table.add_column("Value")
    table.add_column("Options")
    for f in fields:
        opts = ", ".join(f["options"]) if f["options"] else "—"
        table.add_row(f["name"], f["type"], str(f["value"] or ""), opts)
    rprint(table)


@app.command(name="fill-form")
def fill_form(
    input: Path = typer.Argument(..., help="PDF form to fill"),
    output: Path = typer.Option(..., "-o", "--output"),
    data: list[str] = typer.Option(..., "-d", "--data", help="Field=Value pairs e.g. -d name=Alice -d age=30"),
) -> None:
    """Fill form fields in a PDF. Pass -d field=value for each field."""
    from quill.features.forms import fill_form as _fill

    parsed = {}
    for item in data:
        if "=" not in item:
            rprint(f"[red]✗[/red] Invalid format '{item}', expected field=value")
            raise typer.Exit(1)
        k, v = item.split("=", 1)
        parsed[k.strip()] = v.strip()

    _fill(input, output, parsed)
    rprint(f"[green]✓[/green] Form filled → {output}")


@app.command(name="flatten-form")
def flatten_form(
    input: Path = typer.Argument(..., help="PDF form to flatten"),
    output: Path = typer.Option(..., "-o", "--output"),
) -> None:
    """Flatten a PDF form — make all fields non-editable."""
    from quill.features.forms import flatten_form as _flatten

    _flatten(input, output)
    rprint(f"[green]✓[/green] Form flattened → {output}")


@app.command(name="create-form")
def create_form(
    output: Path = typer.Option(..., "-o", "--output"),
    config: Path = typer.Option(..., "-c", "--config", help="JSON file describing form fields"),
) -> None:
    """Create an interactive PDF form from a JSON field definition."""
    import json
    from quill.features.forms import create_form as _create

    fields = json.loads(config.read_text(encoding="utf-8"))
    _create(output, fields)
    rprint(f"[green]✓[/green] Form created → {output}")


# ── Phase 7 — Conversions ──────────────────────────────────────────────────


@app.command(name="to-images")
def to_images(
    input: Path = typer.Argument(..., help="PDF to convert"),
    output_dir: Path = typer.Option(Path("."), "-o", "--output-dir"),
    fmt: str = typer.Option("png", "--format", "-f", help="png | jpg"),
    dpi: int = typer.Option(150, "--dpi"),
    quality: int = typer.Option(85, "--quality", help="JPEG quality (jpg only)"),
) -> None:
    """Convert PDF pages to PNG or JPEG images."""
    from quill.features.convert import pdf_to_png, pdf_to_jpg

    if fmt == "jpg":
        saved = pdf_to_jpg(input, output_dir, dpi=dpi, quality=quality)
    else:
        saved = pdf_to_png(input, output_dir, dpi=dpi)

    rprint(f"[green]✓[/green] {len(saved)} image(s) → {output_dir}")


@app.command(name="from-images")
def from_images(
    images: list[Path] = typer.Argument(..., help="Image files to combine"),
    output: Path = typer.Option(..., "-o", "--output"),
) -> None:
    """Combine images into a single PDF."""
    from quill.features.convert import images_to_pdf

    images_to_pdf(images, output)
    rprint(f"[green]✓[/green] {len(images)} image(s) → {output}")


@app.command(name="to-markdown")
def to_markdown(
    input: Path = typer.Argument(..., help="PDF to convert"),
    output: Optional[Path] = typer.Option(None, "-o", "--output", help="Save to .md file"),
) -> None:
    """Convert a PDF to Markdown."""
    from quill.features.convert import pdf_to_markdown

    md = pdf_to_markdown(input, output)
    if not output:
        print(md)
    else:
        rprint(f"[green]✓[/green] Markdown → {output}")


@app.command(name="to-json")
def to_json(
    input: Path = typer.Argument(..., help="PDF to convert"),
    output: Optional[Path] = typer.Option(None, "-o", "--output"),
    pages: Optional[str] = typer.Option(None, "-p", "--pages"),
) -> None:
    """Convert PDF text layout to structured JSON."""
    import json
    from quill.features.convert import pdf_to_json

    page_list = [int(p) for p in pages.split(",")] if pages else None
    result = pdf_to_json(input, output, page_list)

    if not output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        rprint(f"[green]✓[/green] JSON → {output}")


@app.command(name="to-word")
def to_word(
    input: Path = typer.Argument(..., help="PDF to convert"),
    output: Path = typer.Option(..., "-o", "--output", help="Output .docx file"),
) -> None:
    """Convert PDF to Word (.docx) via LibreOffice."""
    from quill.features.convert import pdf_to_word

    try:
        pdf_to_word(input, output)
        rprint(f"[green]✓[/green] Word document → {output}")
    except RuntimeError as e:
        rprint(f"[red]✗[/red] {e}")
        raise typer.Exit(1)


@app.command(name="from-word")
def from_word(
    input: Path = typer.Argument(..., help=".docx file to convert"),
    output: Path = typer.Option(..., "-o", "--output", help="Output .pdf file"),
) -> None:
    """Convert Word (.docx) to PDF via LibreOffice."""
    from quill.features.convert import word_to_pdf

    try:
        word_to_pdf(input, output)
        rprint(f"[green]✓[/green] PDF → {output}")
    except RuntimeError as e:
        rprint(f"[red]✗[/red] {e}")
        raise typer.Exit(1)


# ── Phase 8 — Signatures ───────────────────────────────────────────────────


@app.command(name="sign")
def sign_cmd(
    input: Path = typer.Argument(..., help="PDF to sign"),
    output: Path = typer.Option(..., "-o", "--output", help="Signed PDF"),
    name: str = typer.Option(..., "--name", "-n", help="Signer name"),
    reason: str = typer.Option("", "--reason", "-r", help="Reason / purpose"),
    location: str = typer.Option("", "--location", "-l", help="Location"),
    page: int = typer.Option(1, "--page", "-p", help="Page number (1-indexed)"),
    x: float = typer.Option(50, "--x", help="X position in points"),
    y: float = typer.Option(50, "--y", help="Y position in points"),
) -> None:
    """Add a visual signature stamp to a PDF."""
    from quill.features.sign import sign_pdf

    sign_pdf(input, output, name=name, reason=reason, location=location, page=page, x=x, y=y)
    rprint(f"[green]✓[/green] Signed → {output}")


@app.command(name="list-signatures")
def list_signatures_cmd(
    input: Path = typer.Argument(..., help="PDF to inspect"),
) -> None:
    """List signature annotations in a PDF."""
    from quill.features.sign import list_signatures

    sigs = list_signatures(input)
    if not sigs:
        rprint("[dim]No signature annotations found.[/dim]")
        return
    table = Table("Page", "Type", "Author", "Content")
    for s in sigs:
        table.add_row(str(s["page"]), s["type"], s["author"], s["content"][:60])
    rprint(table)


if __name__ == "__main__":
    app()
