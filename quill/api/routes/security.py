"""API routes — Phase 2: security."""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from quill.api.deps import pdf_response, workdir

router = APIRouter(prefix="/security", tags=["Security"])


@router.post("/encrypt", summary="Encrypt a PDF")
async def encrypt(
    file: UploadFile = File(...),
    password: str = Form(...),
    owner_password: str | None = Form(None),
    allow_printing: bool = Form(True),
    allow_copying: bool = Form(True),
    allow_modifying: bool = Form(True),
):
    from quill.features.security import encrypt as _encrypt

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        out = tmp / "encrypted.pdf"
        _encrypt(src, out, password, owner_password, allow_printing, allow_copying, allow_modifying)
        return pdf_response(out, "encrypted.pdf")


@router.post("/decrypt", summary="Remove password from a PDF")
async def decrypt(
    file: UploadFile = File(...),
    password: str = Form(...),
):
    from quill.features.security import decrypt as _decrypt

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        out = tmp / "decrypted.pdf"
        try:
            _decrypt(src, out, password)
        except ValueError:
            raise HTTPException(status_code=400, detail="Wrong password")
        return pdf_response(out, "decrypted.pdf")


@router.post("/info", summary="Security info about a PDF")
async def security_info(
    file: UploadFile = File(...),
    password: str | None = Form(None),
):
    from quill.features.security import check_security

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        info = check_security(src, password)
        return JSONResponse(info)
