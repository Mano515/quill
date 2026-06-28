"""API routes — text editing."""

from fastapi import APIRouter, File, Form, UploadFile

from quill.api.deps import pdf_response, workdir

router = APIRouter(prefix="/edit", tags=["Édition"])


@router.post("/replace-text", summary="Replace text inside a bounding box on a PDF page")
async def replace_text(
    file: UploadFile = File(...),
    page: int = Form(1),
    x0: float = Form(...),
    y0: float = Form(...),
    x1: float = Form(...),
    y1: float = Form(...),
    new_text: str = Form(...),
):
    from quill.features.edit import replace_text as _replace

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        out = tmp / "edited.pdf"
        _replace(src, out, page=page, x0=x0, y0=y0, x1=x1, y1=y1, new_text=new_text)
        return pdf_response(out, "edited.pdf")
