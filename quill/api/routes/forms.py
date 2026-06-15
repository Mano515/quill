"""API routes — Phase 6: forms."""

import json

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from quill.api.deps import pdf_response, workdir

router = APIRouter(prefix="/forms", tags=["Forms"])


@router.post("/list", summary="List form fields in a PDF")
async def list_fields(file: UploadFile = File(...)):
    from quill.features.forms import list_fields as _list

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        return JSONResponse(_list(src))


@router.post("/fill", summary="Fill form fields")
async def fill_form(
    file: UploadFile = File(...),
    data: str = Form(..., description='JSON object e.g. {"name": "Alice", "email": "alice@x.com"}'),
):
    from quill.features.forms import fill_form as _fill

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        out = tmp / "filled.pdf"
        _fill(src, out, json.loads(data))
        return pdf_response(out, "filled.pdf")


@router.post("/flatten", summary="Flatten form fields")
async def flatten_form(file: UploadFile = File(...)):
    from quill.features.forms import flatten_form as _flatten

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        out = tmp / "flattened.pdf"
        _flatten(src, out)
        return pdf_response(out, "flattened.pdf")


@router.post("/create", summary="Create an interactive form from JSON spec")
async def create_form(
    fields: str = Form(..., description="JSON array of field definitions"),
):
    from quill.features.forms import create_form as _create

    with workdir() as tmp:
        out = tmp / "form.pdf"
        _create(out, json.loads(fields))
        return pdf_response(out, "form.pdf")
