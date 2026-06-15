"""Shared utilities for API routes: temp file management, response helpers."""

import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse


@contextmanager
def workdir():
    """Context manager that creates a temp directory and cleans it up after use."""
    with tempfile.TemporaryDirectory(prefix="quill_") as tmp:
        yield Path(tmp)


def pdf_response(path: Path, filename: str) -> FileResponse:
    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def file_response(path: Path, filename: str, media_type: str = "application/octet-stream") -> FileResponse:
    return FileResponse(
        path=str(path),
        media_type=media_type,
        filename=filename,
    )


def parse_pages(pages_str: str | None) -> list[int] | None:
    if not pages_str:
        return None
    return [int(p.strip()) for p in pages_str.split(",") if p.strip()]


def parse_ranges(ranges_str: str | None) -> list[tuple[int, int]] | None:
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
