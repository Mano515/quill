"""API routes — Phase 7: conversions."""

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from quill.api.deps import pdf_response, workdir

router = APIRouter(prefix="/convert", tags=["Convert"])


@router.post("/to-images", summary="Convert PDF pages to PNG images (zip)")
async def to_images(
    file: UploadFile = File(...),
    dpi: int = Form(150),
    fmt: str = Form("png", description="png | jpg"),
):
    import zipfile
    from quill.features.convert import pdf_to_png, pdf_to_jpg

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        out_dir = tmp / "pages"

        saved = pdf_to_jpg(src, out_dir, dpi=dpi) if fmt == "jpg" else pdf_to_png(src, out_dir, dpi=dpi)

        zip_path = tmp / "pages.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for p in saved:
                zf.write(p, p.name)
        return FileResponse(str(zip_path), media_type="application/zip", filename="pages.zip")


@router.post("/from-images", summary="Combine images into a PDF")
async def from_images(files: list[UploadFile] = File(...)):
    from quill.features.convert import images_to_pdf

    with workdir() as tmp:
        imgs = []
        for i, f in enumerate(files):
            p = tmp / f"img_{i}{_ext(f.filename)}"
            p.write_bytes(await f.read())
            imgs.append(p)
        out = tmp / "combined.pdf"
        images_to_pdf(imgs, out)
        return pdf_response(out, "combined.pdf")


@router.post("/to-markdown", summary="Convert PDF to Markdown")
async def to_markdown(file: UploadFile = File(...)):
    from quill.features.convert import pdf_to_markdown

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        out = tmp / "doc.md"
        pdf_to_markdown(src, out)
        return FileResponse(str(out), media_type="text/markdown", filename="doc.md")


@router.post("/to-json", summary="Convert PDF text layout to JSON")
async def to_json(
    file: UploadFile = File(...),
    pages: str | None = Form(None),
):
    from quill.features.convert import pdf_to_json
    from quill.api.deps import parse_pages

    with workdir() as tmp:
        src = tmp / "input.pdf"
        src.write_bytes(await file.read())
        result = pdf_to_json(src, pages=parse_pages(pages))
        return JSONResponse(result)


def _ext(filename: str | None) -> str:
    if not filename:
        return ".png"
    return "." + filename.rsplit(".", 1)[-1] if "." in filename else ".png"
