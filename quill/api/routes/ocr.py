"""API routes — Phase 5: OCR."""

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from quill.api.deps import parse_pages, pdf_response, workdir

router = APIRouter(prefix="/ocr", tags=["OCR"])


@router.post("/pdf-to-images", summary="Convert PDF pages to images (ZIP)")
async def pdf_to_images(
    file: UploadFile = File(...),
    fmt: str = Form("png"),
    dpi: int = Form(150),
    pages: str | None = Form(None),
):
    import zipfile

    from quill.features.ocr import pdf_to_images as _p2i

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        img_dir = tmp / "images"
        imgs = _p2i(src, img_dir, dpi=dpi, fmt=fmt, pages=parse_pages(pages))
        zip_path = tmp / "pages.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for p in imgs:
                zf.write(p, p.name)
        from quill.api.deps import file_response

        return file_response(zip_path, "pages.zip", "application/zip")


@router.post("/ocr", summary="OCR a scanned PDF to searchable PDF + text")
async def ocr_pdf(
    file: UploadFile = File(...),
    lang: str = Form("fra+eng"),
    dpi: int = Form(300),
    deskew: bool = Form(True),
    denoise: bool = Form(False),
    pages: str | None = Form(None),
):
    from quill.features.ocr import ocr_pdf as _ocr

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        out = tmp / "searchable.pdf"
        text = _ocr(src, out, lang=lang, dpi=dpi, deskew=deskew, denoise=denoise, pages=parse_pages(pages))
        if out.exists():
            return pdf_response(out, "searchable.pdf")
        return JSONResponse({"text": text})
