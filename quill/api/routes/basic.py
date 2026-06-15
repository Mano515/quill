"""API routes — Phase 1: basic operations."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from quill.api.deps import parse_pages, parse_ranges, pdf_response, workdir

router = APIRouter(prefix="/basic", tags=["Basic"])


@router.post("/merge", summary="Merge multiple PDFs")
async def merge(files: list[UploadFile] = File(...)) -> FileResponse:
    from quill.features.basic import merge as _merge

    with workdir() as tmp:
        inputs = []
        for i, f in enumerate(files):
            p = tmp / f"input_{i}.pdf"
            p.write_bytes(await f.read())
            inputs.append(p)
        out = tmp / "merged.pdf"
        _merge(inputs, out)
        return pdf_response(out, "merged.pdf")


@router.post("/split", summary="Split a PDF into parts")
async def split(
    file: UploadFile = File(...),
    ranges: str | None = Form(None, description="e.g. '1-3,5-7' — omit for one file per page"),
) -> FileResponse:
    import zipfile
    from quill.features.basic import split as _split

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        page_ranges = parse_ranges(ranges)
        parts = _split(src, tmp / "parts", page_ranges)

        zip_path = tmp / "split.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for p in parts:
                zf.write(p, p.name)

        from fastapi.responses import FileResponse as FR
        return FR(str(zip_path), media_type="application/zip", filename="split.zip")


@router.post("/rotate", summary="Rotate pages")
async def rotate(
    file: UploadFile = File(...),
    degrees: int = Form(90, description="90 | 180 | 270"),
    pages: str | None = Form(None, description="e.g. '1,3' — omit for all"),
) -> FileResponse:
    from quill.features.basic import rotate as _rotate

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        out = tmp / "rotated.pdf"
        _rotate(src, out, degrees, parse_pages(pages))
        return pdf_response(out, "rotated.pdf")


@router.post("/reorder", summary="Reorder pages")
async def reorder(
    file: UploadFile = File(...),
    order: str = Form(..., description="e.g. '3,1,2'"),
) -> FileResponse:
    from quill.features.basic import reorder as _reorder

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        out = tmp / "reordered.pdf"
        _reorder(src, out, [int(p) for p in order.split(",")])
        return pdf_response(out, "reordered.pdf")


@router.post("/delete-pages", summary="Delete specific pages")
async def delete_pages(
    file: UploadFile = File(...),
    pages: str = Form(..., description="e.g. '2,4,6'"),
) -> FileResponse:
    from quill.features.basic import delete_pages as _delete

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        out = tmp / "output.pdf"
        _delete(src, out, [int(p) for p in pages.split(",")])
        return pdf_response(out, "output.pdf")


@router.post("/extract-text", summary="Extract plain text")
async def extract_text(
    file: UploadFile = File(...),
    pages: str | None = Form(None),
) -> JSONResponse:
    from quill.features.basic import extract_text as _extract

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        result = _extract(src, parse_pages(pages))
        return JSONResponse({"pages": {str(k): v for k, v in result.items()}})


@router.post("/info", summary="Get PDF metadata")
async def info(file: UploadFile = File(...)) -> JSONResponse:
    from quill.features.basic import get_metadata

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        meta = get_metadata(src)
        return JSONResponse(meta)
