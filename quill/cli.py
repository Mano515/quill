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


if __name__ == "__main__":
    app()
