"""API routes — Phase 8: signatures."""

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from quill.api.deps import parse_pages, pdf_response, workdir

router = APIRouter(prefix="/sign", tags=["Signatures"])


@router.post("/sign", summary="Add a visual signature stamp to a PDF page")
async def sign_pdf(
    file: UploadFile = File(...),
    name: str = Form(...),
    reason: str = Form(""),
    location: str = Form(""),
    page: int = Form(1),
    x: float = Form(50),
    y: float = Form(50),
    width: float = Form(220),
    height: float = Form(70),
):
    from quill.features.sign import sign_pdf as _sign

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        out = tmp / "signed.pdf"
        _sign(src, out, name=name, reason=reason, location=location, page=page, x=x, y=y, width=width, height=height)
        return pdf_response(out, "signed.pdf")


@router.post("/list", summary="List signature annotations in a PDF")
async def list_signatures(file: UploadFile = File(...)):
    from quill.features.sign import list_signatures as _list

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        return JSONResponse(_list(src))
