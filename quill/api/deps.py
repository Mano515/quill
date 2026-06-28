"""Shared utilities for API routes: temp directory management and response helpers."""

import tempfile
from contextlib import contextmanager
from pathlib import Path

from fastapi.responses import Response


@contextmanager
def workdir():
    """Yield a temporary directory as a Path, then delete it on exit."""
    with tempfile.TemporaryDirectory(prefix="quill_") as tmp:
        yield Path(tmp)


def _make_response(path: Path, filename: str, media_type: str) -> Response:
    """
    Read a file into memory and return an HTTP Response.

    We read eagerly here (instead of using FileResponse) because the caller
    always runs inside a `with workdir()` block. FileResponse is lazy — it
    reads the file when the ASGI server sends the response, which is *after*
    the workdir context has already deleted the temp directory.
    """
    return Response(
        content=path.read_bytes(),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def pdf_response(path: Path, filename: str) -> Response:
    """Return a PDF file as a downloadable HTTP response."""
    return _make_response(path, filename, "application/pdf")


def file_response(path: Path, filename: str, media_type: str = "application/octet-stream") -> Response:
    """Return any file as a downloadable HTTP response."""
    return _make_response(path, filename, media_type)


def parse_pages(pages_str: str | None) -> list[int] | None:
    """Parse a comma-separated page string ('1,3,5') into a list of ints. None means all pages."""
    if not pages_str:
        return None
    return [int(p.strip()) for p in pages_str.split(",") if p.strip()]


def parse_ranges(ranges_str: str | None) -> list[tuple[int, int]] | None:
    """
    Parse a range string ('1-3,5,7-9') into a list of (start, end) tuples.
    A single page like '5' becomes (5, 5). None means the whole document.
    """
    if not ranges_str:
        return None
    result = []
    for part in ranges_str.split(","):
        part = part.strip()
        if "-" in part:
            s, e = part.split("-", 1)
            result.append((int(s), int(e)))
        else:
            result.append((int(part), int(part)))
    return result
